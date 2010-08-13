# OCR for hand-written digits
#

# Local imports
from geometry import *

param_cross_num_lines = 13
param_cell_margin = 2

def digit_ocr(image, cell_corners):
    return digit_ocr_by_line_crossing(image, cell_corners)

def digit_ocr_by_line_crossing(image, cell_corners):
    plu, pru, pld, prd = adjust_cell_corners(image, cell_corners)
    points_left = interpolate_line(plu, pld, param_cross_num_lines)
    points_right = interpolate_line(pru, prd, param_cross_num_lines)
    points_up = interpolate_line(plu, pru, param_cross_num_lines)
    points_down = interpolate_line(pld, prd, param_cross_num_lines)
    hcrossings = []
    vcrossings = []
    for i in range(0, param_cross_num_lines):
        hcrossings.append(crossings(image, points_left[i], points_right[i]))
        vcrossings.append(crossings(image, points_up[i], points_down[i]))
    print hcrossings
    print vcrossings
    return decide_digit(hcrossings, vcrossings)

def decide_digit(hcrossings, vcrossings):
    decision = None
    h = __trim_empty_lists(hcrossings)
    v = __trim_empty_lists(vcrossings)
    if len(h) > 0 and len(v) > 0:
        p = [is_zero(h, v), is_one(h, v), is_two(h, v), is_three(h, v),
             is_four(h, v), is_five(h, v), is_six(h, v), is_seven(h, v),
             is_eight(h, v), is_nine(h, v)]
        print p
        m = max(p)
        if m[0] > 0.0:
            decision = m[1]
    return decision

def crossings(image, p0, p1):
    pixels = []
    crossings = []
    for x, y in walk_line(p0, p1):
        pixels.append(image[y, x] > 0)
#    print pixels
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
            if not value:
                if i - begin > 1:
                    pos = float(begin + i - 1) * 50 / len(pixels)
                    length = float(i - begin) * 100 / len(pixels)
                    crossings.append((pos, length))
                begin = None
    return crossings

# Decision functions for the crossings method
#
def is_zero(hcrossings, vcrossings):
    p = 1.0
    negative = (0.0, 0)
    num_hcrossings = [len(l) for l in hcrossings]
    num_vcrossings = [len(l) for l in vcrossings]
    if min(num_hcrossings) == 0 or min(num_vcrossings) == 0 \
            or max(num_hcrossings) > 3 or max(num_vcrossings) > 3 \
            or len(num_hcrossings) < 4 or len(num_vcrossings) < 4:
        return negative
    num_errors = len([n for n in num_hcrossings + num_vcrossings if n == 3])
    p -= 0.25 * num_errors
    if p <= 0.0:
        return negative
    num_errors = len([n for n in num_hcrossings[1:-1] + num_vcrossings[1:-1] \
                          if n == 1])
    p -= 0.25 * num_errors
    if num_hcrossings[0] == 1 and num_hcrossings[1] == 1 \
            and hcrossings[0][0][1] < hcrossings[1][0][1] \
            and abs(hcrossings[0][0][0] - hcrossings[1][0][0]) < 0.15:
        p += 0.2
    if num_hcrossings[-1] == 1 and num_hcrossings[-2] == 1 \
            and hcrossings[-1][0][1] < hcrossings[-2][0][1] \
            and abs(hcrossings[-1][0][0] - hcrossings[-2][0][0]) < 0.15:
        p += 0.2
    if num_vcrossings[0] == 1 and num_vcrossings[1] == 1 \
        and vcrossings[0][0][1] < vcrossings[1][0][1] \
        and abs(vcrossings[0][0][0] - vcrossings[1][0][0]) < 0.15:
        p += 0.2
    if num_vcrossings[-1] == 1 and num_vcrossings[-2] == 1 \
        and vcrossings[-1][0][1] < vcrossings[-2][0][1] \
            and abs(vcrossings[-1][0][0] - vcrossings[1][0][0]) < 0.15:
        p += 0.2
    if p <= 0.0:
        return negative
    hmiddle = len(hcrossings) // 2
    if num_hcrossings[hmiddle] == 1:
        if num_hcrossings[hmiddle + 1] > 1:
            hmiddle += 1
        else:
            hmiddle -= 1
    vmiddle = len(vcrossings) // 2
    if num_vcrossings[vmiddle] == 1:
        if num_vcrossings[vmiddle + 1] > 1:
            vmiddle += 1
        else:
            vmiddle -= 1
    hdiff = hcrossings[hmiddle][-1][0] - hcrossings[hmiddle][0][0]
    vdiff = vcrossings[vmiddle][-1][0] - vcrossings[vmiddle][0][0]
    p -= max(0, (0.2 - hdiff) * 4)
    p -= max(0, (0.2 - vdiff) * 4)
    if p < 0.0:
        return negative
    else:
        return (p, 0)

def is_one(hcrossings, vcrossings):
    return (0.0, 1)

def is_two(hcrossings, vcrossings):
    return (0.0, 2)

def is_three(hcrossings, vcrossings):
    return (0.0, 3)

def is_four(hcrossings, vcrossings):
    return (0.0, 4)

def is_five(hcrossings, vcrossings):
    return (0.0, 5)

def is_six(hcrossings, vcrossings):
    return (0.0, 6)

def is_seven(hcrossings, vcrossings):
    return (0.0, 7)

def is_eight(hcrossings, vcrossings):
    return (0.0, 8)

def is_nine(hcrossings, vcrossings):
    return (0.0, 9)

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
