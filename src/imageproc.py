import opencv
from opencv import highgui 
import math
import copy

# Local imports
from geometry import *
import ocr

# Adaptive threshold algorithm
param_adaptive_threshold_block_size = 45
param_adaptive_threshold_offset = 0

# Other detection parameters
param_collapse_threshold = 16
param_directions_threshold = 0.4
param_hough_threshold = 220
param_check_corners_tolerance_mul = 6
param_cross_mask_thickness = 8

# Number of pixels to go inside de cell for the mask cross
param_cross_mask_margin = 8

# Percentaje of points of the mask cross that must be active to decide a cross
param_cross_mask_threshold = 0.2
param_bit_mask_threshold = 0.35
param_bit_mask_radius_multiplier = 0.25
param_cell_mask_threshold = 0.6

# Parameters for id boxes detection
param_id_boxes_match_threshold = 0.5
param_id_boxes_min_height = 15

font = opencv.cvInitFont(opencv.CV_FONT_HERSHEY_SIMPLEX, 1.0, 1.0, 0, 3)

class ExamCapture(object):

    default_options = {'infobits': False,
                       'show-lines': False,
                       'show-image-proc': False,
                       'read-id': False,
                       'show-status': False,
                       'capture-from-file': False,
                       'capture-raw-file': None,
                       'capture-proc-file': None}

    @classmethod
    def get_default_options(cls):
        return copy.copy(cls.default_options)

    def __init__(self, camera, boxes_dim, options = {}):
        if options == {}:
            self.options = self.__class__.get_default_options()
        else:
            self.options = options
        if not self.options['capture-from-file']:
            self.image_raw = capture(camera, True)
            self.image_proc = pre_process(self.image_raw)
        elif self.options['capture-raw-file'] is not None:
            self.image_raw = load_image(self.options['capture-raw-file'])
            self.image_proc = pre_process(self.image_raw)
        elif self.options['capture-proc-file'] is not None:
            self.image_raw = load_image(self.options['capture-proc-file'])
            self.image_proc = rgb_to_gray(self.image_raw)
        else:
            raise Exception('Wrong capture options')
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
        self.id = None
        self.id_ocr_original = None
        self.id_scores = None
        self.status = {'overall': False,
                       'lines': False,
                       'boxes': False,
                       'cells': False,
                       'infobits': False,
                       'id-box-hlines': False,
                       'id-box': False}

    def detect(self):
        lines = detect_lines(self.image_proc)
        if len(lines) < 2:
            self.draw_status_bar()
            if self.options['show-status']:
                self.draw_status_flags()
            return
        self.status['lines'] = True
        axes = detect_boxes(lines, self.boxes_dim)
        if axes is not None:
            self.status['boxes'] = True
            self.corner_matrixes = cell_corners(axes[1][1], axes[0][1],
                                                self.image_raw.width,
                                                self.image_raw.height,
                                                self.boxes_dim)
            if len(self.corner_matrixes) > 0:
                self.status['cells'] = True
            self.id_hlines = id_horizontal_lines(axes[1][1], axes[0][1],
                                                 self.boxes_dim)
            if self.id_hlines != []:
                self.status['id-box-hlines'] = True
            if self.options['show-lines']:
                for line in axes[0][1]:
                    draw_line(self.image_drawn, line, (255, 0, 0))
                for line in axes[1][1]:
                    draw_line(self.image_drawn, line, (255, 0, 255))
                for corners in self.corner_matrixes:
                    for h in corners:
                        for c in h:
                            draw_point(self.image_drawn, c)
                if len(self.corner_matrixes) > 0 and self.options['read-id']:
                    for line in self.id_hlines:
                        draw_line(self.image_drawn, line, (255, 255, 0))
            if len(self.corner_matrixes) > 0 and \
                    (not self.options['read-id'] or self.id_hlines != []):
                self.decisions = decide_cells(self.image_proc,
                                              self.corner_matrixes)
                if self.options['infobits']:
                    self.bits = read_infobits(self.image_proc,
                                              self.corner_matrixes)
                    if self.bits is not None:
                        self.status['infobits'] = True
                        self.success = True
                    else:
                        self.success = False
                else:
                    self.success = True
                if self.success and self.options['read-id']:
                    self.id_corners = \
                        id_boxes_geometry(self.image_proc, self.id_hlines,
                                          self.image_raw.width,
                                          self.options['id-num-digits'])
                    if self.id_corners == None:
                        self.success = False
                    else:
                        self.status['id-box'] = True
                        self.detect_id()
                        if self.options['show-lines']:
                            for c in self.id_corners[0]:
                                draw_point(self.image_drawn, c)
                            for c in self.id_corners[1]:
                                draw_point(self.image_drawn, c)
        if self.success:
            self.compute_cells_geometry()
            self.status['overall'] = True
        else:
            self.draw_status_bar()
            if self.options['show-status']:
                self.draw_status_flags()

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
        if self.id is not None:
            draw_text(self.image_drawn, self.id, color_dot, (10, 30))

    def clean_drawn_image(self):
        self.image_drawn = opencv.cvCloneImage(self.image_raw)

    def compute_cells_geometry(self):
        self.centers = []
        self.diagonals = []
        for corners in self.corner_matrixes:
            for i in range(0, len(corners) - 1):
                row_centers = []
                row_diagonals = []
                for j in range(0, len(corners[0]) - 1):
                    row_centers.append(\
                        rect_center(corners[i][j], corners[i][j + 1],
                                    corners[i + 1][j], corners[i + 1][j + 1]))
                    row_diagonals.append(\
                        distance(corners[i][j], corners[i + 1][j + 1]))
                self.centers.append(row_centers)
                self.diagonals.append(row_diagonals)

    def detect_id(self):
        if self.id_corners is None:
            self.id = None
        corners_up, corners_down = self.id_corners
        digits = []
        self.id_scores = []
        for i in range(0, len(corners_up) - 1):
            corners = (corners_up[i], corners_up[i + 1],
                       corners_down[i], corners_down[i + 1])
            digit, scores = (ocr.digit_ocr(self.image_proc, corners,
                                           self.options['show-lines'],
                                           self.image_drawn))
            digits.append(digit)
            self.id_scores.append(scores)
