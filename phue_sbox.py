import phue

b = phue.Bridge('192.168.1.171')
lights = b.get_light_objects()
lights.pop(1)
print(lights)
for light in lights:
    light.transitiontime = 0
    #light.colormode = 'xy'
    print("{}".format(light.colormode))
