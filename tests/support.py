"""Shared helpers for the tests. Nothing here touches real hardware."""

import os
import sys
import threading
import time
import types

import numpy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


class FakeStream:
    """Stands in for a PyAudio stream: feeds the callback from a thread."""

    def __init__(self, callback, silent):
        self.callback = callback
        self.silent = silent
        self.active = False

    def start_stream(self):
        self.active = True
        threading.Thread(target=self._feed, daemon=True).start()

    def _feed(self):
        rng = numpy.random.default_rng(1)
        t = 0
        while self.active:
            if self.silent:
                data = numpy.zeros(2048, numpy.float32)
            else:
                beat = 0.5 * (1 + numpy.sin(t / 5))
                data = (rng.normal(0, 0.1, 2048) * beat).astype(numpy.float32)
            self.callback(data.tobytes(), 1024, None, 0)
            t += 1
            time.sleep(0.03)

    def is_active(self):
        return self.active

    def stop_stream(self):
        self.active = False

    def close(self):
        self.active = False


def fake_pyaudio(silent=False):
    """A module object that can replace pyaudio in sys.modules."""
    opened = []

    class PyAudio:
        def open(self, **kwargs):
            opened.append(kwargs)
            return FakeStream(kwargs['stream_callback'], silent)

        def terminate(self):
            pass

    return types.SimpleNamespace(PyAudio=PyAudio, paFloat32='paFloat32', paContinue=0,
                                 opened=opened)


class StopRun(Exception):
    """Raised by the fake serial port to end led_interface.run()."""


def fake_serial_class(frames_wanted, writes, open_kwargs):
    """A serial.Serial replacement that records (time, bytes) for each write."""

    class FakeSerial:
        def __init__(self, port, baud, **kwargs):
            open_kwargs.append(dict(kwargs, port=port, baud=baud))

        def readline(self):
            return b'Program Started\r\n'

        def write(self, data):
            writes.append((time.monotonic(), bytes(data)))
            if len(writes) > frames_wanted:
                raise StopRun()
            return len(data)

        def flush(self):
            pass

        def reset_output_buffer(self):
            pass

        def close(self):
            pass

    return FakeSerial