#        print digits
        self.id = "".join([str(digit) if digit is not None else '0' \
                               for digit in digits])
        self.id_ocr_original = "".join([str(digit) \
                                            if digit is not None else '.' \
                                            for digit in digits])

    def draw_status_flags(self):
        flags = []
        flags.append(('L', self.status['lines']))
        flags.append(('B', self.status['boxes']))
        flags.append(('C', self.status['cells']))
        flags.append(('M', self.status['infobits']))
        flags.append(('H', self.status['id-box-hlines']))
        flags.append(('N', self.status['id-box']))
        color_good = (255, 0, 0)
        color_bad = (0, 0, 255)
        y = 75
        width = 24
        x = self.image_drawn.width - 5 - len(flags) * width
        for letter, value in flags:
            color = color_good if value else color_bad
            draw_text(self.image_drawn, letter, color, (x, y))
            x += width

    def draw_status_bar(self):
        color = (255, 0, 0)
        progress = 0
        if self.status['lines']:
            progress += 1
        if self.status['boxes']:
            progress += 1
        if self.status['cells']:
            progress += 1
        if self.status['infobits']:
            progress += 1
        if self.status['id-box-hlines']:
            progress += 1
        if self.status['id-box']:
            progress += 1
        max_progress = 6
        if not self.options['read-id']:
            max_progress -= 2
        if not self.options['infobits']:
            max_progress -= 1
        done_ratio = float(progress) / max_progress
        x0 = self.image_drawn.width - 60
        y0 = 10
        width = 50
        height = 20
        point0 = (x0, y0)
        point1 = (x0 + width, y0 + height)
        opencv.cvRectangle(self.image_drawn, point0, point1, color)
        point1 = round_point((x0 + done_ratio * width, y0 + height))
        opencv.cvRectangle(self.image_drawn, point0, point1, color,
                           opencv.CV_FILLED)

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

def draw_line(image, line, color = (0, 0, 255, 0)):
    theta = line[1]
    points = set()
    if math.sin(theta) != 0.0:
        points.add(line_point(line, x = 0))
        points.add(line_point(line, x = image.width - 1))
    if math.cos(theta) != 0.0:
        points.add(line_point(line, y = 0))
        points.add(line_point(line, y = image.height - 1))
    p_draw = [p for p in points if p[0] >= 0 and p[1] >= 0
              and p[0] < image.width and p[1] < image.height]
    if len(p_draw) == 2:
        opencv.cvLine(image, p_draw[0], p_draw[1], color, 1)

def draw_point(image, point, color = (255, 0, 0, 0), radius = 2):
    x, y = point
    if x >= 0 and x < image.width and y >= 0 and y < image.height:
        opencv.cvCircle(image, point, radius, color, opencv.CV_FILLED)
    else:
        print "draw_point: bad point (%d, %d)"%(x, y)

