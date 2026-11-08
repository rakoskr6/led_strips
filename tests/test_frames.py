"""Frames sent to the Arduino, image mode, and the audio maths."""

import glob
import os
import unittest

import numpy

from support import REPO
import led_interface as li

FRAME_LENGTH = li.NUM_SUBPIXELS + 1


class ColourTest(unittest.TestCase):

    def test_to_byte_range_and_rounding(self):
        # 0.5 gives 127, not 128, exactly like the colour library the old code used.
        self.assertEqual([li.to_byte(v) for v in (0, 0.5, 0.6, 1, -1, 2)], [0, 127, 153, 255, 0, 255])

    @unittest.skipUnless(__import__('importlib').util.find_spec('colour'), 'colour library not installed')
    def test_to_byte_matches_old_colour_library(self):
        from colour import Color
        rng = numpy.random.default_rng(0)
        for _ in range(2000):
            rgb = tuple(float(v) for v in rng.random(3))
            old_hex = Color(rgb=rgb).hex_l[1:]
            old = [int(old_hex[i:i + 2], 16) for i in (0, 2, 4)]
            self.assertEqual([li.to_byte(v) for v in rgb], old, rgb)


class PatternFrameTest(unittest.TestCase):

    def setUp(self):
        self.config = dict(li.DEFAULT_CONFIG)

    def test_every_pattern_and_option_gives_a_full_frame(self):
        builder = li.FrameBuilder(numpy.random.default_rng(0))
        for pattern in range(len(li.PATTERNS)):
            for shimmer in (False, True):
                for runners in (False, True):
                    config = dict(self.config, shimmer=shimmer, use_runners=runners)
                    colors = li.pattern_colors(pattern, li.DEFAULT_CUSTOM_COLORS)
                    data = builder.build(colors, 0.7, config)
                    self.assertEqual(len(data), FRAME_LENGTH)
                    self.assertEqual(data[0], li.FRAME_COMMAND)

    def test_any_number_of_colours_fills_the_strip(self):
        builder = li.FrameBuilder()
        for count in range(1, 12):
            self.assertEqual(len(builder.build([(1, 0, 0)] * count, 1, self.config)), FRAME_LENGTH)

    def test_two_colour_pattern_alternates(self):
        data = li.FrameBuilder().build([(1, 0, 0), (0, 1, 0)], 1, self.config)
        self.assertEqual(data[1:7], bytes([255, 0, 0, 0, 255, 0]))
        self.assertEqual(data[-6:], bytes([255, 0, 0, 0, 255, 0]))

    def test_runners_wrap_and_move(self):
        config = dict(self.config, use_runners=True, num_runners=2, runner_length=3,
                      runner_distance=100, runner_speed=1)
        builder = li.FrameBuilder()
        builder.position = 498
        data = builder.build([(0, 0, 0)], 0.5, config)
        lit = [i for i in range(li.NUM_LEDS) if data[1 + 3 * i]]
        self.assertEqual(lit, [0, 98, 99, 100, 498, 499])
        self.assertEqual(data[1 + 3 * 498], min(255, 2 * int(255 * 0.5)))
        self.assertEqual(builder.position, 499)

    def test_pulse_is_a_triangle_wave(self):
        values = [round(li.pulse_brightness(p, 10), 2) for p in range(11)]
        self.assertEqual(values, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0])


class ImageTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.old_cwd = os.getcwd()
        os.chdir(REPO)
        cls.images = li.ImageFrames()

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.old_cwd)

    def test_every_image_gives_full_frames(self):
        config = dict(li.DEFAULT_CONFIG, load_image=True, num_runners=10)
        for path in sorted(glob.glob('images/*')):
            with self.subTest(path=path):
                frames = self.images.load(path)
                self.assertTrue(frames)
                self.assertTrue(all(len(f) == li.NUM_SUBPIXELS for f in frames))
                for runners in (False, True):
                    data = li.FrameBuilder().build([(1, 1, 1)], 0.8, dict(config, use_runners=runners), frames)
                    self.assertEqual(len(data), FRAME_LENGTH)

    def test_mapping_matches_the_old_pixel_by_pixel_code(self):
        from map import coord_index_map
        from PIL import Image
        xs = [c[0] for c in coord_index_map]
        ys = [c[1] for c in coord_index_map]
        min_x, min_y, max_x, max_y = min(xs), min(ys), max(xs), max(ys)
        for path in ('images/rainbowvert.png', 'images/smile.jpg', 'images/redblue.png'):
            with self.subTest(path=path):
                image = Image.open(path).convert('RGB')
                width, height = image.size
                expected = [0] * li.NUM_SUBPIXELS
                for (x, y), index in coord_index_map.items():
                    px = int((float(x - min_x) / float(max_x - min_x)) * float(width - 1))
                    py = int((float(y - min_y) / float(max_y - min_y)) * float(height - 1))
                    expected[index * 3:index * 3 + 3] = image.getpixel((px, py))
                self.assertEqual(list(li.ImageFrames().load(path)[0]), expected)

    def test_broken_path_is_remembered(self):
        images = li.ImageFrames()
        with self.assertLogs('led_strips', 'ERROR') as logs:
            self.assertIsNone(images.get('images/does_not_exist.gif'))
            self.assertIsNone(images.get('images/does_not_exist.gif'))
        self.assertEqual(len(logs.records), 1)

    def test_gif_loads_all_frames(self):
        frames = li.ImageFrames().get('images/rainbow.gif')
        self.assertGreater(len(frames), 1)

    def test_gif_frame_is_held_for_gif_delay_frames(self):
        builder = li.FrameBuilder()
        config = dict(li.DEFAULT_CONFIG, load_image=True, gif_delay=3, mode='static', amplitude=1.0)
        frames = [numpy.full(li.NUM_SUBPIXELS, value) for value in (10, 20)]
        shown = [builder.build([], 1, config, frames)[1] for _ in range(7)]
        self.assertEqual(shown, [10, 10, 10, 20, 20, 20, 10])


class LoudnessTest(unittest.TestCase):

    def setUp(self):
        self.old_err = numpy.seterr(all='raise')   # as in led_interface.main()

    def tearDown(self):
        numpy.seterr(**self.old_err)

    def test_silence_is_dark_and_raises_nothing(self):
        loudness = li.Loudness()
        loudness.resize(40, 3)
        values = {loudness.update(numpy.zeros(2048, numpy.float32)) for _ in range(50)}
        self.assertEqual(values, {0.0})

    def test_music_stays_between_0_and_1(self):
        loudness = li.Loudness()
        loudness.resize(40, 3)
        rng = numpy.random.default_rng(3)
        values = [loudness.update((rng.normal(0, 0.2, 2048) * (i % 10)).astype(numpy.float32))
                  for i in range(100)]
        self.assertGreaterEqual(min(values), 0)
        self.assertLessEqual(max(values), 1)
        self.assertGreater(max(values), 0.5)


if __name__ == '__main__':
    unittest.main()
