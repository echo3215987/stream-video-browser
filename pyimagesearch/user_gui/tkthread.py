# History
# kenney_chen
# 2021/04/13
# - 移除 GUI - Calbration 按鈕
# - 移除 相關Calbration  code.

# Echo_Lee
# - 2021/04/15
# - 異常訊息顯示在Pi GUI畫面

# import the necessary packages
from PIL import Image, ImageTk
import cv2
import datetime
import os
import subprocess
import tkinter as tk
import threading
#import RPi.GPIO as GPIO

class TKThread():
    
    switch = 0   # 0:status, 1:video, 2:calibrate
    recovery = 0 # 0:no recovery, 1:occured recovery
    text_id = None
    frame = None
    iscalibrate = False
    calibrateColor = ''
    
    def __init__(self):
        self.ip = ''
        self.status = 'Normal'
        self.item = ''
    
    def closeWindwos(self):
        # find the process number and kill it
        pid = os.getpid()
        args = ('kill', str(pid))
        
        #GPIO.cleanup()
        
        debugDate = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with open("/home/pi/debugLog.txt", 'a') as f:
            f.write("%s %s\n" % (debugDate, 'Close the process vai kill command'))
            
        subprocess.call('%s %s' % args, shell=True)
        
      
    def functionRecovery(self):
        self.recovery = 1
    
    def functionSwitch(self):
        if self.switch != 1:
            self.text_id = None
            self.canvas_status.delete("all")
            self.switch = 1
        elif self.switch != 0:
            self.switch = 0
            self.text_id = None
            self.canvas_status.delete("all")
            self.reportStatus(self.status)
      
    def _reportStatus(self, status):
        self.status = status
        self.canvas_status.delete("all")
        
        if status == 'Normal':
            self.canvas_status.create_text(240, 105, text=self.ip, font='Verdana 20 bold', fill='#ffffff')
            self.canvas_status.create_text(240, 150, text='Stress Testing', font='Verdana 20 bold', fill='#ffffff')
            self.canvas_status.config(bg="#90ee90")
            
    def reportStatus(self, status):
        self.status = status
        self.canvas_status.delete("all")

        if status == 'Stop':
            self.canvas_status.create_text(240, 105, text=self.ip, font='Verdana 20 bold', fill='#ffffff')
            self.canvas_status.config(bg="#90ee90")
            self.canvas_status.create_text(240, 150, text='Test Ending', font='Verdana 20 bold', fill='#ffffff')
            self.canvas_status.config(bg="#90ee90")
        elif status != 'Normal':
            if status == 'HANG UP':
                self.canvas_status.create_text(240, 105, text='Hang Up', font='Verdana 20 bold',fill='#ffffff')
            elif status == 'BLACK':
                self.canvas_status.create_text(240, 105, text='Black Screen', font='Verdana 20 bold',fill='#ffffff')
            elif status == 'BSOD':
                self.canvas_status.create_text(240, 105, text='Blue Screen', font='Verdana 20 bold',fill='#ffffff')                     
            self.canvas_status.config(bg="red")
            
        elif status == 'Normal':
            self.canvas_status.create_text(240, 105, text=self.ip, font='Verdana 20 bold', fill='#ffffff')
            self.canvas_status.create_text(240, 150, text='Stress Testing', font='Verdana 20 bold', fill='#ffffff')
            self.canvas_status.config(bg="#90ee90")
    
    def showVideo(self, frame):
        self.frame = frame
        self.frame = cv2.resize(self.frame, (480, 240))
        image2 = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        image2 = Image.fromarray(image2)
        image2 = ImageTk.PhotoImage(image2)
        if self.text_id == None:
            self.text_id = self.canvas_status.create_image(0, 0, image = image2, anchor = tk.NW)
        else:
            self.canvas_status.itemconfig(self.text_id, image = image2)
            self.canvas_status.image = image2
    
    def startService(self, ip, version):

        # |-----------------------| #
        # |                       | #
        # |                       | #
        # |        Display        | #
        # |                       | #
        # |-----------------------| #
        # |VideoBTN|RecBTN|CaliBTN| #
        # |-----------------------| #
        
        self.root = tk.Tk()
        self.root.title("System Status Detection (%s)" % version ) 
        self.root.geometry('480x290')
        self.root.resizable(0,0)
        self.root.protocol("WM_DELETE_WINDOW", self.closeWindwos)
        
        self.ip = ip
        
        # layout
        
        self.canvas_status = tk.Canvas(self.root, bg='#90ee90')
            
        self.button_recovery = tk.Button(self.root, text="Recover", command=self.functionRecovery)
        self.button_switch = tk.Button(self.root, text="Camera View", command=self.functionSwitch)
        
        self.button_recovery.place(x=240, y=240, width=240, height=50)
        self.button_switch.place(x=0, y=240, width=240, height=50)
        self.text_id = self.canvas_status.place(x=0, y=0, width=480, height=242)
        
        self.canvas_status.create_text(240, 105, text=self.ip, font='Verdana 20 bold', fill='#ffffff')
        self.canvas_status.config(bg="#90ee90")
        
        self.root.mainloop()

        
    