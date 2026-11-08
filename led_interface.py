#!/usr/bin/env python3
"""Music-reactive Christmas lights for the Raspberry Pi.

Listens to the Audio Injector sound card, turns the loudness of the bass into a
brightness value and streams colour frames over USB serial to the Arduino Mega
running FastLED (arduino_code/led_control.ino). The colours can also be
mirrored to Pixelblaze controllers over websocket.

Files this script uses, relative to the working directory (/home/pi/led_strips):
  config.json        settings, re-read every frame so the website can change them live
  colorsettings.txt  first two lines are the two custom colours ("r,g,b" from 0 to 1)
  network.cfg        Pixelblaze addresses (not in git)
  status.log         rewritten every second with our PID and the time, so the
                     website can tell we are alive
  images/, map.py    pictures for image mode, and where each LED is on the tree
"""

import collections
import configparser
import json
import logging
import math
import os
import signal
import sys
import threading
import time

import numpy
import serial
from PIL import Image
from scipy.signal import butter, filtfilt
from websocket import create_connection

logger = logging.getLogger('led_strips')

# Arduino. NUM_LEDS must match NUM_LEDS in arduino_code/led_control.ino.
SERIAL_PORT = '/dev/ttyACM0'
SERIAL_BAUD = 500000
NUM_LEDS = 500
NUM_SUBPIXELS = NUM_LEDS * 3      # one byte each for red, green and blue
FRAME_COMMAND = 0                 # command byte meaning "one colour per LED follows"
FRAME_LENGTH = NUM_SUBPIXELS + 1
# The Arduino only finds the start of a frame by counting bytes, and it can't
# receive while FastLED.show() runs (about 15 ms for 500 LEDs). So after each
# frame has been fully sent, wait SHOW_GAP before sending the next one. The
# next frame is built during the gap, so this doesn't delay what you see; one
# frame takes about 30 ms to send + 20 ms gap = 50 ms (20 frames a second).
# Below 0.015 the first LEDs can start showing the wrong colours again.
SHOW_GAP = 0.020
SERIAL_WRITE_TIMEOUT = 1.0        # seconds; longer means the Arduino stopped reading
# A burst of FRAME_LENGTH palette commands (0x02, each one byte long) brings the
# Arduino back to the start of a frame wherever it was. The strip briefly shows
# its built-in Christmas palette. RESYNC_SETTLE covers the last few palette
# redraws it may still be doing after the burst.
RESYNC_BYTE = 0x02
RESYNC_SETTLE = 0.1

# Audio input (Audio Injector HAT), passed straight through to the speakers.
AUDIO_CHANNELS = 2
AUDIO_RATE = 32000
LOWPASS_HZ = 100                  # only the bass drives the lights
STREAM_TIMEOUT = 0.25             # seconds without audio before a frame counts as a stall
MAX_STALLS = 2                    # restart the audio stream after more stalls than this

CONFIG_FILE = 'config.json'
COLOR_FILE = 'colorsettings.txt'
STATUS_FILE = 'status.log'
NETWORK_FILE = 'network.cfg'
PIXELBLAZE_SECTIONS = ['pixelblaze', 'pixelblaze_cabinets']
PIXELBLAZE_TIMEOUT = 2            # seconds allowed for connecting or sending
PIXELBLAZE_RETRY_INTERVAL = 30    # seconds between reconnect attempts

