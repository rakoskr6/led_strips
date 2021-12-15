#!/usr/bin/python
from __future__ import print_function
from colour import Color
from datetime import datetime
from scipy import signal
import collections
import phue
import serial, time, numpy
import subprocess
import thread

global sending
global decoded
global lastcallback
global some_modulus
global b,a
global lights

def pya_callback(in_data, frame_count, time_info, status):
    config = 0
    global decoded
    global lastcallback, b, a
    lastcallback = now
    decoded = numpy.fromstring(in_data, 'Float32')
    return (in_data, pyaudio.paContinue)

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
    for i in range(width):
        inList[1+((pos+i)%454)*3] = min(255,2*val)
        inList[2+((pos+i)%454)*3] = min(255,2*val)
        inList[3+((pos+i)%454)*3] = min(255,2*val)

def now():
    return float(datetime.now().strftime('%s.%f'))

def hue_send(index, inColor):
    global lights
    hueHue = int(inColor.hue*65535)
    hueSaturation = int(inColor.saturation*254)
    hueBrightness = int(inColor.luminance*254)
    lights[index].hue = hueHue
    lights[index].saturation = hueSaturation
    lights[index].brightness = hueBrightness

def led_send(sobj,amplitude,colors):
    global some_modulus
    global sending
    #if sending == True:
    #    return
    raw_list = []
    for elem in colors:
        if elem[0] == '#':
            elem = elem[1:]
        raw_list.append(int(elem[0:2],16))
        raw_list.append(int(elem[2:4],16))
        raw_list.append(int(elem[4:6],16))
        #raw_list.append(int('00',16))   
    whitecorrect_list = whitecorrect(raw_list)
    raw_list = raw_list*75 + whitecorrect_list*(150) + [0]*12
    #print(repr(raw_list))
    #raw_list = [0] + [255]*1359
    #print(some_modulus)
    raw_list = [0] + raw_list
    add_runner(raw_list,some_modulus%1362,int(255*ampValue),10)
    
    add_runner(raw_list,(some_modulus+150)%1362,int(255*ampValue),10)
    
    add_runner(raw_list,(some_modulus+300)%1362,int(255*ampValue),10)
    
    #thislist = 150*[128]+1200*[0]
    #send_data = bytearray([0]+rotated_list)
    raw_list = addnoise(raw_list)
    send_data = bytearray(raw_list)
    #send_data = bytearray([0] + raw_list*1350)
    #raw_list = 1350*[20]
    #raw_list[some_modulus%len(raw_list)] = 128
    some_modulus += 1
    #send_data = bytearray([0]+raw_list)
    #print(send_data)
    #print(repr(send_data) + str(len(send_data)))
    #print(len(send_data))
    #print("attempting to send bits")
    sending = True
    #print(sobj.read(sobj.in_waiting))
    bitssent = sobj.write(send_data)
    time.sleep(0.044)
    sending = False
    #print("Successfully sent {} bytes".format(bitssent))
    #time.sleep(0.005)
    #return send_data
    return

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

