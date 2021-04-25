#!/usr/bin/python3
#coding=utf-8
# import the necessary packages
import RPi.GPIO as GPIO
import time

s2_pin = 23
s3_pin = 22
signal_pin = 27

class ColorSensor:
    def __init__(self):
        # Initail the raspberry pi gpio
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(signal_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(s2_pin, GPIO.OUT)
        GPIO.setup(s3_pin, GPIO.OUT)

    def get_sensor_value(self, color):
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

cs = ColorSensor()
print(type(cs.get_sensor_value("red")))
