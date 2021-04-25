#!/usr/bin/python3

# import the necessary packages
from imutils.video import VideoStream
from flask import Response, Flask, render_template, request, jsonify, send_from_directory
from pyimagesearch.color_sensor import ColorSensor
from pyimagesearch.motion_detection import SingleMotionDetector
from pyimagesearch.user_gui import TKThread
import configparser
import cv2
import datetime
import imutils
import numpy as np
import os
import re
import requests
import socket
import statistics
import subprocess
import sys
import threading
import time
import RPi.GPIO as GPIO

#######################################################
#         Load config file to initial setting         #
#######################################################
config = configparser.ConfigParser()
config.read('/home/pi/stream-video-browser/cameraConfig.ini')

APAddress = config.get('Network', 'APADDRESS')
serverAddress = config.get('Network', 'SERVERADDRESS')

serPort = config.get('Network', 'SERPORT')
checkVerAPI = config.get('API', 'CHECKVERSION')
postDataAPI = config.get('API', 'POSTDATA')

# total detect time = detect_duration * (detect_amount + 1) 
detect_duration = int(config.get('Detection', 'DURATION'))
detect_amount = int(config.get('Detection', 'AMOUNT'))

cali_average = int(config.get('Calibration', 'AVERAGE'))
cali_item1 = config.get('Calibration', 'ITEM1')
cali_item2 = config.get('Calibration', 'ITEM2')
cali_item3 = config.get('Calibration', 'ITEM3')
cali_timer1 = int(config.get('Calibration', 'TIMER1'))
cali_timer2 = int(config.get('Calibration', 'TIMER2'))
cali_timer3 = int(config.get('Calibration', 'TIMER3'))

Black_W_GR = float(config.get('Color', 'BLACK_W_GR'))
Black_W_BR = float(config.get('Color', 'BLACK_W_BR'))
Black_W_BG = float(config.get('Color', 'BLACK_W_BG'))
Black_WO_GR = float(config.get('Color', 'BLACK_WO_GR'))
Black_WO_BR = float(config.get('Color', 'BLACK_WO_BR'))
Black_WO_BG = float(config.get('Color', 'BLACK_WO_BG'))
Blue_GR = float(config.get('Color', 'BLUE_GR'))
Blue_BR = float(config.get('Color', 'BLUE_BR'))
Blue_BG = float(config.get('Color', 'BLUE_BG'))

#------Use RGB upper/lower to limit blue/black screen
Black_WO_RED_U = float(config.get('Color', 'BLACK_WO_RED_U'))
Black_WO_RED_D = float(config.get('Color', 'BLACK_WO_RED_D'))
Black_WO_GREEN_U = float(config.get('Color', 'BLACK_WO_GREEN_U'))
Black_WO_GREEN_D = float(config.get('Color', 'BLACK_WO_GREEN_D'))
Black_WO_BLUE_U = float(config.get('Color', 'BLACK_WO_BLUE_U'))
Black_WO_BLUE_D = float(config.get('Color', 'BLACK_WO_BLUE_D'))

Black_W_RED_U = float(config.get('Color', 'BLACK_W_RED_U'))
Black_W_RED_D = float(config.get('Color', 'BLACK_W_RED_D'))
Black_W_GREEN_U = float(config.get('Color', 'BLACK_W_GREEN_U'))
Black_W_GREEN_D = float(config.get('Color', 'BLACK_W_GREEN_D'))
Black_W_BLUE_U = float(config.get('Color', 'BLACK_W_BLUE_U'))
Black_W_BLUE_D = float(config.get('Color', 'BLACK_W_BLUE_D'))

Blue_RED_U = float(config.get('Color', 'BLUE_RED_U'))
Blue_RED_D = float(config.get('Color', 'BLUE_RED_D'))
Blue_GREEN_U = float(config.get('Color', 'BLUE_GREEN_U'))
Blue_GREEN_D = float(config.get('Color', 'BLUE_GREEN_D'))
Blue_BLUE_U = float(config.get('Color', 'BLUE_BLUE_U'))
Blue_BLUE_D = float(config.get('Color', 'BLUE_BLUE_D'))


current_version = 'camera_v1.06'
piAddress = ''

