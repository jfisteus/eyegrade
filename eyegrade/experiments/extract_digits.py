# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2011 Jesus Arias Fisteus
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

import eyegrade.imageproc as imageproc
import eyegrade.ocr as ocr
import eyegrade.utils as utils

def process_image(filename, dimensions, options, context):
    corners = []
    corners_int = []
    options['capture-proc-file'] = filename
    for idx in range(0, len(imageproc.param_hough_thresholds)):
        context.hough_thresholds_idx = idx
        image = imageproc.ExamCapture(dimensions, context, options)
        image.detect()
        if image.success:
            break
    if image.success:
        corners_up, corners_down = image.id_corners
        for i in range(0, len(corners_up) - 1):
            c = (corners_up[i], corners_up[i + 1],
                 corners_down[i], corners_down[i + 1])
            corners_int.append(ocr.adjust_cell_corners(image.image_proc, c))
            corners.append(c)
    return corners, corners_int


def main():
    options = imageproc.ExamCapture.get_default_options()
    options['read-id'] = True
    options['id-num-digits'] = 9
    options['infobits'] = True
    options['capture-from-file'] = True
    dimensions = [(4, 10), (4, 10)]
    context = imageproc.ExamCaptureContext()
    image_template = ('exam-%s-%d.png-proc')
    results = utils.read_results('eyegrade-answers.csv')
    for result in results:
        seq = int(result['seq-num'])
        sid = result['student-id']
        corners, corners_int = process_image(image_template%(sid, seq),
                                             dimensions, options, context)
        if len(corners) > 0 and len(sid) == 9:
            for i, digit in enumerate(sid):
                data = ['exam-%s-%d.png-proc'%(sid, seq), digit, i]
                data.extend(corners[i])
                data.extend(corners_int[i])
                print '\t'.join([str(d) for d in data])

if __name__ == '__main__':
    main()
