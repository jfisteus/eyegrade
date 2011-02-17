import math
import copy
import sys
import pygame

# Local imports
from geometry import *
import ocr

# Import the cv module. If new style bindings not found, use the old ones:
try:
    import cv
    cv_new_style = True
except ImportError:
    import cvwrapper
    cv = cvwrapper.CVWrapperObject()
    cv_new_style = False

# Adaptive threshold algorithm
param_adaptive_threshold_block_size = 45
param_adaptive_threshold_offset = 0

# Other detection parameters
param_collapse_lines_maxgap = 7
param_directions_threshold = 0.4
param_hough_thresholds = [280, 260, 240, 225, 210, 195, 180, 160, 140]
param_failures_threshold = 10
param_check_corners_tolerance_mul = 6

# Thickness of the cross mask, as a fraction of the width of the cell
param_cross_mask_thickness = 0.2

# Number of pixels to go inside de cell for the mask cross
param_cross_mask_margin = 0.6
param_cross_mask_margin_2 = 0.75
param_cell_mask_margin = 0.9

# Percentage of points of the mask cross that must be active to decide a cross
param_cross_mask_threshold = 0.08

# Percentage of points outside the mask cross that must be active to
# decide a cleared answer
param_clear_out_threshold = 0.35

# Percentage of points inside the mask cross that must be active to
# decide a cleared answer
param_clear_in_threshold = 0.2

param_bit_mask_threshold = 0.35
param_bit_mask_radius_multiplier = 0.25
param_cell_mask_threshold = 0.6

# Parameters for id boxes detection
param_id_boxes_min_energy_threshold = 0.5
param_id_boxes_mean_energy_threshold = 0.75
param_id_boxes_energy_break = 0.99
param_id_boxes_min_height = 15
param_id_boxes_discard_distance = 20

# Other parameters
param_error_log = 'eyegrade-errors.log'
param_error_image_pattern = 'error-%s.png'

font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 1.0, 1.0, 0, 3)

class ExamCapture(object):

    default_options = {'infobits': False,
                       'show-lines': False,
                       'debug-ocr': False,
                       'show-image-proc': False,
                       'read-id': False,
                       'show-status': False,
                       'capture-from-file': False,
                       'capture-raw-file': None,
                       'capture-proc-file': None,
                       'error-logging': False,
                       'logging-dir': '.'}

    @classmethod
    def get_default_options(cls):
        return copy.copy(cls.default_options)

    def __init__(self, boxes_dim, context, options=None):
        if options is not None:
            self.options = options
        else:
            self.options = self.__class__.get_default_options()
        self.context = context
        if not self.options['capture-from-file']:
            self.image_raw = capture(self.context.camera, True)
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
            self.image_drawn = cv.CloneImage(self.image_raw)
        else:
            self.image_drawn = gray_ipl_to_rgb(self.image_proc)
        self.height = self.image_raw.height
        self.width = self.image_raw.width
        self.boxes_dim = boxes_dim
        self.num_questions = sum([b[1] for b in boxes_dim])
        self.decisions = [-1] * self.num_questions
        self.corner_matrixes = None
        self.bits = None
        self.success = False
        self.solutions = None
        self.centers = []
        self.diagonals = []
        self.id = None
        self.id_ocr_original = None
        self.id_scores = None
        self.id_corners = None
        self.status = {'overall': False,
                       'lines': False,
                       'boxes': False,
                       'cells': False,
                       'infobits': False,
                       'id-box-hlines': False,
                       'id-box': False}

    def detect_safe(self):
        try:
            self.detect()
        except Exception:
            self.success = False
            self.status['cells'] = False
            self.context.notify_failure()
            if self.options['error-logging']:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.write_error_trace(exc_type, exc_value, exc_traceback)
            # else... silence the exception, and try with the next capture

    def detect(self):
        axes = None
        lines = detect_lines(self.image_proc,
                             self.context.get_hough_threshold())
        if len(lines) >= 2:
            self.status['lines'] = True
            axes = detect_boxes(lines, self.boxes_dim)
