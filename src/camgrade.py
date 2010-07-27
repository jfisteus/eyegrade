import pygame
import Image
from pygame.locals import *
import sys
import ConfigParser, os
from optparse import OptionParser
import opencv
#this is important for capturing/displaying images
from opencv import highgui 
import imageproc
import time
import copy

class Exam(object):
    def __init__(self, image, model, solutions, im_id = None,
                 save_stats = False):
        self.image = image
        self.model = model
        self.solutions = solutions
        self.im_id = im_id
        self.correct = None
        self.score = None
        self.student_id = -1
        self.original_decisions = copy.copy(self.image.decisions)
        self.save_stats = save_stats

    def grade(self):
        good = 0
        bad = 0
        undet = 0
        self.correct = []
        for i in range(0, len(self.image.decisions)):
            if self.image.decisions[i] > 0:
                if self.solutions[i] == self.image.decisions[i]:
                    good += 1
                    self.correct.append(True)
                else:
                    bad += 1
                    self.correct.append(False)
            elif self.image.decisions[i] < 0:
                undet += 1
                self.correct.append(False)
            else:
                self.correct.append(False)
        self.score = (good, bad, undet)

    def draw_answers(self):
        good, bad, undet = self.score
        self.image.draw_answers(self.solutions, self.model, self.correct,
                                self.score[0], self.score[1], self.score[2],
                                self.im_id)

    def save_image(self, filename_pattern):
        highgui.cvSaveImage(filename_pattern%self.im_id, self.image.image_drawn)

    def save_debug_images(self, filename_pattern):
        raw_pattern = filename_pattern + "-raw"
        proc_pattern = filename_pattern + "-proc"
        highgui.cvSaveImage(raw_pattern%self.im_id, self.image.image_raw)
        highgui.cvSaveImage(proc_pattern%self.im_id, self.image.image_proc)

    def save_answers(self, answers_file, stats = None):
        sep = "\t"
        f = open(answers_file, "a")
        f.write(str(self.im_id))
        f.write(sep)
        f.write(str(self.student_id))
        f.write(sep)
        f.write(str(self.model))
        f.write(sep)
        f.write(str(self.score[0]))
        f.write(sep)
        f.write(str(self.score[1]))
        f.write(sep)
        f.write(str(self.score[2]))
        f.write(sep)
        f.write("/".join([str(d) for d in self.image.decisions]))
        if stats is not None and self.save_stats:
            f.write(sep)
            f.write(str(stats['time']))
            f.write(sep)
            f.write(str(stats['manual-changes']))
        f.write('\n')
        f.close()

    def toggle_answer(self, question, answer):
        if self.image.decisions[question] == answer:
            self.image.decisions[question] = 0
        else:
            self.image.decisions[question] = answer
        self.grade()
        self.image.clean_drawn_image(True)
        self.draw_answers()

    def num_manual_changes(self):
        return len([d1 for (d1, d2) in \
                        zip(self.original_decisions, self.image.decisions) \
                        if d1 != d2])

class PerformanceProfiler(object):
    def __init__(self):
        self.start()

    def start(self):
        self.time0 = time.time()

    def finish_exam(self, exam):
        time1 = time.time()
        stats = {}
        stats['time'] = time1 - self.time0
        stats['manual-changes'] = exam.num_manual_changes()
        self.time0 = time1
        return stats

def init(camera_dev):
    camera = imageproc.init_camera(camera_dev)
    return camera

def process_exam_data(filename):
    exam_data = ConfigParser.SafeConfigParser()
    exam_data.read([filename])
    num_models = exam_data.getint("exam", "num-models")
    solutions = []
    for i in range(0, num_models):
        key = "model-" + chr(65 + i)
        solutions.append(parse_solutions(exam_data.get("solutions", key)))
    dimensions = parse_dimensions(exam_data.get("exam", "dimensions"))
    return solutions, dimensions

def parse_solutions(s):
    return [int(num) for num in s.split("/")]

def parse_dimensions(s):
    dimensions = []
    boxes = s.split(";")
    for box in boxes:
        dims = box.split(",")
        dimensions.append((int(dims[0]), int(dims[1])))
    return dimensions

def decode_model_2x31(bits):
    # x3 = x0 ^ x1 ^ not x2; x0-x3 == x4-x7
    valid = False
    if len(bits) == 3:
        valid = True
    elif len(bits) >= 4:
        if (bits[3] == bits[0] ^ bits[1] ^ (not bits[2])):
            if len(bits) < 8:
                valid = True
            else:
                valid = (bits[0:4] == bits[4:8])
    if valid:
        return bits[0] | bits[1] << 1 | bits[2] << 2
    else:
        return None

