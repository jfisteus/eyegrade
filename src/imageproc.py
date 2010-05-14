import opencv
from opencv import highgui 

class Capturer:
    def __init__(self, input_dev = 0):
        self.camera = highgui.cvCreateCameraCapture(input_dev)

    def capture(self):
        image = highgui.cvQueryFrame(self.camera)
        return self.pre_process(image)

    def capture_pil(self):
        return gray_ipl_to_rgb_pil(self.capture())

    def pre_process(self, image):
        gray = opencv.cvCreateImage((image.width, image.height), image.depth, 1)
        thr = opencv.cvCreateImage((image.width, image.height), image.depth, 1)
        opencv.cvCvtColor(image, gray, opencv.CV_RGB2GRAY)
        opencv.cvAdaptiveThreshold(gray, thr, 255,
                                   opencv.CV_ADAPTIVE_THRESH_GAUSSIAN_C,
                                   opencv.CV_THRESH_BINARY, 17, 5)
        return thr

def gray_ipl_to_rgb_pil(image):
    rgb = opencv.cvCreateImage((image.width, image.height), image.depth, 3)
    opencv.cvCvtColor(image, rgb, opencv.CV_GRAY2RGB)
    return opencv.adaptors.Ipl2PIL(rgb)

