import ncnn

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