# Used for any setting that is missing from config.json or can't be read.
DEFAULT_CONFIG = {
    'mode': 'music',              # static, pulse or music
    'global_brightness': 1.0,     # multiplies every brightness
    'amplitude': 1.0,             # brightness in static mode, 0.0 to 1.0
    'pulsewidth': 50,             # frames per pulse in pulse mode
    'decay_len': 40,              # frames of history used to judge loud vs quiet
    'decay_len_s': 3,             # frames averaged to smooth the brightness
    'adjust': 1.0,                # passed to the Pixelblazes
    'pattern_time': 10,           # seconds between colour patterns
    'wireless_music': False,      # True: Pixelblazes pulse with the music too
    'shimmer': False,             # add random flicker
    'use_runners': False,         # add bright moving dots
    'num_runners': 3,
    'runner_length': 10,          # LEDs per runner
    'runner_distance': 100,       # LEDs between runners
    'runner_speed': 1,            # LEDs per frame
    'load_image': False,          # show an image instead of the colour patterns
    'image_path': './images/rainbow.gif',
    'gif_delay': 2,               # frames to hold each GIF frame
    'sleep_time': 0.04,           # not used; kept so the website can still set it
}
INT_SETTINGS = {'pulsewidth', 'decay_len', 'decay_len_s', 'num_runners', 'runner_length',
                'runner_distance', 'runner_speed', 'gif_delay'}
MIN_VALUES = {'pulsewidth': 1, 'decay_len': 1, 'decay_len_s': 1, 'gif_delay': 1,
              'num_runners': 0, 'runner_length': 0}
MODES = ('static', 'pulse', 'music')

DEFAULT_CUSTOM_COLORS = ((1.0, 1.0, 1.0), (0.5, 0.5, 0.0))

# The colour patterns the lights cycle through. None means the two custom
# colours from colorsettings.txt.
PATTERNS = [
    [(1, 0, 0), (1, 0, 0), (0, 1, 0), (0, 1, 0)],               # red, red, green, green
    [(1, 0, 0), (0, 1, 0), (0, 0, 1)],                          # red, green, blue
    [(1, 0, 0), (0, 1, 0), (1, 0.8, 0), (0, 0, 1), (1, 0, 1)],  # five colours
    [(0, 1, 1), (0, 0, 1)],                                     # blues
    [(0.9, 0.8, 0.8), (0.5, 0.45, 0.45)],                       # warm white
    [(0, 1, 0), (0, 1, 0)],                                     # green
    None,                                                       # custom colours
]
FIRST_PATTERN = 1


# ---------------------------------------------------------------- settings

def _convert_setting(key, value, default):
    """Convert a value from config.json to the type of its default, or raise ValueError."""
    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in ('true', 'false'):
            return value.strip().lower() == 'true'
        raise ValueError('expected true or false')
    if isinstance(default, (int, float)):
        if isinstance(value, bool):
            raise ValueError('expected a number')
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('expected a finite number')
        if key in INT_SETTINGS:
            number = int(round(number))
        return max(number, MIN_VALUES.get(key, number))
    if key == 'mode' and value not in MODES:
        raise ValueError('expected one of ' + ', '.join(MODES))
    return str(value)


class ConfigFile:
    """config.json, re-read on every frame.

    A setting that is missing falls back to DEFAULT_CONFIG; one that is invalid
    (for example a half-written file) keeps its previous value.
    """

    def __init__(self, path=CONFIG_FILE):
        self.path = path
        self.values = dict(DEFAULT_CONFIG)
        self._last_text = None

    def reload(self):
        try:
            with open(self.path) as fd:
                text = fd.read()
        except OSError as e:
            if self._last_text is not False:
                logger.warning("Can't read %s (%s); using previous settings", self.path, e)
                self._last_text = False
            return self.values
        if text == self._last_text:
            return self.values
        self._last_text = text

        try:
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise ValueError('top level is not an object')
        except ValueError as e:
            logger.warning('%s is not valid (%s); using previous settings', self.path, e)
            return self.values

        values = {}
        for key, default in DEFAULT_CONFIG.items():
            if key not in raw:
                values[key] = default
                continue
            try:
                values[key] = _convert_setting(key, raw[key], default)
            except (TypeError, ValueError) as e:
                logger.warning('Ignoring %s=%r in %s (%s)', key, raw[key], self.path, e)
                values[key] = self.values[key]
        self.values = values
        return values