# decleared camera parameters
vs = cv2.VideoCapture(0)
_CAMERA_WIDTH  = int(vs.get(cv2.CAP_PROP_FRAME_WIDTH))  # default value = 640
_CAMERA_HEIGHT = int(vs.get(cv2.CAP_PROP_FRAME_HEIGHT)) # default value = 480 
_CAMERA_FPS    = int(vs.get(cv2.CAP_PROP_FPS))          # default value = 30

video_path = '/home/pi/stream-video-browser/video/'
fourcc = cv2.VideoWriter_fourcc(*'XVID')                # video encoding XVID
# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful for multiple browsers/tabs
# are viewing the stream)
outputFrame = None
lock = threading.Lock()
data = {"id":piAddress, "state":"Normal", "afterStateChangeSec":0, "videoName":{}}

# decleared color sensor parameters
csReCountFlag = False # use to re-count screen
csOthers  = 0 # use to count other screen
csBlackW  = 0 # use to count black screen with backlight
csBlackWO = 0 # use to count black screen without backlight
csBlue    = 0 # use to count blue screen

isAbnormal = False
iscalibrate = False
recoveryFlag = False

debug_log_name = ""

# decleared website parameters
app = Flask(__name__)

# decleared user interface parameters
TKT = TKThread()

def defineDebugLogName():
    global debug_log_name
    path = "/home/pi/stream-video-browser/DebugLog/"
    fileIndex = 0
    for i in range(4):
        if os.path.isfile("%sdebugLog_%d.txt" % (path, i)):
            fileIndex += 1
    if fileIndex == 4:
        subprocess.call(["rm", "/home/pi/stream-video-browser/DebugLog/debugLog_4.txt"])
        subprocess.call(["mv", "/home/pi/stream-video-browser/DebugLog/debugLog_3.txt", "/home/pi/stream-video-browser/DebugLog/debugLog_4.txt"])
        subprocess.call(["mv", "/home/pi/stream-video-browser/DebugLog/debugLog_2.txt", "/home/pi/stream-video-browser/DebugLog/debugLog_3.txt"])
        subprocess.call(["mv", "/home/pi/stream-video-browser/DebugLog/debugLog_1.txt", "/home/pi/stream-video-browser/DebugLog/debugLog_2.txt"])
        subprocess.call(["mv", "/home/pi/stream-video-browser/DebugLog/debugLog_0.txt", "/home/pi/stream-video-browser/DebugLog/debugLog_1.txt"])
        debug_log_name = "%sdebugLog_%d.txt" % (path, 0)
    else:
        debug_log_name = "%sdebugLog_%d.txt" % (path, fileIndex)


# save the debug log to txt file
def printDebugLog(debugMsg):
    global debug_log_name
    # can use linux command "$ tail -f debugLog.txt" on termail to view the real time log
    debugDate = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(debug_log_name, 'a') as f:
        f.write("%s %s\n" % (debugDate, debugMsg))

# check version
def checkVersion():
    url = checkVerAPI
    
    try:
        # Get the latest version from dct server
        r = requests.get(url, timeout=0.5)
    except requests.ConnectionError:
        # Can not connect server
        print("Server can not be connected.")
        printDebugLog('Server can not be connected!')
        return False # Can not reach server

    # 檢查狀態碼是否 OK
    if r.status_code == requests.codes.ok:
        print("Server OK")
        latest_version = r.text
    else:
        # Can not connect server
        print("LAN does not be connected.")
        printDebugLog('LAN does not be connected!')
        return False # Can not reach server

    # check the version
    pattern = re.compile(r"camera\_v(\d)\.(\d){2}\.zip")
    match = pattern.match(latest_version)
    

    if match != None and latest_version != (('%s.zip') %current_version):
        printDebugLog('Run script to doing update!')
        subprocess.call(["/home/pi/camera_update.sh"], shell=True)
    else:
        printDebugLog('The latest version does not be release!')


# recovery function
def recFunction(whoDo):
    global isAbnormal, csReCountFlag, TKT, data, recoveryFlag
    data = {"id": piAddress, "state": "Normal", "afterStateChangeSec": 0, "videoName":{}}
    isAbnormal = False
    csReCountFlag = True
    recoveryFlag = True
    args = ('rm', '/home/pi/stream-video-browser/video/*.avi')
    subprocess.call('%s %s' % args, shell=True)
    TKT.reportStatus('Normal')
    printDebugLog('Device had recovery via %s' % whoDo)

