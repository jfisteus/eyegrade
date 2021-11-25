# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2021 Jesus Arias Fisteus
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
# <https://www.gnu.org/licenses/>.
#

import math
import itertools
import statistics


# Data representation:
# - points: tuples (x, y)
# - Lines: tuples (rho, theta) as returned by the Hough transform
#          or two points p1 and p2 in the line.
#

# Functions on points
#
def distance(p1, p2):
    """Returns the distance from p1 to p2."""
    return math.sqrt(
        (p1[0] - p2[0]) * (p1[0] - p2[0]) + (p1[1] - p2[1]) * (p1[1] - p2[1])
    )


def diff_points(p1, p2):
    """Returns a tuple (p1.x - p2.x, p1.y - p2.y)."""
    return (p1[0] - p2[0], p1[1] - p2[1])


def add_points(p1, p2):
    """Returns a tuple (p1.x + p2.x, p1.y + p2.y)."""
    return (p1[0] + p2[0], p1[1] + p2[1])


def multiply_vector(vector, factor):
    """Multiplies a vector of two coordinates by a given factor."""
    return (factor * vector[0], factor * vector[1])


def round_point(point):
    """Rounds the coordinates of the point to the nearest integers."""
    return int(round(point[0])), int(round(point[1]))


def angles_perpendicular(angle1, angle2):
    """Returns True if angles are perpendicular or almost perpendicular.

       There is a margin of +-0.1 radians in which they are still
       considered perpendicular.

    """
    return (
        abs(angle2 - angle1 - math.pi / 2) < 0.1
        or abs(angle2 - angle1 + math.pi / 2) < 0.1
    )


def points_closer_to_horizontal(p1, p2):
    """Returns True if the line joining the two points is closer to
       the horizontal than to the vertical.
    """
    d = diff_points(p1, p2)
    return abs(d[0]) > abs(d[1])


# Functions on two-dimensional vectors
#
def scalar_product(vector1, vector2):
    """Returns the scalar product of two vectors."""
    return vector1[0] * vector2[0] + vector1[1] * vector2[1]


def module(vector):
    """Returns the module of a vector, given its two coordinates."""
    return math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])


def angle_cosine(vector1, vector2):
    """Returns cos(angle) where angle is the angle between
       vector1 and vector2"""
    return scalar_product(vector1, vector2) / module(vector1) / module(vector2)


# Funtions on lines defined by two points
#
def slope(p1, p2):
    """Returns the slope of the line from p1 to p2."""
    return float(p2[1] - p1[1]) / (p2[0] - p1[0])


def slope_inv(p1, p2):
    """Returns the inverse of the slope of the line from p1 to p2."""
    return float(p2[0] - p1[0]) / (p2[1] - p1[1])


def closer_points(p1, p2, offset):
    """Returns a pair of points that are in the line that joins
       p1 and p2, but closer than them by offset."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    k = float(offset) / math.sqrt(dx * dx + dy * dy)
    return (
        (int(p1[0] + dx * k), int(p1[1] + dy * k)),
        (int(p2[0] - dx * k), int(p2[1] - dy * k)),
    )


def closer_points_rel(p1, p2, offset_ratio, abs_offset=0):
    """Returns a pair of points that are in the line that joins
       p1 and p2, but closer than them by the given ratio.

       Example: offset_ratio == 0.9 implies the distance between the
       new points is 0.9 the distance between the original points.
       Points go then closer by abs_offset on each side.

    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    xoff = abs_offset * float(dx) / (abs(dx) + abs(dy))
    yoff = abs_offset * float(dy) / (abs(dx) + abs(dy))
    k = (1.0 - float(offset_ratio)) / 2
    return (
        (int(p1[0] + dx * k + xoff), int(p1[1] + dy * k + yoff)),
        (int(p2[0] - dx * k - xoff), int(p2[1] - dy * k - yoff)),
    )


def walk_line(p0, p1):
    """Returns a generator of points in the line from p0 to p1 such
       that they are connected (in the way they would do to draw a
       line. Order of points is not guaranteed: points may go p0->p1
       or p1->p0. See walk_line_ordered if points must go from p0 to
       p1."""
    # Bresenham's algorithm as found in Wikipedia
    x0, y0 = p0
    x1, y1 = p1
    steep = abs(y1 - y0) > abs(x1 - x0)
    if steep:
        # swap values:
        x0, y0 = y0, x0
        x1, y1 = y1, x1
    if x0 > x1:
        # swap values:
        x0, x1 = x1, x0
        y0, y1 = y1, y0
    deltax = x1 - x0
    deltay = abs(y1 - y0)
    error = deltax / 2
    y = y0
    ystep = 1 if y0 < y1 else -1
    for x in range(x0, x1 + 1):
        yield (x, y) if not steep else (y, x)
        error = error - deltay
        if error < 0:
            y = y + ystep
            error = error + deltax


def walk_line_ordered(p0, p1):
    """Wrapper for walk_line that guarantees that points go from p0 to p1."""
    x0, y0 = p0
    x1, y1 = p1
    if abs(y1 - y0) > abs(x1 - x0):
        reverse = y0 > y1
    else:
        reverse = x0 > x1
    if not reverse:
        return walk_line(p0, p1)
    else:
        return reversed([p for p in walk_line(p0, p1)])


