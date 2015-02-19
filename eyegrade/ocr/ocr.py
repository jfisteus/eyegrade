# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2015 Jesus Arias Fisteus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#

# OCR for hand-written digits
#
import tre

import cv2

import numpy as np ###
import image_preprocessing as imp ###

from . import geometry as g

param_cross_num_lines = 15
param_cell_margin = 2
param_max_errors = 4

classifier = cv2.SVM() ###
classifier.load('eyegrade_SVM.dat') ###

# Tre initializations
tre_fz = tre.Fuzzyness(maxerr = param_max_errors)
regexps = [(r'^1{0,2}222+1{0,2}$', # zero
            r'^1{0,2}222+1{0,2}$',
            r'^/(XXX/|X._/|_.X/|.X./)+X_X/(X_X/)+(XXX/|X._/|_.X/|.X./)+$',
            r'^/(XXX/|X._/|_.X/|.X./)+X_X/(X_X/)+(XXX/|X._/|_.X/|.X./)+$'),
           (r'^11+(22+1+|211+|111+)11+$', # one
            r'^1+$|^1{0,2}2+11+$',
            r'^/(_.X/|_X./)(_.X/|_X./)+(X.X/)*(_X_/|__X/|XX_/)+'
            + r'(.XX/|XX./){0,2}$',
            r'(XXX/|XX_/_XX)'),
           (r'^1+2{0,4}111+2{0,2}11{0,2}$', # two
            r'^1{0,3}2*3+2+1{0,3}$',
            r'^/(.../){0,3}(__X/)*(_X./)+(X._/)+(.XX/|XX./|X_X/)+(.../){0,2}$',
            r'^/(._X/|X_./)+(XXX/)+(._X/|X_./)+(._./)*$'),
           (r'^1+2{0,2}11+2?11+2{0,2}1+$', # three
            r'^1*(22+3+|2+33+|333+)(44?2+)?2{0,2}1{0,2}$',
            r'^/(X._/|_.X/|XXX/)(X._/|_.X/|XXX/){0,2}(X_X){0,2}(_.X/|_X./)+'
            + r'(X._/){0,2}(XX./|.XX/)+(X._/){0,2}(_.X/)+(X_X/){0,2}'
            + r'(X._/|_.X/|XXX/)(X._/|_.X/|XXX/){0,2}$',
            r'^/(._X/|X_./)*(XXX/)(XXX/)+(X../|.X./|..X/)*$'),
           (r'^1{0,2}22+111+$', # four
            r'^11?(22?1|11+)(22?|1+)1+$',
            r'^/(X_./|._X/)(X_./|._X/)+(X_X/)+(XX./|.XX/)+(..X/)+(.X./){0,3}$',
            r'^/(X._/|.X_/)+(.X./)(.X./)+(.XX/|XX./)+$'),
           (r'^1+2{0,2}1+2{0,2}1+2{0,3}1+$', # five
            r'^1?2{0,2}(2|3)33+(1|2){0,4}$',
            r'^/(XX./|.XX/|X._/|_.X/)+(X__/)+(XX./|.XX/){0,3}(__X/)+'
            + r'(X_X/)*(.XX/|XX./|X__/|__X/)+$',
            r'^/(.../)+(XXX/)(XXX/)+(X../|.XX/)+(_X_/|__X/){0,2}$'),
           (r'^1{0,2}2{0,3}111+2{0,2}3{0,2}22+1{0,2}$', # six
            r'^1{0,2}2{0,2}333+2{0,2}1{0,2}$',
            r'^/(.../){0,3}(X__/|_X_/)(X__/|_X_/)+(X._/)+(.../)(.../){0,2}'
            + '(X_X/)+(.../)(.../){0,2}$',
            r'^/(.X./|..X/)+(XXX/)+(.../){0,3}$'),
           (r'11?(22{0,2}|1+)2?1+2?11+', # seven
            r'1+2(2|1)+11?',
            r'^/(X../|..X/){0,3}(_X./|_.X/)+(.XX/)(.XX/)?(_X./|_.X/)'
            + r'(_X./|_.X/)+(.X_/|X._/)*$',
            r'^/(_X./)*(X._/)+(.XX/)+.*$'),
           (r'^1{0,2}22+1+22+1{0,2}$', # eight
            r'^1{0,2}2{0,2}333+2{0,2}1{0,2}$',
            r'^/(.../)(.../){0,3}(X_X/)+(.../)*(.X_/|_X./|X__/|__X/)+'
            + r'(.../)*(X_X/)+',
            r'(XXX/)(XXX/)(XXX/)'),
           (r'^1{0,2}22+3?2?12?11+$', # nine
            r'^1{0,2}(2+3+2*|222+)1+$',
            r'^/(.../)+(X_X/)+(_XX/|XXX/)(_XX/|XXX/)?(_.X/)+(_X./)*$',
            r'^/(X._/|.X_/)(X._/|.X_/)+(XX./|.XX/)+$')]
