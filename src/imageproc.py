import opencv
from opencv import highgui 
import math

class Capturer:
    def __init__(self, input_dev = 0):
        self.camera = highgui.cvCreateCameraCapture(input_dev)

    def capture(self):
        return opencv.cvCloneImage(highgui.cvQueryFrame(self.camera))

    def capture_pil(self):
        return gray_ipl_to_rgb_pil(self.capture())

    def pre_process(self, image):
        gray = rgb_to_gray(image)
        thr = opencv.cvCreateImage((image.width, image.height), image.depth, 1)
        opencv.cvAdaptiveThreshold(gray, thr, 255,
                                   opencv.CV_ADAPTIVE_THRESH_GAUSSIAN_C,
                                   opencv.CV_THRESH_BINARY_INV, 17, 5)
        return thr

def gray_ipl_to_rgb_pil(image):
    rgb = opencv.cvCreateImage((image.width, image.height), image.depth, 3)
    opencv.cvCvtColor(image, rgb, opencv.CV_GRAY2RGB)
    return opencv.adaptors.Ipl2PIL(rgb)

def rgb_to_gray(image):
    gray = opencv.cvCreateImage((image.width, image.height), image.depth, 1)
    opencv.cvCvtColor(image, gray, opencv.CV_RGB2GRAY)
    return gray

def load_image_grayscale(filename):
    return rgb_to_gray(highgui.cvLoadImage(filename))

def load_image(filename):
    return highgui.cvLoadImage(filename)

def draw_tangent(image, rho, theta, color = (0, 0, 255, 0)):
    points = set()
    if (math.sin(theta) != 0.0):
        points.add((0, int(rho / math.sin(theta))))
        points.add((image.width - 1, int((rho - (image.width - 1)
                                     * math.cos(theta)) / math.sin(theta))))
    if (math.cos(theta) != 0.0):
        points.add((int(rho / math.cos(theta)), 0))
        points.add((int((rho - (image.height - 1) * math.sin(theta))
                        / math.cos(theta)), image.height - 1))
    p_draw = [p for p in points if p[0] >= 0 and p[1] >= 0
              and p[0] < image.width and p[1] < image.height]
    if len(p_draw) == 2:
        opencv.cvLine(image, p_draw[0], p_draw[1], color, 1)
    else:
        print "len(p_draw) ==", len(p_draw), "-", rho, theta
        print p_draw

def detect_lines(image):
    st = opencv.cvCreateMemStorage()
    return opencv.cvHoughLines2(image, st, opencv.CV_HOUGH_STANDARD,
                                1, 0.01, 300)

def draw_lines(image_raw, image_proc):
    lines = detect_lines(image_proc)
    for line in lines:
        draw_tangent(image_raw, line[0], line[1], (255, 0, 0))