# send data to dct via post api
def postData2DCT(data):
    stime = time.time()
    ftime = True
    while True:
        if (time.time() - stime < 5) or (ftime == True): 
            try:
                ftime = False
                url = postDataAPI
                print(url)
                r = requests.post(url, json=data, timeout=0.5)
                printDebugLog("Send data to DCT: %s" % r.text)
                if r.status_code == 200:
                    printDebugLog("Data had post to DCT")
                else:
                    printDebugLog("Get error status code: %s" % r.status_code)
                break
            except requests.exceptions.ConnectTimeout:
                # DCT server network lost
                stime = time.time()
                printDebugLog("DCT server connect timeout %d seconds" % data['afterStateChangeSec'])
                data['afterStateChangeSec'] += 5
                break   # Test_v9 Let code not in while loop. "requests" command will make sensor detect got wrong value.
            except requests.exceptions.ConnectionError:
                # Raspberry pi network lost
                stime = time.time()
                printDebugLog("DCT server connect error %d seconds" % data['afterStateChangeSec']) 
                data['afterStateChangeSec'] += 5
                break   # Test_v9 Let code not in while loop. "requests" command will make sensor detect got wrong value.

# detect the internet is connected
def findIPAddress():
    try:
        # we need to connect the AP address to confirm the network function
        # also use this function to get the raspberry pi IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((APAddress, 80))
        ip = s.getsockname()[0]
        s.close()
        return True, ip
    except OSError:
        pass
    # no internet
    return False, '0.0.0.0'

def user_interface(deviceIP, version):
    TKT.startService(deviceIP, version)
    
def calibrationFlow(item, timer):
    print("start %s calibration" % item)
    
    # show calibration for item 
    TKT.calibrateUpdateCanvas(item)
    
    # delay 5 second
    time.sleep(5)
    
    stime = time.time()
    i = 0
    flag = True
    
    # count down timer
    while time.time() - stime < (timer+1):
        if int(time.time() - stime) % 5 == 0 and flag:
            TKT.calibrateUpdateCanvas(timer-(5*i))
            flag = False
            i += 1
        
        if int(time.time() - stime) % 5 != 0:
            flag = True
    
    # Do calibration
    calibration(item)
        
    print("end calibration")
    
