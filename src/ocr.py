# OCR for hand-written digits
#
import tre

# Local imports
from geometry import *
import imageproc

param_cross_num_lines = 13
param_cell_margin = 2
param_max_errors = 4

# Tre initializations
tre_fz = tre.Fuzzyness(maxerr = param_max_errors)
regexps = [(r'^1{0,2}222+1{0,2}$', # zero
            r'^1{0,2}222+1{0,2}$'),
           (r'^11{0,3}(22+1+|211+|111+)11+$', # one
            r'^1+|1{0,2}22+11+$'),
           (r'^11?2+111+2{0,2}11{0,2}$', # two
            r'^1{0,3}2{0,2}(2|3)(2|3)(2|3)+11{0,2}$'),
           (r'^1+2{0,2}11+2?11+2{0,2}1+$', # three
            r'^1?22+33?(44?2+)?2{0,2}1{0,2}$'),
           (r'^1{0,2}22+111+$', # four
            r'^11?(22?1|11+)(22?|1+)1+$'),
           (r'^111+2{0,2}11+2{0,2}1+$', # five
            r'^1?2{0,2}333+2{0,2}1{0,2}$'),
           (r'^1{0,2}2{0,3}111+2{0,2}3{0,2}22+1{0,2}$', # six
            r'^1{0,2}2{0,2}333+2{0,2}1{0,2}$'),
           (r'11?(22{0,2}|1+)2?1+2?11+', # seven
            r'1+2(2|1)+11?'),
           (r'^1{0,2}22+1+22+1{0,2}$', # eight
            r'^1{0,2}2{0,2}333+2{0,2}1{0,2}$'),
           (r'^1{0,2}22+111+$', # nine
            r'^1{0,2}(2+3+2*|222+)1+$')]
re_compiled = []
for pair in regexps:
    re_compiled.append((tre.compile(pair[0], tre.EXTENDED),
                        tre.compile(pair[1], tre.EXTENDED)))

# limits: for each digit (min_len_num_hcrossings, min_len_num_vcrossings,
#                         max_num_hcrossings, max_num_vcrossings,
#                         min_num_hcrossings, min_num_vcrossings)
limits = [(4, 4, 3, 3, 1, 1), # zero
          (4, 1, 3, 3, 1, 1), # one
          (4, 4, 3, 4, 1, 1), # two
          (4, 4, 3, 4, 1, 1), # three
          (4, 4, 2, 2, 1, 1), # four
          (4, 4, 3, 4, 1, 1), # five
          (4, 4, 3, 3, 1, 1), # six
          (4, 3, 3, 3, 1, 1), # seven
          (4, 4, 3, 3, 1, 1), # eight
          (4, 3, 3, 3, 1, 1)] # nine

def digit_ocr(image, cell_corners, debug = None, image_drawn = None):
    assert(not debug or image_drawn is not None)
    return digit_ocr_by_line_crossing(image, cell_corners, debug, image_drawn)

def digit_ocr_by_line_crossing(image, cell_corners, debug, image_drawn):
    points = adjust_cell_corners(image, cell_corners)
    if debug:
        for point in points:
            imageproc.draw_point(image_drawn, point)
    plu, pru, pld, prd = points
    points_left = interpolate_line(plu, pld, param_cross_num_lines)
    points_right = interpolate_line(pru, prd, param_cross_num_lines)
    points_up = interpolate_line(plu, pru, param_cross_num_lines)
    points_down = interpolate_line(pld, prd, param_cross_num_lines)
    hcrossings = []
    vcrossings = []
    for i in range(0, param_cross_num_lines):
        hcrossings.append(crossings(image, points_left[i], points_right[i],
                                    debug, image_drawn))
        vcrossings.append(crossings(image, points_up[i], points_down[i],
                                    debug, image_drawn))
    if debug:
        print hcrossings
        print vcrossings
    return decide_digit(hcrossings, vcrossings, debug)

def decide_digit(hcrossings, vcrossings, debug = False):
    decision = None
    hcrossings = __trim_empty_lists(hcrossings)
    vcrossings = __trim_empty_lists(vcrossings)
    if len(hcrossings) > 0 and len(vcrossings) > 0:
        num_hcrossings = [len(l) for l in hcrossings]
        num_vcrossings = [len(l) for l in vcrossings]
        if debug:
            print num_hcrossings
            print num_vcrossings
        hstr = ''.join([str(v) for v in num_hcrossings])
        vstr = ''.join([str(v) for v in num_vcrossings])
        scores = []
        for i in range(0, 10):
            if min(num_hcrossings) < limits[i][4] \
                    or min(num_vcrossings) < limits[i][5] \
                    or max(num_hcrossings) > limits[i][2] \
                    or max(num_vcrossings) > limits[i][3] \
                    or len(num_hcrossings) < limits[i][0] \
                    or len(num_vcrossings) < limits[i][1]:
                p = 0.0
            else:
                hmatch = re_compiled[i][0].search(hstr, tre_fz)
                vmatch = re_compiled[i][1].search(vstr, tre_fz)
                hscore = max(1.0 - 0.3 * hmatch.cost, 0.0) if hmatch else 0.0
                vscore = max(1.0 - 0.3 * vmatch.cost, 0.0) if vmatch else 0.0
                if debug:
                    print i, hscore, vscore
                p = hscore * vscore
            scores.append((p, i))
        if debug:
            print sorted(scores, reverse = True)
        m = max(scores)
        if m[0] > 0.0:
            decision = m[1]
    return decision

def crossings(image, p0, p1, debug = False, image_drawn = None):
    pixels = []
    crossings = []
    for x, y in walk_line(p0, p1):
        pixels.append(image[y, x] > 0)
        if debug:
            if image[y, x] > 0:
                color = (255, 255, 0, 0)
            else:
                color = (200, 200, 200, 0)
            imageproc.draw_point(image_drawn, (x, y), color, 0)
    # Filter the value sequence
    for i in range(1, len(pixels) - 1):
        if not pixels[i - 1] and not pixels[i + 1]:
            pixels[i] = False
        elif pixels[i - 1] and pixels[i + 1]:
            pixels[i] = True
    # detect crossings
    begin = None
    for i, value in enumerate(pixels):
        if begin is None:
            if value:
                begin = i
        else:
            if not value or i == len(pixels) - 1:
                if i - begin > 1:
                    pos = float(begin + i - 1) * 50 / len(pixels)
                    length = float(i - begin) * 100 / len(pixels)
                    crossings.append((pos, length))
                begin = None
    return crossings

# Other auxiliary functions
#
def __trim_empty_lists(lists):
    """Receives a list of lists. Returns a new list of lists without
       any empty lists at the beginning or end of it."""
    if len(lists) == 0:
        return []
    begin = -1
    end = 0
    for i in range(0, len(lists)):
        if len(lists[i]) > 0:
            end = i + 1
            if begin == -1:
                begin = i
    return lists[begin:end]

def adjust_cell_corners(image, corners):
    plu, pru, pld, prd = corners
    plu = adjust_cell_corner(image, plu, prd)
    prd = adjust_cell_corner(image, prd, plu)
    pru = adjust_cell_corner(image, pru, pld)
    pld = adjust_cell_corner(image, pld, pru)
    return(plu, pru, pld, prd)

def adjust_cell_corner(image, corner, towards_corner):
    margin = None
    for x, y in walk_line_ordered(corner, towards_corner):
        if margin is None:
            if image[y, x] == 0:
                margin = param_cell_margin
        else:
            margin -= 1
            if margin == 0:
                return (x, y)
    # In case of failure, return the original point
    return corner
