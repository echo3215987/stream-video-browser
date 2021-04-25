#!/usr/bin/env python
# coding: utf-8

# Copyright © 2021 AA
# History:
# 3/3
#   - Baseline建立
#       - 取第一次偵測左上角白色方框後40秒, 才取10秒的frame建立baseline
#   - 測項開始/結束才進行偵測, 重開機不偵測
#       - 偵測左上角白色方框出現為測項開始
#       - 偵測重開機提示視窗出現為測項結束
#   - 測試計畫結束, 停止偵測程式
#       - 出現PASSED視窗, 停止偵測
# 3/4
#   - 測項開始: 偵測左上角白色方框改用二值化方式
# 3/9
#   - 改用YUV偵測藍色像素
# 3/11
#  - 調整baseline(藍色與黑色spec:前景的1/2 pixel)
#  - 調整左上角白色框偵測('h'uv高明亮、h's'v低飽和、找離0,0最近的白色點)

# 3/16
#  - 調整baseline(藍色與黑色spec:前景的1/2 pixel)
#  - 調整左上角白色框偵測(9個rgb範圍, 找離0,0最近的白色點, 限定面積範圍)
# 3/18
#  - detect階段先去背景
#  - 修正畫面上debug message的bug
#  - inference影片刪去背景
#  - 修正baseline流程
# 3/19
#  - 修正blue/black pixel計算bug, 只計算fg_mask內的pixel數量
# 3/20
#  - 修正抓白色定位框bug, 抓coutour左上角座標的計算方法修正
#  - 抓白色定位框的流程優化
#       - Search : 連續40個frame check pass後固定位置, 後續frame只check不search
#       - Check : 連續40個frame check fail後重新search
#  - 用is_test_item優化error type分類
#  - 提高blue/black pixel spec
#  - 修正baseline流程 
#      - 連續10個frame符合fgmask rule
#      - 用最後三個fgmask組成FG_MASK
#  - 改用createBackgroundSubtractorGMG, FPS剩下24
# 3/22
#  - 優化測試計畫結束辨識
#      - 1. 利用RGB找出passed綠色視窗
#      - 2. 視窗位置需在正中間, 視窗面積>4000
#      - 3. 75秒內必須找到5次的passed綠色視窗
# 3/29
#  - 改成class寫法
# 4/8
#  - 加入yolov4_faster, BSOD異常條件加入qrcode判斷
# 4/14
#  - 降低QRCODE threshold (0.8->0.7)
#  - 改變QRCODE偵測圖片(前景圖片->原始圖片)
# 4/20
#  - fix bug:修改detections參數改成self.detections

# 4/22 (version v1.10)
# - 調整baseline條件
#     - 前景取畫面正中心(寬&高:畫面的1/5-4/5)
#     - 前景變動像素超過30%以上

import cv2
import matplotlib.pyplot as plt
import numpy as np
import imageio
import datetime
import multiprocessing
import threading
import os
import warnings
warnings.filterwarnings('ignore')
warnings.simplefilter(action='ignore', category=FutureWarning)
import glob
import time
import datetime
import pandas as pd
from functools import reduce
from yolov4_faster import YoloV4_Fastest

MAIN_VER='04/22 15:32'

COLOR_MARRSGREEN = (69,79,1)
COLOR_PLASTICPINK = (147,20,255)
COLOR_GREEN = (0,255,0)
COLOR_RED = (0,0,255)
COLOR_WHITE = (255,255,255)
COLOR_BLUE = (255,144,30)
COLOR_ORANGE = (0,128,235)
COLOR_PURPLE = (255,53,159)

ANOMALY_BLUE = 1
ANOMALY_BLUE_STR = 'BSOD'
ANOMALY_BLACK = 2
ANOMALY_BLACK_STR = 'BLACK'
ANOMALY_HANG_UP = 3
ANOMALY_HANG_UP_STR = 'HANG UP'

