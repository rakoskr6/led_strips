#!/usr/bin/python
import serial, time
from colour import Color

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

ser = serial.Serial('/dev/ttyAMA0', 115200, rtscts=1)

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

ser.close()