def calibration(color):

    cs = ColorSensor()
    stime = time.time()
    red_array   = []
    blue_array  = []
    green_array = []
    config_GR = ''
    config_BR = ''
    config_BG = ''
    GR_result = 0
    BR_result = 0
    BG_result = 0
    #------Use RGB upper/lower to limit blue/black screen
    config_red_U = ''
    config_red_D = ''
    config_green_U = ''
    config_green_D = ''
    config_blue_U = ''
    config_blue_D = ''
    RED_U_result = 0
    RED_D_result = 0
    GREEN_U_result = 0
    GREEN_D_result = 0
    BLUE_U_result = 0
    BLUE_D_result = 0
    #------Use RGB upper/lower to limit blue/black screen
    
    if TKT.switch == 2:
        TKT.calibrateChangeGUI(True)
    
    for times in range(cali_average):
        red_array.append(cs.get_sensor_value('red'))
        blue_array.append(cs.get_sensor_value('blue'))
        green_array.append(cs.get_sensor_value('green'))

    # red_array.remove(max(red_array))
    # red_array.remove(min(red_array))
    # blue_array.remove(max(blue_array))
    # blue_array.remove(min(blue_array))
    # green_array.remove(max(green_array))
    # green_array.remove(min(green_array))

    red_average = statistics.mean(red_array)
    blue_average = statistics.mean(blue_array)
    green_average = statistics.mean(green_array)
    
    red_std = np.std(red_array)
    blue_std = np.std(blue_array)
    green_std = np.std(green_array)

    # GR_result = (green_average + (4 * green_std))/(red_average - (4 * red_std))
    # BR_result = (blue_average + (4 * blue_std))/(red_average - (4 * red_std))
    # BG_result = (blue_average + (4 * blue_std))/(green_average - (4 * green_std))

    #------Use RGB upper/lower to limit blue/black screen, 6 sigma
    # For V1.05_Test_v8, some sensor got big deviation, set tolerance to +-30%
    if (6 * red_std) < (red_average*3/10):
        red_std = red_average*3/10
    else:
        red_std = 6 * red_std
    if (6 * green_std) < (green_average*3/10):
        green_std = green_average*3/10
    else:
        green_std = 6 * green_std
    if (6 * blue_std) < (blue_average*3/10):
        blue_std = blue_average*3/10
    else:
        blue_std = 6 * blue_std
    # For black WO need a spicial threshold
    # For V1.05_Test_v7, some units sensor value change huge, enlarge the sensor threshold
    if color == 'blackWO':
        red_std = red_average
        blue_std = blue_average
        green_std = green_average

    RED_U_result = red_average + red_std
    RED_D_result = red_average - red_std
    GREEN_U_result = green_average + green_std
    GREEN_D_result = green_average - green_std
    BLUE_U_result = blue_average + blue_std
    BLUE_D_result = blue_average - blue_std

    debugMsg = "@%s- red_average:%d, red_std:%d, green_average:%d, green_std:%d, blue_average:%d, blue_std:%d" \
               % (color, red_average, red_std, green_average, green_std, blue_average, blue_std)
    printDebugLog(debugMsg)
   
    if color == 'blue':
        config_GR = 'BLUE_GR'
        config_BR = 'BLUE_BR'
        config_BG = 'BLUE_BG'
        config_red_U = 'BLUE_RED_U'
        config_red_D = 'BLUE_RED_D'
        config_green_U = 'BLUE_GREEN_U'
        config_green_D = 'BLUE_GREEN_D'
        config_blue_U = 'BLUE_BLUE_U'
        config_blue_D = 'BLUE_BLUE_D'

    elif color == 'blackWO':
        config_GR = 'BLACK_WO_GR'
        config_BR = 'BLACK_WO_BR'
        config_BG = 'BLACK_WO_BG'
        config_red_U = 'BLACK_WO_RED_U'
        config_red_D = 'BLACK_WO_RED_D'
        config_green_U = 'BLACK_WO_GREEN_U'
        config_green_D = 'BLACK_WO_GREEN_D'
        config_blue_U = 'BLACK_WO_BLUE_U'
        config_blue_D = 'BLACK_WO_BLUE_D'

    elif color == 'blackW':
        config_GR = 'BLACK_W_GR'
        config_BR = 'BLACK_W_BR'
        config_BG = 'BLACK_W_BG'
        config_red_U = 'BLACK_W_RED_U'
        config_red_D = 'BLACK_W_RED_D'
        config_green_U = 'BLACK_W_GREEN_U'
        config_green_D = 'BLACK_W_GREEN_D'
        config_blue_U = 'BLACK_W_BLUE_U'
        config_blue_D = 'BLACK_W_BLUE_D'
        
    # update existing value
    # config.set('Color', config_GR, "{:.6f}".format(GR_result))
    # config.set('Color', config_BR, "{:.6f}".format(BR_result))
    # config.set('Color', config_BG, "{:.6f}".format(BG_result))

    #------Use RGB upper/lower to limit blue/black screen, 3 sigma
    # update existing value
    config.set('Color', config_red_U, "{:.6f}".format(RED_U_result))
    config.set('Color', config_red_D, "{:.6f}".format(RED_D_result))
    config.set('Color', config_green_U, "{:.6f}".format(GREEN_U_result))
    config.set('Color', config_green_D, "{:.6f}".format(GREEN_D_result))
    config.set('Color', config_blue_U, "{:.6f}".format(BLUE_U_result))
    config.set('Color', config_blue_D, "{:.6f}".format(BLUE_D_result))
    
    # save to a file
    with open('/home/pi/stream-video-browser/cameraConfig.ini', 'w') as configfile:
        config.write(configfile)
        
    if TKT.switch == 2:
        TKT.calibrateChangeGUI(False)

def get_color():
    global csOthers, csBlackW, csBlackWO, csBlue, csReCountFlag
    
    if csBlackW >= 4 and csBlackWO < 3 and csBlue < 3 and csOthers < 3:
        color = 'blackW' # black screen with backlight
    elif csBlackW < 3 and csBlackWO >= 3 and csBlue < 3 and csOthers < 3:
        color = 'blackWO' # black screen without backlight
    elif csBlackW < 3 and csBlackWO < 3 and csBlue >= 6 and csOthers < 3:
        color = 'blue' # blue
    else:
        color = 'others' # others

    debugMsg = "Read csBlackW:%d, csBlackWO:%d, csBlue:%d, csOthers:%d. Result:%s" \
               % (csBlackW, csBlackWO, csBlue, csOthers, color)
    printDebugLog(debugMsg)
    csReCountFlag = True
    return color

