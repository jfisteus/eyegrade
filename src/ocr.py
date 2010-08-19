# OCR for hand-written digits
#
import tre

# Local imports
from geometry import *
import imageproc

param_cross_num_lines = 15
param_cell_margin = 2
param_max_errors = 4

# Tre initializations
tre_fz = tre.Fuzzyness(maxerr = param_max_errors)
regexps = [(r'^1{0,2}222+1{0,2}$', # zero
            r'^1{0,2}222+1{0,2}$',
            r'^/(.X./)+X_X/(X_X/)+(.X./)+$',
            r'^/(.X./)+X_X/(X_X/)+(.X./)+$'),
           (r'^11{0,4}(22+1+|211+|111+)1+$', # one
            r'^1+|1{0,2}22+11+$',
            r'^/(_.X/|_X./)(_.X/|_X./)+(X.X/)*(_X_/|__X/|XX_/)+'
            + r'(.XX/|XX./){0,2}$',
            r'(XXX/|XX_/_XX)'),
           (r'^11?2+111+2{0,2}11{0,2}$', # two
            r'^1{0,3}2{0,2}(2|3)(2|3)(2|3)+11{0,2}$',
            r'^/(.X./)+(.../)*(_X./)+(X._/)*(X_./)+(.XX/|XX./)+(.../){0,2}$',
            r'^/(._X/|X_./)+(XXX/)+(._X/|X_./)+(._./)*$'),
           (r'^1+2{0,2}11+2?11+2{0,2}1+$', # three
            r'^1?22+33+(44?2+)?2{0,2}1{0,2}$',
            r'^/(.../)(.../){0,2}(_.X/|_X./)+(..X/)*(XX./|.XX/)+(..X/)*'
            + r'(_.X/)+(.../)(.../){0,2}$',
            r'^/(._X/|X_./|_X./)*(XXX/)(XXX/)+(X../|.X./|..X/)*$'),
           (r'^1{0,2}22+111+$', # four
            r'^11?(22?1|11+)(22?|1+)1+$',
            r'^/(X_./|._X/)(X_./|._X/)+(XX./|.XX/)+(..X/)+(.X./){0,3}$',
            r'^/(X._/|.X_/)+(.X./)(.X./)+(.XX/|XX./)+$'),
           (r'^111+2{0,2}11+2{0,2}1+$', # five
            r'^1?2{0,2}333+2{0,2}1{0,2}$',
            r'^/(.XX/|XX./)+(X__/)+(XX./)+(__X/)+(X_X/)*(.XX/|XX./)+$',
            r'^/(.../)+(XXX/)(XXX/)+(X../|.XX/)+$'),
           (r'^1{0,2}2{0,3}111+2{0,2}3{0,2}22+1{0,2}$', # six
            r'^1{0,2}2{0,2}333+2{0,2}1{0,2}$',
            r'^/(.../)*(.X_/)*(X._/)+(.X./)+(XX./|.XX/)*(X.X/)+(.X./)+$',
            r'^/(.X./|..X/)+(XXX/)+(.../){0,3}$'),
           (r'11?(22{0,2}|1+)2?1+2?11+', # seven
            r'1+2(2|1)+11?',
            r'^/(XX./|.XX/)+(_X./|_.X/)+(XX./){0,2}(_X./|_.X/)'
            + r'(_X./|_.X/)+(.X_/)*$',
            r'^/(_X./)*(X._/)+(.XX/)+.*$'),
           (r'^1{0,2}22+1+22+1{0,2}$', # eight
            r'^1{0,2}2{0,2}333+2{0,2}1{0,2}$',
            r'^/(.../)(.../){0,3}(X_X/)+(.../)*(.X_/|_X./)+(.../)*(X_X/)+',
            r'(XXX/)(XXX/)(XXX/)'),
           (r'^1{0,2}22+111+$', # nine
            r'^1{0,2}(2+3+2*|222+)1+$',
            r'^/(.../)+(X_X/)+(_.X/|_X./)(_.X/|_X./)+$',
            r'^/(X._/|.X_/)(X._/|.X_/)+(XX./|.XX/)+$')]
re_compiled = []
for row in regexps:
    re_compiled.append((tre.compile(row[0], tre.EXTENDED),
                        tre.compile(row[1], tre.EXTENDED),
                        tre.compile(row[2], tre.EXTENDED),
                        tre.compile(row[3], tre.EXTENDED)))

