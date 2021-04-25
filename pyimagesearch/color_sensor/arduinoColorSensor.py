#!/usr/bin/python3
#coding=utf-8
import serial
import datetime
import subprocess
import os
import sys
red=0
green=0
blue=0

#ser = serial.Serial('/dev/ttyUSB0',baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=2, xonxoff=False, rtscts=False, dsrdtr=False)


def check_color(red,green,blue): #for study
    #check which one color
    if int(red)>4500 and int(green)<1000 and int(blue)<1000:
        result = "red"
    elif int(red)>1000 and int(red)<2000 and int(green) >3500 and int(blue)>1000 and int(blue)<2000:
        result = "green"
    elif int(red) <500 and int(green)>500 and int(green)<1500 and int(blue)>3000:
        result = "blue"
    elif  int(red)>5000 and int(green)>4000 and int(blue)>4000:
        result = "white"
    elif  (int(red)<300 and int(green)<300 and int(blue)<300) and (int(red)>45 and int(green)>45 and int(blue)>45):
        result = "black w"
    elif  int(red)<50 and int(green)<50 and int(blue)<50:
        result = "black wo"
    else:
        result = "unknow"
    return result
def pi_serial(): #for study
    global red
    global green
    global blue
    
    ser = serial.Serial('/dev/ttyUSB0',115200)
    
    while True:
        read_serial=ser.readline()
        while len(read_serial)<20: #skip Incomplete data of readline() 
            read_serial=ser.readline()            
        if not read_serial[0:5]=="b'red": #align the bytes of read_serialserial
            read_serial=ser.readline()            
        str_read = read_serial.rstrip().decode("UTF-8", "replace")
        color = str_read.split(",")# red:0000,green:0000,blue:0000, split by "," 
        
        #get RGB values
        red_us = int(color[0].split(":")[1]) # red:0000, split by ":", and get values  
        green_us = int(color[1].split(":")[1])
        blue_us = int(color[2].split(":")[1])
        
        red = int((1/red_us)*1000000) # abs() is Absolute value. f=1/T us *1000000.
        green = int((1/green_us)*1000000) 
        blue = int((1/blue_us)*1000000)
        
        result = check_color(red,green,blue)
            
        summary = "red:"+str(red)+", green:"+str(green)+", blue:"+str(blue)+" "+result
        print(summary)
        os.system("echo "+str(datetime.datetime.now())+", "+summary+" >>ttyUSB0.txt")
    ser.close()

class ColorSensor:
    def __init__(self):
        # Initail 
        pass
    def get_sensor_value(self,getcolor): #for DCT2.0. color = "red", "green" or "blue"
        red=0
        green=0
        blue=0
        logfile="ttyUSB0.txt"
        if os.path.exists(logfile):
            os.system("rm "+logfile)
            print("rm older log")
        
        ser = serial.Serial('/dev/ttyUSB0',115200)
        read_serial=ser.readline()
        #print("before",str(len(read_serial)),read_serial)
        while len(read_serial)<20: #fix know issue 1. skip Incomplete data of readline() 
            read_serial=ser.readline()
        if not read_serial[0:5]=="b'red": #fix know issue 2. align the bytes of read_serialserial
            read_serial=ser.readline()
        
            #print("after",str(len(read_serial)),read_serial)        
        str_read = read_serial.rstrip().decode("UTF-8", "replace")
        color = str_read.split(",")# red:0000,green:0000,blue:0000, split by "," 
            
        #get RGB values
        red_us = int(color[0].split(":")[1]) # red:0000, split by ":", and get values  
        green_us = int(color[1].split(":")[1])
        blue_us = int(color[2].split(":")[1])
        
        #skip rgb=0, (1/0)*1000000
        if red_us != 0:
            red = int((1/red_us)*1000000) # abs() is Absolute value. f=1/T us *1000000.
        else: 
            red=0
        if green_us != 0:
            green = int((1/green_us)*1000000) # abs() is Absolute value. f=1/T us *1000000.
        else: 
            green=0
        if blue_us != 0:
            blue = int((1/blue_us)*1000000) # abs() is Absolute value. f=1/T us *1000000.
        else: 
            blue=0
            
        summary = "red:"+str(red)+", green:"+str(green)+", blue:"+str(blue)
        print(summary)
        os.system("echo "+str(datetime.datetime.now())+", "+summary+" >>"+logfile)
        ser.close()
        
        return red, green, blue    
if __name__ == '__main__':
    #pi_serial()
    cs = ColorSensor()
    print(cs.get_sensor_value("blue")) #return color value

"""
know issue 1.
Traceback (most recent call last):
  File "./arduinoColorSensor.py", line 50, in <module>
    pi_serial()
  File "./arduinoColorSensor.py", line 23, in pi_serial
    red = color[0].split(":")[1] # red:0000, split by ":", and get values
IndexError: list index out of range

know issue 2.
Traceback (most recent call last):
  File "./arduinoColorSensor.py", line 50, in <module>
    pi_serial()
  File "./arduinoColorSensor.py", line 19, in pi_serial
    str_read = read_serial.decode("UTF-8").rstrip()
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xfe in position 3: invalid start byte

know issue 3.
Traceback (most recent call last):
  File "/usr/lib/python3.7/threading.py", line 917, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.7/threading.py", line 865, in run
    self._target(*self._args, **self._kwargs)
  File "./webstreaming.py", line 479, in detect_color
    red = statistics.mean(red_array)  
  File "/usr/lib/python3.7/statistics.py", line 311, in mean
    T, total, count = _sum(data)
  File "/usr/lib/python3.7/statistics.py", line 147, in _sum
    for n,d in map(_exact_ratio, values):
  File "/usr/lib/python3.7/statistics.py", line 229, in _exact_ratio
    raise TypeError(msg.format(type(x).__name__))
TypeError: can't convert type 'tuple' to numerator/denominator

# red_array: <class 'list'>   [142.5780485151746]
  red: <class 'float'>   142.5780485151746

"""

    