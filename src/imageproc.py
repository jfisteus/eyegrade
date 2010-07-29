import opencv
from opencv import highgui 
import math

# Adaptive threshold algorithm
param_adaptive_threshold_block_size = 45
param_adaptive_threshold_offset = 0

# Other detection parameters
param_collapse_threshold = 18
param_directions_threshold = 0.3
param_hough_threshold = 230
param_check_corners_tolerance_mul = 3
param_cross_mask_thickness = 8

# Number of pixels to go inside de cell for the mask cross
param_cross_mask_margin = 8

# Percentaje of points of the mask cross that must be active to decide a cross
param_cross_mask_threshold = 0.2
param_bit_mask_threshold = 0.3
param_cell_mask_threshold = 0.45

font = opencv.cvInitFont(opencv.CV_FONT_HERSHEY_SIMPLEX, 1.0, 1.0, 0, 3)

class ExamCapture(object):

    default_options = [('infobits', False),
                       ('show-lines', False),
                       ('show-image-proc', False)]

    def __init__(self, camera, boxes_dim, options = {}):
        self.set_options(options)
        self.image_raw = capture(camera, True)
        self.image_proc = pre_process(self.image_raw)
        if not self.options['show-image-proc']:
            self.image_drawn = opencv.cvCloneImage(self.image_raw)
        else:
            self.image_drawn = gray_ipl_to_rgb(self.image_proc)
        self.height = self.image_raw.height
        self.width = self.image_raw.width
        self.boxes_dim = boxes_dim
        self.decisions = None
        self.corner_matrixes = None
        self.bits = None
        self.success = False
        self.solutions = None
        self.centers = []
        self.diagonals = []

    def set_options(self, options):
        for key, value in self.__class__.default_options:
            if not key in options:
                options[key] = value
        self.options = options

    def detect(self):
        lines = detect_lines(self.image_proc)
        if len(lines) < 2:
            return
        axes = detect_boxes(lines, self.boxes_dim)
        if axes is not None:
            self.corner_matrixes = cell_corners(axes[1][1], axes[0][1],
                                                self.image_raw.width,
                                                self.image_raw.height,
                                                self.boxes_dim)
            if self.options['show-lines']:
                for line in axes[0][1]:
                    draw_tangent(self.image_drawn, line[0], line[1],
                                 (255, 0, 0))
                for line in axes[1][1]:
                    draw_tangent(self.image_drawn, line[0], line[1],
                                 (255, 0, 255))
                for corners in self.corner_matrixes:
                    for h in corners:
                        for c in h:
                            draw_corner(self.image_drawn, c[0], c[1])
            if len(self.corner_matrixes) > 0:
                self.decisions = decide_cells(self.image_proc,
                                              self.corner_matrixes)
                if self.options['infobits']:
                    self.bits = read_infobits(self.image_proc,
                                              self.corner_matrixes)
                    self.success = (self.bits is not None)
                else:
                    self.success = True
        if self.success:
            self.compute_cells_geometry()
        draw_success_indicator(self.image_drawn, self.success)

    def draw_answers(self, solutions, model,
                     correct, good, bad, undet, im_id = None):
        base = 0
        color_good = (0, 164, 0)
        color_bad = (0, 0, 255)
        color_dot = (255, 0, 0)
        color = (255, 0, 0)
        for corners in self.corner_matrixes:
            for i in range(0, len(corners) - 1):
                d = self.decisions[base + i]
                if d > 0:
                    if correct is not None:
                        if correct[base + i]:
                            color = color_good
                        else:
                            color = color_bad
                    draw_cell_highlight(self.image_drawn,
                                        self.centers[base + i][d - 1],
                                        self.diagonals[base + i][d - 1], color)
                if solutions is not None and not correct[base + i]:
                    ans = solutions[base + i]
                    draw_cell_center(self.image_drawn,
                                     self.centers[base + i][ans - 1], color_dot)
            base += len(corners) - 1
        text = "Model %s: %d / %d"%(chr(65 + model), good, bad)
        if undet > 0:
            color = (0, 0, 255)
            text = text + " / " + str(undet)
        else:
            color = (255, 0, 0)
        draw_text(self.image_drawn, text, color,
                  (10, self.image_drawn.height - 20))
        if im_id is not None:
            color = (255, 0, 0) if self.success else (0, 0, 255)
            draw_text(self.image_drawn, str(im_id), color, (10, 65))

    def clean_drawn_image(self, success_indicator = True):
        self.image_drawn = opencv.cvCloneImage(self.image_raw)
        if success_indicator:
            draw_success_indicator(self.image_drawn, self.success)

    def compute_cells_geometry(self):
        self.centers = []
        self.diagonals = []
        for corners in self.corner_matrixes:
            for i in range(0, len(corners) - 1):
                row_centers = []
                row_diagonals = []
                for j in range(0, len(corners[0]) - 1):
                    row_centers.append(\
                        cell_center(corners[i][j], corners[i][j + 1],
                                    corners[i + 1][j], corners[i + 1][j + 1]))
                    row_diagonals.append(\
                        distance(corners[i][j], corners[i + 1][j + 1]))
                self.centers.append(row_centers)
                self.diagonals.append(row_diagonals)

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
                               opencv.CV_THRESH_BINARY_INV,
                               param_adaptive_threshold_block_size,
                               param_adaptive_threshold_offset)
    return thr