def draw_cross_mask(image, plu, pru, pld, prd, color = (255)):
    opencv.cvLine(image, plu, prd, color, param_cross_mask_thickness)
    opencv.cvLine(image, pld, pru, color, param_cross_mask_thickness)

def draw_cell_highlight(image, center, diagonal, color = (255, 0, 0)):
    radius = int(round(diagonal / 3.5))
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

def id_horizontal_lines(hlines, vlines, boxes_dim):
    h_expected = 3 + max([box[1] for box in boxes_dim])
    if len(hlines) < h_expected:
        lines = []
    else:
        lines = hlines[-h_expected:-h_expected + 2]
        if lines[1][0] - lines[0][0] < param_id_boxes_min_height:
            lines = []
    return lines

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
    plu, prd = closer_points(plu, prd, param_cross_mask_margin)
    pru, pld = closer_points(pru, pld, param_cross_mask_margin)
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
            center = round_point((corners[-1][i][0] + dx[0] / 2 + dy[0] / 2.6,
                                 corners[-1][i][1] + dx[1] / 2 + dy[1] / 2.6))
            bits.append(decide_infobit(image, mask, masked, center, dy))
    # Check validity
    if min([b[0] ^ b[1] for b in bits]) == True:
        return [b[0] for b in bits]
    else:
        return None

def decide_infobit(image, mask, masked, center_up, dy):
    center_down = add_points(center_up, dy)
    radius = int(round(math.sqrt(dy[0] * dy[0] + dy[1] * dy[1]) \
                           * param_bit_mask_radius_multiplier))
    if radius == 0:
        radius = 1
    opencv.cvSetZero(mask)
    opencv.cvCircle(mask, center_up, radius, (1), opencv.CV_FILLED)
    mask_pixels = opencv.cvCountNonZero(mask)
    opencv.cvMul(image, mask, masked)
    masked_pixels_up = opencv.cvCountNonZero(masked)
    opencv.cvSetZero(mask)
    opencv.cvCircle(mask, center_down, radius, (1), opencv.CV_FILLED)
    opencv.cvMul(image, mask, masked)
    masked_pixels_down = opencv.cvCountNonZero(masked)
    if mask_pixels < 1:
        print "Radius:", radius, "/ Mask pixels:", mask_pixels
        return (False, False)
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

def id_boxes_geometry(image, hlines, iwidth, num_cells):
    success = False
    plu, pru = line_bounds_adaptive(image, hlines[0], iwidth, 3)
    if plu is not None:
        pld, prd = line_bounds_adaptive(image, hlines[1], iwidth, 3)
    if plu is not None and pld is not None:
        # adjust corners
        outer_up = [plu, pru]
        outer_down = [pld, prd]
        success = id_boxes_adjust(image, outer_up, outer_down,
                                  hlines[0], hlines[1], 7, 0, iwidth)
        if success:
            corners_up = interpolate_line(outer_up[0], outer_up[1],
                                          num_cells + 1)
            corners_down = interpolate_line(outer_down[0], outer_down[1],
                                            num_cells + 1)
            success = id_boxes_adjust(image, corners_up, corners_down,
                                      hlines[0], hlines[1], 5, 5, iwidth)
    if success:
        return (corners_up, corners_down)
    else:
        return None

def id_boxes_adjust(image, corners_up, corners_down, line_up, line_down,
                    x_var, rho_var, iwidth):
    for i in range(0, len(corners_up)):
        up = corners_up[i]
        down = corners_down[i]
        selected = id_boxes_adjust_points(image, up, down, line_up, line_down,
                                          x_var, iwidth)
        if selected is not None:
            if rho_var > 0:
                if i == 0:
                    interval = (0, 2 * rho_var)
                elif i == len(corners_up) - 1:
                    interval = (- 2 * rho_var, 0)
                else:
                    interval = (- rho_var, rho_var)
                corners_up[i] = \
                    id_boxes_adjust_point_vertically(image, selected[0],
                                                     line_up, interval, iwidth)
                corners_down[i] = \
                    id_boxes_adjust_point_vertically(image, selected[1],
                                                     line_down, interval,
                                                     iwidth)
            else:
                corners_up[i] = selected[0]
                corners_down[i] = selected[1]
        else:
            return False
    return True