HSV_BLUE_LOWER = [100,43,46]
HSV_BLUE_UPPER = [124,255,255]
HSV_BLACK_LOWER = [0,0,0]
HSV_BLACK_UPPER = [180,255,46]
GRAY_WHITE_LOWER = 127
GRAY_WHITE_UPPER = 255
YUV_UV_LOWER = 120
YUV_UV_UPPER = 136
YUV_Y_LOWER = 213
YUV_Y_UPPER = 256

KEEP_FRAME_COUNT = 300
ABNORMAL_SEC = 20
CHECK_SEC = 10
FONT_SIZE = 0.5

class AnomalyDct(object):
    _defaults = {
        'width': 640,
        'height': 480
    }

    @classmethod
    def get_defaults(cls, n):
        if n in cls._defaults:
            return cls._defaults[n]
        else:
            return "Unrecognized attribute name '" + n + "'"        
        
    def __init__(self, **kwargs):
        self.__dict__.update(self._defaults)
        self.__dict__.update(kwargs)
        self.initpara()
        self.inityolo()
        self.get_mask()
        
    def initpara(self):
        self.d_folder = '/home/pi/stream-video-browser/video/'
        self.fps = 5
        self.success = True
        self.fid = 0
        self.image_list = []
        self.anomaly_list = np.array([])
        self.fps_list = []
        self.baseline_list = []
        self.fgmask_list = []
        self.FG_MASK = None
        self.fg_accum_score = 0 
        self.vindex = 0
 
        self.spec_black = -1
        self.spec_blue = -1
        self.spec_var = 200
        self.var_pixel=-1 
        self.blue_score=-1 
        self.black_score=-1

        self.anomaly_type = ''
        self.oclock = False
        self.oclock_list = []

        self.file_cnt = 0
        self.all_list = []
        self.all_frame_cnt_limit = 900
        self.is_test_item = False
        self.is_passed = False
        self.is_hang = False
        self.is_anomaly = False
        self.baseline_pass = False
        self.wblock_accum_score = 0
        self.search_wblock = True
        self.feature_dict={}
        
        self.passed_x_lower = int(self.width*0.3)
        self.passed_x_upper = int(self.width*0.8)
        self.passed_y_lower = int(self.height*0.45)
        self.passed_y_upper = int(self.height*0.6)
        self.passed_list = []
        
        self.obj_class = ''
        self.obj_score = -1
        self.obj_bbox = np.array([])
        self.is_qrcode = False
        self.is_pass = False
        
        self.detect = True
        
    def inityolo(self):
        self.yolo = YoloV4_Fastest()
        
    def set_video_writer(self):
        self.writer_inf = imageio.get_writer(os.path.join(self.d_folder, self.fname + ('_%d.avi' % self.vindex)), format='avi', mode='I', fps=self.fps)
    
    def get_img_feature_YUV(self, image, fgmask, lower=YUV_UV_LOWER, upper=YUV_UV_UPPER):
        image_yuv_blue = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
        image_yuv_black = image_yuv_blue.copy()
        image_yuv_blue = cv2.bitwise_and(image_yuv_blue, image_yuv_blue, mask=fgmask)
        mask1 = cv2.inRange(image_yuv_blue, (0,upper,0), (256,256,lower))
        mask2 = cv2.inRange(image_yuv_blue, (0,upper,lower), (256,256,128))
        mask3 = cv2.inRange(image_yuv_blue, (0,128,0), (256,upper,lower))
        mask = mask1+mask2+mask3
        mask = cv2.bitwise_and(mask, mask, mask=fgmask)
        blue_score = np.count_nonzero(mask)
        cv2.bitwise_and(image_yuv_black, image_yuv_black, mask=fgmask)
        mask = cv2.inRange(image_yuv_black, (0,lower,lower), (43,upper,upper))
        mask = cv2.bitwise_and(mask, mask, mask=fgmask)
        black_score = np.count_nonzero(mask)
        img_feature = [blue_score, black_score]
        return img_feature

    def get_img_feature_YUV_pmu(self, image, lower=YUV_UV_LOWER, upper=YUV_UV_UPPER):
        image_yuv_blue = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
        image_yuv_black = image_yuv_blue.copy()
        mask1 = cv2.inRange(image_yuv_blue, (0,upper,0), (256,256,lower))
        mask2 = cv2.inRange(image_yuv_blue, (0,upper,lower), (256,256,128))
        mask3 = cv2.inRange(image_yuv_blue, (0,128,0), (256,upper,lower))
        mask = mask1+mask2+mask3
        blue_score = np.count_nonzero(mask)
        mask = cv2.inRange(image_yuv_black, (0,lower,lower), (43,upper,upper))
        black_score = np.count_nonzero(mask)
        img_feature = [blue_score, black_score]
        return img_feature
    
    def draw_fps(self, start, image, fps_list):
        end = time.time()
        seconds = end - start
        if seconds == 0:
            time.sleep(0.001)
            end = time.time()
            seconds = end - start
        fps = np.round(1 / seconds, 2)
        fps_list.append(fps)
        return fps

    def put_text(self, image):
        is_anomaly = self.feature_dict.get('is_anomaly', False)
        is_anomaly_len = self.feature_dict.get('is_anomaly_len',0)
        color = COLOR_BLUE if (is_anomaly_len>0) else COLOR_ORANGE
        color = COLOR_RED if is_anomaly else color
        font = cv2.FONT_HERSHEY_SIMPLEX
        img_mask=np.zeros_like(image)
        msg_w, msg_h = 10, 140
        lspace = 16
        for i, (k,v) in enumerate(self.feature_dict.items(), start=1):
            if type(v) == np.float64:
                msg = f'{str(k)}:{v:.1f}'
            else: 
                msg = f'{str(k)}:{str(v)}'        
            img_mask = cv2.rectangle(img_mask, (msg_w, msg_h+lspace*i-13), (msg_w+len(msg)*8, msg_h+lspace*i), (1,1,1), thickness=-1) 
            img_mask = cv2.putText(img_mask, msg, (msg_w, msg_h+lspace*i) , font , FONT_SIZE, color , 1, cv2.LINE_AA)
        image = cv2.addWeighted(image, 1, img_mask, 0.9, 0)
        return image

    def anomaly(self, anomaly_list, anomaly_id, image, anomaly_str):
        anomaly_list = np.append(anomaly_list, anomaly_id)
        unique, counts = np.unique(anomaly_list, return_counts=True)
        if len(unique) == 1:
            if len(anomaly_list) != self.fps*ABNORMAL_SEC:
                cv2.putText(image, anomaly_str, (480, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_BLUE, 2, cv2.LINE_AA)
            if len(anomaly_list) == self.fps*ABNORMAL_SEC:
                cv2.putText(image, anomaly_str, (480, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_RED, 2, cv2.LINE_AA)
                return True, anomaly_list
        else:
            anomaly_list = [] #reset anomaly detect
        return False, anomaly_list

    def keep_last_video_anomaly(self):
        if len(self.image_list) >= KEEP_FRAME_COUNT:
            del self.image_list[0]
        self.image_list.append(self.image)

    def get_lefttop_dist(self, cnt):
        cx = cnt[:,:,0].min()
        cy = cnt[:,:,1].min()
        return np.sqrt(cx**2 + cy**2)

    def get_Wblack(self, img, search_wblock=True):
        status = False
        wblock_center_list = []
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if 'wblack_center' in self.feature_dict:
            cx, cy = self.feature_dict['wblack_center']
            wblock_center_list.append((cx,cy))
        if search_wblock:
            white_mask = cv2.inRange(hsv_img, (0,0,200), (256,80,256))
            contour, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
            contour = list(filter(lambda c: (cv2.contourArea(c)>1000) & ((cv2.contourArea(c)<200000)), contour))
            if len(contour)==0:
                cx, cy = 70,70
                wblock_center_list.append((cx,cy))
            else:
                #取最接近左上角的contour
                lefttop_dists = np.array(list(map(lambda c:self.get_lefttop_dist(c), contour)))
                #在白色方框內取一個圓圈範圍
                wblock_idx = np.argmin(lefttop_dists)
                wblock_cont = contour[wblock_idx]
                lefttop_dists = list(map(lambda c: np.sqrt(c[0]**2 + c[1]**2), wblock_cont.squeeze()))
                wblock_idx = np.argmin(lefttop_dists)
                cx, cy = wblock_cont[wblock_idx].squeeze()
                cx, cy = cx+30, cy+30
                wblock_center_list.append((cx,cy))
        for cx, cy in wblock_center_list:
            wblock_mask = np.zeros(gray_img.shape, dtype = "uint8")
            cv2.circle(wblock_mask, (cx, cy), 20, 255, -1)
            wblock_hsv = cv2.bitwise_and(hsv_img, hsv_img, mask=wblock_mask)
            wblock_s = wblock_hsv[:,:,1]
            wblock_gray = cv2.bitwise_and(gray_img, gray_img, mask=wblock_mask)
            wblock_s_mean = wblock_s[np.where(wblock_s>0)].mean() if len(np.where(wblock_s>0)[0])>0 else 0
            wblock_gray_mean = wblock_gray[np.where(wblock_gray>0)].mean() if len(np.where(wblock_gray>0)[0])>0 else 0
            wblock_gray_std = wblock_gray[np.where(wblock_gray>0)].std() if len(np.where(wblock_gray>0)[0])>0 else 0
            if (wblock_gray_std<10) & (wblock_gray_mean>127) & (wblock_s_mean<100) & (cx<120) & (cy<120):
                status = True
                break

#         self.feature_dict['wblock_search'] = search_wblock
#         self.feature_dict['wblack_status'] = status    
        self.feature_dict['wblack_center'] = (cx, cy) if status else self.feature_dict.get('wblack_center', (0,0))      
#         self.feature_dict['wblock_gray_std'] = wblock_gray_std
#         self.feature_dict['wblock_gray_mean'] = wblock_gray_mean
#         self.feature_dict['wblock_s_mean'] = wblock_s_mean
        return status

    def get_pass_window(self, img, passed_x_lower, passed_x_upper, passed_y_lower, passed_y_upper):
        status = False
        img_area = img.shape[0]*img.shape[1]
        lower_color = (53,239,70)
        upper_color = (98,255,121)
        mask1 = cv2.inRange(img, lower_color, upper_color)
        lower_color = (29,174,66) 
        upper_color = (124,255,151) 
        mask2 = cv2.inRange(img, lower_color, upper_color)
        lower_color = (36,190,40) 
        upper_color = (109,255,171) 
        mask3 = cv2.inRange(img, lower_color, upper_color)
        mask = mask1 + mask2 + mask3

        passes_mask = np.zeros(mask.shape, dtype=np.uint8)
        passes_mask[passed_y_lower:passed_y_upper, passed_x_lower:passed_x_upper] = 255
        mask = cv2.bitwise_and(mask, mask, mask=passes_mask)
        contour, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
        contour = list(filter(lambda c: cv2.contourArea(c)>4000, contour))
        if len(contour)==0:
            return status
        status = True
        return status
    
    def get_mask(self):
        self.height1 = int(self.height*(1/5))
        self.height2 = int(self.height*(4/5))
        self.width1 = int(self.width*(1/5))
        self.width2 = int(self.width*(4/5))

        mask_black = np.zeros((self.height, self.width), dtype="uint8")
        cv2.rectangle(mask_black, (self.width1, self.height1), (self.width2, self.height2), 255, -1)

        mask_white = np.zeros((self.height, self.width), dtype="uint8")
        cv2.rectangle(mask_white, (0, 0), (self.width, self.height), 255, -1)
        image_mask = cv2.bitwise_and(mask_white, mask_white, mask=mask_black)
        
        self.fg_pixels = np.count_nonzero(image_mask)
        self.spec_black = self.fg_pixels*2//3
        self.spec_blue = self.fg_pixels*2//3
        self.FG_MASK = image_mask 
        
    def create_baseline(self):
        contour, _ = cv2.findContours(self.fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
        if len(contour)>0:
            contour = sorted(contour, key=lambda c: cv2.contourArea(c), reverse=True)
            self.fg_contour = contour[0]
            self.fgmask = cv2.drawContours(np.zeros_like(self.fgmask), [self.fg_contour], -1, 255, -1)
            self.fgmask = cv2.morphologyEx(self.fgmask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=3)
            self.fgmask = cv2.bitwise_and(self.fgmask, self.fgmask, mask=self.FG_MASK)
            self.fg_pixels = np.count_nonzero(self.fgmask)
            self.fg_ratio = self.fg_pixels/((self.height2-self.height1)*(self.width2-self.width1))
            if self.fg_ratio> 0.3:
                self.fg_accum_score = self.fg_accum_score+1
            else:
                self.fg_accum_score = 0

            if self.fg_accum_score>2:
                self.feature_dict['spec_black'] = self.spec_black
                self.feature_dict['spec_blue'] = self.spec_blue 
                self.baseline_pass = True
                print(self.fid, 'baseline_pass')
            
    
    def _create_baseline(self):
        contour, _ = cv2.findContours(self.fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
        if len(contour)>0:
            contour = sorted(contour, key=lambda c: cv2.contourArea(c), reverse=True)
            self.fg_contour = contour[0]
            self.fgmask = cv2.drawContours(np.zeros_like(self.fgmask), [self.fg_contour], -1, 255, -1)
            self.fgmask = cv2.morphologyEx(self.fgmask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=3)
            self.fg_pixels = np.count_nonzero(self.fgmask)
            self.fg_ratio = self.fg_pixels/(self.width*self.height)
            if (self.fg_ratio> 0.5) & (self.fg_ratio< 0.9):
                print(self.fid)
                self.fg_accum_score = self.fg_accum_score+1
                self.fgmask_list.append(self.fgmask)
            else:
                self.fg_accum_score = 0
                self.fgmask_list = []

            if self.fg_accum_score>10:
                self.FG_MASK = reduce(lambda a, b:a+b, self.fgmask_list[-3:])
                self.spec_black = self.fg_pixels*2//3
                self.spec_blue = self.fg_pixels*2//3
                self.feature_dict['spec_black'] = self.spec_black
                self.feature_dict['spec_blue'] = self.spec_blue        
                self.baseline_pass = True
                print(self.fid, 'baseline_pass')
            else:
                self.FG_MASK = np.ones_like(self.fgmask)
    
    def get_vbb_score(self):
        self.var_mask = cv2.bitwise_and(self.fgmask, self.fgmask, mask=self.FG_MASK)
        self.var_pixel = np.count_nonzero(self.var_mask)
        self.blue_score, self.black_score = self.get_img_feature_YUV(self.image, self.FG_MASK)
        self.feature_dict['var_pixel'] = self.var_pixel
        self.feature_dict['blue_score'] = self.blue_score
        self.feature_dict['blue_ratio'] = f'{(self.blue_score/self.spec_blue*100):.0f}%'
        self.feature_dict['black_score'] = self.black_score
        self.feature_dict['black_ratio'] = f'{self.black_score/self.spec_black*100:.0f}%'
        self.is_hang = (self.var_pixel < self.spec_var)
    
    def detect_obj(self, detections, obj_str):
        self.obj_class = ''
        self.obj_score = -1
        self.obj_bbox = np.array([])
        is_obj_detected = False
        if len(detections)>0:
            for idx, detection in enumerate(detections):
                obj_class = detection.label
                obj_score = detection.prob
                print(obj_class, obj_score)
            detections_obj = list(filter(lambda x: x.label==obj_str, detections))
            detections_obj = sorted(detections_obj, key = lambda x: float(x.prob), reverse=True)
            detections_obj = list(filter(lambda x: float(x.prob)>=0.7, detections_obj))
            if len(detections_obj) != 0:
                detections_obj = detections_obj[0]
                self.obj_class = detections_obj.label
                self.obj_score = detections_obj.prob
                obj_rect = detections_obj.rect
                x,y,w,h= obj_rect.x, obj_rect.y, obj_rect.w, obj_rect.h
                x1, y1 = int(x),int(y)
                x2, y2 = int(x+w), int(y+h)
                self.obj_bbox = np.array([x1,y1,x2,y2])
                is_obj_detected = True
        self.feature_dict['obj_class'] = self.obj_class
        self.feature_dict['obj_score'] = self.obj_score
        self.feature_dict['obj_bbox'] = self.obj_bbox
        return is_obj_detected
    
    def detect_qrcode(self, detections):
        self.is_qrcode = False
        self.is_qrcode = self.detect_obj(detections, 'qrcode')
#         self.feature_dict['is_qrcode'] = self.is_qrcode
        
        
    def detect_pass(self):
        self.detections = self.yolo(self.image_copy)
        self.is_pass = False
        self.is_pass = self.detect_obj(self.detections, 'pass')
        self.feature_dict['is_pass'] = self.is_pass
        # -- stop detect --
        if self.is_pass:
            ad.writer_inf.close()
#             threading.Thread(target=self.save_test_video, args=(self.d_folder, self.image_list, self.fname, self.fps)).start() 
            print(self.fid, ' pass')
            
    def detect_pmuprocess(self):
        self.is_pmuprocess = False
        self.is_pmuprocess = self.detect_obj(self.detections, 'pmuprocess')
#         self.feature_dict['is_pmuprocess'] = self.is_pmuprocess
    
    def anomaly_detect(self):
        # -- anomaly detect --
        if self.is_hang:
            detections = self.yolo(self.image_copy)
            self.detect_qrcode(detections)
            if (self.blue_score > self.spec_blue) & (self.is_test_item == False) & (self.is_qrcode == True): #blue screen
                self.anomaly_type = ANOMALY_BLUE_STR
                cv2.putText(self.image, self.anomaly_type, (480, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_RED, 2, cv2.LINE_AA)
                self.is_anomaly = True
#                 self.is_anomaly, self.anomaly_list = self.anomaly(self.anomaly_list, ANOMALY_BLUE, self.image, ANOMALY_BLUE_STR)
            elif (self.black_score > self.spec_black) & (self.is_test_item == False): #black screen
                self.anomaly_type = ANOMALY_BLACK_STR
                self.is_anomaly, self.anomaly_list = self.anomaly(self.anomaly_list, ANOMALY_BLACK, self.image, ANOMALY_BLACK_STR)
            else:
                self.anomaly_type = ANOMALY_HANG_UP_STR
                self.is_anomaly, self.anomaly_list = self.anomaly(self.anomaly_list, ANOMALY_HANG_UP, self.image, ANOMALY_HANG_UP_STR)
        # -- normal detect --
        else:        
            self.anomaly_type = 'pass'
            self.anomaly_list = []
        self.feature_dict['is_hang'] = self.is_hang    
        self.feature_dict['anomaly_type'] = self.anomaly_type
        self.feature_dict['anomaly_list_len'] = len(self.anomaly_list)
        self.feature_dict['is_anomaly'] = self.is_anomaly
        
    def anomaly_detect_pmu(self):
        # -- anomaly detect --
        if (self.is_hang) & (self.count_sec<self.fid):
            detections = self.yolo(self.image_copy)
            self.detect_qrcode(detections)
            if (self.blue_score > self.spec_blue) & (self.is_qrcode == True): #blue screen
                self.anomaly_type = ANOMALY_BLUE_STR
                cv2.putText(self.image, self.anomaly_type, (480, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_RED, 2, cv2.LINE_AA)
                self.is_anomaly = True
#                 self.is_anomaly, self.anomaly_list = self.anomaly(self.anomaly_list, ANOMALY_BLUE, self.image, ANOMALY_BLUE_STR)
            elif (self.black_score > self.spec_black): #black screen
                self.anomaly_type = ANOMALY_BLACK_STR
                self.is_anomaly, self.anomaly_list = self.anomaly(self.anomaly_list, ANOMALY_BLACK, self.image, ANOMALY_BLACK_STR)
            else:
                self.anomaly_type = ANOMALY_HANG_UP_STR
                self.is_anomaly, self.anomaly_list = self.anomaly(self.anomaly_list, ANOMALY_HANG_UP, self.image, ANOMALY_HANG_UP_STR)
        # -- normal detect --
        else:        
            self.anomaly_type = 'pass'
            self.anomaly_list = []
        self.feature_dict['is_hang'] = self.is_hang    
        self.feature_dict['anomaly_type'] = self.anomaly_type
        self.feature_dict['anomaly_list_len'] = len(self.anomaly_list)
        self.feature_dict['is_anomaly'] = self.is_anomaly

    def save_test_video(self, folder, image_list, fname, fps):
        self.vindex += 1
        writer = imageio.get_writer(os.path.join(folder, fname + ('_%d.avi' % self.vindex)), format='avi', mode='I', fps=fps)
        for img in image_list:
            writer.append_data(img[:,:,::-1])
        writer.close()
        
    # -- raw video -- 
    def save_complete_video(self):
        if self.DEBUG:
            return
        self.writer_inf.append_data(self.image_copy[:,:,::-1])
        if self.fid % self.all_frame_cnt_limit == 0:
            self.vindex += 1
            self.writer_inf = imageio.get_writer(os.path.join(folder, fname + ('_%d.avi' % self.vindex)), format='avi', mode='I', fps=fps)
            
    def _save_complete_video(self):
        self.image_copy = self.image.copy()
        if self.DEBUG:
            return
        self.all_list.append(self.image_copy)
        if len(self.all_list) % self.all_frame_cnt_limit == 0:
            threading.Thread(target=self.save_test_video, args=(self.d_folder, self.all_list, self.fname, self.fps)).start()
            self.all_list = []
            
    # -- inference video -- 
    def _keep_inference_video(self): 
        self.all_list.append(self.image)
        if len(self.all_list) % self.all_frame_cnt_limit == 0:
            threading.Thread(target=self.save_test_video, args=(self.d_folder, self.all_list, self.fname, self.fps)).start()
            self.all_list = []
            
    def keep_inference_video(self):
        self.writer_inf.append_data(self.image[:,:,::-1])
            
    def draw_picture(self, start):
        self.process_fps = self.draw_fps(start, self.image, self.fps_list)
        self.feature_dict['process_fps'] = self.process_fps
        self.image = cv2.bitwise_and(self.image, self.image, mask=self.FG_MASK)
        color1 = COLOR_GREEN if self.is_test_item else COLOR_RED
        color2 = COLOR_ORANGE if self.is_hang else COLOR_GREEN
        if 'wblack_center' in self.feature_dict:
            self.wblack_center = self.feature_dict['wblack_center']
            self.image = cv2.circle(self.image, self.wblack_center, 20, color1, 3)
            self.image = cv2.circle(self.image, self.wblack_center, 9, color2, -1)
        self.image = self.put_text(self.image)
        self.keep_last_video_anomaly()
