"""Reading config.json in led_interface.py, and changing it with set_config.py."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from support import REPO
import led_interface as li
import set_config


class ConfigFileTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, 'config.json')
        shutil.copy(os.path.join(REPO, 'config.json'), self.path)
        self.config_file = li.ConfigFile(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, text):
        with open(self.path, 'w') as fd:
            fd.write(text)

    def update(self, **changes):
        with open(self.path) as fd:
            raw = json.load(fd)
        raw.update(changes)
        self.write(json.dumps(raw))

    def test_repo_config_loads(self):
        values = self.config_file.reload()
        self.assertIn(values['mode'], li.MODES)
        self.assertIsInstance(values['runner_speed'], int)

    def test_text_numbers_and_bools_are_converted(self):
        self.update(runner_speed='3', shimmer='false', amplitude='0.5')
        with self.assertNoLogs('led_strips', 'WARNING'):
            values = self.config_file.reload()
        self.assertEqual((values['runner_speed'], values['shimmer'], values['amplitude']), (3, False, 0.5))

    def test_bad_values_keep_the_previous_value(self):
        before = self.config_file.reload()
        self.update(mode='disco', runner_speed='fast', global_brightness=float('nan'))
        with self.assertLogs('led_strips', 'WARNING'):
            values = self.config_file.reload()
        for key in ('mode', 'runner_speed', 'global_brightness'):
            self.assertEqual(values[key], before[key], key)

    def test_minimums(self):
        self.update(gif_delay=0, pulsewidth=-5, decay_len=0)
        values = self.config_file.reload()
        self.assertEqual((values['gif_delay'], values['pulsewidth'], values['decay_len']), (1, 1, 1))

    def test_missing_keys_use_defaults(self):
        self.write('{}')
        self.assertEqual(self.config_file.reload(), li.DEFAULT_CONFIG)

    def test_half_written_or_missing_file_keeps_previous_settings(self):
        before = self.config_file.reload()
        self.write('{"mode": "sta')
        with self.assertLogs('led_strips', 'WARNING'):
            self.assertEqual(self.config_file.reload(), before)
        os.remove(self.path)
        with self.assertLogs('led_strips', 'WARNING'):
            self.assertEqual(self.config_file.reload(), before)


class SetConfigTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, 'config.json')
        shutil.copy(os.path.join(REPO, 'config.json'), self.path)
        patcher = mock.patch.object(set_config, 'CONFIG_FILE', self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_set(self, key, value):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            set_config.set_config(key, value)
        return out.getvalue(), err.getvalue()

    def load(self):
        with open(self.path) as fd:
            return json.load(fd)

    def test_types_are_kept(self):
        for key, value in (('runner_speed', '3'), ('num_runners', '7'), ('shimmer', 'False'),
                           ('global_brightness', '0.5'), ('mode', 'static'), ('amplitude', '0.5')):
            self.run_set(key, value)
        data = self.load()
        self.assertIs(type(data['runner_speed']), int)
        self.assertEqual(data['runner_speed'], 3)
        self.assertEqual(data['num_runners'], 7)
        self.assertIs(data['shimmer'], False)
        self.assertEqual(data['global_brightness'], 0.5)
        self.assertEqual(data['mode'], 'static')
        self.assertEqual(data['amplitude'], 0.5)

    def test_invalid_values_leave_the_file_alone(self):
        with open(self.path) as fd:
            before = fd.read()
        for key, value in (('shimmer', 'maybe'), ('runner_speed', 'fast'), ('global_brightness', 'inf'),
                           ('runner_speed', 'nan'), ('amplitude', '-Infinity')):
            with self.subTest(key=key, value=value):
                with self.assertRaises(SystemExit) as raised:
                    self.run_set(key, value)
                self.assertNotEqual(raised.exception.code, 0)
                with open(self.path) as fd:
                    self.assertEqual(fd.read(), before)

    def test_unknown_key_is_ignored_with_a_warning(self):
        before = self.load()
        out, err = self.run_set('no_such_key', '1')
        self.assertIn('unknown key', err)
        self.assertEqual(self.load(), before)

    def test_file_format_and_no_leftover_temp_files(self):
        self.run_set('runner_speed', '4')
        with open(self.path) as fd:
            text = fd.read()
        self.assertEqual(text, json.dumps(json.loads(text), indent=4))
        self.assertEqual([f for f in os.listdir(self.tmp) if f.endswith('.tmp')], [])

    def test_needs_exactly_two_arguments(self):
        result = subprocess.run([sys.executable, os.path.join(REPO, 'set_config.py'), 'only_one'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