# limits: for each digit (min_len_num_hcrossings, min_len_num_vcrossings,
#                         max_num_hcrossings, max_num_vcrossings,
#                         min_num_hcrossings, min_num_vcrossings)
limits = [(4, 4, 3, 3, 1, 1), # zero
          (4, 1, 3, 3, 1, 1), # one
          (4, 4, 3, 4, 1, 1), # two
          (4, 4, 3, 4, 1, 1), # three
          (4, 4, 3, 3, 1, 1), # four
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
        h = float(i) / (param_cross_num_lines - 1)
        hcrossings.append(crossings(image, points_left[i], points_right[i],
                                    h, debug, image_drawn))
        vcrossings.append(crossings(image, points_up[i], points_down[i],
                                    h, debug, image_drawn))
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
        signatures = crossings_signatures(hcrossings, vcrossings)
        print signatures
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
                hnmatch = re_compiled[i][0].search(hstr, tre_fz)
                vnmatch = re_compiled[i][1].search(vstr, tre_fz)
                hnscore = max(1.0 - 0.2 * hnmatch.cost if hnmatch else 0.3, 0.3)
                vnscore = max(1.0 - 0.2 * vnmatch.cost if vnmatch else 0.3, 0.3)
                hpmatch = re_compiled[i][2].search(signatures[0], tre_fz)
                vpmatch = re_compiled[i][3].search(signatures[1], tre_fz)
                hpscore = max(1.0 - 0.2 * hpmatch.cost if hpmatch else 0.5, 0.5)
                vpscore = max(1.0 - 0.2 * vpmatch.cost if vpmatch else 0.5, 0.5)
                if debug:
                    print i, hnscore, vnscore, hpscore, vpscore
                p = hnscore * vnscore * hpscore * vpscore
            scores.append((p, i))
        if debug:
            print sorted(scores, reverse = True)
        m = max(scores)
        if m[0] > 0.0:
            decision = m[1]
    return decision

def crossings(image, p0, p1, h, debug = False, image_drawn = None):
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
                end = i if value else i - 1
                if end - begin > 0:
                    n = len(pixels)
                    begin_rel = float(begin) / n
                    end_rel = float(end) / n
                    center_rel = (begin_rel + end_rel) / 2
                    length = end - begin + 1
                    length_rel = float(length) / n
                    crossings.append((begin_rel, end_rel,
                                      center_rel, length, h))
                begin = None
    return crossings

# Other auxiliary functions
#
def crossings_signatures(hcrossings, vcrossings):
    min_length_px = min([min([v[3] for v in c]) \
                             for c in hcrossings + vcrossings \
                             if len(c) > 0])
    width_threshold = max(2.0 * min_length_px, 16.0)
    if min_length_px < 8:
        min_length_px = 8
    min_v = hcrossings[0][0][4]
    max_v = hcrossings[-1][0][4]
    min_h = vcrossings[0][0][4]
    max_h = vcrossings[-1][0][4]
    signatures = []
    for crossings, min_pos, max_pos \
            in (hcrossings, min_h, max_h), (vcrossings, min_v, max_v):
#        min_pos = min([min([v[0] for v in c]) for c in crossings if len(c) > 0])
#        max_pos = max([max([v[1] for v in c]) for c in crossings if len(c) > 0])
        region_width = (max_pos - min_pos) / 3
        if region_width < 0.1:
            region_width = 0.1
        limits = (max_pos - 2 * region_width, max_pos - region_width)
#        print ">>>", min_pos, max_pos, region_width, limits
        particles = ['']
        for row in crossings:
            mark = [False, False, False]
            for c in row:
                m = [False, False, False]
                m[0] = c[0] < limits[0]
                m[1] = (c[0] < limits[1] and c[1] >= limits[0])
                m[2] = c[1] >= limits[1]
                if c[3] <= width_threshold \
                        and (c[2] < limits[0] or c[2] >= limits[1]):
                    m[1] = False
                for i in range(3):
                    mark[i] = mark[i] or m[i]
            particles.append(''.join(['X' if m else '_' for m in mark]))
        particles.append('')
        signatures.append('/'.join(particles))
    return signatures

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
    # Filter noise at the borders of the cell
    if len(lists[begin]) == 1 and len(lists[begin + 1]) == 0 \
            and lists[begin][0][3] < 4:
        begin += 1
        while begin < end and len(lists[begin]) == 0:
            begin += 1
    if len(lists[end - 1]) == 1 and len(lists[end - 2]) == 0 \
            and lists[end - 1][0][3] < 4:
        end -= 1
        while end >= 1 and len(lists[end - 1]) == 0:
            end -= 1
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
