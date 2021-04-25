#!/usr/bin/python3
#coding=utf-8
import serial
import datetime
import queue
import subprocess
import re
import os
import sys
import RPi.GPIO as GPIO
import time
red=0
green=0
blue=0
q_green = queue.Queue()
q_blue = queue.Queue()
s2_pin = 23 #gpio
s3_pin = 22
signal_pin = 27
#ser = serial.Serial('/dev/ttyUSB0',baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=2, xonxoff=False, rtscts=False, dsrdtr=False)

class ColorSensor:
    com='/dev/ttyUSB0'
    LED=0 #LED 1=ON or 0=OFF
    logfile="ttyUSB0.txt" #for debug=
    usb_sensor_type=True #USB first and then GPIO
    os.system("ls /dev/ttyUSB*") 
    
    def __init__(self):
        # Initail
        if os.path.exists(self.logfile):
            os.system("rm "+self.logfile)
                            
        ser = serial.Serial()
        ser.port = self.com        
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
            print("Reading...")
            if self.LED==0:
                ser.write(b"\xA5\x6A\x0F") #LED OFF.A5+cmd+sum. sum=A5+cmd low 8 bits.
            elif self.LED==1:
                ser.write(b"\xA5\x60\x05") #LED ON.  
            else:
                pass
        except Exception as ex:
            #print ("open serial port error " + str(ex))
            #print("com:", self.com[-1:])
            if int(self.com[-1:])<4: #if no USB sensor, change to GPIO sensor.
                self.com='/dev/ttyUSB'+str(int(self.com[-1:])+1)
                #print("com:", self.com)
                self.usb_sensor_type=True
                self.__init__() #re-run for com0~3                
            elif int(self.com[-1:])>3:
                print("go to gpio")
                self.usb_sensor_type=False
                self.init_gpio()
            else:
                print("Init fail: Color sensor not found")
    def init_gpio(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(signal_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(s2_pin, GPIO.OUT)
        GPIO.setup(s3_pin, GPIO.OUT)
    def usb_sensor(self,getcolor): #for DCT2.0. color = "red", "green" or "blue"
        #logfile="ttyUSB0.txt" #for debug
        #os.system("ls /dev/ttyUSB*")  
        #print("ttyUSB0 reading...")
        if(getcolor=="red"):
            ser = serial.Serial(self.com,9600) #115200, 9600
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
                            os.system("echo "+str(datetime.datetime.now())+", "+str(rgb)+" >>"+self.logfile)
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
    def gpio_sensor(self, color):
        # TCS3200 color sensor use s2, s3 pin to select the photodiode type
        # red   : s2 = 0, s3 = 0
        # green : s2 = 1, s3 = 1
        # blue  : s2 = 0, s3 = 1
        if color == 'red':
            GPIO.output(s2_pin, GPIO.LOW)
            GPIO.output(s3_pin, GPIO.LOW)
        elif color == 'blue':
            GPIO.output(s2_pin, GPIO.LOW)
            GPIO.output(s3_pin, GPIO.HIGH)
        elif color == 'green':
            GPIO.output(s2_pin, GPIO.HIGH)
            GPIO.output(s3_pin, GPIO.HIGH)
        
        NUM_CYCLES = 10
        
        # delay 0.3s to wait GPIO stable 
        time.sleep(0.3)
        
        start = time.time()
        for impulse_count in range(NUM_CYCLES):
                GPIO.wait_for_edge(signal_pin, GPIO.FALLING, timeout=160)
        duration = time.time() - start
        color = NUM_CYCLES /duration
        return color
    
    def get_sensor_value(self,getcolor): #for DCT2.0. color = "red", "green" or "blue"
        #print("self.usb_sensor",type(self.usb_sensor_flag))
        #print("self.usb_sensor",self.usb_sensor_type)
        if self.usb_sensor_type==True:
            #print("USB sensor")
            return self.usb_sensor(getcolor)
        elif self.usb_sensor_type==False:
            #print("GPIO sensor")
            return self.gpio_sensor(getcolor)
        else:
            print("Color sensor not found")
        
if __name__ == '__main__':
    cs = ColorSensor()
    for i in range(10):    
        red = cs.get_sensor_value("red")
        green = cs.get_sensor_value("green")
        blue = cs.get_sensor_value("blue")
    
    while True:
        red = cs.get_sensor_value("red")
        green = cs.get_sensor_value("green")
        blue = cs.get_sensor_value("blue")
        print(red, green, blue)
    GPIO.cleanup()
    