#        for line in lines:
#            draw_line(self.image_drawn, line, (0, 0, 255))
        if axes is None:
            self.context.next_hough_threshold()
        else:
            self.status['boxes'] = True
            axes = filter_axes(axes, self.boxes_dim, self.image_raw.width,
                               self.image_raw.height, self.options['read-id'])
            self.corner_matrixes = cell_corners(axes[1][1], axes[0][1],
                                                self.image_raw.width,
                                                self.image_raw.height,
                                                self.boxes_dim)
            if len(self.corner_matrixes) > 0:
                self.status['cells'] = True
            if self.options['show-lines']:
                for line in axes[0][1]:
                    draw_line(self.image_drawn, line, (255, 0, 0))
                for line in axes[1][1]:
                    draw_line(self.image_drawn, line, (255, 0, 255))
                for corners in self.corner_matrixes:
                    for h in corners:
                        for c in h:
                            draw_point(self.image_drawn, c)
            if len(self.corner_matrixes) > 0:
#                draw_cell_crosses(self.image_drawn, self.corner_matrixes)
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
                    self.id_hlines, self.id_corners = \
                        id_boxes_geometry(self.image_proc,
                                          self.options['id-num-digits'],
                                          axes[1][1], self.boxes_dim)
                    if self.id_hlines:
                        self.status['id-box-hlines'] = True
                        if self.options['show-lines']:
                            for line in self.id_hlines:
                                draw_line(self.image_drawn, line, (255, 255, 0))
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
                self.context.notify_success()
            else:
                self.context.notify_failure()
        if self.status['cells']:
            self.compute_cells_geometry()
            self.status['overall'] = True

    def write_error_trace(self, exc_type, exc_value, exc_traceback):
        import datetime
        import re
        import traceback
        import os
        if not self.options['capture-from-file']:
            print 'Exception catched! Storing trace into a log file...'
            date = str(datetime.datetime.now())
            logname = os.path.join(self.options['logging-dir'], param_error_log)
            file_ = open(logname, 'a')
            file_.write('-' * 60 + '\n')
            file_.write(date + '\n')
            file_.write('Hough threshold: %d\n'\
                            %self.context.get_hough_threshold())
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      file=file_)
            file_.close()
            im_file = param_error_image_pattern%re.sub(r'[-\ \.:]', '_', date)
            cv.SaveImage(os.path.join(self.options['logging-dir'], im_file),
                         self.image_raw)
        else:
            traceback.print_exception(exc_type, exc_value, exc_traceback)

    def draw_status(self):
        self.draw_status_bar()
        if self.options['show-status']:
            self.draw_status_flags()
            self.draw_hough_threshold()

    def draw_answers(self, frozen, solutions, model,
                     correct, good, bad, undet, im_id = None):
        base = 0
        color_good = (0, 210, 0)
        color_bad = (0, 0, 255)
        color_dot = (255, 0, 0)
        color_blank = (192, 0, 192)
        if self.status['cells']:
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
                                            self.diagonals[base + i][d - 1],
                                            color)
                    if len(solutions) > 0 and not correct[base + i]:
                        color = color_blank if d == 0 else color_dot
                        radius = 5 if d == 0 else 3
                        ans = solutions[base + i]
                        draw_cell_center(self.image_drawn,
                                         self.centers[base + i][ans - 1],
                                         color, radius)
                base += len(corners) - 1
        if model is not None:
            text = "Model %s: %d / %d"%(model, good, bad)
        else:
            text = "Model ?: %d / %d"%(good, bad)
        if undet > 0:
            color = color_bad
            text = text + " / " + str(undet)
        else:
            color = color_dot
        draw_text(self.image_drawn, text, color,
                  (10, self.image_drawn.height - 20))
        if frozen:
            if im_id is not None:
                if self.status['infobits'] and model is not None:
                    color = color_dot
                else:
                    color = color_bad
                draw_text(self.image_drawn, str(im_id), color, (10, 65))
            if self.id is not None:
                draw_text(self.image_drawn, self.id, color, (10, 30))
        else:
            self.draw_status_bar()
        if self.options['show-status']:
            self.draw_status_flags()
            self.draw_hough_threshold()

    def clean_drawn_image(self):
        self.image_drawn = cv.CloneImage(self.image_raw)

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
                                           self.options['debug-ocr'],
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

    def draw_hough_threshold(self):
        pos = (self.image_drawn.width - 77, 110)
        draw_text(self.image_drawn, str(self.context.get_hough_threshold()),
                  position=pos)

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
        cv.Rectangle(self.image_drawn, point0, point1, color)
        point1 = round_point((x0 + done_ratio * width, y0 + height))
        cv.Rectangle(self.image_drawn, point0, point1, color, cv.CV_FILLED)

