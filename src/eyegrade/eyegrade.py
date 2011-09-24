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

import sys
import os
from optparse import OptionParser
import time
import csv
import re

# Local imports
import imageproc
import utils
import gui

param_max_wait_time = 0.15 # seconds

class PerformanceProfiler(object):
    def __init__(self):
        self.start()
        self.num_captures = 0
        self.num_student_id_changes = 0

    def start(self):
        self.time0 = time.time()

    def count_capture(self):
        self.num_captures += 1

    def count_student_id_change(self):
        self.num_student_id_changes += 1

    def finish_exam(self, exam):
        time1 = time.time()
        stats = {}
        stats['time'] = time1 - self.time0
        stats['manual-changes'] = exam.num_manual_changes()
        stats['num-captures'] = self.num_captures
        stats['num-student-id-changes'] = self.num_student_id_changes
        self.compute_ocr_stats(stats, exam)
        self.time0 = time1
        self.num_captures = 0
        self.num_student_id_changes = 0
        return stats

    def compute_ocr_stats(self, stats, exam):
        if exam.image.id is None or exam.image.id_ocr_original is None:
            digits_total = 0
            digits_error = 0
        else:
            digits_total = len(exam.image.id)
            digits_error = len([1 for a, b in zip(exam.image.id,
                                                  exam.image.id_ocr_original) \
                                    if a != b])
        stats['id-ocr-digits-total'] = digits_total
        stats['id-ocr-digits-error'] = digits_error
        if exam.image.id_ocr_original is not None:
            stats['id-ocr-detected'] = exam.image.id_ocr_original
        else:
            stats['id-ocr-detected'] = '-1'

