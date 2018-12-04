#!/usr/bin/python
from __future__ import print_function
import serial, time, numpy
from colour import Color
import collections
import subprocess
from datetime import datetime

global sending
global decoded
global lastcallback
global some_modulus

def pya_nightlight_callback(in_data, frame_count, time_info, status):
    global ser
    global n # tripped value
    global k # timer
    global rollingArray
    global rollingArraySmall
    decoded = numpy.fromstring(in_data, 'Float32')
    amplitude = numpy.sqrt(numpy.mean(numpy.square(decoded)))
    rollingArraySmall.append(amplitude)
    rollingArray.append(amplitude)
    noise_floor = sum(rollingArray)/len(rollingArray)
    amplitude = sum(rollingArraySmall)/len(rollingArraySmall)
    k = (k-1) if k > 0 else 0
    if amplitude > 0.05:
        n = 1
        k = 250
    amplitudeColor = Color(rgb=(0,k/500.0,0)).hex_l
    colorList = [amplitudeColor] * 10
    #print noise_floor, amplitude
    if n == 1:
        led_send(ser, 5, colorList)
        #time.sleep(0.025)
        #time.sleep(0.005)
        led_send(ser, 6, colorList)
        if k == 0:
            n = 0
    return (in_data, pyaudio.paContinue)

def pya_callback(in_data, frame_count, time_info, status):
    config = 0
    global decoded
    global lastcallback
    lastcallback = float(datetime.now().strftime('%s.%f'))
    decoded = numpy.fromstring(in_data, 'Float32')
    return (in_data, pyaudio.paContinue)

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

def led_send(sobj,amplitude,colors):
    global some_modulus
    global sending
    if sending == True:
        return
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
    whitecorrect_list = whitecorrect(raw_list)
    raw_list = raw_list*75 + whitecorrect_list*(150) + [0]*12
    raw_list = [0]+ raw_list
    #print(repr(raw_list))
    #raw_list = [0] + [255]*1359
    #print(some_modulus)
    add_runner(raw_list,some_modulus%1362,int(255*ampValue),5)
    
    add_runner(raw_list,(some_modulus+150)%1362,int(255*ampValue),5)
    
    add_runner(raw_list,(some_modulus+300)%1362,int(255*ampValue),5)
    
    #thislist = 150*[128]+1200*[0]
    #send_data = bytearray([0]+rotated_list)
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
    #print("Successfully? sent {} bits".format(bitssent))
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

if __name__ == '__main__':
    import pyaudio
    global decoded
    global lastcallback
    global some_modulus
    decoded = None
    # Setup code
    #ser = serial.Serial('/dev/ttyAMA0', 2000000, rtscts=1, writeTimeout=0)
    ser = serial.Serial('/dev/ttyACM0', 500000, writeTimeout=0)
    print(ser.readline())
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

    numpy.seterr(all='raise')
    auto_restart = 1
    old_decoded = None
    sending = False
    while (auto_restart):
        paobj = pyaudio.PyAudio()
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
            if type(decoded) == type(None):
                if waiting == False:
                    print("Waiting for stream", end ="")
                    waiting = True
                else:
                    print(".", end="")
                continue
            waiting = False
            currtime = float(datetime.now().strftime('%s.%f'))
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
            n = (n+1)%40
            #print(k,n)
            amplitude = numpy.sqrt(numpy.mean(numpy.square(decoded)))
            amplitude = numpy.sum(numpy.absolute(decoded))
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
                ampValue = (min(1,(amplitude-minVal)/(maxVal-minVal))) 
            except Exception as e:
                print("aaaa something went wrong in the stream, restarting")
                break
            #print(ampValue)
            if config == 0:
                amplitudeColor = Color(rgb=(ampValue,0,0))
                amplitudeColor2 = Color(rgb=(0,ampValue,0))
            elif config == 1:
                amplitudeColor = Color(rgb=(0,ampValue,ampValue))
                amplitudeColor2 = Color(rgb=(0,0,ampValue))
            elif config == 2:
                amplitudeColor = Color(rgb=(ampValue,ampValue*0.6,ampValue*0.6))
                amplitudeColor2 = Color(rgb=(ampValue,ampValue*0.6,ampValue*0.6))
            else:
                amplitudeColor =  Color(rgb=(ampValue,ampValue,ampValue))
                amplitudeColor2 =  Color(rgb=(ampValue*0.6,ampValue*0.6,ampValue*0.6))
                
            #amplitudeColor = Color(hsv=(0.5,ampValue,ampValue))
            #amplitudeColor2 = Color(hsv=(0.75,ampValue,ampValue))
            pattern1 = ([amplitudeColor.hex_l] + [amplitudeColor2.hex_l])
            pattern2 = ([amplitudeColor2.hex_l] + [amplitudeColor.hex_l])
            if k:
                colorList = pattern1
                colorList2 = pattern2
            else:
                colorList = pattern2
                colorList2 = pattern1
            #print(colorList)
            #led_send(ser, 6, colorList)
            #time.sleep(0.005)
            #time.sleep(0.025)
            led_send(ser, ampValue, colorList)
            #time.sleep(0.050)
        stream.stop_stream()
        stream.close()
        paobj.terminate()

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
