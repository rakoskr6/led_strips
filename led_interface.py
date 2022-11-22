#!/usr/bin/python
from __future__ import print_function

import collections
import configparser
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime

import numpy
import phue
import serial
import thread
from PIL import Image
from colour import Color
from scipy import signal
from websocket import create_connection

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()


global sending
global decoded
global lastcallback
global runner_modulus
global b,a

AUDIO_CHANNELS = 2


def pya_callback(in_data, frame_count, time_info, status):
    global decoded
    global lastcallback, b, a
    lastcallback = float(datetime.now().strftime('%s.%f'))
    decoded = numpy.fromstring(in_data, 'Float32')
    #filtered = signal.filtfilt(b,a,decoded,padlen=200).astype(np.float32).tostring()
    return (in_data, pyaudio.paContinue)

def bytebound(val):
    return int(max(0, min(255, val)))

def addnoise(inList):
    assert (len(inList)-1)%3 == 0
    noise = numpy.repeat(numpy.random.normal(0,5,(len(inList)-1)//3),3)
    outList = [inList[0]] + [max(0, min(255, int(elem))) for elem in list(inList[1:] + noise)]   
    return outList

def add_runner(inList, pos, val, width):
    global num_leds
    for i in range(width):
        inList[1+((pos+i)%(num_leds/3))*3] = min(255,2*val)
        inList[2+((pos+i)%(num_leds/3))*3] = min(255,2*val)
        inList[3+((pos+i)%(num_leds/3))*3] = min(255,2*val)

def now():
    return float(datetime.now().strftime('%s.%f'))

def get_led_boundary_box():
    """Returns a tuple of size 4 with the x/y coordinates of the LED boundaries"""
    from map import coord_index_map
    min_x = min([coord[0] for coord in coord_index_map.keys()])
    max_x = max([coord[0] for coord in coord_index_map.keys()])
    min_y = min([coord[1] for coord in coord_index_map.keys()])
    max_y = max([coord[1] for coord in coord_index_map.keys()])
    return min_x, min_y, max_x, max_y

def get_image_boundary_box(image_path):
    image = Image.open(image_path)
    img_max_x, img_max_y = image.size
    bbox_image = (0, 0, img_max_x-1, img_max_y-1)
    return image, bbox_image

def generate_frame(image, bbox_lights, bbox_image):
    from map import coord_index_map
    subpixels = [0] * 900
    for coord in coord_index_map.keys():
        pixel_index = coord_index_map[coord]
        remapped_coords = remap_pixels(coord, bbox_lights, bbox_image)
        subpixels[pixel_index * 3:pixel_index * 3 + 3] = image.getpixel(remapped_coords)
    return subpixels

def gen_image(image_path):
    global image_is_gif
    bbox_lights = get_led_boundary_box()
    image, bbox_image = get_image_boundary_box(image_path)
    if image_is_gif and image.is_animated:
        # out_list is going to be a list of lists
        num_frames = image.n_frames
        out_list = []
        for i in range(num_frames):
            image.seek(i)
            rgb_image = image.convert('RGB')
            subpixels = generate_frame(rgb_image, bbox_lights, bbox_image)
            out_list.append([0] + list(subpixels))
    else:
        subpixels = generate_frame(image, bbox_lights, bbox_image)
        out_list = [0] + list(subpixels)
    return out_list

# remap from coordinate plane 1 to plane 2
def remap_pixels(coord, bbox_1, bbox_2):
    min_x1, min_y1, max_x1, max_y1 = bbox_1
    min_x2, min_y2, max_x2, max_y2 = bbox_2
    x_in, y_in = coord
    # print("bbox_1: {}, bbox_2: {}, coord: {}".format(bbox_1, bbox_2, coord))
    x_out = int(((float(x_in-min_x1)/float(max_x1-min_x1))*float(max_x2-min_x2))+min_x2)
    y_out = int(((float(y_in-min_y1)/float(max_y1-min_y1))*float(max_y2-min_y2))+min_y2)
    return (x_out, y_out)
    

def debug_indexing(gif_modulus):
    input("Press enter for next")
    raw_list = 900*[0]
    print("index is {}".format(gif_modulus))
    raw_list[(3*gif_modulus)%900:(3*gif_modulus+3)%900] = (255, 255, 255)
    return [0] + raw_list

def led_send(sobj,amplitude,colors):
    global runner_modulus
    global gif_modulus
    global sending
    global num_leds
    global image_pixel_list
    global image_is_gif
    to_kill = 0
    #if sending == True:
    #    return
    raw_list = []
    '''
    if len(colors) != 450:
        print("'colors' must be of length 450'")
        return
    '''
    for elem in colors:
        if elem[0] == '#':
            elem = elem[1:]
        raw_list.append(int(elem[0:2],16))
        raw_list.append(int(elem[2:4],16))
        raw_list.append(int(elem[4:6],16))
    raw_list = raw_list*(int(round((num_leds)/float(len(raw_list)))))
    raw_list = raw_list[0:num_leds]
    raw_list = [0] + raw_list

    if lightConfig['load_image']:
        # cast so we don't overwrite it
        if image_is_gif and isinstance(image_pixel_list[0], list):
            raw_list = list(image_pixel_list[(gif_modulus//lightConfig['gif_delay'])%len(image_pixel_list)])
        else:
            raw_list = list(image_pixel_list)
        # add amplitude for image mode
        if lightConfig['mode'] != 'static':
            amp = amplitude
        else:
            amp = lightConfig['amplitude']
        for index in range(1,len(raw_list)):
            raw_list[index] = int(min(255, raw_list[index]*amp))

    runner_speed = 2
    if lightConfig['use_runners'] == True:
        runner_speed = lightConfig['runner_speed']
        runner_len = lightConfig['runner_length']
        num_runners = lightConfig['num_runners']
        runner_distance = lightConfig['runner_distance']
        for i in range(num_runners):
            add_runner(raw_list,(runner_modulus+(runner_distance*i))%num_leds,int(255*ampValue),runner_len)

    #thislist = 150*[128]+1200*[0]
    #send_data = bytearray([0]+rotated_list)
    
    debug_indexing = False
    if debug_indexing:
        raw_list = debug_indexing(gif_modulus)

    global lightConfig
    if lightConfig['shimmer'] == True:
        raw_list = addnoise(raw_list)
    raw_list[len(raw_list)-to_kill:len(raw_list)] = to_kill*[0] 

    # print("Sending length {} list".format(len(raw_list)))
    send_data = bytearray(raw_list)
    #send_data = bytearray([0] + raw_list*1350)
    #raw_list = 1350*[20]
    #raw_list[runner_modulus%len(raw_list)] = 128
    runner_modulus = (runner_modulus+runner_speed%num_leds)
    gif_modulus = (gif_modulus+1)%1000000
    #send_data = bytearray([0]+raw_list)

    logger.debug(send_data)
    logger.debug(repr(send_data) + str(len(send_data)))
    logger.debug(len(send_data))
    logger.debug("attempting to send bits")

    sending = True
    #print(sobj.read(sobj.in_waiting))
    # send_start = time.time()
    ## DEBUG:
    # send_data = bytearray([0] + [10,10,10]*300)
    bitssent = sobj.write(send_data)
    # send_end = time.time()
    time.sleep(0.04)
    # time.sleep(1.00)
    sending = False
    # print("Successfully sent {} bytes".format(bitssent))
    #time.sleep(0.005)
    #return send_data
    return
    '''
    raw_list = []
    #raw_list.append(int('00',16))
    sobj.write(bytearray('00'))
    for elem in colors:
        if elem[0] == '#':
            elem = elem[1:]
        raw_list.append(int(elem[2:4],16))
        raw_list.append(int(elem[4:6],16))
        raw_list.append(int(elem[0:2],16))

    send_data = bytearray(raw_list)
    print(repr(send_data) + str(len(send_data)))
    sobj.write(send_data)
    '''
    pass

def reloadColors():
    try:
        with open('colorsettings.txt', 'r') as fd:
            data = fd.readlines()
            c1_r, c1_g, c1_b = [float(elem) for elem in data[0].strip().split(',')]
            c2_r, c2_g, c2_b = [float(elem) for elem in data[1].strip().split(',')]
            return c1_r, c1_g, c1_b, c2_r, c2_g, c2_b
    except:
        return [1.0, 1.0, 1.0, 0.5, 0.5, 0]
    return [1.0, 1.0, 1.0, 0.5, 0.5, 0]

def reloadConfig():
    try:
        with open('config.json', 'r') as fd:
            # this is dangerous but whatever
            # config = ast.literal_eval(fd.read())
            config = json.load(fd)
    except Exception as e:
        print("Error reloading config: " + str(e))
        raise
    return config

def send_to_network(colorList):
    global ws
    colorsToSend = {
        "setVars" : {
        'adjust': lightConfig['adjust'],
        'numColors' : len(colorList),
        'colorList' : [elem for sublist in [list(elem.rgb) for elem in colorList] for elem in sublist]
        }
    }
    try:
        ws.send(json.dumps(colorsToSend))
    except:
        print("Lost connection to websocket server, is it on?")
        # something went wrong here hahaha
        ws = None
        websocket_connected = False
        # print("attempting to reconnect")
        # ws = create_connection("ws://192.168.1.161:81")
        # ws.send(json.dumps(colorsToSend))
    return

def hue_send(index, inColor):
    global lights
    hueHue = int(inColor.hue*65535)
    hueSaturation = int(inColor.saturation*254)
    hueBrightness = int(inColor.luminance*128)
    lights[index].hue = hueHue
    lights[index].saturation = hueSaturation
    lights[index].brightness = hueBrightness

def heartbeat():
    global pid
    global last_heartbeat_time
    currtime = int(time.time())
    if last_heartbeat_time < currtime:
        with open('status.log', 'w') as fd:
            fd.write("{}\n{}\n".format(pid, currtime))

######################################
#      Main Loop                     #
######################################

if __name__ == '__main__':
    print("Starting LED strip interface")
    import pyaudio
    global decoded
    global lastcallback
    global runner_modulus
    global lastconfigchange
    global b, a
    global websocket_connected
    global ws
    global num_leds
    global lightConfig
    global lights
    global bridgeEnabled
    global last_heartbeat_time
    global pid
    global image_pixel_list
    # globals hurt me
    global image_is_gif
    # define pid and last_heartbeat_time to write to status.log
    # this is read by the PHP scripts on the webserver
    # to check if we're alive
    pid = os.getpid()
    last_heartbeat_time = int(time.time())
    print("Starting on pid {} at time {}".format(pid, last_heartbeat_time))
    heartbeat()
    # read configuration options for the phillips hue and 
    # pixelBlaze.
    network_config = configparser.ConfigParser()
    network_config.read('network.cfg')
    print(network_config.sections())
    bridgeEnabled = False
    # num_leds = 1350+12
    # num_leds = 150+12
    # this is the number of subpixels; aka: the number of LEDs * 3
    num_leds = 900
    decoded = None
    # default lightConfig, this gets reloaded every loop iteration
    lightConfig = {'mode': 'static', 'amplitude': 0.5}
    # Setup code for the serial interface to the Arduino running FastLED
    #ser = serial.Serial('/dev/ttyAMA0', 2000000, rtscts=1, writeTimeout=0)
    ser = serial.Serial('/dev/ttyACM0', 500000, writeTimeout=0)
    # websocket connection for pixelblaze
    # Returned exception if pixel blaze not found, so added try - KR
    try:
        use_pixelblaze = network_config['pixelblaze'].getboolean('enabled')
    except Exception as e:
        use_pixelblaze = False

    ws = None
    if not use_pixelblaze:
        print("Pixelblaze is disabled via network.cfg")
        ws = None
    # Check use_pixelblaze to startup the websocket for the pixelblaze
    if use_pixelblaze:
        try:
            ws = create_connection("ws://" + network_config['pixelblaze']['address'])
            websocket_connected = True
        except Exception as e:
            print(e)
            websocket_connected = False
    #print(ser.read(ser.in_waiting))
    # Returned exception if Hue not found, so added try - KR
    # Check  for phue
    try:
        use_hue = network_config['phue'].getboolean('enabled')
    except Exception as e:
        use_hue = False
    if not use_hue:
        print("Philips Hue is disabled via network.cfg")
    # init all the philips hue bridge code
    if use_hue:
        huebridge = phue.Bridge(network_config['phue']['address'])
        try:
            print("Connecting to hue...")
            huebridge.connect()
            bridgeEnabled = True
            print("Connected!")
        except Exception as e:
            print("{}".format(e))
            bridgeEnabled = False
        huebridge.set_light([1,3,4], 'on', True, transitiontime=0)
        lights = huebridge.get_light_objects()
        lights.pop(1)
        print(lights)
        for light in lights:
            light.transitiontime = 0 
        last_hue_c = Color(rgb=(0,0,0))
        last_hue_c2 = Color(rgb=(0,0,0))
    
    print("Starting serial connection to Arduino...")
    print(ser.readline())
    print("read!")
    # initialize DSP state variables
    minVal = 1
    maxVal = 0
    n = 0
    k = 0
    runner_modulus = 0
    gif_modulus = 0
    rollingArray = collections.deque(maxlen=8)
    rollingArraySmall = collections.deque(maxlen=3)
    rollingArray.append(0.0)
    rollingArraySmall.append(0.0)
    badcount = 0
    WIDTH = 2
    RATE = 32000
    FORMAT = pyaudio.paFloat32
    c1_r, c1_g, c1_b, c2_r, c2_g, c2_b = reloadColors()
    numpy.seterr(all='raise')
    auto_restart = 1
    old_decoded = None
    sending = False
    lastconfigchange = now()
    b, a = signal.butter(5, 100/(0.5*RATE), btype='lowpass')
    paobj = pyaudio.PyAudio()

    image_is_gif = False
    image_pixel_list = gen_image("./images/rainbowvert.png")
    last_image = 'none'
    # initialize processing loop for everything
    logger.info("Starting processing loop")
<<<<<<< HEAD
    print("starting loop")
=======
>>>>>>> fff97cc2b295bad04a935a188e4a37d630a00d79
    while (auto_restart):
        stream = paobj.open(format=FORMAT,
                        channels=AUDIO_CHANNELS,
                        rate=RATE,
                        input=True,
                        output=True,
                        stream_callback=pya_callback)
        stream.start_stream()
        config = 1 
        waiting = False
        lightConfig = {'mode': 'static', 'amplitude': 1}
        while stream.is_active():
            try:
                # heartbeat every time we loop to keep the PHP dog happy
                heartbeat()
            except Exception as e:
                pass
            try:
                # reload config on the fly, try catch with and use old value if we fail
                new_lightConfig = reloadConfig()
                lightConfig = new_lightConfig
                if last_image != lightConfig['image_path']:
                    logger.info("Loading new image file: {}".format(lightConfig['image_path']))
                    if lightConfig['image_path'].endswith('.gif'):
                        image_is_gif = True
                    else:
                        image_is_gif = False
                    image_pixel_list_temp = gen_image(lightConfig['image_path'])
                    # BAD because we are using globals, image_pixel_list needs to only change when it needs to
                    image_pixel_list = image_pixel_list_temp
                last_image = lightConfig['image_path']
            except Exception:
                logger.error("Falling back to old lightConfig")
                logger.error(traceback.format_exc())

            # DSP dequeue for rolling amplitude calculation
            try:
                if lightConfig['mode'] == 'music' and lightConfig['decay_len']:
                    if len(rollingArray) != lightConfig['decay_len']:
                        newRollingArray = collections.deque(maxlen=lightConfig['decay_len'])
                        newRollingArray += rollingArray
                        rollingArray = newRollingArray
                if lightConfig['mode'] == 'music' and lightConfig['decay_len_s']:
                    if len(rollingArraySmall) != lightConfig['decay_len_s']:                
                        newRollingArraySmall = collections.deque(maxlen=lightConfig['decay_len_s'])
                        newRollingArraySmall += rollingArraySmall
                        rollingArraySmall = newRollingArraySmall
            except Exception as e:
                logger.error("Failed to set decay length")
                logger.error(e)
            if type(decoded) == type(None):
                if waiting == False:
                    print("Waiting for stream", end ="")
                    waiting = True
                else:
                    print(".", end="")
                continue
            else:
                last_decoded = decoded
            waiting = False
            currtime = now()
            try:
                p_time = lightConfig['pattern_time']
            except:
                p_time = 10
            if (currtime - lastconfigchange) > p_time:
                config = (config+1)%5
                logger.info("Config is now {}".format(config))
                lastconfigchange = now()
            #print("Currtime: {0}".format(currtime))
            #print("Callback: {0}".format(lastcallback))
            # stream is flaky so sometimes it dies, print BAD! and restart automatically 
            # if we die more than 3 times
            if (currtime - lastcallback) > 0.25:
                print("BAD!")
                badcount += 1
                if badcount > 2:
                    badcount = 0
                    break
            if n == 20:
               k = (k+1)%2 
               c1_r, c1_g, c1_b, c2_r, c2_g, c2_b = reloadColors()
            n = (n+1)%40
            #print(k,n)
            #filtered = decoded
            filtered = signal.filtfilt(b,a,decoded)
            #amplitude = numpy.sqrt(numpy.mean(numpy.square(filtered)))
            amplitude = numpy.sum(numpy.absolute(filtered))
            #amplitude = numpy.sum(numpy.absolute(last_decoded))
            #print("FIL: {}".format(amplitude))
            #print("RAW: {}\n".format(rawamplitude))
            rollingArray.append(amplitude)
            rollingArraySmall.append(amplitude)
            #maxVal = max(rollingArray) if max(rollingArray) > 0.1 else 0.3
            #minVal = min(rollingArray) if min(rollingArray) < 0.4 else 0.04
            #maxVal = amplitude if amplitude > maxVal else maxVal
            #minVal = amplitude if amplitude < minVal else minVal
            #print(len(decoded))
            maxVal = max(rollingArray)
            minVal = min(rollingArray)
            #minVal = min(rollingArray)
            #maxVal = 0.8
            #print(amplitude, minVal, maxVal)
            #print(amplitude)
            amplitude = sum(rollingArraySmall)/len(rollingArraySmall)
            #amplitudeColor = Color(hsl=(0, 0, (amplitude/(maxVal-minVal))))
            try: 
                # pulse mode
                if lightConfig['mode'] == 'pulse':
                    pulsewidth = lightConfig['pulsewidth']
                    interp = runner_modulus % pulsewidth
                    ampValue = (1-(interp/float(pulsewidth))) if interp > pulsewidth/2 else (interp/float(pulsewidth))
                elif lightConfig['mode'] == 'static':
                    # static mode
                    ampValue = lightConfig['amplitude']
                elif lightConfig['mode'] == 'music':
                    # music mode 
                    ampValue = (min(1,(amplitude-minVal)/(maxVal-minVal))) 
            except Exception as e:
                print("aaaa something went wrong in the stream, restarting")
                break
            # print(ampValue)
            ac_list = []
            static_color_list = []
            # add global_brightness from config
            if 'global_brightness' in lightConfig.keys():
                ampValue = ampValue * lightConfig['global_brightness']

            # this config is just some predefined patterns we loop through
            if config == 0:
                static_color_list.append(Color(rgb=(1,0,0)))
                static_color_list.append(Color(rgb=(0,1,0)))
                ac_list.append(Color(rgb=(ampValue,0,0)))
                ac_list.append(Color(rgb=(0,ampValue,0)))
            elif config == 2:
                ac_list.append(Color(rgb=(0,ampValue,ampValue)))
                ac_list.append(Color(rgb=(0,0,ampValue)))
                static_color_list.append(Color(rgb=(0,1,1)))
                static_color_list.append(Color(rgb=(0,0,1)))
            elif config == 1:
                static_color_list.append(Color(rgb=(1,0,0)))
                static_color_list.append(Color(rgb=(0,1,0)))
                static_color_list.append(Color(rgb=(0,0,1)))
                ac_list.append(Color(rgb=(ampValue,0,0)))
                ac_list.append(Color(rgb=(0,ampValue,0)))
                ac_list.append(Color(rgb=(0,0,ampValue)))
            elif config == 3:
                static_color_list.append(Color(rgb=(1,0.9,0.9)))
                static_color_list.append(Color(rgb=(0.6,0.5,0.5)))
                ac_list.append(Color(rgb=(ampValue,ampValue,ampValue)))
                ac_list.append(Color(rgb=(ampValue*0.6,ampValue*0.6,ampValue*0.6)))
            else:
                # CUSTOM COLORS BASED OFF OF STUFF defined in the first 
                # two lines of colorsettings.txt
                static_color_list.append(Color(rgb=(c1_r,c1_g,c1_b)))
                static_color_list.append(Color(rgb=(c2_r,c2_g,c2_b)))
                ac_list.append(Color(rgb=(ampValue*c1_r,ampValue*c1_g,ampValue*c1_b)))
                ac_list.append(Color(rgb=(ampValue*c2_r,ampValue*c2_g,ampValue*c2_b)))
                
            # Hue bulb integration
              
            if(bridgeEnabled):
                if last_hue_c != static_color_list[0]:
                    # send new colors to hue
                    last_hue_c = static_color_list[0]
                    thread.start_new_thread(hue_send, (0, last_hue_c))
                    thread.start_new_thread(hue_send, (1, last_hue_c))
                if last_hue_c2 != static_color_list[1]:
                    last_hue_c2 = static_color_list[1]
                    # send new colors to hue
                    thread.start_new_thread(hue_send, (2, last_hue_c2))
            if config == 1:
                pattern = (elem.hex_l for elem in ac_list)
                #print(pattern)
                if k:
                    static_color_list.reverse()
                    ac_list.reverse()
            else:
                if k:
                    static_color_list.reverse()
                    ac_list.reverse()
                pattern = ([ac_list[0].hex_l] + [ac_list[1].hex_l])
            colorList = pattern
            # send pattern to wireless strips
            if ws and websocket_connected:
                # this is WAY TOO STROBEY
                if lightConfig['wireless_music']:
                    send_to_network(ac_list)
                else:
                    send_to_network(static_color_list)
            #print(colorList)
            #led_send(ser, 6, colorList)
            #time.sleep(0.005)
            #time.sleep(0.025)
            led_send(ser, ampValue, colorList)
            # while ser.in_waiting:
            #     print(ser.readline())
            # time.sleep(10.00)
            #time.sleep(0.050)
        print("auto restarting")
        stream.stop_stream()
        stream.close()
        #paobj.terminate()

    '''
    color_red = 'FF0000'
    color_green = '00FF00'
    color_blue = '0000FF'
    color_off = '000000'

    color_list = [color_off]*10

    i = 0

    gradient = list(Color("#010000").range_to(Color("#880000"), 50))
    gradient = gradient + gradient[::-1]

    gradient2 = list(Color("#000100").range_to(Color("#008800"), 50))
    gradient2 = gradient2 + gradient2[::-1]

    # infinite loop!
    
    while True:
        start = time.time()
        # casting a list as a list to do a copy
        color_list_temp = [gradient[i%len(gradient)].hex_l]*10
        color_list_temp2 = [gradient2[i%len(gradient2)].hex_l]*10

        led_send(ser, 6, color_list_temp)
        led_send(ser, 5, color_list_temp2)
        i = (i+1)%len(gradient)
        # lock framerate to 50 per second
        #time.sleep(max(1./50 - (time.time() - start), 0))
        #print("{:0.10f} Hz".format(1./((time.time() - start))))
    '''

    ser.close()