def read_custom_colors(path=COLOR_FILE):
    """Return the two custom colours from the first two lines of colorsettings.txt."""
    try:
        with open(path) as fd:
            lines = fd.readlines()
        colors = tuple(tuple(float(v) for v in line.strip().split(',')) for line in lines[:2])
        if len(colors) != 2 or any(len(c) != 3 for c in colors):
            raise ValueError
        return colors
    except (OSError, ValueError):
        return DEFAULT_CUSTOM_COLORS


def pattern_colors(index, custom_colors):
    """Full-brightness colours for pattern number `index`."""
    pattern = PATTERNS[index]
    return list(custom_colors) if pattern is None else list(pattern)


def to_byte(value):
    """Turn a colour value from 0.0 to 1.0 into a byte, rounding like the colour library."""
    return max(0, min(255, int(value * 255 + 0.5 - 5e-7)))


# ------------------------------------------------------------------- audio

class AudioInput:
    """The sound card stream. Audio is passed straight through to the output."""

    def __init__(self):
        import pyaudio  # imported here so the rest of the module works without it
        self._pyaudio = pyaudio
        self._pa = pyaudio.PyAudio()
        self.stream = None
        self.samples = None
        self.last_callback = 0.0

    def _callback(self, in_data, frame_count, time_info, status):
        self.last_callback = time.time()
        self.samples = numpy.frombuffer(in_data, dtype=numpy.float32)
        return (in_data, self._pyaudio.paContinue)

    def open(self):
        self.stream = self._pa.open(format=self._pyaudio.paFloat32,
                                    channels=AUDIO_CHANNELS,
                                    rate=AUDIO_RATE,
                                    input=True,
                                    output=True,
                                    stream_callback=self._callback)
        self.stream.start_stream()

    def is_active(self):
        return self.stream is not None and self.stream.is_active()

    def close(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def terminate(self):
        self.close()
        self._pa.terminate()


class Loudness:
    """Turns audio buffers into a brightness from 0.0 (quiet) to 1.0 (loud).

    Loudness is judged against the quietest and loudest of the last
    `decay_len` buffers, then averaged over the last `decay_len_s`.
    """

    def __init__(self):
        self._b, self._a = butter(5, LOWPASS_HZ / (0.5 * AUDIO_RATE), btype='lowpass')
        self.history = collections.deque([0.0], maxlen=8)
        self.recent = collections.deque([0.0], maxlen=3)

    def resize(self, history_len, recent_len):
        if self.history.maxlen != history_len:
            self.history = collections.deque(self.history, maxlen=history_len)
        if self.recent.maxlen != recent_len:
            self.recent = collections.deque(self.recent, maxlen=recent_len)

    def update(self, samples):
        amplitude = float(numpy.sum(numpy.absolute(filtfilt(self._b, self._a, samples))))
        self.history.append(amplitude)
        self.recent.append(amplitude)
        quietest = min(self.history)
        loudest = max(self.history)
        if loudest - quietest < 1e-9:
            # Silence (or a perfectly steady sound): nothing to react to.
            return 0.0
        average = sum(self.recent) / len(self.recent)
        return max(0.0, min(1.0, (average - quietest) / (loudest - quietest)))


def pulse_brightness(position, pulsewidth):
    """Triangle wave used by pulse mode."""
    interp = position % pulsewidth
    if interp > pulsewidth / 2:
        return 1 - interp / float(pulsewidth)
    return interp / float(pulsewidth)


# ------------------------------------------------------------------ images

class ImageFrames:
    """Pictures and GIFs mapped onto the LEDs' positions on the tree (map.py).

    LEDs that map.py doesn't list stay dark in image mode.
    """

    def __init__(self):
        from map import coord_index_map
        coords = numpy.array(list(coord_index_map.keys()), dtype=float)
        indices = numpy.array(list(coord_index_map.values()))
        self._min = coords.min(axis=0)
        self._span = coords.max(axis=0) - self._min
        keep = indices < NUM_LEDS
        self._coords = coords[keep]
        self._indices = indices[keep]
        self.loaded_path = None
        self.frames = None
        self._failed_path = None

    def _render(self, rgb_image):
        width, height = rgb_image.size
        scaled = (self._coords - self._min) / self._span * (width - 1, height - 1)
        xs = scaled[:, 0].astype(int)
        ys = scaled[:, 1].astype(int)
        pixels = numpy.asarray(rgb_image)
        frame = numpy.zeros((NUM_LEDS, 3), dtype=numpy.int32)
        frame[self._indices] = pixels[ys, xs]
        return frame.reshape(-1)

    def load(self, path):
        """Return a list of frames, each NUM_SUBPIXELS long."""
        frames = []
        with Image.open(path) as image:
            for i in range(getattr(image, 'n_frames', 1)):
                image.seek(i)
                frames.append(self._render(image.convert('RGB')))
        return frames

    def get(self, path):
        """Frames for `path`, loading them if the path changed. None if it can't be loaded."""
        if path != self.loaded_path and path != self._failed_path:
            logger.info('Loading image %s', path)
            try:
                self.frames = self.load(path)
                self.loaded_path = path
                self._failed_path = None
            except Exception as e:
                logger.error("Can't load image %s: %s", path, e)
                self._failed_path = path
                return None
        return self.frames if path == self.loaded_path else None


# ------------------------------------------------------------------ frames

def repeat_pattern(colors):
    """Repeat a list of colours along the whole strip."""
    pattern = [to_byte(value) for color in colors for value in color]
    repeats = -(-NUM_SUBPIXELS // len(pattern))
    return numpy.array((pattern * repeats)[:NUM_SUBPIXELS], dtype=numpy.float64)


class FrameBuilder:
    """Builds the bytes sent to the Arduino for each frame."""

    def __init__(self, rng=None):
        self.position = 0      # moves the runners and drives pulse mode
        self.frame_count = 0   # steps through GIF frames
        self._rng = rng if rng is not None else numpy.random.default_rng()

    def build(self, colors, brightness, config, image_frames=None):
        """colors: the pattern, already scaled by brightness. Returns NUM_SUBPIXELS + 1 bytes."""
        with numpy.errstate(all='ignore'):
            if image_frames:
                frame = numpy.array(image_frames[(self.frame_count // config['gif_delay'])
                                                 % len(image_frames)], dtype=numpy.float64)
                amount = config['amplitude'] if config['mode'] == 'static' else brightness
                frame = numpy.trunc(numpy.minimum(255, frame * amount))
            else:
                frame = repeat_pattern(colors)

            speed = 2
            if config['use_runners']:
                speed = config['runner_speed']
                starts = self.position + config['runner_distance'] * numpy.arange(config['num_runners'])
                leds = (starts[:, None] + numpy.arange(config['runner_length'])[None, :]) % NUM_LEDS
                frame.reshape(NUM_LEDS, 3)[leds.ravel()] = min(255, 2 * int(255 * brightness))

            if config['shimmer']:
                noise = numpy.repeat(self._rng.normal(0, 5, NUM_LEDS), 3)
                frame = numpy.trunc(frame + noise)

            frame = numpy.clip(frame, 0, 255).astype(numpy.uint8)

        self.position += speed
        self.frame_count += 1
        return bytes([FRAME_COMMAND]) + frame.tobytes()


# ------------------------------------------------------------- Pixelblaze

class PixelBlaze:
    """One Pixelblaze, fed from a background thread.

    send() never blocks, so a Pixelblaze that is slow or offline can't stall
    the main LEDs. While it's offline, colours are dropped and a reconnect is
    tried every retry_interval seconds.
    """

    def __init__(self, name, address, connect=create_connection,
                 retry_interval=PIXELBLAZE_RETRY_INTERVAL):
        self.name = name
        self.address = address
        self._connect_to = connect
        self._retry_interval = retry_interval
        self._ws = None
        self._pending = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._reported_down = False
        threading.Thread(target=self._run, name='pixelblaze-' + name, daemon=True).start()

    def send(self, colors, adjust):
        payload = json.dumps({'setVars': {
            'adjust': adjust,
            'numColors': len(colors),
            'colorList': [float(value) for color in colors for value in color],
        }})
        with self._lock:
            self._pending = payload
        self._wake.set()

    def _connect(self):
        try:
            self._ws = self._connect_to('ws://' + self.address, timeout=PIXELBLAZE_TIMEOUT)
        except Exception as e:
            self._ws = None
            if not self._reported_down:
                logger.warning("Can't reach Pixelblaze %s at %s (%s); retrying every %d s",
                               self.name, self.address, e, self._retry_interval)
                self._reported_down = True
            return False
        logger.info('Connected to Pixelblaze %s at %s', self.name, self.address)
        self._reported_down = False
        return True

    def _disconnect(self):
        try:
            self._ws.close()
        except Exception:
            pass
        self._ws = None

    def _run(self):
        while True:
            if self._ws is None and not self._connect():
                time.sleep(self._retry_interval)
                continue
            self._wake.wait()
            self._wake.clear()
            with self._lock:
                payload, self._pending = self._pending, None
            if payload is None:
                continue
            try:
                self._ws.send(payload)
            except Exception as e:
                logger.warning('Lost connection to Pixelblaze %s (%s)', self.name, e)
                self._disconnect()   # the next loop reconnects straight away


def start_pixelblazes(path=NETWORK_FILE):
    network_config = configparser.ConfigParser()
    network_config.read(path)
    pixelblazes = []
    for name in PIXELBLAZE_SECTIONS:
        try:
            enabled = network_config.getboolean(name, 'enabled', fallback=False)
            address = network_config.get(name, 'address', fallback='')
        except ValueError as e:
            logger.warning('Bad [%s] section in %s: %s', name, path, e)
            continue
        if not enabled:
            logger.info('%s is disabled in %s', name, path)
        elif not address:
            logger.warning('%s has no address in %s', name, path)
        else:
            pixelblazes.append(PixelBlaze(name, address))
    return pixelblazes


# ---------------------------------------------------------------- heartbeat

class Heartbeat:
    """Writes "<pid>\\n<unix time>\\n" to status.log once a second for the website."""

    def __init__(self, path=STATUS_FILE):
        self.path = path
        self.pid = os.getpid()
        self._last = None
        self._failed = False

    def beat(self):
        now = int(time.time())
        if now == self._last:
            return
        self._last = now
        temp_path = self.path + '.tmp'
        try:
            with open(temp_path, 'w') as fd:
                fd.write('{}\n{}\n'.format(self.pid, now))
            os.replace(temp_path, self.path)
            self._failed = False
        except OSError as e:
            if not self._failed:
                logger.warning("Can't write %s: %s", self.path, e)
                self._failed = True


# --------------------------------------------------------------- main loop

class Arduino:
    """The serial link to the Arduino, paced so it never loses track of frames."""

    def __init__(self, port=SERIAL_PORT):
        try:
            # exclusive: a second copy of this script can't open the port and
            # mix its frames in with ours.
            self.serial = serial.Serial(port, SERIAL_BAUD, write_timeout=SERIAL_WRITE_TIMEOUT,
                                        timeout=5, exclusive=True)
        except serial.SerialException as e:
            logger.error("Can't open %s (%s). Is another copy of led_interface.py running?", port, e)
            sys.exit(1)
        self._next_send = 0.0
        logger.info('Waiting for the Arduino on %s...', port)
        greeting = self.serial.readline().decode('ascii', errors='replace').strip()
        logger.info('Arduino says: %s', greeting or '(nothing within 5 seconds)')

    def _write(self, data, gap):
        wait = self._next_send - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.serial.write(data)
        self.serial.flush()   # returns once every byte has gone out
        self._next_send = time.monotonic() + gap

    def resync(self):
        """Make sure the Arduino's next byte is the start of a frame."""
        logger.info('Resyncing the Arduino')
        self._write(bytes([RESYNC_BYTE]) * FRAME_LENGTH, RESYNC_SETTLE)

    def send(self, frame):
        try:
            self._write(frame, SHOW_GAP)
        except serial.SerialTimeoutException:
            # Part of the frame may be stuck or lost, so the Arduino has
            # probably lost its place.
            logger.warning('Serial write timed out; resyncing the Arduino')
            self.serial.reset_output_buffer()
            self.resync()

    def close(self):
        self.serial.close()


def run():
    logger.info('Starting LED strip interface (pid %d)', os.getpid())
    # Open the Arduino first, so a second copy exits before touching status.log.
    arduino = Arduino()
    heartbeat = Heartbeat()
    heartbeat.beat()
    arduino.resync()
    pixelblazes = start_pixelblazes()
    config_file = ConfigFile()
    images = ImageFrames()
    frames = FrameBuilder()
    loudness = Loudness()
    audio = AudioInput()

    custom_colors = read_custom_colors()
    last_pattern_change = time.time()
    frame_number = 0
    swap = False
    stalls = 0

    try:
        while True:
            audio.open()
            pattern = FIRST_PATTERN
            waiting = False
            logger.info('Audio stream started')

            while audio.is_active():
                heartbeat.beat()
                config = config_file.reload()
                loudness.resize(config['decay_len'], config['decay_len_s'])

                if audio.samples is None:
                    if not waiting:
                        logger.info('Waiting for audio...')
                        waiting = True
                    time.sleep(0.01)
                    continue
                waiting = False

                now = time.time()
                if now - last_pattern_change > config['pattern_time']:
                    pattern = (pattern + 1) % len(PATTERNS)
                    logger.debug('Pattern is now %d', pattern)
                    last_pattern_change = now

                # The stream sometimes stops delivering audio; restart it if so.
                if now - audio.last_callback > STREAM_TIMEOUT:
                    logger.warning('No audio for %.2f s', now - audio.last_callback)
                    stalls += 1
                    if stalls > MAX_STALLS:
                        stalls = 0
                        break

                # Every 40 frames, swap the colour order and re-read the custom colours.
                if frame_number == 20:
                    swap = not swap
                    custom_colors = read_custom_colors()
                frame_number = (frame_number + 1) % 40

                try:
                    level = loudness.update(audio.samples)
                except (ArithmeticError, ValueError) as e:
                    logger.error('Audio maths failed (%s); restarting the stream', e)
                    break

                if config['mode'] == 'music':
                    brightness = level
                elif config['mode'] == 'pulse':
                    brightness = pulse_brightness(frames.position, config['pulsewidth'])
                else:
                    brightness = config['amplitude']
                brightness *= config['global_brightness']

                full_colors = pattern_colors(pattern, custom_colors)
                if swap:
                    full_colors.reverse()
                colors = [tuple(value * brightness for value in color) for color in full_colors]

                for pixelblaze in pixelblazes:
                    pixelblaze.send(colors if config['wireless_music'] else full_colors,
                                    config['adjust'])

                image_frames = images.get(config['image_path']) if config['load_image'] else None
                arduino.send(frames.build(colors, brightness, config, image_frames))

            logger.warning('Restarting the audio stream')
            audio.close()
    finally:
        audio.terminate()
        arduino.close()


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    # Any maths error in the audio processing raises, so the stream gets restarted.
    numpy.seterr(all='raise')
    # Let systemd's stop (SIGTERM) close the audio stream and serial port cleanly.
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    try:
        run()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
