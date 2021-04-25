#!/usr/bin/python3
#coding=utf-8
import serial
import datetime
import queue
import subprocess
import re
import os
import sys
red=0
green=0
blue=0
q_green = queue.Queue()
q_blue = queue.Queue()
#ser = serial.Serial('/dev/ttyUSB0',baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=2, xonxoff=False, rtscts=False, dsrdtr=False)
com='/dev/ttyUSB0'
LED=0 #LED 1=ON or 0=OFF
logfile="ttyUSB0.txt" #for debug=

class ColorSensor:
    
    def __init__(self):
        # Initail
        if os.path.exists(logfile):
            os.system("rm "+logfile)
            
        os.system("ls /dev/ttyUSB*")
        ser = serial.Serial()
        ser.port = com

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
            print("ttyUSB0 reading...")
            if LED==0:
                ser.write(b"\xA5\x6A\x0F") #LED OFF.A5+cmd+sum. sum=A5+cmd low 8 bits.
            elif LED==1:
                ser.write(b"\xA5\x60\x05") #LED ON.  
            else:
                pass
        except Exception as ex:
            print ("open serial port error " + str(ex))

    def get_sensor_value(self,getcolor): #for DCT2.0. color = "red", "green" or "blue"
        #logfile="ttyUSB0.txt" #for debug
        #os.system("ls /dev/ttyUSB*")  
        #print("ttyUSB0 reading...")
        if(getcolor=="red"):
            ser = serial.Serial(com,9600) #115200, 9600
            #while True:
            if (ser.read()==b"Z"):
                if (ser.read()==b"Z"):
                    if (ser.read()==b"E"):
                        if (ser.read()==b"\x03"):
                            red=int.from_bytes(ser.read(), "big")#255 is white, 0 is black
                            green=int.from_bytes(ser.read(), "big")
                            blue=int.from_bytes(ser.read(), "big")
                            c=int.from_bytes(ser.read(), "big")
                            q_green.put(green)
                            q_blue.put(blue)
                            rgb = "red:"+str(red)+", green:"+str(green)+", blue:"+str(blue)
                            print(rgb)
                            os.system("echo "+str(datetime.datetime.now())+", "+str(rgb)+" >>"+logfile)
                            return red
            
        elif(getcolor=="green"):
            green=q_green.get()
            #print(green)
            return green
        elif(getcolor=="blue"):
            blue=q_blue.get()
            #print(blue)
            return blue
        else:
            print("wrong value")
        ser.close()
if __name__ == '__main__':
    cs = ColorSensor()
    for i in range(10):    
        cs.get_sensor_value("red")
        cs.get_sensor_value("green")
        cs.get_sensor_value("blue")