def read_config():
    defaults = {"camera-dev": "-1",
                "save-filename-pattern": "exam-%%03d.png"}
    config = ConfigParser.SafeConfigParser(defaults)
    config.read([os.path.expanduser('~/.camgrade.cfg')])
    return config

def read_cmd_options():
    parser = OptionParser("usage: %prog [options]")
    parser.add_option("-e", "--exam-data-file", dest = "ex_data_filename",
                      help = "read model data from FILENAME")
    parser.add_option("-a", "--answers-file", dest = "answers_filename",
                      help = "write students' answers to FILENAME")
    parser.add_option("-s", "--start-id", dest = "start_id", type = "int",
                      help = "start at the given exam id",
                      default = 0)
    parser.add_option("-o", "--output-dir", dest = "output_dir",
                      help = "store captured images at the given directory")
    parser.add_option("-d", "--debug", action="store_true", dest = "debug",
                      default = False, help = "activate debugging features")
    parser.add_option("-c", "--camera", type="int", dest = "camera_dev",
                      help = "camera device to be selected (-1 for default)")
    parser.add_option("--stats", action="store_true", dest = "save_stats",
                      default = False,
                      help = "save performance stats to the answers file")
    (options, args) = parser.parse_args()
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
    if min_dst <= image.diagonals[i][j] / 2:
        return (clicked_row, clicked_col + 1)
    else:
        return None

def dump_camera_buffer(camera):
    for i in range(0, 6):
        imageproc.capture(camera, False)

def show_image(image, screen):
    im = opencv.adaptors.Ipl2PIL(image)
    pg_img = pygame.image.frombuffer(im.tostring(), im.size, im.mode)
    screen.blit(pg_img, (0,0))
    pygame.display.flip()

def select_camera(options, config):
    if options.camera_dev is None:
        try:
            camera = config.getint('default', 'camera-dev')
        except:
            camera = -1
    else:
        camera = options.camera_dev
    return camera

def main():
    options = read_cmd_options()
    config = read_config()
    save_pattern = config.get('default', 'save-filename-pattern')

    if options.ex_data_filename is not None:
        solutions, dimensions = process_exam_data(options.ex_data_filename)
    else:
        solutions = []
        dimensions = []
    if options.output_dir is not None:
        save_pattern = os.path.join(options.output_dir, save_pattern)
    if options.answers_filename is not None:
        answers_file = options.answers_filename
    else:
        answers_file = 'camgrade-answers.txt'
        if options.output_dir is not None:
            answers_file = os.path.join(options.output_dir, answers_file)
    im_id = options.start_id

    fps = 8.0
    pygame.init()
    window = pygame.display.set_mode((640,480))
    pygame.display.set_caption("camgrade")
    screen = pygame.display.get_surface()
    camera = init(select_camera(options, config))

    profiler = PerformanceProfiler()
    while True:
        image = imageproc.ExamCapture(camera, dimensions, True)
        image.detect(options.debug)
        success = image.success
        if success:
            model = decode_model_2x31(image.bits)
            if model is not None:
                exam = Exam(image, model, solutions[model], im_id,
                            options.save_stats)
                exam.grade()
                exam.draw_answers()
            else:
                success = False

        events = pygame.event.get()
        for event in events:
            if event.type == QUIT or \
                    (event.type == KEYDOWN and event.key == 27):
                sys.exit(0)

        show_image(image.image_drawn, screen)
        if success:
            continue_waiting = True
            while continue_waiting:
                event = pygame.event.wait()
                if event.type == QUIT:
                    sys.exit(0)
                elif event.type == KEYDOWN:
                    if event.key == 27:
                        sys.exit(0)
                    elif event.key == 8:
                        continue_waiting = False
                    elif event.key == 32:
                        stats = profiler.finish_exam(exam)
                        exam.save_image(save_pattern)
                        exam.save_answers(answers_file, stats)
                        if options.debug:
                            exam.save_debug_images(save_pattern)
                        im_id += 1
                        continue_waiting = False
                elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                    cell = cell_clicked(exam.image, event.pos)
                    if cell is not None:
                        question, answer = cell
                        exam.toggle_answer(question, answer)
                        show_image(exam.image.image_drawn, screen)
            dump_camera_buffer(camera)
        else:
            pygame.time.delay(int(1000 * 1.0/fps))

if __name__ == "__main__":
    main()
