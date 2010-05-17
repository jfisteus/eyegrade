import opencv
from opencv import highgui 
import math

param_collapse_threshold = 20
param_directions_threshold = 0.2

class Capturer:
    def __init__(self, input_dev = 0):
        self.camera = highgui.cvCreateCameraCapture(input_dev)

    def capture(self, clone = False):
        image = highgui.cvQueryFrame(self.camera)
        if clone:
            return opencv.cvCloneImage(image)
        else:
            return image

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

def draw_corner(image, x, y, color = (0, 0, 255, 0)):
    if x >= 0 and x < image.width and y >= 0 and y < image.height:
        opencv.cvCircle(image, (x, y), 5, color, opencv.CV_FILLED)
    else:
        print "draw_corner: bad point (%d, %d)"%(x, y)

def detect_lines(image):
    st = opencv.cvCreateMemStorage()
    lines = opencv.cvHoughLines2(image, st, opencv.CV_HOUGH_STANDARD,
                                 1, 0.01, 230)
    return lines

def draw_lines(image_raw, image_proc, boxes_dim):
    lines = detect_lines(image_proc)
    if lines.total < 2:
        return
    axes = detect_boxes(lines, boxes_dim)
    if axes is not None:
        corner_matrixes = cell_corners(axes[1][1], axes[0][1], boxes_dim)
        for line in axes[0][1]:
            draw_tangent(image_raw, line[0], line[1], (255, 0, 0))
        for line in axes[1][1]:
            draw_tangent(image_raw, line[0], line[1], (255, 0, 255))
        for corners in corner_matrixes:
            for h in corners:
                for c in h:
                    draw_corner(image_raw, c[0], c[1])

def detect_directions(lines):
    assert(lines.total >= 2)
    s_lines = sorted([(l[0], l[1]) for l in lines], key = lambda x: x[1])
    axes = []
    rho, theta = s_lines[0]
    axes.append((theta, [(rho, theta)]))
    for rho, theta in s_lines[1:]:
        if abs(theta - axes[-1][0]) < param_directions_threshold:
            axes[-1][1].append((rho, theta))
        else:
            axes.append((theta, [(rho, theta)]))
    if abs(axes[0][0] - axes[-1][0] + math.pi) < param_directions_threshold:
        axes[0][1].extend([(-rho, theta - math.pi) \
                           for rho, theta in axes[-1][1]])
        del axes[-1]
    for i in range(0, len(axes)):
        avg = sum([theta for rho, theta in axes[i][1]]) / len(axes[i][1])
        axes[i] = (avg, sorted(axes[i][1], key = lambda x: abs(x[0])))
    if abs(axes[-1][0] - math.pi) < abs(axes[0][0]):
        axes = axes[-1:] + axes[0:-1]
    return axes

def detect_boxes(lines, boxes_dim):
    expected_horiz = 1 + max([box[1] for box in boxes_dim])
    expected_vert = 4 + sum([box[0] for box in boxes_dim])
    axes = detect_directions(lines)
    axes = [axis for axis in axes if len(axis[1]) >= 5]
    if len(axes) == 2:
        perpendicular = abs(axes[1][0] - axes[0][0] - math.pi / 2) < 0.1 \
            or abs(axes[1][0] - axes[0][0] + math.pi / 2) < 0.1
        if perpendicular:
            axes[0] = (axes[0][0], collapse_lines(axes[0][1], False))
            axes[1] = (axes[1][0], collapse_lines(axes[1][1], True))
            return axes
    return None

def collapse_lines(lines, horizontal):
    if horizontal:
        print "Angle:", lines[0][1]
        threshold = max(param_collapse_threshold \
            - abs(lines[0][1] - math.pi / 2) * 24, param_collapse_threshold / 2)
    else:
        threshold = param_collapse_threshold
    print "Threshold", threshold
    coll = []
    first = 0
    sum_rho = lines[0][0]
    sum_theta = lines[0][1]
    for i in range(1, len(lines)):
        if abs(lines[i][0] - lines[first][0]) > threshold:
            coll.append((sum_rho / (i - first), sum_theta / (i - first)))
            first = i
            sum_rho = lines[i][0]
            sum_theta = lines[i][1]
        else:
            sum_rho += lines[i][0]
            sum_theta += lines[i][1]
    coll.append((sum_rho / (len(lines) - first),
                 sum_theta / (len(lines) - first)))
    return coll

def cell_corners(hlines, vlines, boxes_dim):
    if len(hlines) != 1 + max([box[1] for box in boxes_dim]) \
            or len(vlines) != 4 + sum([box[0] for box in boxes_dim]):
        return []
    corner_matrixes = []
    vini = 1
    for box_dim in boxes_dim:
        width, height = box_dim
        corners = []
        for i in range(0, height + 1):
            cpart = []
            corners.append(cpart)
            for j in range(vini, vini + width + 1):
                c = intersection(hlines[i], vlines[j])
                cpart.append(c)
        corner_matrixes.append(corners)
        vini += 2 + width
    return corner_matrixes

def intersection(hline, vline):
    rho1, theta1 = hline
    rho2, theta2 = vline
    y = (rho1 * math.cos(theta2) - rho2 * math.cos(theta1)) \
        / (math.sin(theta1) * math.cos(theta2) \
               - math.sin(theta2) * math.cos(theta1))
    x = (rho2 - y * math.sin(theta2)) / math.cos(theta2)
    return (int(x), int(y))

def test_image(image_path):
    imrgb = load_image(image_path)
    im = load_image_grayscale(image_path)
    draw_lines(imrgb, im, [[4,10],[4,10]])
    highgui.cvSaveImage("/tmp/test-processed.png", imrgb)
