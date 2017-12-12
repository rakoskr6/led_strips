#!/usr/bin/python

from led_interface import led_send
import time, os, serial

#def ping_red():
ser = serial.Serial('/dev/ttyAMA0', 115200, rtscts=1)

color_red = 'FF0000'
color_green = '00FF00'
color_blue = '0000FF'
color_off = '000000'

color_list = [color_off]*10
color_list2 = [color_red]*10

led_send(ser, 6, color_list)
led_send(ser, 5, color_list)

time.sleep(0.1)

led_send(ser, 6, color_list2)
led_send(ser, 5, color_list2)

time.sleep(0.1)


led_send(ser, 6, color_list)
led_send(ser, 5, color_list)

time.sleep(0.1)

ser.close()