class ExamCaptureContext:
    """ Class intended for persistency of data accross several
        ExamCapture objects.

    """
    def __init__(self, fixed_hough_threshold=None):
        if not fixed_hough_threshold:
            self.hough_thresholds = param_hough_thresholds
        else:
            self.hough_thresholds = [fixed_hough_threshold]
        self.hough_thresholds_idx = 0
        self.failures_in_a_row = 0
        self.camera = None

    def init_camera(self, camera_id):
        """Initializes the camera device.

           If the given camera_id is -1, camera ids are tested one by
           until one works.

        """
        self.camera = None
        if camera_id != -1:
            self.camera = self.__try_camera(camera_id)
            self.camera_id = camera_id
        if self.camera is None:
            self.camera, self.camera_id = self.__try_next_camera(-1)
        return self.camera is not None

    def next_camera(self):
        """Selects the next camera available.

           Note that changing camera does not seem to work currently
           in OpenCV, at least in Linux.

        """

        if self.camera is not None:
            del self.camera
        camera, camera_id = self.__try_next_camera(self.camera_id)
        if camera is not None:
            self.camera, self.camera_id = camera, camera_id
            return True
        else:
            return False

    def get_hough_threshold(self):
        return self.hough_thresholds[self.hough_thresholds_idx]

    def next_hough_threshold(self):
        self.hough_thresholds_idx = (self.hough_thresholds_idx + 1) % \
            len(self.hough_thresholds)
        self.failures_in_a_row = 0

    def notify_failure(self):
        self.failures_in_a_row += 1
        if self.failures_in_a_row > param_failures_threshold:
            self.next_hough_threshold()

    def notify_success(self):
        self.failures_in_a_row = 0

    def __try_next_camera(self, cur_camera_id):
        camera = None
        camera_id = -1
        for i in range(cur_camera_id + 1, 10) + range(0, cur_camera_id + 1):
            print "Trying camera", i
            camera = self.__try_camera(i)
            if camera is not None:
                camera_id = i
                break
        return (camera, camera_id)

    def __try_camera(self, camera_id):
        cam = cv.CaptureFromCAM(camera_id)
        image = cv.QueryFrame(cam)
        if image is not None:
            return cam
        else:
            return None

def init_camera(input_dev = -1):
    return cv.CaptureFromCAM(input_dev)

def capture(camera, clone = False):
    image = cv.QueryFrame(camera)
    if clone:
        return cv.CloneImage(image)
    else:
        return image

def pre_process(image):
    gray = rgb_to_gray(image)
    thr = cv.CreateImage((image.width, image.height), image.depth, 1)
    cv.AdaptiveThreshold(gray, thr, 255,
                         cv.CV_ADAPTIVE_THRESH_GAUSSIAN_C,
                         cv.CV_THRESH_BINARY_INV,
                         param_adaptive_threshold_block_size,
                         param_adaptive_threshold_offset)
    return thr

def gray_ipl_to_rgb(image):
    rgb = cv.CreateImage((image.width, image.height), image.depth, 3)
    cv.CvtColor(image, rgb, cv.CV_GRAY2RGB)
    return rgb

def rgb_to_gray(image):
    gray = cv.CreateImage((image.width, image.height), image.depth, 1)
    cv.CvtColor(image, gray, cv.CV_RGB2GRAY)
    return gray

def load_image_grayscale(filename):
    return rgb_to_gray(cv.LoadImage(filename))

def load_image(filename):
    return cv.LoadImage(filename)

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
        cv.Line(image, p_draw[0], p_draw[1], color, 1)

def draw_point(image, point, color = (255, 0, 0, 0), radius = 2):
    x, y = point
    if x >= 0 and x < image.width and y >= 0 and y < image.height:
        cv.Circle(image, point, radius, color, cv.CV_FILLED)
    else:
        print "draw_point: bad point (%d, %d)"%(x, y)

def draw_cross_mask(image, plu, pru, pld, prd, color, thickness):
    cv.Line(image, plu, prd, color, int(thickness))
    cv.Line(image, pld, pru, color, int(thickness))