def detect_color():
    global csOthers, csBlackW, csBlackWO, csBlue, csReCountFlag, isAbnormal, iscalibrate
    global Black_W_BR, Black_W_GR, Black_W_BG, Black_WO_BR, Black_WO_GR, Black_WO_BG, Blue_GR, Blue_BG, Blue_BR
    global Black_WO_RED_U, Black_WO_RED_D, Black_WO_GREEN_U, Black_WO_GREEN_D, Black_WO_BLUE_U, Black_WO_BLUE_D
    global Black_W_RED_U, Black_W_RED_D, Black_W_GREEN_U, Black_W_GREEN_D, Black_W_BLUE_U, Black_W_BLUE_D
    global Blue_RED_U, Blue_RED_D, Blue_GREEN_U, Blue_GREEN_D, Blue_BLUE_U, Blue_BLUE_D
    red_array   = []
    blue_array  = []
    green_array = []
    
    cs = ColorSensor()
    
    while True:
        
        if TKT.recovery:
            # because the sendData2DCT function will keep on when network lost,
            # put the recovery function on color sensor threading
            recFunction('GUI')
            TKT.recovery = 0
            print('do recovery')
            
        #TODO: recover count value
        if csReCountFlag:
            csReCountFlag = False
            csOthers  = 0
            csBlackW  = 0
            csBlackWO = 0
            csBlue    = 0
        
        # if doing calibration, disable get sensor value to avoid conflict
        if not iscalibrate and not TKT.iscalibrate:
            red_array.clear()
            blue_array.clear()
            green_array.clear()

            # Get 3 times data, and then remove MAX/MIN
            for times in range(3):
                red_array.append(cs.get_sensor_value('red'))
                blue_array.append(cs.get_sensor_value('blue'))
                green_array.append(cs.get_sensor_value('green'))

            red_array.remove(max(red_array))
            red_array.remove(min(red_array))
            blue_array.remove(max(blue_array))
            blue_array.remove(min(blue_array))
            green_array.remove(max(green_array))
            green_array.remove(min(green_array))
            red = statistics.mean(red_array)
            blue = statistics.mean(blue_array)
            green = statistics.mean(green_array)
            #red   = cs.get_sensor_value('red')
            #blue  = cs.get_sensor_value('blue')
            #green = cs.get_sensor_value('green')
        else:
            if TKT.iscalibrate:
                #calibration(TKT.calibrateColor)
                isAbnormal = True
                calibrationFlow(cali_item1, cali_timer1)
                calibrationFlow(cali_item2, cali_timer2)
                calibrationFlow(cali_item3, cali_timer3)
                TKT.switch = 0
                TKT.reportStatus('Normal')
                TKT.iscalibrate = False
                isAbnormal = False
                # Black_W_GR = float(config.get('Color', 'BLACK_W_GR'))
                # Black_W_BR = float(config.get('Color', 'BLACK_W_BR'))
                # Black_W_BG = float(config.get('Color', 'BLACK_W_BG'))
                # Black_WO_GR = float(config.get('Color', 'BLACK_WO_GR'))
                # Black_WO_BR = float(config.get('Color', 'BLACK_WO_BR'))
                # Black_WO_BG = float(config.get('Color', 'BLACK_WO_BG'))
                # Blue_GR = float(config.get('Color', 'BLUE_GR'))
                # Blue_BR = float(config.get('Color', 'BLUE_BR'))
                # Blue_BG = float(config.get('Color', 'BLUE_BG'))

                #------Use RGB upper/lower to limit blue/black screen
                Black_WO_RED_U = float(config.get('Color', 'BLACK_WO_RED_U'))
                Black_WO_RED_D = float(config.get('Color', 'BLACK_WO_RED_D'))
                Black_WO_GREEN_U = float(config.get('Color', 'BLACK_WO_GREEN_U'))
                Black_WO_GREEN_D = float(config.get('Color', 'BLACK_WO_GREEN_D'))
                Black_WO_BLUE_U = float(config.get('Color', 'BLACK_WO_BLUE_U'))
                Black_WO_BLUE_D = float(config.get('Color', 'BLACK_WO_BLUE_D'))

                Black_W_RED_U = float(config.get('Color', 'BLACK_W_RED_U'))
                Black_W_RED_D = float(config.get('Color', 'BLACK_W_RED_D'))
                Black_W_GREEN_U = float(config.get('Color', 'BLACK_W_GREEN_U'))
                Black_W_GREEN_D = float(config.get('Color', 'BLACK_W_GREEN_D'))
                Black_W_BLUE_U = float(config.get('Color', 'BLACK_W_BLUE_U'))
                Black_W_BLUE_D = float(config.get('Color', 'BLACK_W_BLUE_D'))

                Blue_RED_U = float(config.get('Color', 'BLUE_RED_U'))
                Blue_RED_D = float(config.get('Color', 'BLUE_RED_D'))
                Blue_GREEN_U = float(config.get('Color', 'BLUE_GREEN_U'))
                Blue_GREEN_D = float(config.get('Color', 'BLUE_GREEN_D'))
                Blue_BLUE_U = float(config.get('Color', 'BLUE_BLUE_U'))
                Blue_BLUE_D = float(config.get('Color', 'BLUE_BLUE_D'))

                printDebugLog("Calibration finished. Reboot Pi!")
                time.sleep(1)
                os.system('sudo shutdown -r now')   # Test_v9 reboot after calibration

            else:
                # workround for API calibrate command
                red = 1
                blue = 1
                green = 1

        time.sleep(1)
            
        # GR_ratio = green/red
        # BR_ratio = blue/red
        # BG_ratio = blue/green

        #------Use RGB upper/lower to limit blue/black screen
        if (red < Black_WO_RED_U) and (red > Black_WO_RED_D) and \
            (green < Black_WO_GREEN_U) and (green > Black_WO_GREEN_D) and \
            (blue < Black_WO_BLUE_U) and (blue > Black_WO_BLUE_D):
            csBlackWO = csBlackWO + 1
            color_status = 'BlackScreen w/o'
        elif (red < Black_W_RED_U) and (red > Black_W_RED_D) and \
            (green < Black_W_GREEN_U) and (green > Black_W_GREEN_D) and \
            (blue < Black_W_BLUE_U) and (blue > Black_W_BLUE_D):
            csBlackW = csBlackW + 1
            color_status = 'BlackScreen w/'
            # For extend Black WO judge timing
            csBlackWO = 0
        elif (red < Blue_RED_U) and (red > Blue_RED_D) and \
            (green < Blue_GREEN_U) and (green > Blue_GREEN_D) and \
            (blue < Blue_BLUE_U) and (blue > Blue_BLUE_D):
            csBlue = csBlue + 1
            color_status = 'BlueScreen'
            # For extend Black WO judge timing
            csBlackWO = 0
        else:
            csOthers = csOthers + 1
            color_status = 'Others'
            # For extend Black WO judge timing
            csBlackWO = 0
        
        print("R = %f, G = %f, B = %f, The result is : %s" % (red, green, blue, color_status))#test
