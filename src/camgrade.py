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

def get_image(camera):
    im_raw = imageproc.capture(camera, True)
    im_proc = imageproc.pre_process(im_raw)
    return im_raw, im_proc

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

def save_answers(answers, answer_id, answers_file):
    model, decisions, good, bad, undet = answers
    sep = "\t"
    f = open(answers_file, "a")
    f.write(str(answer_id))
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
    pygame.display.set_caption("WebCam Demo")
    screen = pygame.display.get_surface()

    camera = init(config)
    last_successful_im = None
    while True:
        im_raw, im_proc = get_image(camera)
    #    im = imageproc.gray_ipl_to_rgb_pil(im_proc)
        success, decisions, bits, corners = \
            imageproc.detect(im_raw, im_proc, dimensions, True)
        if success:
            model = decode_model_2x31(bits)
            if model is not None:
                good, bad, undet, correct = grade(model, decisions, solutions)
                text = "Model %s: %d / %d"%(chr(65 + model), good, bad)
                if undet > 0:
                    color = (0, 0, 255)
                    text = text + " / " + str(undet)
                else:
                    color = (255, 0, 0)
                imageproc.draw_text(im_raw, text, color,
                                    (10, im_raw.height - 20))
                imageproc.draw_answers(im_raw, corners, decisions, correct)
                last_successful_im = im_raw
                last_answers = (model, decisions, good, bad, undet)
            else:
                success = False
        imageproc.draw_success_indicator(im_raw, success)
        color = (255, 0, 0) if last_successful_im is not None else (0, 0, 255)
        imageproc.draw_text(im_raw, str(im_id), color, (10, 65))

    #    imageproc.detect_lines(im_proc)
        im = opencv.adaptors.Ipl2PIL(im_raw)
        events = pygame.event.get()
        for event in events:
            if event.type == QUIT:
                sys.exit(0)
            elif event.type == KEYDOWN:
                if last_successful_im is not None:
                    save_image(last_successful_im, im_id, save_pattern)
                    if answers_file is not None:
                        save_answers(last_answers, im_id, answers_file)
                    im_id += 1
                    last_successful_im = None
                    last_answers = None
        pg_img = pygame.image.frombuffer(im.tostring(), im.size, im.mode)
        screen.blit(pg_img, (0,0))
        pygame.display.flip()
        pygame.time.delay(int(1000 * 1.0/fps))

if __name__ == "__main__":
    main()
