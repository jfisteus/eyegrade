import opencv
from opencv import highgui 
import math

param_collapse_threshold = 18
param_directions_threshold = 0.3
param_hough_threshold = 230
param_check_corners_tolerance_mul = 3
param_cross_mask_thickness = 6

# Number of pixels to go inside de cell for the mask cross
param_cross_mask_margin = 8

# Percentaje of points of the mask cross that must be active to decide a cross
param_cross_mask_threshold = 0.2
param_bit_mask_threshold = 0.3

font = opencv.cvInitFont(opencv.CV_FONT_HERSHEY_SIMPLEX, 1.0, 1.0, 0, 3)

def init_camera(input_dev = -1):
    return highgui.cvCreateCameraCapture(input_dev)

def capture(camera, clone = False):
    image = highgui.cvQueryFrame(camera)
    if clone:
        return opencv.cvCloneImage(image)
    else:
        return image

def pre_process(image):
    gray = rgb_to_gray(image)
    thr = opencv.cvCreateImage((image.width, image.height), image.depth, 1)
    opencv.cvAdaptiveThreshold(gray, thr, 255,
                               opencv.CV_ADAPTIVE_THRESH_GAUSSIAN_C,
                               opencv.CV_THRESH_BINARY_INV, 17, 5)
    return thr

def detect(image_raw, image_proc, boxes_dim, infobits = False):
    decisions = None
    corner_matrixes = None
    bits = None
    success = False
    lines = detect_lines(image_proc)
    if len(lines) < 2:
        return (False, None, None, None)
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
                    draw_corner(image_raw, c[0], c[1])
        if len(corner_matrixes) > 0:
            decisions = decide_cells(image_proc, corner_matrixes)
#            draw_answers(image_raw, corner_matrixes, decisions)
            if infobits:
                bits = read_infobits(image_proc, corner_matrixes)
                success = (bits is not None)
#                bits_text = "".join(["1" if b[1] else "0" for b in bits])
#                draw_text(image_raw, bits_text)
            else:
                success = True
    draw_success_indicator(image_raw, success)
    return (success, decisions, bits, corner_matrixes)

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

def draw_corner(image, x, y, color = (255, 0, 0, 0)):
    if x >= 0 and x < image.width and y >= 0 and y < image.height:
        opencv.cvCircle(image, (x, y), 5, color, opencv.CV_FILLED)
    else:
        print "draw_corner: bad point (%d, %d)"%(x, y)

def draw_cross_mask(image, plu, pru, pld, prd, color = (255)):
    opencv.cvLine(image, plu, prd, color, param_cross_mask_thickness)
    opencv.cvLine(image, pld, pru, color, param_cross_mask_thickness)

def draw_cell_highlight(image, plu, pru, pld, prd, color = (255, 0, 0)):
    center = cell_center(plu, pru, pld, prd)
    radius = int(math.sqrt((plu[0] - prd[0]) * (plu[0] - prd[0]) \
                           + (plu[1] - prd[1]) * (plu[1] - prd[1])) / 3.5)
    opencv.cvCircle(image, center, radius, color, 2)

def draw_answers(image, corner_matrixes, decisions, correct = None):
    base = 0
    color_good = (0, 164, 0)
    color_bad = (0, 0, 255)
    color = (255, 0, 0)
    for corners in corner_matrixes:
        for i in range(0, len(corners) - 1):
            d = decisions[base + i]
            if d > 0:
                if correct is not None:
                    color = color_good if correct[base + i] else color_bad
                draw_cell_highlight(image, corners[i][d - 1], corners[i][d],
                                    corners[i + 1][d - 1], corners[i + 1][d],
                                    color)
        base += len(corners) - 1

def draw_text(image, text, color = (255, 0, 0), position = (10, 30)):
    opencv.cvPutText(image, text, position, font, color)

def draw_success_indicator(image, success):
    position = (image.width - 15, 15)
    color = (0, 192, 0) if success else (0, 0, 255)
    opencv.cvCircle(image, position, 10, color, opencv.CV_FILLED)

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
#        print "Failure in differences"
#        print difs
#        print difs2
        return False
    if 0.5 * max(difs) > min(difs):
        return False
    # Check that no points are negative
    for corners in corner_matrixes:
        for row in corners:
            for point in row:
                if point[0] < 0 or point[0] >= width \
                        or point[1] < 0 or point[1] >= height:
#                    print "Failure at point", point
                    return False
    # Success if control reaches here
    return True