#        print("BG: %f, BR: %f, GR: %f. The result is : %s" % (BG_ratio, BR_ratio, GR_ratio, color_status))#test
        debugMsg1 = "red: %f, green: %f, blue: %f. The result is : %s" % (red, green, blue, color_status)
#       debugMsg = "BG: %f, BR: %f, GR: %f. The result is : %s" % (BG_ratio, BR_ratio, GR_ratio, color_status)
        if not isAbnormal:
            printDebugLog(debugMsg1)
#            printDebugLog(debugMsg)
"""        
        if (GR_ratio < Black_WO_GR) and (BR_ratio < Black_WO_BR) and \
           (BG_ratio < Black_WO_BG) and blue < 20:
            csBlackWO = csBlackWO + 1
            color_status = 'BlackScreen w/o'
        elif (GR_ratio < Black_W_GR) and (BR_ratio < Black_W_BR) and \
             (BG_ratio < Black_W_BG) and blue < 450:
            csBlackW = csBlackW + 1
            color_status = 'BlackScreen w/'
        elif (GR_ratio < Blue_GR) and (BR_ratio < Blue_BR) and (BG_ratio < Blue_BG):
            csBlue = csBlue + 1
            color_status = 'BlueScreen'
        else:
            csOthers = csOthers + 1
            color_status = 'Others'
"""
        