def interpolate_line(p0, p1, num_points):
    """Returns a list of num_points points in the line from p0 to p1.

       The list includes p0 and p1 and points are ordered from p0 to
       p1.

       """
    num_divisions = num_points - 1
    dx = float(p1[0] - p0[0]) / num_divisions
    dy = float(p1[1] - p0[1]) / num_divisions
    points = [p0]
    for i in range(1, num_divisions):
        points.append(round_point((p0[0] + dx * i, p0[1] + dy * i)))
    points.append(p1)
    return points


def interpolate_line_progressive(p0, p1, num_points, factor):
    """Returns a list of num_points points in the line from p0 to p1.

       The list includes p0 and p1 and points are ordered from p0 to
       p1.

       Distances are progressive according to factor: if factor > 1
       there is more space in between the first points; if factor == 1 there
       is exactly the same space between points; if factor < 1, there is
       more space between the last points.

       This function is twice as slow as the non progressive version.
       When factor is 1 the other version should be used instead.

       """
    diff = diff_points(p1, p0)
    n = num_points - 1
    h1 = 2.0 / n / (factor + 1)
    delta = h1 * (factor - 1) / (n - 1)
    positions = [
        h1 * (i - 1) + 0.5 * delta * (i * i - 3 * i + 2)
        for i in range(1, num_points + 1)
    ]
    points = [
        round_point(add_points(p0, multiply_vector(diff, pos))) for pos in positions
    ]
    # Just in case it wasn't rounded to the proper value
    points[-1] = p1
    return points


# Functions on lines represented as rho, theta
#
def intersection(hline, vline):
    """Returns the intersection point of a (nearly) horizontal line
       with a (nearly) vertical line. Results may be wrong in
       other cases."""
    rho1, theta1 = hline
    rho2, theta2 = vline
    y = (rho1 * math.cos(theta2) - rho2 * math.cos(theta1)) / math.sin(theta1 - theta2)
    x = (rho2 - y * math.sin(theta2)) / math.cos(theta2)
    return round_point((x, y))


def line_point(line, x=None, y=None):
    """Returns a point in the line with the given x or y coordinate.
       Either x or y must be None. Throws division by zero exception
       if x is set and the line is vertical or if y is set and the
       line is horizontal."""
    assert (x is None) ^ (y is None)
    rho, theta = line
    if y is None:
        y = int((rho - x * math.cos(theta)) / math.sin(theta))
    else:
        x = int((rho - y * math.sin(theta)) / math.cos(theta))
    return round_point((x, y))


def point_is_valid(point, dimensions):
    """Returns True if the coordinates of the point are within the bounds
       of the image, False otherwise. Parameter dimensions is a tuple
       (image_width, image_height)."""
    if (
        point[0] >= 0
        and point[1] >= 0
        and point[0] < dimensions[0]
        and point[1] < dimensions[1]
    ):
        return True
    else:
        return False


def project_point(point, from_line, to_line):
    """Assuming that both lines are parallel, traces a perpendicular
       line from from_line to to_line that contains the given point,
       and returns the intersection point of that line with from_line.
       In order to simplify computation, the function does not
       consider the angle of to_line, i.e. it assumes the same angle
       as from_line. The result is therefore only an approximation,
       valid when angles are close enough."""
    theta = from_line[1]
    d = to_line[0] - from_line[0]
    delta_x = d * math.cos(theta)
    delta_y = d * math.sin(theta)
    return (point[0] + delta_x, point[1] + delta_y)


def min_rho_difference(lines):
    """Being lines a list of lines (rho, theta) sorted according to rho,
       from low to high, returns the minimum difference between two
       consecutive lines. The size of the list must be at least two."""
    assert len(lines) >= 2
    min_diff = lines[1][0] - lines[0][0]
    for i in range(2, len(lines)):
        diff = lines[i][0] - lines[i - 1][0]
        if diff < min_diff:
            min_diff = diff
    return min_diff


def discard_spurious_lines(lines, expected):
    """ Discards the discordant line(s).

    Discards the line or lines that minimizes the variance
    of the distances between the set of the other lines
    (of size expected).

    The hypothesis is that, when more lines than expected
    were detected, the variance of the distances bewteen
    lines will be minimized when the spurious lines are
    out of the set of selected lines.

    Be aware of the number of possible combinations before
    calling this function. Having just one or two extra lines
    should generally be ok.

    """
    best_variance = math.inf
    for combination in itertools.combinations(lines, expected):
        diffs = [b[0] - a[0] for a, b in zip(combination[:-1], combination[1:])]
        variance = statistics.variance(diffs)
        if variance < best_variance:
            best_combination = combination
            best_variance = variance
    return best_combination


# Functions on rectangles
#
def rect_center(plu, pru, pld, prd):
    """Returns the center of the rectangle with the given corners.
       Note: l/r are for left, right; u, d are for up/down."""
    return round_point((float(plu[0] + prd[0]) / 2, float(plu[1] + prd[1]) / 2))


# Functions on angles (in radians)
#
def distance_closest_axis(angle, axes_angles):
    """Returns the distance of angle to the closest angle in 'axes_angles'

       Axes are computed in pi modulus (that is, 0 equals pi).
       'axes_angles' is an iterable of angles. All parameters are in
       radians. Distance is returned as an angle in radians. +/- pi
       variations of the angles are also tested. The angle is
       normalized to the range [0, pi).

    """
    axes_expanded = []
    for a in axes_angles:
        a = a % math.pi
        axes_expanded.append(a)
        if a > math.pi / 2:
            axes_expanded.append(a - math.pi)
        else:
            axes_expanded.append(a + math.pi)
    angle_normalized = angle % math.pi
    return min([abs(angle_normalized - aa) for aa in axes_expanded])
