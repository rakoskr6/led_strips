import serial, time
ser = serial.Serial('/dev/ttyACM0', 500000, writeTimeout=0)
while not ser.in_waiting:
    continue
print(ser.read(ser.in_waiting))
time.sleep(1)
i = 0
print('GO!')
time.sleep(1)
'''
while(1):
   time.sleep(0.016)
   ser.write(bytearray([1,0,0,i%255]))
   time.sleep(0.016)
   ser.write(bytearray([1,0,i%255,0]))
   time.sleep(0.016)
   ser.write(bytearray([1,i%255,0,0]))
   i += 1
'''
