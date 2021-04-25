#!/usr/bin/env python
# coding: utf-8

# # Pi YOLO-FASTEST TEST

# In[1]:


import sys, os, cv2, time
import imageio
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import ncnn


# In[2]:


def checkFolderExist(path):
    if not os.path.exists(path):
        os.makedirs(path)

def draw_boxes_v2(image, box, score, class_name, color):
    xmin, ymin, xmax, ymax = list(map(int, box))
    score = '{:.2f}'.format(score)
    label = '-'.join([class_name, score])
    font_size=0.6
    ret, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_size, 2)
    cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, 8)
    cv2.rectangle(image, (xmin, ymax - ret[1] - baseline), (xmin + ret[0], ymax), color, -1)
    cv2.putText(image, label, (xmin, ymax - baseline), cv2.FONT_HERSHEY_SIMPLEX, font_size, (255, 255, 255), 2)


# In[3]:


class Rect(object):
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def area(self):
        return self.w * self.h

    def intersection_area(self, b):
        x1 = np.maximum(self.x, b.x)
        y1 = np.maximum(self.y, b.y)
        x2 = np.minimum(self.x + self.w, b.x + b.w)
        y2 = np.minimum(self.y + self.h, b.y + b.h)
        return np.abs(x1 - x2) * np.abs(y1 - y2)
    
class Detect_Object(object):
    def __init__(self, label=0, prob=0, x=0, y=0, w=0, h=0):
        self.label = label
        self.prob = prob
        self.rect = Rect(x, y, w, h)
        
class YoloV4_Fastest:
    def __init__(self):
        self.target_size = 308
        self.mean_vals = []
        self.norm_vals = [1 / 255.0, 1 / 255.0, 1 / 255.0]

        self.net = ncnn.Net()
        self.net.opt.use_vulkan_compute = False
        self.net.opt.num_threads = 4

        self.net.load_param("model/yolov4-dct-opt.param")
        self.net.load_model("model/yolov4-dct-opt.bin")

        self.class_names = ["qrcode", "pass", "restart"]

    def __del__(self):
        self.net = None

    def __call__(self, img):
        img_h = img.shape[0]
        img_w = img.shape[1]

        mat_in = ncnn.Mat.from_pixels_resize(
            img,
            ncnn.Mat.PixelType.PIXEL_BGR2RGB,
            img.shape[1],
            img.shape[0],
            self.target_size,
            self.target_size,
        )
        mat_in.substract_mean_normalize(self.mean_vals, self.norm_vals)
        ex = self.net.create_extractor()
        ex.input("data", mat_in)
        ret, mat_out = ex.extract("output")
        objects = []
        for i in range(mat_out.h):
            values = mat_out.row(i)

            obj = Detect_Object()
            obj.prob = values[1]
            if obj.prob<0.5:
                continue            
            obj.label = values[0]
            obj.label = self.class_names[int(obj.label)-1]
            obj.rect.x = values[2] * img_w
            obj.rect.y = values[3] * img_h
            obj.rect.w = values[4] * img_w - obj.rect.x
            obj.rect.h = values[5] * img_h - obj.rect.y
            objects.append(obj)
        return objects


# **init yolo**

# In[4]:


yolo = YoloV4_Fastest()


# **detect**

# In[8]:



image_draw = cv2.imread('1200px-Bsodwindows10.png')
detections = yolo(image_draw)
if len(detections)>0:
    bbox_list=[]

for idx, detection in enumerate(detections):
    obj_class = detection.label
    obj_score = detection.prob
    obj_rect = detection.rect
    x,y,w,h= obj_rect.x, obj_rect.y, obj_rect.w, obj_rect.h
    x1, y1 = int(x),int(y)
    x2, y2 = int(x+w), int(y+h)  
    obj_bbox = np.array([x1,y1,x2,y2])
    bbox_list.append((obj_bbox, obj_score, obj_class))
for bbox in bbox_list:
    obj_bbox, obj_score, obj_class = bbox
    _ = draw_boxes_v2(image_draw, obj_bbox, obj_score, obj_class, (220,220,220))
image_draw = cv2.putText(image_draw, f'FPS:', (20,75) , cv2.FONT_HERSHEY_SIMPLEX , 0.8, (0,255,0), 1 )
image_draw = cv2.putText(image_draw, f'FID:', (20,95) , cv2.FONT_HERSHEY_SIMPLEX , 0.8, (0,255,0), 1 )
#plt.imshow(cv2.cvtColor(image_draw, cv2.COLOR_BGR2RGB))
cv2.imwrite('cc1.png', image_draw)



