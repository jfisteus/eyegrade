import math

# Data representation:
# - points: tuples (x, y)
# - Lines: tuples (rho, theta) as returned by the Hough transform
#          or two points p1 and p2 in the line.
#

# Functions on points
#
def distance(p1, p2):
    """Returns the distance from p1 to p2."""
    return math.sqrt((p1[0] - p2[0]) * (p1[0] - p2[0]) \
                         + (p1[1] - p2[1]) * (p1[1] - p2[1]))

def diff_points(p1, p2):
    """Returns a tuple (p1.x - p2.x, p1.y - p2.y)."""
    return (p1[0] - p2[0], p1[1] - p2[1])

def add_points(p1, p2):
    """Returns a tuple (p1.x + p2.x, p1.y + p2.y)."""
    return (p1[0] + p2[0], p1[1] + p2[1])

def round_point(point):
    """Rounds the coordinates of the point to the nearest integers."""
    return int(round(point[0])), int(round(point[1]))

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
    return ((int(p1[0] + dx * k), int(p1[1] + dy * k)),
            (int(p2[0] - dx * k), int(p2[1] - dy * k)))

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
    for x in xrange(x0, x1 + 1):
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
       p1."""
    num_divisions = num_points - 1
    dx = float(p1[0] - p0[0]) / num_divisions
    dy = float(p1[1] - p0[1]) / num_divisions
    points = [p0]
    for i in range(1, num_divisions):
        points.append(round_point((p0[0] + dx * i, p0[1] + dy * i)))
    points.append(p1)
    return points

# Functions on lines represented as rho, theta
#
def intersection(hline, vline):
    """Returns the intersection point of a (neraly) horizontal line
       with a (nearly) vertical line. Results may be wrong in
       other cases."""
    rho1, theta1 = hline
    rho2, theta2 = vline
    y = (rho1 * math.cos(theta2) - rho2 * math.cos(theta1)) \
        / (math.sin(theta1) * math.cos(theta2) \
               - math.sin(theta2) * math.cos(theta1))
    x = (rho2 - y * math.sin(theta2)) / math.cos(theta2)
    return round_point((x, y))

def line_point(line, x = None, y = None):
    """Returns a point in the line with the given x or y coordinate.
       Either x or y must be None. Throws division by zero exception
       if x is set and the line is vertical or if y is set and the
       line is horizontal."""
    assert((x is None) ^ (y is None))
    rho, theta = line
    if y is None:
        y = int((rho - x * math.cos(theta)) / math.sin(theta))
    else:
        x = int((rho - y * math.sin(theta)) / math.cos(theta))
    return round_point((x, y))

# Functions on rectangles
#
def rect_center(plu, pru, pld, prd):
    """Returns the center of the rectangle with the given corners.
       Note: l/r are for left, right; u, d are for up/down."""
    return round_point((float(plu[0] + prd[0]) / 2, float(plu[1] + prd[1]) / 2))

