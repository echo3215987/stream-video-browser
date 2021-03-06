#!/usr/bin/python3
#coding=utf-8
import serial
import datetime
import subprocess
import re
import os
import sys
red=0
green=0
blue=0

#ser = serial.Serial('/dev/ttyUSB0',baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=2, xonxoff=False, rtscts=False, dsrdtr=False)


class ColorSensor:
    logfile="ttyUSB0.txt" #for debug=
    def __init__(self):
        # Initail 
        if os.path.exists(self.logfile):
            os.system("rm "+self.logfile)                
        ser = serial.Serial()
        ser.port = "/dev/ttyUSB0"
         
        #115200,N,8,1
        ser.baudrate = 9600 #115200
        ser.bytesize = serial.EIGHTBITS #number of bits per bytes
        ser.parity = serial.PARITY_NONE #set parity check
        ser.stopbits = serial.STOPBITS_ONE #number of stop bits
         
        ser.timeout = 0.5          #non-block read 0.5s
        ser.writeTimeout = 0.5     #timeout for write 0.5s
        ser.xonxoff = False    #disable software flow control
        ser.rtscts = False     #disable hardware (RTS/CTS) flow control
        ser.dsrdtr = False     #disable hardware (DSR/DTR) flow control
         
        try: 
            ser.open()
        except Exception as ex:
            print ("open serial port error " + str(ex))
    def pi_serial(self): #for study
        global red
        global green
        global blue
        
        ser = serial.Serial('/dev/ttyUSB0',9600) #115200
        
        while True: #loop
            read_serial=ser.readline()
            while len(read_serial)<20: #skip Incomplete data of readline() 
                read_serial=ser.readline()
            if not read_serial[0:6]=="b'red:": #align the bytes of read_serialserial
                read_serial=ser.readline()
            str_read = read_serial.rstrip().decode("UTF-8", "replace")
            color = str_read.split(",")# red:0000,green:0000,blue:0000, split by "," 
            
            #get RGB values
            red_us = int(color[0].split(":")[1]) # red:0000, split by ":", and get values  
            green_us = int(color[1].split(":")[1])
            blue_us = int(color[2].split(":")[1])
            
            #skip r/g/b_us=0, (1/0)*1000000
            if red_us != 0:
                red = float((1/red_us)*1000000) # abs() is Absolute value. f=1/T us *1000000.
            else: 
                red=0
            if green_us != 0:
                green = float((1/green_us)*1000000) # abs() is Absolute value. f=1/T us *1000000.
            else: 
                green=0
            if blue_us != 0:
                blue = float((1/blue_us)*1000000) # abs() is Absolute value. f=1/T us *1000000.
            else: 
                blue=0
                
            summary = "red:"+str(red)+", green:"+str(green)+", blue:"+str(blue)
            print(summary)
            os.system("echo "+str(datetime.datetime.now())+", "+summary+" >>ttyUSB0.txt")
        ser.close()
    def timetofrequency(self, time): #duration time to frequency
        if time != 0:
            frequency = float((1/time)*1000000) # f=1/T us *1000000.
        else: 
            frequency=0
        return frequency
    def get_sensor_value(self,getcolor): #for DCT2.0. color = "red", "green" or "blue"
        red=0
        green=0
        blue=0
        red_us=0.0
        green_us=0.0
        blue_us=0.0
        #logfile="ttyUSB0.txt" #for debug

        ser = serial.Serial('/dev/ttyUSB0',9600) #115200

        str_read = ""
        while str_read=="": #if one of process has error, redo
            while str_read=="": #if read data not match, redo read
                read_serial=ser.readline()
                #print("\nbefore",str(len(read_serial)),read_serial)
                try:
                    str_read_utf8 = read_serial.rstrip().decode("UTF-8", "replace")
                    #print("str_read_utf8:",str_read_utf8)
                except:
                    print("retry")
                list_read = re.findall(r"\w*:\d*.\d*,\w*:\d*.\d*,\w*:\d*.\d*",str_read_utf8)
                #print("list_read:",list_read,type(list_read)) #list_read: ['red:7735,green:1946,blue:8814'] <class 'list'>
                str_read = "".join(list_read) #list to str
                #print("str_read",str_read,type(str_read))


            #print("after",str(len(read_serial)),read_serial)
            color = str_read.split(",")# red:0000,green:0000,blue:0000, split by ","
            #print("color: ",color[0])
            
            try:
            #get R,G,B values
                red = float(color[0].split(":")[1]) # red:0000, split by ":", and get values
                green = float(color[1].split(":")[1])
                blue = float(color[2].split(":")[1])
                #print(red)
            except: #if error, retry
                str_read==""
                print("error",Exception)
            #skip r/g/b_us=0, (1/0)*1000000
            #red = self.timetofrequency(red_us)
            #green = self.timetofrequency(green_us)
            #blue = self.timetofrequency(blue_us)

            summary = "red:"+str(red)+", green:"+str(green)+", blue:"+str(blue)
            print(summary) #for debug
            os.system("echo "+str(datetime.datetime.now())+", "+summary+" >>"+self.logfile) #for debug
        ser.close()
        
        if getcolor=="red": #report to webstreaming.py with 1 color value.
            return red
        elif getcolor=="green":
            return green
        elif getcolor=="blue":
            return blue

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
after 34 b'red:1\xf5red:178,green:683,blue:161\r\n'

"""

    
