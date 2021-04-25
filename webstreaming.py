# History
# kenney_chen
# 2021/04/13
# - 移除 相關 color senor/Calbration  code.

# - Echo_Lee
# - 2021/04/14
# - 1.video格式mp4改avi
# - 2.去背景function改用opencv mog2
# - 3.改用原始圖片進行yolo object detection(qrcode)
# - 4.Recovery重新偵測機制

# - Echo_Lee
# - 2021/04/15
# - 新增 Yolo->偵測程式的防呆機制
# -   1. 檢查特定資料夾有yolo model相關檔案
# -   2. 設定yolo model相關檔案存取權限

# - Echo_Lee
# - 2021/04/16 (version v1.07)
# - 取得yolo model的路徑改絕對路徑
# - yolo防呆機制, 將異常訊息顯示在Pi GUI上
# - 

# - Echo_Lee
# - 2021/04/19 (version v1.08)
# - 解決client停止偵測->recovery機制後, 可正常Camera view
# - 1. recovery刪除檔案, 沒檔案會出現exception, 加上try catch機制
# - 2. 改變ad.detect參數設定, 重新偵測

# - Echo_Lee
# - 2021/04/20 (version v1.09)
#  - fix bug:修改detections參數改成self.detections

# - Echo_Lee
# - 2021/04/22 (version v1.10)
# - 調整baseline條件
#     - 前景取畫面正中心(寬&高:畫面的1/5-4/5)
#     - 前景變動像素超過30%以上
# - 更新yolo model加入UHD QRCODE的標註資料

#!/usr/bin/python3

# import the necessary packages
from imutils.video import VideoStream
from flask import Response, Flask, render_template, request, jsonify, send_from_directory
#from pyimagesearch.color_sensor import ColorSensor
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

from anomaly_dct import AnomalyDct

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


current_version = 'camera_v1.10'
piAddress = ''

# decleared camera parameters
#vs = cv2.VideoCapture(0)
#_CAMERA_WIDTH  = int(vs.get(cv2.CAP_PROP_FRAME_WIDTH))  # default value = 640
#_CAMERA_HEIGHT = int(vs.get(cv2.CAP_PROP_FRAME_HEIGHT)) # default value = 480 
#_CAMERA_FPS    = int(vs.get(cv2.CAP_PROP_FPS))          # default value = 30

 
# -- set camera resolution and fps --
vs = cv2.VideoCapture(0)  
vs.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
vs.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
vs.set(cv2.CAP_PROP_FPS, 5)


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
    try:
        args = ('rm', '/home/pi/stream-video-browser/video/*.avi')
        subprocess.call('%s %s' % args, shell=True)
    except:
        print("rm: cannot remove '/home/pi/stream-video-browser/video/*.avi': No such file or directory")
        printDebugLog("rm: cannot remove '/home/pi/stream-video-browser/video/*.avi': No such file or directory")
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