if __name__ == '__main__':
    import pyaudio
    global decoded
    global lastcallback
    global some_modulus
    global lastconfigchange
    global b, a
    decoded = None
    bridgeEnabled = False
    # Set up serial bridge to Arduino running LED drivers
    ser = serial.Serial('/dev/ttyACM0', 500000, writeTimeout=0)
    # Flush out the serial interface 
    # theoretically this should reset the LEDS
    print(ser.readline())
   
    # Attempt to connect to the Philips Hue Bridge
    ''' 
    huebridge = phue.Bridge('192.168.1.171')
    try:
        print("Connecting to hue...")
        huebridge.connect()
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
    '''
    minVal = 1
    maxVal = 0
    n = 0
    k = 0
    some_modulus = 0
    rollingArray = collections.deque(maxlen=100)
    rollingArraySmall = collections.deque(maxlen=5)
    rollingArray.append(0.0)
    rollingArraySmall.append(0.0)
    badcount = 0
    WIDTH = 2
    CHANNELS = 2
    RATE = 48000
    FORMAT = pyaudio.paFloat32
    c1_r, c1_g, c1_b, c2_r, c2_g, c2_b = reloadColors()
    numpy.seterr(all='raise')
    auto_restart = True
    old_decoded = None
    sending = False
    lastconfigchange = now()
    while (auto_restart):
        paobj = pyaudio.PyAudio()
        stream = paobj.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        output=True,
                        stream_callback=pya_callback)
        stream.start_stream()
        config = 4 
        waiting = False
        while stream.is_active():
            if type(decoded) == type(None):
                if waiting == False:
                    print("Waiting for stream", end ="")
                    waiting = True
                else:
                    print(".", end="")
                continue
            waiting = False
            currtime = now()
            if (currtime - lastconfigchange) > 10:
                config = (config+1)%5
                lastconfigchange = now()
            #print("Currtime: {0}".format(currtime))
            #print("Callback: {0}".format(lastcallback))
            if (currtime - lastcallback) > 0.25:
                print("BAD!")
                badcount += 1
                if badcount > 5:
                    badcount = 0
                    break
            if n == 20:
                k = (k+1)%2 
                c1_r, c1_g, c1_b, c2_r, c2_g, c2_b = reloadColors()
                '''
                baseColor = Color(rgb=(c1_r,c1_g,c1_b))
                baseColor2 = Color(rgb=(c2_r,c2_g,c2_b))
                thread.start_new_thread(hue_send, (0, baseColor))
                thread.start_new_thread(hue_send, (1, baseColor))
                thread.start_new_thread(hue_send, (2, baseColor2))
                '''
            n = (n+1)%40
            amplitude = numpy.sum(numpy.absolute(decoded))
            rollingArray.append(amplitude)
            rollingArraySmall.append(amplitude)
            maxVal = max(rollingArray)
            minVal = min(rollingArray)
            amplitude = sum(rollingArraySmall)/len(rollingArraySmall)
            try: 
                ampValue = (min(1,(amplitude-minVal)/(maxVal-minVal))) 
            except Exception as e:
                print("aaaa something went wrong in the stream, restarting")
                break
            #print(ampValue)
            if config == 0:
                amplitudeColor = Color(rgb=(ampValue,0,0))
                amplitudeColor2 = Color(rgb=(0,ampValue,0))
            elif config == 2:
                amplitudeColor = Color(rgb=(0,ampValue,ampValue))
                amplitudeColor2 = Color(rgb=(0,0,ampValue))
            elif config == 1:
                amplitudeColor = Color(rgb=(ampValue,ampValue*0.6,ampValue*0.4))
                amplitudeColor2 = Color(rgb=(ampValue,ampValue*0.6,ampValue*0.4))
            elif config == 3:
                amplitudeColor =  Color(rgb=(ampValue,ampValue,ampValue))
                amplitudeColor2 =  Color(rgb=(ampValue*0.6,ampValue*0.6,ampValue*0.6))
            else:
                # CUSTOM COLORS BASED OFF OF STUFF aaa
                amplitudeColor = Color(rgb=(ampValue*c1_r,ampValue*c1_g,ampValue*c1_b))
                amplitudeColor2 = Color(rgb=(ampValue*c2_r,ampValue*c2_g,ampValue*c2_b))
            pattern1 = ([amplitudeColor.hex_l] + [amplitudeColor2.hex_l])
            pattern2 = ([amplitudeColor2.hex_l] + [amplitudeColor.hex_l])
            if k:
                colorList = pattern1
                colorList2 = pattern2
            else:
                colorList = pattern2
                colorList2 = pattern1
            led_send(ser, ampValue, colorList)
        stream.stop_stream()
        stream.close()
        paobj.terminate()
    # close serial after gracefully terminating?
    ser.close()
