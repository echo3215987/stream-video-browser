#!/usr/bin/python3
from pyimagesearch.color_sensor import ColorSensor 

cs = ColorSensor()
print(cs.get_sensor_value("red"))