def draw_cell_highlight(image, center, diagonal, color = (255, 0, 0)):
    radius = int(round(diagonal / 3.5))
    cv.Circle(image, center, radius, color, 2)

def draw_cell_center(image, center, color=(255, 0, 0), radius=4):
    cv.Circle(image, center, radius, color, cv.CV_FILLED)

def draw_text(image, text, color = (255, 0, 0), position = (10, 30)):
    cv.PutText(image, text, position, font, color)

def draw_success_indicator(image, success):
    position = (image.width - 15, 15)
    color = (0, 192, 0) if success else (0, 0, 255)
    cv.Circle(image, position, 10, color, cv.CV_FILLED)

def draw_cell_crosses(image, corner_matrixes):
    for corners in corner_matrixes:
        for i in range(0, len(corners) - 1):
            for j in range(0, len(corners[0]) - 1):
                thickness = (distance(corners[i][j], corners[i][j + 1])
                             * param_cross_mask_thickness)
                plu, prd = closer_points_rel(corners[i][j],
                                             corners[i + 1][j + 1],
                                             param_cross_mask_margin,
                                             thickness / 2)
                pru, pld = closer_points_rel(corners[i][j + 1],
                                             corners[i + 1][j],
                                             param_cross_mask_margin,
                                             thickness / 2)
                draw_cross_mask(image, plu, pru, pld, prd, (0, 0, 255),
                                thickness)
                plu, prd = closer_points_rel(corners[i][j],
                                             corners[i + 1][j + 1],
                                             param_cross_mask_margin_2,
                                             thickness / 4)
                pru, pld = closer_points_rel(corners[i][j + 1],
                                             corners[i + 1][j],
                                             param_cross_mask_margin_2,
                                             thickness / 4)
                draw_cross_mask(image, plu, pru, pld, prd, (0, 0, 255),
                                thickness / 2)

def detect_lines(image, hough_threshold):
    st = cv.CreateMemStorage()
    lines = cv.HoughLines2(image, st, cv.CV_HOUGH_STANDARD,
                           1, 0.01, hough_threshold)

    # Trick to use both new and old style bindings
    len_lines = len(lines) if cv_new_style else lines.total
    if len_lines > 500:
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
    v_expected = len(boxes_dim) + sum([box[0] for box in boxes_dim])
    h_expected = 1 + max([box[1] for box in boxes_dim])
    axes = detect_directions(lines)
    axes = [axis for axis in axes \
                if len(axis[1]) >= min(v_expected, h_expected)]
    if len(axes) == 3:
        if angles_perpendicular(axes[0][0], axes[1][0]):
            del axes[2]
        elif angles_perpendicular(axes[0][0], axes[2][0]):
            del axes[1]
        else:
            del axes[0]
    if len(axes) == 2:
        if angles_perpendicular(axes[0][0], axes[1][0]):
            return axes
    else:
        return None

def filter_axes(axes, boxes_dim, image_width, image_height, read_id):
    """Filters out lines near borders and lines too close to other lines.

       - axes: [(vlines_angle, vlines), (hlines_angle, hlines)]
       - boxes_dim: expected answer boxes dimensions
       - image_width, image_height: image size
       - read_id: True if the id must be read
       Returns a new axes object with updated lines if success or
       the lines without collapsing if not.

    """
    # First, filter out lines too close to image borders
    axes = ((axes[0][0], [l for l in axes[0][1] \
                             if ((abs(l[0]) < 0.97 * image_width and
                                  abs(l[0]) > 0.03 * image_width) or
                                 not angles_perpendicular(math.pi / 2, l[1]))]),
            (axes[1][0], [l for l in axes[1][1] \
                              if ((abs(l[0]) < 0.97 * image_width and
                                  abs(l[0]) > 0.03 * image_height) or
                                  not angles_perpendicular(0.0, l[1]))]))
    # Now, colapse lines that are too close
    v_expected = len(boxes_dim) + sum([box[0] for box in boxes_dim])
    h_expected = 1 + max([box[1] for box in boxes_dim])
    if read_id:
        h_expected += 2
    hlines = collapse_lines_angles(axes[1][1], h_expected, True)
    if hlines is None:
        return axes
    vlines = collapse_lines_angles(axes[0][1], v_expected, False)
    if vlines is None:
        return axes
    return [(axes[0][0], vlines), (axes[1][0], hlines)]