def detect_motion(frameCount):
    # grab global references to the video stream, output frame, and
    # lock variables
    global vs, outputFrame, lock, isAbnormal, data, recoveryFlag
    
    # initialize the motion detector and the total number of frames
    # read thus far
    md = SingleMotionDetector(accumWeight=0.1)
    
    total = 0
    vindex = 0
    hasMotion = 0
    write_flag = 0
    isMoveCount = 0
    isAbnormalCount = 0
    read_color_flag = 1
    abnormalVideoIndex = 0
    abnormalVideoRecord = True
    lastColor = 'others'
    startTime = time.time()
    curr = datetime.datetime.now().strftime("%Y%m%d_%H%M")

    # loop over frames from the video stream
    while True:
        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        _, frame = vs.read()        
        
        # does not need to save the video if detect abnormal status
        # save video every five minute
        if not isAbnormal:
            if int(time.time() - startTime) <= 300 and write_flag == 0:
                write_flag = 1
                video_name = video_path + curr + ('_%d.avi' % vindex)
                out = cv2.VideoWriter(video_name, fourcc, int(_CAMERA_FPS), (int(_CAMERA_WIDTH), int(_CAMERA_HEIGHT)))
                vindex += 1
                printDebugLog('%s start saving.' % video_name)
            elif int(time.time() - startTime) > 300 and write_flag == 1:
                write_flag = 0
                startTime = time.time()

            if write_flag == 1:
                out.write(frame)
                
        if recoveryFlag:
            # after doing recovery, initialize paramter and wait recovery occured
            vindex = 0
            write_flag = 0
            isMoveCount = 0
            isAbnormalCount = 0
            lastColor = 'others'
            abnormalVideoRecord = True
            recoveryFlag = False
            startTime = stime = time.time()
            if curr == datetime.datetime.now().strftime("%Y%m%d_%H%M"):
                # if filename is same as last one, the video can not be record
                # so add one second to avoid the same video name after recovery
                temp = datetime.datetime.now()
                curr = (temp + datetime.timedelta(0,60)).strftime("%Y%m%d_%H%M")
            else:
                curr = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            
        
        
        #frame = imutils.resize(frame, width=1080)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
 
        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        
        

        if total > frameCount:
            if int(time.time() - stime) < detect_duration or isAbnormal or (csBlackWO > 0 and csBlackWO < 3):   # For extend black WO judge timing
                total = frameCount + 1
                hasMotion = 0
                #data = {"id":piAddress, "state":"Normal", "afterStateChangeSec":0, "videoName":{}}
            else:
                # read color value every 40 seconds
                # if color is not blue or black, detect the image motion.
                if read_color_flag == 1:
                    currColor = get_color()
                    #currColor = 'others'
                    read_color_flag = 0
                
                if currColor != 'others':
                    if lastColor == currColor:
                        isAbnormalCount += 1
                        if abnormalVideoRecord:
                            abnormalVideoRecord = False
                            abnormalVideoIndex = vindex
                        if isAbnormalCount == detect_amount:
                            isAbnormalCount = detect_amount
                            isAbnormal = True
                            TKT.reportStatus(currColor)
                            printDebugLog("Image color abnormal: %s" % currColor)
                            
                            # send the status to DCT server
                            data = {"id":piAddress, "state":currColor, "afterStateChangeSec":0, "videoName":{}}
                            
                            if vindex - abnormalVideoIndex > 2:
                                totalIndex = 3
                            else:
                                totalIndex = vindex - abnormalVideoIndex + 1
                            
                            for i in range(totalIndex):
                                videoName = curr + ('_%d' % (abnormalVideoIndex + i - 1))
                                data['videoName'][str(i)] = videoName
                                
                            postData2DCT(data)                                          
                    else:
                        abnormalVideoRecord = True
                        isAbnormalCount = 0
                    stime = time.time()
                    lastColor = currColor
                    read_color_flag = 1
                else:
                    # detect motion in the image
                    motion = md.detect(gray)
                    isAbnormalCount = 0
                    # check to see if motion was found in the frame
                    if motion is not None:
                        hasMotion += 1
                        # unpack the tuple and draw the box surrounding the "motion area" on the output frame (debug use)
                        # (thresh, (minX, minY, maxX, maxY)) = motion
                        # cv2.rectangle(frame, (minX, minY), (maxX, maxY), (0, 0, 255), 2)
                    
                    md.update(gray)
                    total += 1
                    if total > frameCount + 32:
                        print("vindex:%d" % vindex)
                        print("abnormalVideoIndex:%d" % abnormalVideoIndex)
                        print("isMoveCount:%d" % isMoveCount)
                        stime = time.time()
                        if not hasMotion:
                            if isMoveCount == detect_amount:
                                isMoveCount = detect_amount
                                isAbnormal = True
                                TKT.reportStatus('Hang')
                                printDebugLog("Image does not detect motion")
                                
                                # send the status to DCT server
                                data = {'id':piAddress, 'state':'hang', 'afterStateChangeSec':0, 'videoName':{}}
                                
                                if vindex - abnormalVideoIndex > 2:
                                    totalIndex = 3
                                else:
                                    totalIndex = vindex - abnormalVideoIndex + 1
                                
                                for i in range(totalIndex):
                                    videoName = curr + ('_%d' % (abnormalVideoIndex + i - 1))
                                    data['videoName'][str(i)] = videoName
                                print(data)
                                postData2DCT(data)
                            else:
                                if abnormalVideoRecord:
                                    abnormalVideoRecord = False
                                    abnormalVideoIndex = vindex
                                isMoveCount += 1
                        else:
                            if isMoveCount == 0:
                                isMoveCount = 0
                                abnormalVideoRecord = True
                            else:
                                isMoveCount -= 1
                        read_color_flag = 1
        else:
            md.update(gray)
            total += 1
            stime = time.time()
        
        # switch the user interface to preview camera image
        if TKT.switch == 1:
            TKT.showVideo(frame)
            
        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = frame

