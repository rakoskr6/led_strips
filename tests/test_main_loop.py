"""Runs led_interface.run() end to end with a fake Arduino and fake audio."""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

import serial

from support import REPO, StopRun, fake_pyaudio, fake_serial_class
import led_interface as li

FRAMES = 40


def run_lights(config_changes, silent=False):
    """Run the main loop for FRAMES frames in a scratch copy of the repo files."""
    work = tempfile.mkdtemp()
    try:
        for name in ('config.json', 'colorsettings.txt'):
            shutil.copy(os.path.join(REPO, name), work)
        shutil.copytree(os.path.join(REPO, 'images'), os.path.join(work, 'images'))
        config_path = os.path.join(work, 'config.json')
        with open(config_path) as fd:
            config = json.load(fd)
        config.update(config_changes)
        with open(config_path, 'w') as fd:
            json.dump(config, fd)

        writes, open_kwargs = [], []
        pyaudio = fake_pyaudio(silent)
        old_cwd = os.getcwd()
        os.chdir(work)
        try:
            with mock.patch.dict(sys.modules, {'pyaudio': pyaudio}), \
                    mock.patch.object(li.serial, 'Serial', fake_serial_class(FRAMES, writes, open_kwargs)), \
                    _quiet():
                try:
                    li.run()
                except StopRun:
                    pass
        finally:
            os.chdir(old_cwd)
        with open(os.path.join(work, 'status.log')) as fd:
            status = fd.read()
        return writes, open_kwargs, pyaudio.opened, status
    finally:
        shutil.rmtree(work, ignore_errors=True)


class _quiet:
    """Silence led_interface's log output while the main loop runs."""

    def __enter__(self):
        li.logging.disable(li.logging.CRITICAL)

    def __exit__(self, *exc):
        li.logging.disable(li.logging.NOTSET)


class MainLoopTest(unittest.TestCase):

    SCENARIOS = [
        ('music', {'mode': 'music'}, False),
        ('silence', {'mode': 'music'}, True),
        ('pulse with runners', {'mode': 'pulse', 'use_runners': True}, False),
        ('GIF with runners', {'mode': 'static', 'load_image': True, 'image_path': './images/swirl.gif',
                              'use_runners': True, 'shimmer': False}, False),
        ('PNG in music mode', {'mode': 'music', 'load_image': True, 'image_path': './images/kyle.png'}, False),
    ]

    def test_scenarios(self):
        for name, changes, silent in self.SCENARIOS:
            with self.subTest(name):
                writes, open_kwargs, opened, status = run_lights(changes, silent)

                # Serial port: right settings, opened exclusively.
                self.assertEqual(open_kwargs[0]['port'], '/dev/ttyACM0')
                self.assertEqual(open_kwargs[0]['baud'], 500000)
                self.assertIs(open_kwargs[0]['exclusive'], True)
                # Audio: 2 channels of float32 at 32 kHz, passed through to the output.
                self.assertEqual((opened[0]['format'], opened[0]['channels'], opened[0]['rate'],
                                  opened[0]['input'], opened[0]['output']),
                                 ('paFloat32', 2, 32000, True, True))

                # Starts with the resync burst, then waits for it to settle.
                self.assertEqual(writes[0][1], bytes([li.RESYNC_BYTE]) * li.FRAME_LENGTH)
                self.assertGreaterEqual(writes[1][0] - writes[0][0], li.RESYNC_SETTLE - 0.002)

                # Every frame is the command byte plus 1500 colour bytes, SHOW_GAP apart.
                frames = writes[1:FRAMES + 1]
                self.assertEqual(len(frames), FRAMES)
                for _, data in frames:
                    self.assertEqual(len(data), li.FRAME_LENGTH)
                    self.assertEqual(data[0], li.FRAME_COMMAND)
                gaps = [b[0] - a[0] for a, b in zip(frames, frames[1:])]
                self.assertGreaterEqual(min(gaps), li.SHOW_GAP - 0.001)

                # status.log: "<pid>\n<time>\n".
                pid, stamp, rest = status.split('\n')
                self.assertEqual((pid, rest), (str(os.getpid()), ''))
                self.assertLess(abs(int(stamp) - time.time()), 5)


class ArduinoTest(unittest.TestCase):

    def test_write_timeout_clears_output_and_resyncs(self):
        log = []

        class TimeoutSerial:
            def __init__(self, *args, **kwargs):
                self.fail = True

            def readline(self):
                return b''

            def write(self, data):
                log.append(('write', len(data), data[0]))
                if self.fail and data[0] == li.FRAME_COMMAND:
                    self.fail = False
                    raise serial.SerialTimeoutException('Write timeout')
                return len(data)

            def flush(self):
                log.append(('flush',))

            def reset_output_buffer(self):
                log.append(('reset',))

        with mock.patch.object(li.serial, 'Serial', TimeoutSerial), self.assertLogs('led_strips', 'INFO'):
            arduino = li.Arduino()
            arduino.send(bytes(li.FRAME_LENGTH))
            arduino.send(bytes(li.FRAME_LENGTH))
        self.assertEqual(log, [('write', 1501, 0), ('reset',), ('write', 1501, li.RESYNC_BYTE), ('flush',),
                               ('write', 1501, 0), ('flush',)])

    def test_second_copy_exits_if_port_is_busy(self):
        def busy(*args, **kwargs):
            raise serial.SerialException('Could not exclusively lock port /dev/ttyACM0')

        with mock.patch.object(li.serial, 'Serial', busy), self.assertLogs('led_strips', 'ERROR'):
            with self.assertRaises(SystemExit) as raised:
                li.Arduino()
        self.assertEqual(raised.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