def collapse_lines_angles(lines, expected, horizontal):
    """Collapses lines that are close together.

       Receives the list of pairs of lines (rho, theta), the expected
       number of lines to be matched, and whether lines are horizontal
       or not. Returns the lines or None if the expected number of
       lines is not matched.

    """
    if len(lines) < 2:
        return None
    success = False
    main_lines = []
    sum_rho = lines[0][0]
    sum_theta = lines[0][1]
    num_lines = 1
    new_group = True
    last_line = lines[0]
    for line in lines[1:]:
        if ((((horizontal and line[1] > last_line[1]) or
              (not horizontal and line[1] < last_line[1])) and
             abs(line[0] - last_line[0]) >= 5) or
            abs(line[0] - last_line[0]) > param_collapse_lines_maxgap):
            main_lines.append((sum_rho / num_lines, sum_theta / num_lines))
            sum_rho = line[0]
            sum_theta = line[1]
            num_lines = 1
        else:
            sum_rho += line[0]
            sum_theta += line[1]
            num_lines += 1
        last_line = line
    main_lines.append((sum_rho / num_lines, sum_theta / num_lines))
    if (not horizontal and len(main_lines) == expected) or horizontal:
        return main_lines
    else:
        return None

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
    corners = corner_matrixes[(len(corner_matrixes) - 1) // 2]
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

    # Check that the sequence of points is coherent
    for corners in corner_matrixes:
        for i in range(0, len(corners) - 1):
            for j in range(0, len(corners[0]) - 1):
                if corners[i][j][1] >= corners[i + 1][j][1] or \
                        corners[i][j + 1][1] >= corners[i + 1][j + 1][1] or \
                        corners[i][j][0] >= corners[i][j + 1][0] or \
                        corners[i + 1][j][0] >= corners[i + 1][j + 1][0]:
                    return False

    # Success if control reaches here
    return True

def decide_cells(image, corner_matrixes):
    dim = (image.width, image.height)
    mask = cv.CreateImage(dim, 8, 1)
    masked = cv.CreateImage(dim, 8, 1)
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
    thickness = distance(plu, pru) * param_cross_mask_thickness
    cv.SetZero(mask)
    iplu, iprd = closer_points_rel(plu, prd, param_cross_mask_margin,
                                   thickness / 2)
    ipru, ipld = closer_points_rel(pru, pld, param_cross_mask_margin,
                                   thickness / 2)
    draw_cross_mask(mask, iplu, ipru, ipld, iprd, (1), thickness)
    iplu, iprd = closer_points_rel(plu, prd, param_cross_mask_margin_2,
                                   thickness / 4)
    ipru, ipld = closer_points_rel(pru, pld, param_cross_mask_margin_2,
                                   thickness / 4)
    draw_cross_mask(mask, iplu, ipru, ipld, iprd, (1), thickness / 2)
    mask_pixels = cv.CountNonZero(mask)
    cv.Mul(image, mask, masked)
    masked_pixels = cv.CountNonZero(masked)
    cell_marked = masked_pixels > param_cross_mask_threshold * mask_pixels
    # If the whole cell is marked, don't count the result:
    if cell_marked:
        iplu, iprd = closer_points_rel(plu, prd, param_cell_mask_margin)
        ipru, ipld = closer_points_rel(pru, pld, param_cell_mask_margin)
        pix_total, pix_set = count_pixels_in_cell(image, iplu, ipru, ipld, iprd)
        cell_marked = (masked_pixels < param_clear_in_threshold * mask_pixels or
                       (pix_set - masked_pixels) < (pix_total - mask_pixels) * \
                           param_clear_out_threshold)
    # Debug
#    iplu, iprd = closer_points_rel(plu, prd, param_cell_mask_margin)
#    ipru, ipld = closer_points_rel(pru, pld, param_cell_mask_margin)
#    pix_total, pix_set = count_pixels_in_cell(image, iplu, ipru, ipld, iprd)
#    print 'total: %d, set: %d, mask: %d, masked: %d'%(pix_total, pix_set,
#                                                      mask_pixels,
#                                                      masked_pixels)
    return cell_marked

def read_infobits(image, corner_matrixes):
    dim = (image.width, image.height)
    mask = cv.CreateImage(dim, 8, 1)
    masked = cv.CreateImage(dim, 8, 1)
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
    radius = int(round(math.sqrt(dy[0] * dy[0] + dy[1] * dy[1]) / 3))
    cv.SetZero(mask)
    cv.Circle(mask, center_up, radius, (1), cv.CV_FILLED)
    mask_pixels = cv.CountNonZero(mask)
    cv.Mul(image, mask, masked)
    masked_pixels_up = cv.CountNonZero(masked)
    cv.SetZero(mask)
    cv.Circle(mask, center_down, radius, (1), cv.CV_FILLED)
    cv.Mul(image, mask, masked)
    masked_pixels_down = cv.CountNonZero(masked)
    if mask_pixels < 1:
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

def id_boxes_geometry(image, num_cells, lines, boxes_dim):
    success = False
    # First, select the upper and bottom id lines
    discard = 1 + max([box[1] for box in boxes_dim])
    lim = 3.5 * lines[-discard][0] - 2.5 * lines[-discard + 1][0]
    hlines = [l for l in lines[:-discard] if l[0] > lim]
    if len(hlines) < 2:
        return None, None
    elif len(hlines) > 2:
        hlines = [hlines[0], hlines[-1]]
#        weights = [(count_pixels_in_horizontal_line(image, line), line) \
#                       for line in lines]
#        hlines = [weights[0][1], weights[1][1]]
    min_height = 0.5 * (lines[-discard + 1][0] - lines[-discard][0])
    if hlines[1][0] - hlines[0][0] < min_height:
        return None, None
    # Now, adjust corners
    pairs_left, pairs_right = line_bounds_adaptive(image, hlines[0], hlines[1],
                                                   image.width, 5)
    all_bounds = [(l[0], r[0], l[1], r[1]) \
                      for l in pairs_left for r in pairs_right]
#    print "len(all_bounds):", len(all_bounds)
#    i = 1
    for bounds in all_bounds[:5]:
        corners = id_boxes_check_points(image, bounds, hlines,
                                        image.width, num_cells)
        if corners is not None:
#            print "success", i
            success = True
            break
#        i += 1
    if success:
        return hlines, corners
    else:
        return hlines, None

def id_boxes_check_points(image, points, hlines, iwidth, num_cells):
    plu, pru, pld, prd = points
    outer_up = [plu, pru]
    outer_down = [pld, prd]
    success = id_boxes_adjust(image, outer_up, outer_down,
                              hlines[0], hlines[1], 10, 5, iwidth)
    if success:
        corners_up = interpolate_line(outer_up[0], outer_up[1],
                                      num_cells + 1)
        corners_down = interpolate_line(outer_down[0], outer_down[1],
                                        num_cells + 1)
        success = id_boxes_adjust(image, corners_up, corners_down,
                                  hlines[0], hlines[1], 10, 5, iwidth)
    if success:
        return (corners_up, corners_down)
    else:
        return None

def id_boxes_adjust(image, corners_up, corners_down, line_up, line_down,
                    x_var, rho_var, iwidth):
    mean_energy = 0.0
    num_corners = len(corners_up)
    for i in range(0, num_corners):
        up = corners_up[i]
        down = corners_down[i]
        selected, energy = id_boxes_adjust_points(image, up, down,
                                                  line_up, line_down,
                                                  x_var, iwidth)
#        print "...", energy
        mean_energy += energy / num_corners
        if energy < param_id_boxes_min_energy_threshold:
            return False
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
#    print mean_energy
    if mean_energy > param_id_boxes_mean_energy_threshold:
        return True
    else:
        return False

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
    pairs = [(u, v) for u in points_up for v in points_down]
    energies = []
    best = None
    for u, v in pairs:
        energy = id_boxes_match_level(image, u, v)
        if energy > param_id_boxes_energy_break:
            best = ((u, v), energy)
            break
        else:
            energies.append((energy, u, v))
    if best is not None:
        return best
    else:
        energies.sort(reverse = True)
        if len(energies) > 0:
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
            return selected, energies[0][0]
        else:
            return None, 0.0

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
    total = 0
    marked = 0
    points = sorted([plu, pru, pld, prd], key = lambda p: p[1])
    same_side = (points[0][0] < points[1][0] and points[2][0] < points[3][0] or
                 points[0][0] > points[1][0] and points[2][0] > points[3][0])
    if points[0][1] < points[1][1]:
        slope1 = slope_inv(points[0], points[1])
        if same_side:
            slope2 = slope_inv(points[0], points[2])
        else:
            slope2 = slope_inv(points[0], points[3])
        t, m = count_pixels_horiz(image, points[0], slope1, points[0], slope2,
                                  points[0][1], points[1][1])
        total += t
        marked += m
    if points[1][1] < points[2][1]:
        if same_side:
            slope1 = slope_inv(points[0], points[2])
            slope2 = slope_inv(points[1], points[3])
        else:
            slope1 = slope_inv(points[0], points[3])
            slope2 = slope_inv(points[1], points[2])
        t, m = count_pixels_horiz(image, points[0], slope1, points[1], slope2,
                                  points[1][1], points[2][1])
        total += t
        marked += m
    if points[2][1] < points[3][1]:
        slope1 = slope_inv(points[2], points[3])
        if same_side:
            slope2 = slope_inv(points[1], points[3])
            point2 = points[1]
        else:
            slope2 = slope_inv(points[2], points[3])
            point2 = points[2]
        t, m = count_pixels_horiz(image, points[2], slope1, point2, slope2,
                                  points[2][1], points[3][1])
        total += t
        marked += m
    return total, marked

def count_pixels_horiz(image, p0, slope0, p1, slope1, yini, yend):
    pix_total = 0
    pix_marked = 0
    for y in range(yini, yend):
        x1 = int(round(p0[0] + slope0 * (y - p0[1])))
        x2 = int(round(p1[0] + slope1 * (y - p1[1])))
        inc = 1 if x1 < x2 else -1
        for x in range(x1, x2 + inc, inc):
            pix_total += 1
            if image[y, x] > 0:
                pix_marked += 1
    return (pix_total, pix_marked)

def line_bounds_adaptive(image, line_up, line_down, iwidth, rho_var):
    points_left_up, points_right_up = \
        line_bounds_one_line(image, line_up, iwidth, rho_var)
    points_left_down, points_right_down = \
        line_bounds_one_line(image, line_down, iwidth, rho_var)
    pairs_left = [line_bounds_rank(p_up, p_down, line_up, line_down) \
                  for p_up in points_left_up for p_down in points_left_down]
    pairs_right = [line_bounds_rank(p_up, p_down, line_up, line_down) \
                   for p_up in points_right_up for p_down in points_right_down]
    pairs_left.sort()
    pairs_right.sort()
    return ([(pair[1], pair[2]) for pair in pairs_left \
                 if pair[0] <= param_id_boxes_discard_distance],
            [(pair[1], pair[2]) for pair in pairs_right \
                 if pair[0] <= param_id_boxes_discard_distance])

def line_bounds_rank(p_up, p_down, line_up, line_down):
    p_down_ideal = project_point(p_up, line_up, line_down)
    rank = distance(p_down, p_down_ideal)
    return (rank, p_up, p_down)

def line_bounds_one_line(image, line, iwidth, rho_var):
    rho, theta = line
    lines = [line]
    for i in range(1, rho_var + 1):
        lines.append((rho + i, theta))
        lines.append((rho - i, theta))
    points_left = []
    points_right = []
    for l in lines:
        pl, pr = line_bounds(image, l, iwidth)
        if pl is not None:
            points_left.append(pl)
            points_right.append(pr)
    return points_left, points_right

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

def count_pixels_in_horizontal_line(image, line):
    p0 = line_point(line, x = 0)
    if p0[1] < 0:
        p0 = line_point(line, y = 0)
    p1 = line_point(line, x = image.width - 1)
    if p1[1] < 0:
        p1 = line_point(line, y = 0)
    active_points = 0
    for x, y in walk_line(p0, p1):
        if image[y, x] > 0:
            active_points += 1
    return active_points

def cvimage_to_pygame(image):
    image_rgb = cv.CreateMat(image.height, image.width, cv.CV_8UC3)
    cv.CvtColor(image, image_rgb, cv.CV_BGR2RGB)
    return pygame.image.frombuffer(image_rgb.tostring(),
                                   cv.GetSize(image_rgb), 'RGB')