def id_boxes_adjust_points(image, p_up, p_down, line_up, line_down,
                           x_var, iwidth):
    points_up = []
    points_down = []
    for x in range(p_up[0] - x_var, p_up[0] + x_var + 1):
        p = line_point(line_up, x = x)
        if p[0] >= 0 and p[0] < iwidth and p[1] >= 0:
            points_up.append(p)
    for x in range(p_down[0] - x_var, p_down[0] + x_var + 1):
        p = line_point(line_down, x = x)
        if p[0] >= 0 and p[0] < iwidth and p[1] >= 0:
            points_down.append(p)
    energies = [(id_boxes_match_level(image, u, v), u, v) \
                    for u in points_up for v in points_down]
    energies.sort(reverse = True)
    if len(energies) > 0 and energies[0][0] > param_id_boxes_match_threshold:
        lim = len(energies)
        for i in range(1, lim):
            if energies[i][0] < energies[0][0]:
                lim = i
                break
        best = energies[:lim]
        avgx_up = float(sum([u[0] for (e, u, v) in best])) / len(best)
        avgx_down = float(sum([v[0] for (e, u, v) in best])) / len(best)
        best = [(abs(avgx_up - u[0]) + abs(avgx_down - v[0]), u, v) \
                    for (e, u, v) in best]
        best.sort()
        selected = best[0][1:]
        return selected
    else:
        return None

def id_boxes_adjust_point_vertically(image, point, line, interval, iwidth):
    rho, theta = line
    lines = [line]
    for i in range(interval[0], interval[1] + 1):
        lines.append((rho + i, theta))
        lines.append((rho - i, theta))
    values = []
    for l in lines:
        match = 0
        for xx in range(point[0] - 2, point[0] + 3):
            x, y = line_point(l, x = xx)
            if y >= 0 and x >= 0 and x < iwidth and image[y, x] > 0:
                match += 1
        p = line_point(l, x = point[0])
        values.append((match, p[1], p))
    values.sort(reverse = True)
    best = [(m, p) for (m, y, p) in values if m == values[0][0]]
    return best[len(best) // 2][1]

def id_boxes_match_level(image, p0, p1):
    points = [(x, y) for (x, y) in walk_line(p0, p1)]
    active = len([(x, y) for (x, y) in points if image[y, x] > 0])
    return float(active) / len(points)

# Utility functions
#
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
        slopes[0] = slope_inv(points[0], points[1])
    if points[2][1] == points[3][1]:
        if points[1][0] < points[0][0] and points[3][0] > points[2][0]:
            points = [points[0], points[1], points[3], points[2]]
    else:
        slopes[3] = slope_inv(points[2], points[3])
    slopes[1] = slope_inv(points[0], points[2])
    slopes[2] = slope_inv(points[1], points[3])
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
        x1 = int(round(p0[0] + slope0 * (y - p0[1])))
        x2 = int(round(p1[0] + slope1 * (y - p1[1])))
        inc = 1 if x1 < x2 else -1
        for x in range(x1, x2, inc):
            pix_total += 1
            if image[y, x] > 0:
                pix_marked += 1
    return (pix_total, pix_marked)

def line_bounds_adaptive(image, line, iwidth, rho_var):
    rho, theta = line
    lines = [line]
    for i in range(1, rho_var + 1):
        lines.append((rho + i, theta))
        lines.append((rho - i, theta))
    points = []
    for l in lines:
        pl, pr = line_bounds(image, l, iwidth)
        if pl is not None:
            points.append(pl)
            points.append(pr)
    if len(points) > 0:
        return min(points), max(points)
    else:
        return None, None

def line_bounds(image, line, iwidth):
    # points of intersection with x = 0 and x = width - 1
    p0 = line_point(line, x = 0)
    if p0[1] < 0:
        p0 = line_point(line, y = 0)
    p1 = line_point(line, x = iwidth - 1)
    if p1[1] < 0:
        p1 = line_point(line, y = 0)

    if not point_is_valid(p0, (image.width, image.height)) \
            or not point_is_valid(p1, (image.width, image.height)):
        return None, None

    # get bounds
    ini_found = False
    ini = None
    end = None
    last = 0
    count = 0
    for x, y in walk_line(p0, p1):
        value = 1 if image[y, x] > 0 else 0
        if value == last:
            count += 1
        else:
            last = value
            count = 1
        if not ini_found:
            if last == 1:
                if count == 1:
                    ini = (x, y)
                elif count == 3:
                    ini_found = True
        else:
            if last == 1 and count > 2:
                end = (x, y)
    if ini is None or end is None:
        ini = None
        end = None
    return ini, end