def read_cmd_options():
    parser = OptionParser(usage = "usage: %prog [options] EXAM_CONFIG_FILE",
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option("-e", "--exam-data-file", dest = "ex_data_filename",
                      help = "read model data from FILENAME")
    parser.add_option("-a", "--answers-file", dest = "answers_filename",
                      help = "write students' answers to FILENAME")
    parser.add_option("-s", "--start-id", dest = "start_id", type = "int",
                      help = "start at the given exam id",
                      default = 0)
    parser.add_option("-o", "--output-dir", dest = "output_dir", default = '.',
                      help = "store captured images at the given directory")
    parser.add_option("-d", "--debug", action="store_true", dest = "debug",
                      default = False, help = "activate debugging features")
    parser.add_option("-c", "--camera", type="int", dest = "camera_dev",
                      help = "camera device to be selected (-1 for default)")
    parser.add_option("--stats", action="store_true", dest = "save_stats",
                      default = False,
                      help = "save performance stats to the answers file")
    parser.add_option("--id-list", dest = "ids_file", default = None,
                      help = "file with the list of valid student ids")
    parser.add_option("--capture-raw", dest = "raw_file", default = None,
                      help = "capture from raw file")
    parser.add_option("--capture-proc", dest = "proc_file", default = None,
                      help = "capture from pre-processed file")
    parser.add_option("--fixed-hough", dest = "fixed_hough", default = None,
                      type = "int", help = "fixed Hough transform threshold")
    parser.add_option("-f", "--ajust-first", action="store_true",
                      dest = "adjust", default = False,
                      help = "don't lock on an exam until SPC is pressed")

    (options, args) = parser.parse_args()
    if len(args) == 1:
        options.ex_data_filename = args[0]
    elif len(args) == 0:
        parser.error("Exam configuration file required")
    elif len(args) > 1:
        parser.error("Too many input command-line parameters")
    if options.raw_file is not None and options.proc_file is not None:
        parser.error("--capture-raw and --capture-proc are mutually exclusive")
    return options

def cell_clicked(image, point):
    min_dst = None
    clicked_row = None
    clicked_col = None
    for i, row in enumerate(image.centers):
        for j, center in enumerate(row):
            dst = imageproc.distance(point, center)
            if min_dst is None or dst < min_dst:
                min_dst = dst
                clicked_row = i
                clicked_col = j
    if (min_dst is not None and
        min_dst <= image.diagonals[clicked_row][clicked_col] / 2):
        return (clicked_row, clicked_col + 1)
    else:
        return None

def dump_camera_buffer(camera):
    if camera is not None:
        for i in range(0, 6):
            imageproc.capture(camera, False)

def select_camera(options, config):
    if options.camera_dev is None:
        camera = config['camera-dev']
    else:
        camera = options.camera_dev
    return camera

def main():
    options = read_cmd_options()
    config = utils.read_config()
    save_pattern = config['save-filename-pattern']

    exam_data = utils.ExamConfig(options.ex_data_filename)
    solutions = exam_data.solutions
    dimensions = exam_data.dimensions
    id_num_digits = exam_data.id_num_digits
    read_id = (id_num_digits > 0)
    save_pattern = os.path.join(options.output_dir, save_pattern)
    if options.answers_filename is not None:
        answers_file = options.answers_filename
    else:
        answers_file = 'eyegrade-answers.csv'
        answers_file = os.path.join(options.output_dir, answers_file)

    im_id = options.start_id
    valid_student_ids = None
    if options.ids_file is not None:
        valid_student_ids = utils.read_student_ids(filename=options.ids_file,
                                                   with_names=True)

    interface = gui.PygameInterface((640, 480), read_id, options.ids_file)

    profiler = PerformanceProfiler()

    # Initialize options
    imageproc_options = imageproc.ExamCapture.get_default_options()
    imageproc_options['logging-dir'] = options.output_dir
    if read_id:
        imageproc_options['read-id'] = True
        imageproc_options['id-num-digits'] = id_num_digits
    if options.debug:
        imageproc_options['show-status'] = True
        imageproc_options['error-logging'] = True
    if config['error-logging']:
        imageproc_options['error-logging'] = True
    if not options.fixed_hough:
        imageproc_context = imageproc.ExamCaptureContext()
    else:
        imageproc_context = imageproc.ExamCaptureContext(options.fixed_hough)

    # Initialize capture source
    if options.proc_file is not None:
        imageproc_options['capture-from-file'] = True
        imageproc_options['capture-proc-file'] = options.proc_file
    elif options.raw_file is not None:
        imageproc_options['capture-from-file'] = True
        imageproc_options['capture-raw-file'] = options.raw_file
    else:
        imageproc_context.init_camera(select_camera(options, config))
        if imageproc_context.camera is None:
            print >> sys.stderr, 'ERROR: No camera found!'
            sys.exit(1)

    # Program main loop
    lock_mode = not options.adjust
    last_time = time.time()
    interface.update_text('Searching...', False)
    interface.set_statusbar_message(utils.program_name + ' ' + utils.version)
    interface.set_search_toolbar(True)
    latest_graded_exam = None
    while True:
        override_id_mode = False
        exam = None
        model = None
        manual_detection = False
        profiler.count_capture()
        image = imageproc.ExamCapture(dimensions, imageproc_context,
                                      imageproc_options)
        image.detect_safe()
        success = image.success
        if image.status['infobits']:
            model = utils.decode_model(image.bits)
            if model is not None and model in solutions:
                exam = utils.Exam(image, model, solutions[model],
                                  valid_student_ids, im_id, options.save_stats,
                                  exam_data.score_weights,
                                  imageproc.save_image)
                exam.grade()
                latest_graded_exam = exam
            else:
                success = False

        interface.set_manual_detect_enabled(False)
        events = interface.events_search_mode()
        for event, event_info in events:
            if event == gui.event_quit:
                sys.exit(0)
            elif event == gui.event_debug_proc and options.debug:
                imageproc_options['show-image-proc'] = \
                    not imageproc_options['show-image-proc']
            elif event == gui.event_debug_lines and options.debug:
                imageproc_options['show-lines'] = \
                    not imageproc_options['show-lines']
            elif event == gui.event_snapshot:
                if latest_graded_exam is None:
                    exam = utils.Exam(image, model, {}, valid_student_ids,
                                      im_id, options.save_stats,
                                      exam_data.score_weights,
                                      imageproc.save_image)
                    exam.grade()
                    interface.set_manual_detect_enabled(True)
                else:
                    exam = latest_graded_exam
                success = True
                if options.ids_file is not None:
                    exam.reset_student_id_filter(False)
                else:
                    exam.reset_student_id_editor()
                    override_id_mode = True
            elif event == gui.event_manual_detection:
                exam = utils.Exam(image, model, {}, valid_student_ids, im_id,
                                  options.save_stats, exam_data.score_weights,
                                  imageproc.save_image)
                exam.grade()
                interface.set_manual_detect_enabled(True)
                # Set the event to repeat again in lock_mode
                interface.enqueue_event((gui.event_manual_detection, None))
                success = True
                if options.ids_file is not None:
                    exam.reset_student_id_filter(False)
                else:
                    exam.reset_student_id_editor()
                    override_id_mode = True
            elif event == gui.event_lock:
                lock_mode = True

        # Enter review mode if the capture was succesfully read or the
        # image was locked by the user
        if success and lock_mode:
            continue_waiting = True
            manual_detection_mode = False
            manual_points = []
            exam.lock_capture()
            exam.draw_answers()
            interface.show_capture(exam.image.image_drawn, False)
            interface.update_text(exam.get_student_name(), False)
            if exam.score is not None:
                interface.update_status(exam.score, False)
            interface.set_review_toolbar(True)
            while continue_waiting:
                event, event_info = interface.wait_event_review_mode()
                if event == gui.event_quit:
                    sys.exit(0)
                elif event == gui.event_cancel_frame:
                    continue_waiting = False
                elif event == gui.event_save:
                    stats = profiler.finish_exam(exam)
                    exam.save_image(save_pattern)
                    exam.save_answers(answers_file, config['csv-dialect'],
                                      stats)
                    if options.debug:
                        exam.save_debug_images(save_pattern)
                    im_id += 1
                    continue_waiting = False
                elif event == gui.event_manual_id:
                    override_id_mode = True
                    exam.reset_student_id_editor()
                    exam.draw_answers()
                    interface.show_capture(exam.image.image_drawn, False)
                    interface.update_text(exam.get_student_name())
                elif (event == gui.event_next_id
                      or event == gui.event_previous_id):
                    if not override_id_mode and options.ids_file is not None:
                        if len(exam.student_id_filter) == 0:
                            if event == gui.event_next_id:
                                exam.try_next_student_id()
                            else:
                                exam.try_previous_student_id()
                        else:
                            exam.reset_student_id_filter()
                        profiler.count_student_id_change()
                        exam.draw_answers()
                        interface.show_capture(exam.image.image_drawn, False)
                        interface.update_text(exam.get_student_name())
                elif event == gui.event_id_digit:
                    if override_id_mode:
                        exam.student_id_editor(event_info)
                    elif options.ids_file is not None:
                        exam.filter_student_id(event_info)
                    profiler.count_student_id_change()
                    exam.draw_answers()
                    interface.show_capture(exam.image.image_drawn, False)
                    interface.update_text(exam.get_student_name())
                elif event == gui.event_debug_proc and options.debug:
                    imageproc_options['show-image-proc'] = \
                        not imageproc_options['show-image-proc']
                    continue_waiting = False
                elif event == gui.event_debug_lines and options.debug:
                    imageproc_options['show-lines'] = \
                        not imageproc_options['show-lines']
                    continue_waiting = False
                elif event == gui.event_manual_detection:
                    exam.image.clean_drawn_image()
                    interface.show_capture(exam.image.image_drawn, False)
                    interface.update_text(('Manual detection: click on the '
                                           'outer corners of the answer '
                                           'box(es)'))
                    manual_detection_mode = True
                    manual_points = []
                elif event == gui.event_click:
                    if not manual_detection_mode:
                        cell = cell_clicked(exam.image, event_info)
                        if cell is not None:
                            question, answer = cell
                            exam.toggle_answer(question, answer)
                            interface.show_capture(exam.image.image_drawn,
                                                   False)
                            interface.update_status(exam.score)
                    else:
                        manual_points.append(event_info)
                        exam.image.draw_corner(event_info)
                        interface.show_capture(exam.image.image_drawn, True)
                        if len(manual_points) == 4 * len(exam.image.boxes_dim):
                            corner_matrixes = imageproc.process_box_corners(
                                manual_points, exam.image.boxes_dim)
                            if corner_matrixes != []:
                                exam.image.detect_manual(corner_matrixes)
                                if exam.image.status['infobits']:
                                    exam.model = utils.decode_model(image.bits)
                                    if exam.model is not None:
                                        exam.solutions = solutions[exam.model]
                                        exam.grade()
                                        interface.update_status(exam.score,
                                                                False)
                            else:
                                exam.image.clean_drawn_image()
                                interface.set_statusbar_message(('Manual '
                                                                 'detection '
                                                                 'failed!'),
                                                                False)
                            exam.draw_answers()
                            interface.show_capture(exam.image.image_drawn,
                                                   False)
                            interface.update_text('', True)
                            manual_detection_mode = False
            dump_camera_buffer(imageproc_context.camera)
            interface.update_text('Searching...', False)
            interface.update_status(None, False)
            interface.set_search_toolbar(True)
            latest_graded_exam = None
            if imageproc_options['capture-from-file']:
                sys.exit(0)
        else:
            if exam is not None:
                exam.draw_answers()
            else:
                image.draw_status()
            interface.show_capture(image.image_drawn)
            current_time = time.time()
            diff = current_time - last_time
            if current_time > last_time and diff < param_max_wait_time:
                interface.delay(param_max_wait_time - diff)
                last_time += 1
            else:
                if diff > 3 * param_max_wait_time:
                    dump_camera_buffer(imageproc_context.camera)
                last_time = current_time
            if imageproc_options['capture-from-file']:
                interface.wait_key()
                sys.exit(1)

if __name__ == "__main__":
    main()
