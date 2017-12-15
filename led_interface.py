#!/usr/bin/python
import serial, time, numpy
from colour import Color
import collections
import subprocess

global decoded

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
        time.sleep(0.005)
        led_send(ser, 6, colorList)
        if k == 0:
            n = 0
    return (in_data, pyaudio.paContinue)

def pya_callback(in_data, frame_count, time_info, status):
    config = 0
    global decoded
    decoded = numpy.fromstring(in_data, 'Float32')
    return (in_data, pyaudio.paContinue)


def led_send(sobj, addr,colors):
    raw_list = [addr]
    if len(colors) != 10:
        print("'colors' must be of length 10'")
        return
    for elem in colors:
        if elem[0] == '#':
            elem = elem[1:]
        raw_list.append(int(elem[2:4],16))
        raw_list.append(int(elem[4:6],16))
        raw_list.append(int(elem[0:2],16))
        raw_list.append(int('00',16))
    #print(repr(raw_list))
    send_data = bytearray(raw_list)
    #print(repr(send_data))
    #print(len(send_data))
    sobj.write(send_data)
    time.sleep(0.005)
    return send_data
    pass

if __name__ == '__main__':
    import pyaudio
    global decoded
    decoded = None
    # Setup code
    ser = serial.Serial('/dev/ttyAMA0', 115200, rtscts=1)
    minVal = 1
    maxVal = 0
    n = 0
    k = 0
    rollingArray = collections.deque(maxlen=100)
    rollingArraySmall = collections.deque(maxlen=5)
    rollingArray.append(0.0)
    rollingArraySmall.append(0.0)

    WIDTH = 2
    CHANNELS = 2
    RATE = 48000
    FORMAT = pyaudio.paFloat32

    paobj = pyaudio.PyAudio()

    stream = paobj.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    output=True,
                    stream_callback=pya_callback)
    #                stream_callback=pya_nightlight_callback)

    stream.start_stream()
    config = 0

    while stream.is_active():
        if type(decoded) == type(None):
            continue
        if n == 10:
           k = (k+1)%2 
        n = (n+1)%20
        #print(k,n)
        amplitude = numpy.sqrt(numpy.mean(numpy.square(decoded)))
        amplitude = numpy.sum(numpy.absolute(decoded))
        rollingArray.append(amplitude)
        rollingArraySmall.append(amplitude)
        #maxVal = max(rollingArray) if max(rollingArray) > 0.1 else 0.3
        #minVal = min(rollingArray) if min(rollingArray) < 0.4 else 0.04
        #maxVal = amplitude if amplitude > maxVal else maxVal
        #minVal = amplitude if amplitude < minVal else minVal
        print(len(decoded))
        maxVal = max(rollingArray)
        minVal = min(rollingArray)
        #minVal = min(rollingArray)
        #maxVal = 0.8
        print(amplitude, minVal, maxVal)

        amplitude = sum(rollingArraySmall)/len(rollingArraySmall)
        #amplitudeColor = Color(hsl=(0, 0, (amplitude/(maxVal-minVal))))
        ampValue = (min(1,(amplitude-minVal)/(maxVal-minVal)))
        if config == 1:
            amplitudeColor = Color(rgb=(ampValue,0,0))
            amplitudeColor2 = Color(rgb=(0,ampValue,0))
        else:
            amplitudeColor = Color(rgb=(0,ampValue,ampValue))
            amplitudeColor2 = Color(rgb=(0,0,ampValue))
        #amplitudeColor = Color(hsv=(0.5,ampValue,ampValue))
        #amplitudeColor2 = Color(hsv=(0.75,ampValue,ampValue))
        pattern1 = ([amplitudeColor.hex_l] + [amplitudeColor2.hex_l])*5
        pattern2 = ([amplitudeColor2.hex_l] + [amplitudeColor.hex_l])*5
        if k:
            colorList = pattern1
            colorList2 = pattern2
        else:
            colorList = pattern2
            colorList2 = pattern1
        #print(colorList)
        led_send(ser, 6, colorList)
        time.sleep(0.005)
        #time.sleep(0.025)
        led_send(ser, 5, colorList2)
        #time.sleep(0.025)
        time.sleep(0.005)
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
