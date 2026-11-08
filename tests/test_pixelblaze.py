"""Pixelblaze connections run in the background and recover on their own."""

import json
import threading
import time
import unittest

import support  # noqa: F401  (puts the repo on sys.path)
import led_interface as li


class FakeWebSocket:
    def __init__(self, sent, fail_after):
        self.sent = sent
        self.fail_after = fail_after
        self.count = 0

    def send(self, payload):
        self.count += 1
        if self.count > self.fail_after:
            raise ConnectionError('gone')
        self.sent.append(json.loads(payload))

    def close(self):
        pass


class PixelBlazeTest(unittest.TestCase):

    def setUp(self):
        self.sent = []
        self.connects = []
        self.plan = ['ok']            # first connect works, later ones fail
        self.lock = threading.Lock()

    def connect(self, url, timeout):
        with self.lock:
            self.connects.append((url, time.monotonic()))
            outcome = self.plan.pop(0) if self.plan else 'down'
        if outcome == 'down':
            time.sleep(0.2)
            raise TimeoutError('timed out')
        return FakeWebSocket(self.sent, fail_after=3)

    def test_sends_never_block_and_reconnects_are_spaced_out(self):
        with self.assertLogs('led_strips', 'INFO'):
            pixelblaze = li.PixelBlaze('test', '1.2.3.4:81', connect=self.connect, retry_interval=1)
            time.sleep(0.2)
            start = time.monotonic()
            for _ in range(20):
                pixelblaze.send([(1, 0, 0), (0, 0.5, 0)], 1.0)
                time.sleep(0.05)
            elapsed = time.monotonic() - start
            time.sleep(3)

        # 20 sends with 50 ms sleeps; the sends themselves add almost nothing.
        self.assertLess(elapsed, 20 * 0.05 + 0.15)
        self.assertEqual(self.sent[0], {'setVars': {'adjust': 1.0, 'numColors': 2,
                                                    'colorList': [1.0, 0.0, 0.0, 0.0, 0.5, 0.0]}})
        self.assertEqual(self.connects[0][0], 'ws://1.2.3.4:81')
        # Lost after 3 sends: one immediate reconnect, then one per retry_interval.
        self.assertGreaterEqual(len(self.connects), 3)
        gaps = [b[1] - a[1] for a, b in zip(self.connects[1:], self.connects[2:])]
        self.assertTrue(all(gap >= 0.9 for gap in gaps), gaps)

    def test_start_pixelblazes_reads_network_cfg(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'network.cfg')
            with open(path, 'w') as fd:
                fd.write('[pixelblaze]\nenabled = false\naddress = 1.1.1.1:81\n'
                         '[pixelblaze_cabinets]\nenabled = true\n')
            with self.assertLogs('led_strips', 'INFO') as logs:
                self.assertEqual(li.start_pixelblazes(path), [])
        self.assertTrue(any('disabled' in r.getMessage() for r in logs.records))
        self.assertTrue(any('no address' in r.getMessage() for r in logs.records))


if __name__ == '__main__':
    unittest.main()