re_compiled = []
for row in regexps:
    re_compiled.append((tre.compile(row[0], tre.EXTENDED),
                        tre.compile(row[1], tre.EXTENDED),
                        tre.compile(row[2], tre.EXTENDED),
                        tre.compile(row[3], tre.EXTENDED)))

# limits: for each digit (min_len_num_hcrossings, min_len_num_vcrossings,
#                         max_num_hcrossings, max_num_vcrossings,
#                         min_num_hcrossings, min_num_vcrossings,
#                         min_max_num_hcrossings, min_max_num_vcrossings)
limits = [(4, 4, 3, 3, 1, 1, 2, 2), # zero
          (4, 1, 2, 2, 1, 1, 1, 1), # one
          (4, 4, 3, 3, 1, 1, 1, 2), # two
          (4, 4, 2, 4, 1, 1, 1, 3), # three
          (4, 4, 3, 2, 1, 1, 2, 1), # four
          (4, 4, 2, 3, 1, 1, 1, 3), # five
          (4, 4, 2, 3, 1, 1, 2, 2), # six
          (4, 3, 2, 3, 1, 1, 1, 2), # seven
          (4, 4, 2, 4, 1, 1, 2, 3), # eight
          (4, 3, 2, 3, 1, 1, 2, 2)] # nine

def digit_ocr(image, cell_corners, debug = None, image_drawn = None):
    assert(not debug or image_drawn is not None)
    image_as_vector = imp.image_preprocessing(np.asarray(image[:,:])) ###
    prediction = int(classifier.predict(image_as_vector)) ###
    weights = [0.0]*10 ###
    weights[prediction] = 1.0 ###

    return (prediction, weights) ###

def digit_ocr_by_line_crossing(image, cell_corners, debug, image_drawn):
    points = adjust_cell_corners(image, cell_corners)
    plu, pru, pld, prd = points
    points_left = g.interpolate_line(plu, pld, param_cross_num_lines)
    points_right = g.interpolate_line(pru, prd, param_cross_num_lines)
    points_up = g.interpolate_line(plu, pru, param_cross_num_lines)
    points_down = g.interpolate_line(pld, prd, param_cross_num_lines)
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
        if debug:
            print signatures
        scores = []
        for i in range(0, 10):
            max_num_hcrossings = max(num_hcrossings)
            max_num_vcrossings = max(num_vcrossings)
            if min(num_hcrossings) < limits[i][4] \
                    or min(num_vcrossings) < limits[i][5] \
                    or len(num_hcrossings) < limits[i][0] \
                    or len(num_vcrossings) < limits[i][1]:
                p = 0.0
            else:
                mhcscore = min_max_crossings_score(limits[i][6], limits[i][2],
                                                   max_num_hcrossings)
                mvcscore = min_max_crossings_score(limits[i][7], limits[i][3],
                                                   max_num_vcrossings)
                hnmatch = re_compiled[i][0].search(hstr, tre_fz)
                vnmatch = re_compiled[i][1].search(vstr, tre_fz)
                hnscore = max(1.0 - 0.25 * hnmatch.cost \
                                  if hnmatch else 0.2, 0.2)
                vnscore = max(1.0 - 0.25 * vnmatch.cost \
                                  if vnmatch else 0.2, 0.2)
                hpmatch = re_compiled[i][2].search(signatures[0], tre_fz)
                vpmatch = re_compiled[i][3].search(signatures[1], tre_fz)
                hpscore = max(1.0 - 0.2 * hpmatch.cost if hpmatch else 0.4, 0.4)
                vpscore = max(1.0 - 0.2 * vpmatch.cost if vpmatch else 0.4, 0.4)
                if debug:
                    print i, hnscore, vnscore, hpscore, vpscore, \
                        mhcscore, mvcscore
                p = hnscore * vnscore * hpscore * vpscore * mhcscore * mvcscore
            scores.append((p, i))
        if debug:
            print sorted(scores, reverse = True)
        m = max(scores)
        if m[0] > 0.0:
            decision = m[1]
    else:
        scores = [(0.0, i) for i in range(10)]
    return decision, [score[0] for score in scores]