def detect(DEBUG=False): 
    global vs, outputFrame, lock, isAbnormal, data, recoveryFlag
    curr = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    
    ad = AnomalyDct()
    ad.DEBUG = DEBUG
    ad.vidcap = vs

    #check yolo model file and permission
    time.sleep(5)
    if not os.path.exists(os.path.join('/home/pi/stream-video-browser/model', 'yolov4-dct-opt.bin')):
        printDebugLog('yolo bin missing')
        ad.detect = False
        if hasattr(TKT, 'canvas_status'):
            TKT.reportStatus('yolo bin missing')
        return
    if not os.path.exists(os.path.join('/home/pi/stream-video-browser/model', 'yolov4-dct-opt.param')):
        printDebugLog('yolo param missing')
        ad.detect = False
        if hasattr(TKT, 'canvas_status'):
            TKT.reportStatus('yolo param missing')
        return 
    subprocess.call(['chmod', '0777', '/home/pi/stream-video-browser/model'])
    
    if ad.DEBUG:
        ad.d_folder = 'tmp'
        fname = '20210409_0509_1.avi'
        ad.fname = fname
        ad.vidcap = cv2.VideoCapture(f'video/{fname}')
        output_name = ad.fname.split('/')[-1]
    else:
        ad.fname = curr
        ad.set_video_writer()
    if not os.path.exists(ad.d_folder):
        os.makedirs(ad.d_folder)
        
    ad.mog = cv2.createBackgroundSubtractorMOG2()        
    while ad.success:
        ad.success, ad.image = ad.vidcap.read()
        if ad.success:

            if TKT.recovery:
                recFunction('GUI')
                TKT.recovery = 0
                print('do recovery')  
            
            if recoveryFlag:
                # after doing recovery, initialize paramter and wait recovery occured
                ad.initpara()
                ad.get_mask()
                ad.set_video_writer()

                ad.mog = cv2.createBackgroundSubtractorMOG2()        
                recoveryFlag = False
                ad.detect = True
                startTime = stime = time.time()
                if curr == datetime.datetime.now().strftime("%Y%m%d_%H%M"):
                    # if filename is same as last one, the video can not be record
                    # so add one second to avoid the same video name after recovery
                    temp = datetime.datetime.now()
                    curr = (temp + datetime.timedelta(0,60)).strftime("%Y%m%d_%H%M")
                else:
                    curr = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            
            if isAbnormal:
                ad.detect = False
            
            if ad.detect:
                start = time.time()
                ad.fid += 1
                ad.feature_dict['fid'] = ad.fid
                ad.feature_dict['obj_class'] = ""

                ad.image_copy = ad.image.copy()
                # -- save complete video --
                ad.save_complete_video()
                
                # -- Search white positioning block -- 
                ad.is_test_item = ad.get_Wblack(ad.image, ad.search_wblock)
                ad.wblock_accum_score = max(ad.wblock_accum_score,0) if ad.is_test_item else min(ad.wblock_accum_score,0)
                ad.wblock_accum_score = ad.wblock_accum_score+(1 if ad.is_test_item else -1)
                if ad.wblock_accum_score>40:
                    ad.search_wblock=False
                elif ad.wblock_accum_score<-40:
                    ad.search_wblock=True

                # -- detect pass windows --
                if ad.is_test_item:
                    ad.is_passed = ad.get_pass_window(ad.image, ad.passed_x_lower, ad.passed_x_upper, ad.passed_y_lower, ad.passed_y_upper)
                    ad.feature_dict['is_passed'] = ad.is_passed
                    if ad.is_passed:
                        ad.detect_pass()
                        # -- stop detect --
                        if ad.is_pass:
                            print('pass')
                            ad.detect = False

                # -- Baseline(test_spec) --
                ad.fgmask = ad.mog.apply(ad.image)
                ad.fgmask = np.clip(ad.fgmask, 0, 1)
                if (ad.baseline_pass == False):
                    ad.create_baseline()
                    if ad.baseline_pass:
                        printDebugLog(f'fid:{ad.fid} baseline_pass')
                # -- Detect --
                else:
                    ad.get_vbb_score()
                    ad.anomaly_detect()

                # -- put_text & draw --
                ad.draw_picture(start)
                
                # -- keep inference video --
                if DEBUG:
                    ad.keep_inference_video()
                if ad.is_anomaly:
                    print('anomaly', ad.anomaly_type)
                    printDebugLog(f'anomaly:{ad.anomaly_type}')

                    TKT.reportStatus(ad.anomaly_type)
                    isAbnormal = True
                    # send the status to DCT server
                    data = {'id':piAddress, 'state':ad.anomaly_type, 'afterStateChangeSec':0, 'videoName':{}}
                    vindex = ad.vindex + 2
                    total_index = min(3, vindex)
                    for i in range(0, total_index):
                        data['videoName'][str(i)] = ad.fname + ('_%d' % (vindex-total_index+i))  
                    postData2DCT(data)
                    ad.writer_inf.close()
#                     threading.Thread(target=ad.save_test_video, args=(ad.d_folder, ad.all_list, ad.fname, ad.fps)).start()
                    threading.Thread(target=ad.save_test_video, args=(ad.d_folder, ad.image_list, ad.fname, ad.fps)).start() 
                    ad.detect = False
                    printDebugLog(data)
             # switch the user interface to preview camera image
            if TKT.switch == 1:
                TKT.showVideo(ad.image)
            
            with lock:
                outputFrame = ad.image

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
        t1 = threading.Thread(target=detect, args=())         # Thread: camera
        #t2 = threading.Thread(target=detect_color)                      # Thread: color sensor
        t3 = threading.Thread(target=user_interface, args=(piAddress, current_version)) # Thread: GUI
        
        # need to close the thread when main code is stop
        t1.daemon = True
        #t2.daemon = True
        t3.daemon = True
        
        # start the threading
        t1.start()
        #t2.start()
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
