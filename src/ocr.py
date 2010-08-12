# OCR for hand-written digits
#

# Local imports
from geometry import *

param_cross_num_lines = 13
param_cross_cell_margin = 4

def digit_ocr(image, cell_corners):
    return digit_ocr_by_line_crossing(image, cell_corners)

def digit_ocr_by_line_crossing(image, cell_corners):
    plu, pru, pld, prd = cell_corners
    plu, prd = closer_points(plu, prd, param_cross_cell_margin)
    pru, pld = closer_points(pru, pld, param_cross_cell_margin)
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
    return None

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
