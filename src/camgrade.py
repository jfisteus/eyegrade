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

def init(config):
    camera = imageproc.init_camera(config.getint('default', 'camera-dev'))
    return camera

def save_image(im, im_id, pattern):
    highgui.cvSaveImage(pattern%im_id, im)

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

def grade(model, decisions, solutions):
    if model < len(solutions):
        sol = solutions[model]
        good = 0
        bad = 0
        undet = 0
        correct = []
        for i in range(0, len(decisions)):
            if decisions[i] > 0:
                if sol[i] == decisions[i]:
                    good += 1
                    correct.append(True)
                else:
                    bad += 1
                    correct.append(False)
            elif decisions[i] < 0:
                undet += 1
                correct.append(False)
            else:
                correct.append(False)
    else:
        good = 0
        bad = 0
        undet = len(decisions)
        correct = [false] * undet
    return (good, bad, undet, correct)

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
    parser.add_option("-d", "--output-dir", dest = "output_dir",
                      help = "stored captured images at the given directory")
    (options, args) = parser.parse_args()
    return options

def save_answers(answers, answer_id, student_id, answers_file):
    model, decisions, good, bad, undet = answers
    sep = "\t"
    f = open(answers_file, "a")
    f.write(str(answer_id))
    f.write(sep)
    f.write(str(student_id))
    f.write(sep)
    f.write(str(model))
    f.write(sep)
    f.write(str(good))
    f.write(sep)
    f.write(str(bad))
    f.write(sep)
    f.write(str(undet))
    f.write(sep)
    f.write("/".join([str(d) for d in decisions]))
    f.write('\n')
    f.close()

def cell_clicked(image, point):
    min_dst = None
    row = None
    col = None
    for i, row in enumerate(image.centers):
        for j, point in enumerate(row):
            dst = imageproc.distance(point, image.centers[i][j])
            if min_dst is None or dst < min_dst:
                min_dst = dst
                row = i
                col = j
    if min_dst <= image.diagonals[i][j]:
        return (i, j)
    else:
        return None

def dump_camera_buffer(camera):
    for i in range(0, 6):
        get_image(camera)

def main():
    options = read_cmd_options()
    config = read_config()
    save_pattern = config.get('default', 'save-filename-pattern')

    if options.ex_data_filename is not None:
        solutions, dimensions = process_exam_data(options.ex_data_filename)
    else:
        solutions = []
        dimensions = []
    answers_file = options.answers_filename
    if options.output_dir is not None:
        save_pattern = os.path.join(options.output_dir, save_pattern)
    im_id = options.start_id

    fps = 8.0
    pygame.init()
    window = pygame.display.set_mode((640,480))
    pygame.display.set_caption("camgrade")
    screen = pygame.display.get_surface()

    camera = init(config)
    while True:
        image = imageproc.ExamCapture(camera, dimensions, True)
        image.detect(True)
        success = image.success
        if success:
            model = decode_model_2x31(image.bits)
            if model is not None:
                good, bad, undet, correct = grade(model, image.decisions,
                                                  solutions)
                image.draw_answers(solutions[model], model,
                                   correct, good, bad, undet, im_id)
                answers = (model, image.decisions, good, bad, undet)
            else:
                success = False

        im = opencv.adaptors.Ipl2PIL(image.image_drawn)
        events = pygame.event.get()
        for event in events:
            if event.type == QUIT or \
                    (event.type == KEYDOWN and event.key == 27):
                sys.exit(0)
        pg_img = pygame.image.frombuffer(im.tostring(), im.size, im.mode)
        screen.blit(pg_img, (0,0))
        pygame.display.flip()
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
                        save_image(image.image_drawn, im_id, save_pattern)
                        if answers_file is not None:
                            save_answers(answers, im_id, -1, answers_file)
                        im_id += 1
                        continue_waiting = False
                elif event.type = MOUSEBUTTONDOWN:
                    print "Button:", event.button
                    cell = cell_clicked(image, event.pos)
                    print "Clicked:", cell
            dump_camera_buffer(camera)
        else:
            pygame.time.delay(int(1000 * 1.0/fps))
if __name__ == "__main__":
    main()