def gray_ipl_to_rgb(image):
    rgb = opencv.cvCreateImage((image.width, image.height), image.depth, 3)
    opencv.cvCvtColor(image, rgb, opencv.CV_GRAY2RGB)
    return rgb

def gray_ipl_to_rgb_pil(image):
    return opencv.adaptors.Ipl2PIL(gray_ipl_to_rgb(image))

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

def draw_cell_highlight(image, center, diagonal, color = (255, 0, 0)):
    radius = int(diagonal / 3.5)
    opencv.cvCircle(image, center, radius, color, 2)

def draw_cell_center(image, center, color = (255, 0, 0)):
    radius = 4
    opencv.cvCircle(image, center, radius, color, opencv.CV_FILLED)

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
    cell_marked = masked_pixels >= param_cross_mask_threshold * mask_pixels
    # If the whole cell is marked, don't count the result:
    if cell_marked:
        pix_total, pix_set = count_pixels_in_cell(image, plu, pru, pld, prd)
        cell_marked = pix_set < param_cell_mask_threshold * pix_total
#        print float(pix_set) / pix_total
    return cell_marked

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

def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) * (p1[0] - p2[0]) \
                         + (p1[1] - p2[1]) * (p1[1] - p2[1]))

def slope(p1, p2):
    return float(p2[0] - p1[0]) / (p2[1] - p1[1])

def cell_center(plu, pru, pld, prd):
    return ((plu[0] + prd[0]) / 2, (plu[1] + prd[1]) / 2)

def count_pixels_in_cell(image, plu, pru, pld, prd):
    """
        Count the number of pixels in a given quadrilateral.
        Returns a tuple with the total number of pixels and the
        number of non-zero pixels.
    """
    # Walk the quadrilateral in horizontal lines.
    # First, decide which borders limit each step of horizontal lines.
    points = sorted([plu, pru, pld, prd], key = lambda p: p[1])
    slopes = [None, None, None, None]
    if points[0][1] == points[1][1]:
        if points[1][0] < points[0][0] and points[3][0] > points[2][0]:
            points = [points[1], points[0], points[2], points[3]]
    else:
        slopes[0] = slope(points[0], points[1])
    if points[2][1] == points[3][1]:
        if points[1][0] < points[0][0] and points[3][0] > points[2][0]:
            points = [points[0], points[1], points[3], points[2]]
    else:
        slopes[3] = slope(points[2], points[3])
    slopes[1] = slope(points[0], points[2])
    slopes[2] = slope(points[1], points[3])
    pixels_total = 0
    pixels_active = 0
    c1 = count_pixels_horiz(image, points[0], slopes[0], points[0], slopes[1],
                            points[0][1], points[1][1])
    c2 = count_pixels_horiz(image, points[1], slopes[2], points[0], slopes[1],
                            points[1][1], points[2][1])
    c3 = count_pixels_horiz(image, points[1], slopes[2], points[2], slopes[3],
                            points[2][1], points[3][1])
    return (c1[0] + c2[0] + c3[0], c1[1] + c2[1] + c3[1])

def count_pixels_horiz(image, p0, slope0, p1, slope1, yini, yend):
    pix_total = 0
    pix_marked = 0
    for y in range(yini, yend):
        x1 = int(p0[0] + slope0 * (y - p0[1]))
        x2 = int(p1[0] + slope1 * (y - p1[1]))
        inc = 1 if x1 < x2 else -1
        for x in range(x1, x2, inc):
            pix_total += 1
            if image[y, x] > 0:
                pix_marked += 1
    return (pix_total, pix_marked)

def test_image(image_path):
    imrgb = load_image(image_path)
    im = load_image_grayscale(image_path)
    draw_lines(imrgb, im, [[4,10],[4,10]], True)
    highgui.cvSaveImage("/tmp/test-processed.png", imrgb)