def decide_cells(image, corner_matrixes):
    dim = (image.width, image.height)
    mask = opencv.cvCreateImage(dim, 8, 1)
    masked = opencv.cvCreateImage(dim, 8, 1)
    decisions = []
    for corners in corner_matrixes:
        for i in range(0, len(corners) - 1):
            cell_decisions = []
            for j in range(0, len(corners[0]) - 1):
                cell_decisions.append(\
                    decide_cell(image, mask, masked,
                                corners[i][j], corners[i][j + 1],
                                corners[i + 1][j], corners[i + 1][j + 1]))
            decisions.append(decide_answer(cell_decisions))
    return decisions

def decide_cell(image, mask, masked, plu, pru, pld, prd):
    plu, prd = get_closer_points(plu, prd, param_cross_mask_margin)
    pru, pld = get_closer_points(pru, pld, param_cross_mask_margin)
    opencv.cvSetZero(mask)
    draw_cross_mask(mask, plu, pru, pld, prd, (1))
    mask_pixels = opencv.cvCountNonZero(mask)
    opencv.cvMul(image, mask, masked)
    masked_pixels = opencv.cvCountNonZero(masked)
#    print masked_pixels, mask_pixels, float(masked_pixels) / mask_pixels
    return (masked_pixels >= param_cross_mask_threshold * mask_pixels)

def read_infobits(image, corner_matrixes):
    dim = (image.width, image.height)
    mask = opencv.cvCreateImage(dim, 8, 1)
    masked = opencv.cvCreateImage(dim, 8, 1)
    bits = []
    for corners in corner_matrixes:
        for i in range(1, len(corners[0])):
            dx = diff_points(corners[-1][i - 1], corners[-1][i])
            dy = diff_points(corners[-1][i], corners[-2][i])
            center = (int(corners[-1][i][0] + dx[0] / 2 + dy[0] / 2.8),
                      int(corners[-1][i][1] + dx[1] / 2 + dy[1] / 2.8))
            bits.append(decide_infobit(image, mask, masked, center, dy))
    # Check validity
    if min([b[0] ^ b[1] for b in bits]) == True:
        return [b[0] for b in bits]
    else:
        return None

def decide_infobit(image, mask, masked, center_up, dy):
    center_down = add_points(center_up, dy)
    radius = int(math.sqrt(dy[0] * dy[0] + dy[1] * dy[1])) / 3
    opencv.cvSetZero(mask)
    opencv.cvCircle(mask, center_up, radius, (1), opencv.CV_FILLED)
    mask_pixels = opencv.cvCountNonZero(mask)
    opencv.cvMul(image, mask, masked)
    masked_pixels_up = opencv.cvCountNonZero(masked)
    opencv.cvSetZero(mask)
    opencv.cvCircle(mask, center_down, radius, (1), opencv.CV_FILLED)
    opencv.cvMul(image, mask, masked)
    masked_pixels_down = opencv.cvCountNonZero(masked)
    return (float(masked_pixels_up) / mask_pixels >= param_bit_mask_threshold,
            float(masked_pixels_down) / mask_pixels >= param_bit_mask_threshold)

def decide_answer(cell_decisions):
    marked = [i for i in range(0, len(cell_decisions)) if cell_decisions[i]]
    if len(marked) == 0:
        return 0
    elif len(marked) == 1:
        return marked[0] + 1
    else:
        return -1

# Geometry utility functions
#
def get_closer_points(p1, p2, offset):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    k = float(offset) / math.sqrt(dx * dx + dy * dy)
    return ((int(p1[0] + dx * k), int(p1[1] + dy * k)),
            (int(p2[0] - dx * k), int(p2[1] - dy * k)))

def diff_points(p1, p2):
    return (p1[0] - p2[0], p1[1] - p2[1])

def add_points(p1, p2):
    return (p1[0] + p2[0], p1[1] + p2[1])

def intersection(hline, vline):
    rho1, theta1 = hline
    rho2, theta2 = vline
    y = (rho1 * math.cos(theta2) - rho2 * math.cos(theta1)) \
        / (math.sin(theta1) * math.cos(theta2) \
               - math.sin(theta2) * math.cos(theta1))
    x = (rho2 - y * math.sin(theta2)) / math.cos(theta2)
    return (int(x), int(y))

def cell_center(plu, pru, pld, prd):
    return ((plu[0] + prd[0]) / 2, (plu[1] + prd[1]) / 2)

def test_image(image_path):
    imrgb = load_image(image_path)
    im = load_image_grayscale(image_path)
    draw_lines(imrgb, im, [[4,10],[4,10]], True)
    highgui.cvSaveImage("/tmp/test-processed.png", imrgb)