def crossings(image, p0, p1, h, debug = False, image_drawn = None):
    pixels = []
    crossings = []
    for x, y in g.walk_line(p0, p1):
        pixels.append(image[y, x] > 0)
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
    width_threshold = 3 * min_length_px
    min_v = hcrossings[0][0][4]
    max_v = hcrossings[-1][0][4]
    min_h = vcrossings[0][0][4]
    max_h = vcrossings[-1][0][4]
    signatures = []
    for crossings, min_pos, max_pos \
            in (hcrossings, min_h, max_h), (vcrossings, min_v, max_v):
        region_width = (max_pos - min_pos) / 3
        if region_width < 0.1:
            region_width = 0.1
        limits = (max_pos - 2 * region_width, max_pos - region_width)
        particles = ['']
        for row in crossings:
            mark = [False, False, False]
            for c in row:
                m = [False, False, False]
                m[0] = c[0] < limits[0]
                m[1] = (c[0] < limits[1] and c[1] >= limits[0])
                m[2] = c[1] >= limits[1]
                if len(row) <= 2 and c[3] <= width_threshold \
                        and c[1] - c[0] < region_width \
                        and (c[0] < limits[0] or c[1] >= limits[1]):
                    m[1] = False
                for i in range(3):
                    mark[i] = mark[i] or m[i]
            particles.append(''.join(['X' if mm else '_' for mm in mark]))
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
    if (len(lists[begin]) == 1 and end - begin > 1 \
            and len(lists[begin + 1]) == 0 and lists[begin][0][3] < 6) \
            or (end - begin > 2 and len(lists[begin + 1]) == 0 \
                    and len(lists[begin + 2]) == 0):
        begin += 1
        while begin < end and len(lists[begin]) == 0:
            begin += 1
    if (len(lists[end - 1]) == 1 and end >= 2 and len(lists[end - 2]) == 0 \
            and lists[end - 1][0][3] < 6) \
            or (end >= 3 and len(lists[end - 2]) == 0 \
                    and len(lists[end - 3]) == 0):
        end -= 1
        while end >= 1 and len(lists[end - 1]) == 0:
            end -= 1
    return lists[begin:end]

def min_max_crossings_score(min_max_crossings, max_max_crossings,
                            actual_max_crossings):
    d = min_max_crossings - actual_max_crossings
    if d == 1:
        score = 0.5
    elif d > 1:
        score = 0.1
    else:
        score = 1.0
    d = max_max_crossings - actual_max_crossings
    if d == -1:
        score = score * 0.5
    elif d < -1:
        score = score * 0.1
    return score

def adjust_cell_corners(image, corners):
    plu, pru, pld, prd = corners
    plu = adjust_cell_corner(image, plu, prd)
    prd = adjust_cell_corner(image, prd, plu)
    pru = adjust_cell_corner(image, pru, pld)
    pld = adjust_cell_corner(image, pld, pru)
    return(plu, pru, pld, prd)

def adjust_cell_corner(image, corner, towards_corner):
    margin = None
    for x, y in g.walk_line_ordered(corner, towards_corner):
        if margin is None:
            if image[y, x] == 0:
                margin = param_cell_margin
        else:
            margin -= 1
            if margin == 0:
                return (x, y)
    # In case of failure, return the original point
    return corner