def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')

# Website function
@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")

@app.route("/stopDetect", methods=['GET'])
def stopDetect():
    global isAbnormal
    isAbnormal = True
    TKT.reportStatus('Stop')
    return jsonify(result="success")

@app.route("/recovery", methods=['GET'])
def recovery():
    recFunction('website')
    return jsonify(result="success")

@app.route("/getStatus", methods=['GET'])
def getStatus():
    global data
    return jsonify(data)

@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
        mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route('/download_video/<video_name>', methods=['GET'])
def download_video(video_name):
    path = '/home/pi/stream-video-browser/video/'
    video = video_name + '.avi'
    return send_from_directory(path, video, as_attachment=True)

@app.route("/calibration")
def colorSensorCalibration():
    global iscalibrate
    color = request.args.get("color")
    iscalibrate = True
    calibration(color)
    iscalibrate = False
    response = {"result":"pass"}
    return jsonify(response)

# check to see if this is the main thread of execution
if __name__ == '__main__':
    try:
        # here you put your main loop or block of code
        
        defineDebugLogName()

        # when raspberry pi boot up, the internet may not connect immmediately
        # so we need to wait the network function is normal then start the thread
        while True:
            isconnected, piAddress = findIPAddress()
            if isconnected:
                break
            printDebugLog("No Internet Connected.")
            # Wait 10 seconds, some units' LAN can not be recognize in 5 seconds
            time.sleep(10)
            isconnected, piAddress = findIPAddress()
            if not isconnected:
                printDebugLog("Recheck. No Internet Connected.")
                # No internet, but still run AP.
                break
        
        printDebugLog("Internet has connected.")
        
        rv = checkVersion()

        while rv:
            #wait script to kill process
            pass

        # start a thread that will perform motion detection
        t1 = threading.Thread(target=detect_motion, args=(32,))         # Thread: camera
        t2 = threading.Thread(target=detect_color)                      # Thread: color sensor
        t3 = threading.Thread(target=user_interface, args=(piAddress, current_version)) # Thread: GUI
        
        # need to close the thread when main code is stop
        t1.daemon = True
        t2.daemon = True
        t3.daemon = True
        
        # start the threading
        t1.start()
        t2.start()
        t3.start()
        
        printDebugLog("Start threading service.")
        
        # start the flask app
        app.run(host=piAddress, port=serPort, debug=True,
            threaded=True, use_reloader=False)
            
    except KeyboardInterrupt:
        # here you put any code you want to run before the program
        # exit when you press CTRL+C
        print("key")
    except:
        # this catches All other exception including errors
        # you won't get any error message for debugging
        # so only use it once your code is working
        print('Err: {0[0]}\n {0[1]}\n {0[2]}\n'.format(sys.exc_info()))
    finally:
        GPIO.cleanup() # this ensures a clean exit
        printDebugLog("Close the process.")
