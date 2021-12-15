#!/usr/bin/python
from __future__ import print_function
import serial, time, numpy
from colour import Color
import collections
import subprocess
from datetime import datetime
from scipy import signal
import ast
import json
from websocket import create_connection
import phue
import thread

global sending
global decoded
global lastcallback
global runner_modulus
global b,a

def pya_callback(in_data, frame_count, time_info, status):
    config = 0
    global decoded
    global lastcallback, b, a
    lastcallback = float(datetime.now().strftime('%s.%f'))
    decoded = numpy.fromstring(in_data, 'Float32')
    #filtered = signal.filtfilt(b,a,decoded,padlen=200).astype(np.float32).tostring()
    #print(in_data)
    return (in_data, pyaudio.paContinue)

def bytebound(val):
    return int(max(0, min(255, val)))

def addnoise(inList):
    assert (len(inList)-1)%3 == 0
    noise = numpy.repeat(numpy.random.normal(0,5,(len(inList)-1)//3),3)
    outList = [inList[0]] + [max(0, min(255, int(elem))) for elem in list(inList[1:] + noise)]   
    #print(outList[0])
    return outList

def whitecorrect(inList):
    correctFactor = 0.80
    if (len(inList) % 3 != 0):
        print("UHHHH something is wrong with list {}".format(inList))
    outList = [int(elem*correctFactor) if not (i)%3 else elem for i,elem in enumerate(inList)]
    #print("{} -> {}".format(inList, outList))
    return outList

def add_runner(inList, pos, val, width):
    global num_leds
    for i in range(width):
        inList[1+((pos+i)%(num_leds/3))*3] = min(255,2*val)
        inList[2+((pos+i)%(num_leds/3))*3] = min(255,2*val)
        inList[3+((pos+i)%(num_leds/3))*3] = min(255,2*val)

def now():
    return float(datetime.now().strftime('%s.%f'))

def led_send(sobj,amplitude,colors):
    global runner_modulus
    global sending
    global num_leds
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
        #raw_list.append(int('00',16))   
    #print(len(raw_list))
    ### # whitecorrect_list = whitecorrect(raw_list)
    ### raw_list = (raw_list*(int(round((num_leds-12)/float(len(raw_list))))))[0:num_leds-12]
    ### #print(len(raw_list))
    ### #assert len(raw_list) == num_leds-12
    ### raw_list += [0]*(12)
    ### #print(repr(raw_list))
    ### #raw_list = [0] + [255]*1359
    ### #print(runner_modulus)
    raw_list = raw_list*(int(round((num_leds)/float(len(raw_list)))))
    raw_list = raw_list[0:num_leds]
    raw_list = [0] + raw_list

    '''
    add_runner(raw_list,runner_modulus%num_leds,int(255*ampValue),10)
    
    add_runner(raw_list,(runner_modulus+150)%num_leds,int(255*ampValue),10)
    
    add_runner(raw_list,(runner_modulus+300)%num_leds,int(255*ampValue),10)
    

    #thislist = 150*[128]+1200*[0]
    #send_data = bytearray([0]+rotated_list)
    '''


    global lightConfig
    if lightConfig['shimmer'] == True:
        raw_list = addnoise(raw_list)
    # raw_list[len(raw_list)-to_kill:len(raw_list)] = to_kill*[0] 
    #a[len(a)-4:len(a)] = 4*[0]

    # print("Sending length {} list".format(len(raw_list)))
    send_data = bytearray(raw_list)
    #send_data = bytearray([0] + raw_list*1350)
    #raw_list = 1350*[20]
    #raw_list[runner_modulus%len(raw_list)] = 128
    runner_modulus += 2
    #send_data = bytearray([0]+raw_list)
    #print(send_data)
    #print(repr(send_data) + str(len(send_data)))
    #print(len(send_data))
    #print("attempting to send bits")
    sending = True
    #print(sobj.read(sobj.in_waiting))
    bitssent = sobj.write(send_data)
    time.sleep(0.040)
    sending = False
    #print("Successfully sent {} bytes".format(bitssent))
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
        with open('led_config.cfg', 'r') as fd:
            # this is dangerous but whatever
            config = ast.literal_eval(fd.read())
    except Exception as e:
        print(e)
        config = { 'mode': 'static' }
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
        print("attempting to reconnect")
        ws = create_connection("ws://192.168.1.161:81")
        ws.send(json.dumps(colorsToSend))
    return

def hue_send(index, inColor):
    global lights
    hueHue = int(inColor.hue*65535)
    hueSaturation = int(inColor.saturation*254)
    hueBrightness = int(inColor.luminance*128)
    lights[index].hue = hueHue
    lights[index].saturation = hueSaturation
    lights[index].brightness = hueBrightness

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
    bridgeEnabled = False
    # num_leds = 1350+12
    # num_leds = 150+12
    num_leds = 900
    decoded = None
    lightConfig = {'mode': 'static', 'amplitude': 0.5}
    # Setup code
    #ser = serial.Serial('/dev/ttyAMA0', 2000000, rtscts=1, writeTimeout=0)
    ser = serial.Serial('/dev/ttyACM0', 500000, writeTimeout=0)
    #ser = serial.Serial('/dev/ttyAMA0', 500000, writeTimeout=0)
    # websocket connection for pixelblaze
    use_pixelblaze = False
    ws = None
    if not use_pixelblaze:
        print("Pixelblaze is disabled via use_pixelblaze")
        ws = None
    if use_pixelblaze:
        try:
            ws = create_connection("ws://192.168.1.161:81")
            websocket_connected = True
        except Exception as e:
            print(e)
            websocket_connected = False
    #print(ser.read(ser.in_waiting))
    use_hue = False
    if not use_pixelblaze:
        print("Philips Hue is disabled via use_hue")
    if use_hue:
        huebridge = phue.Bridge('192.168.1.100')
        try:
            print("Connecting to hue...")
            huebridge.connect()
            bridgeEnabled = True
            print("Connected!")
        except Exeption as e:
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
    
    print(ser.readline())
    minVal = 1
    maxVal = 0
    n = 0
    k = 0
    runner_modulus = 0
    b, a = signal.butter(5, 250.0/(0.5*48000), btype='lowpass')
    rollingArray = collections.deque(maxlen=8)
    rollingArraySmall = collections.deque(maxlen=3)
    rollingArray.append(0.0)
    rollingArraySmall.append(0.0)
    badcount = 0
    WIDTH = 2
    CHANNELS = 2
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
    print("Starting processing loop")
    while (auto_restart):
        stream = paobj.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        output=True,
                        stream_callback=pya_callback)
        #                stream_callback=pya_nightlight_callback)
        stream.start_stream()
        config = 1 
        waiting = False
        while stream.is_active():
            lightConfig = reloadConfig()
            #print(lightConfig)
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
                print("Failed to set decay length")
                print(e)
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
                print("Config is now {}".format(config))
                lastconfigchange = now()
            #print("Currtime: {0}".format(currtime))
            #print("Callback: {0}".format(lastcallback))
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
                ac_list.append( Color(rgb=(ampValue,ampValue,ampValue)))
                ac_list.append( Color(rgb=(ampValue*0.6,ampValue*0.6,ampValue*0.6)))
            else:
                # CUSTOM COLORS BASED OFF OF STUFF aaa
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
