import opencv
from opencv import highgui 
import math

param_collapse_threshold = 18
param_directions_threshold = 0.3
param_hough_threshold = 200
param_check_corners_tolerance_mul = 3
param_cross_mask_thickness = 6

# Number of pixels to go inside de cell for the mask cross
param_cross_mask_margin = 8

# Percentaje of points of the mask cross that must be active to decide a cross
param_cross_mask_threshold = 0.25

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

def draw_corner(image, x, y, color = (0, 0, 255, 0)):
    if x >= 0 and x < image.width and y >= 0 and y < image.height:
        opencv.cvCircle(image, (x, y), 5, color, opencv.CV_FILLED)
    else:
        print "draw_corner: bad point (%d, %d)"%(x, y)

def draw_cross_mask(image, plu, pru, pld, prd, color = (255)):
    opencv.cvLine(image, plu, prd, color, param_cross_mask_thickness)
    opencv.cvLine(image, pld, pru, color, param_cross_mask_thickness)

def detect_lines(image):
    st = opencv.cvCreateMemStorage()
    lines = opencv.cvHoughLines2(image, st, opencv.CV_HOUGH_STANDARD,
                                 1, 0.01, param_hough_threshold)
    if lines.total > 500:
        print "Too many lines in detect_directions:", lines.total
        return []
    s_lines = sorted([(float(l[0]), float(l[1])) for l in lines],
                     key = lambda x: x[1])
    return s_lines

def draw_lines(image_raw, image_proc, boxes_dim):
    lines = detect_lines(image_proc)
    if len(lines) < 2:
        return
    axes = detect_boxes(lines, boxes_dim)
    if axes is not None:
        corner_matrixes = cell_corners(axes[1][1], axes[0][1], image_raw.width,
                                       image_raw.height, boxes_dim)
        for line in axes[0][1]:
            draw_tangent(image_raw, line[0], line[1], (255, 0, 0))
        for line in axes[1][1]:
            draw_tangent(image_raw, line[0], line[1], (255, 0, 255))
        for corners in corner_matrixes:
            for h in corners:
                for c in h:
                    draw_corner(image_raw, c[0], c[1], (0, 0, 255))
        if len(corner_matrixes) > 0:
            draw_cross_mask(image_raw, corner_matrixes[0][7][3],
                            corner_matrixes[0][7][4], corner_matrixes[0][8][3],
                            corner_matrixes[0][8][4], (255, 0, 0))
            decide_cell(image_proc, corner_matrixes[0][7][3],
                        corner_matrixes[0][7][4], corner_matrixes[0][8][3],
                        corner_matrixes[0][8][4])

def detect_directions(lines):
    assert(len(lines) >= 2)
    axes = []
    rho, theta = lines[0]
    axes.append((theta, [(rho, theta)]))
    for rho, theta in lines[1:]:
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
    expected_vert = len(boxes_dim) + sum([box[0] for box in boxes_dim])
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
#    if horizontal:
#        print "Angle:", lines[0][1]
#        threshold = max(param_collapse_threshold \
#            - abs(lines[0][1] - math.pi / 2) * 14, param_collapse_threshold / 2)
#    else:
#        threshold = param_collapse_threshold
    threshold = param_collapse_threshold
#    print "Threshold", threshold
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

def cell_corners(hlines, vlines, iwidth, iheight, boxes_dim):
    h_expected = 1 + max([box[1] for box in boxes_dim])
    v_expected = len(boxes_dim) + sum([box[0] for box in boxes_dim])
    if len(vlines) != v_expected:
        return []
    if len(hlines) < h_expected:
        return []
    elif len(hlines) > h_expected:
        hlines = hlines[-h_expected:]
    corner_matrixes = []
    vini = 0
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
        vini += 1 + width
    if check_corners(corner_matrixes, iwidth, iheight):
        return corner_matrixes
    else:
        return []

def check_corners(corner_matrixes, width, height):
    # Check differences between horizontal lines:
    corners = corner_matrixes[0]
    ypoints = [row[-1][1] for row in corners]
    difs = []
    difs2 = []
    for i in range(1, len(ypoints)):
        difs.append(ypoints[i] - ypoints[i - 1])
    for i in range(1, len(difs)):
        difs2.append(difs[i] - difs[i - 1])
    max_difs2 = 1 + float(max(difs) - min(difs)) / len(difs) \
        * param_check_corners_tolerance_mul
    if max(difs2) > max_difs2:
        print "Failure in differences"
        print difs
        print difs2
        return False
    if 0.5 * max(difs) > min(difs):
        return False
    # Check that no points are negative
    for corners in corner_matrixes:
        for row in corners:
            for point in row:
                if point[0] < 0 or point[0] >= width \
                        or point[1] < 0 or point[1] >= height:
                    print "Failure at point", point
                    return False
    # Success if control reaches here
    return True

def decide_cell(image, plu, pru, pld, prd):
    dim = (image.width, image.height)
    plu, prd = get_closer_points(plu, prd, param_cross_mask_margin)
    pru, pld = get_closer_points(pru, pld, param_cross_mask_margin)
    mask = opencv.cvCreateImage(dim, 8, 1)
    masked = opencv.cvCreateImage(dim, 8, 1)
    opencv.cvSetZero(mask)
    draw_cross_mask(mask, plu, pru, pld, prd, (1))
    opencv.cvMul(image, mask, masked)
    draw_cross_mask(mask, plu, pru, pld, prd, (255))
    highgui.cvSaveImage("/tmp/test-mask.png", mask)
    highgui.cvSaveImage("/tmp/test-masked.png", masked)

def get_closer_points(p1, p2, offset):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    k = float(offset) / math.sqrt(dx * dx + dy * dy)
    return ((int(p1[0] + dx * k), int(p1[1] + dy * k)),
            (int(p2[0] - dx * k), int(p2[1] - dy * k)))

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

