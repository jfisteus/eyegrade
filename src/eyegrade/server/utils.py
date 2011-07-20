import array

import eyegrade.utils as utils
import eyegrade.imageproc as imageproc

# Import the cv module. If new style bindings not found, use the old ones:
try:
    import cv
    cv_new_style = True
except ImportError:
    import cvwrapper
    cv = cvwrapper.CVWrapperObject()
    cv_new_style = False

def bitmap_to_image(image_width, image_height, bitmap):
    """Converts an array of bytes into an IPL image.

       Bitmap must be an array.array of type 'B' (unsigned bytes). The
       byte 0 represents the 8 pixels to the upper-left of the image.
       In that byte, the most significative bit is the left-most bit
       of the row. The rest of the bytes go from left to right, up to
       bottom. Each row is represented by an integer number of bytes,
       with the possibility of unused bits in the last byte of each row.

       The returned IPL image will have depth 8 and 1 channel. Pixels
       will be either 255 or 0.

    """
    assert(bitmap.typecode == 'B')
    image = cv.CreateImage((image_width, image_height), 8, 1)
    byte_pos = 0
    bytes_per_row = (image_width + 7) // 8
    masks = (1 << 7, 1 << 6, 1 << 5, 1 << 4, 1 << 3, 1 << 2, 1 << 1, 1)
    for i in range(0, image_height):
        row_pos = 0
        for j in range(0, bytes_per_row):
            byte = bitmap[byte_pos]
            byte_pos += 1
            for k in range(0, 8):
                image[i, row_pos] = 255 if byte & masks[k] else 0
                row_pos += 1
                if row_pos == image_width:
                    break
    return image

def image_to_bitmap(image):
    """Converts an IPL image into an array of bytes.

       See bitmap_to_image() for details.

   """
    assert(image.depth == 8 and image.nChannels == 1)
    bytes_per_row = (image.width + 7) // 8
    bitmap_list = []
    for i in range(0, image.height):
        row_pos = 0
        for j in range(0, bytes_per_row):
            byte = 0
            for k in range(0, 8):
                byte = byte | (image[i, row_pos] > 0) << (7 - k)
                row_pos += 1
                if row_pos == image.width:
                    break
            bitmap_list.append(byte)
    return array.array('B', bitmap_list)

def process_exam(bitmap):
    """Processes and grades an exam represented as a bitmap.

       Returns an XML-formatted string.
       See bitmap_to_image() for the format of the bitmap.

    """
    image = bitmap_to_image(640, 480, bitmap)
    config = utils.read_config()
    exam_data = utils.ExamConfig('../doc/exam-data.sample')
    solutions = exam_data.solutions
    dimensions = exam_data.dimensions
    id_num_digits = exam_data.id_num_digits
    im_id = 0
    valid_student_ids = None
    imageproc_options = imageproc.ExamCapture.get_default_options()
    imageproc_context = imageproc.ExamCaptureContext()
    imageproc_options['capture-from-file'] = True
    imageproc_options['capture-proc-ipl'] = image
    image = imageproc.ExamCapture(dimensions, imageproc_context,
                                  imageproc_options)
    image.detect_safe()
    success = image.success
    exam = None
    if image.status['infobits']:
        model = utils.decode_model(image.bits)
        if model is not None and model in solutions:
            exam = utils.Exam(image, model, solutions[model],
                              valid_student_ids, im_id, False,
                              exam_data.score_weights, imageproc.save_image)
            exam.grade()
        else:
            success = False
    return build_answer(success, exam)

def build_answer(success, exam):
    """Given a processed eyegrade.utils.Exam, returns its XML-formatted string.
    """
    parts = []
    parts.append('<output>')
    parts.append('<ok>{0}</ok>'.format('true' if success else 'false'))
    if success:
        parts.append('<model>{0}</model>'.format(exam.model))
        student_id = exam.student_id
        if student_id is None or student_id == '-1':
            student_id = ''
        student_name = exam.get_student_name()
        if student_name is None:
            student_name = ''
        parts.append('<student id="{0}">{1}</student>'.format(student_id,
                                                              student_name))
        parts.append('<result><good>{0}</good><bad>{1}</bad>'
                     '<blank>{2}</blank><unclear>{3}</unclear>'
                     '</result>'.format(exam.score[0], exam.score[1],
                                        exam.score[2], exam.score[3]))
        parts.append('<answers>')
        for i in range(0, len(exam.correct)):
            parts.append('<answer num="{0}" correct="{1}" answered="{2}"'
                         ' solution="{3}" />'\
                             .format(i + 1,
                                     'true' if exam.correct[i] else 'false',
                                     exam.image.decisions[i],
                                     exam.solutions[i]))
        parts.append('</answers>')
        parts.append('<geometry>')
        for i in range(0, len(exam.image.centers)):
            parts.append('<question num="{0}">'.format(i + 1))
            for j in range(0, len(exam.image.centers[i])):
                center = exam.image.centers[i][j]
                diagonal = exam.image.diagonals[i][j]
                parts.append('<cell choice="{0}" center_x="{1[0]}"'
                             ' center_y="{1[1]}" diagonal="{2}" />'.\
                                 format(j + 1, center, diagonal))
            parts.append('</question>')
        parts.append('</geometry>')
    parts.append('</output>')
    return ''.join(parts)

def save_as_bitmap(image_filename, bitmap_filename):
    import eyegrade.imageproc
    image = cv.LoadImage(image_filename)
    bitmap = image_to_bitmap(eyegrade.imageproc.rgb_to_gray(image))
    with open(bitmap_filename, 'wb') as f:
        bitmap.tofile(f)

def test():
    import eyegrade.imageproc
    image = cv.LoadImage('../captures/test-001-processed.png')
    image_proc = imageproc.rgb_to_gray(image)
    bitmap = image_to_bitmap(image_proc)
    image2 = bitmap_to_image(image_proc.width, image_proc.height, bitmap)
    cv.SaveImage('/tmp/test.png', image2)

def test_server(host, path, image_filename):
    """Sends a valid request to the server in order to test it."""
    import eyegrade.imageproc
    import httplib, urllib
    import sys
    image = cv.LoadImage(image_filename)
    bitmap = image_to_bitmap(eyegrade.imageproc.rgb_to_gray(image))
    headers = {'Content-type': 'application/x-eyegrade-bitmap'}
    conn = httplib.HTTPConnection(host)
    conn.request('POST', path, bitmap, headers)
    response = conn.getresponse()
    if response.status == 200:
        print response.read()
    else:
        print >> sys.stderr, response.status, response.reason
        print response.read()
    conn.close()
