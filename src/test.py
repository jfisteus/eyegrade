import pygame
import Image
from pygame.locals import *
import sys

import opencv
#this is important for capturing/displaying images
from opencv import highgui 
import imageproc

camera = imageproc.init_camera(1)

def get_image():
    im_raw = imageproc.capture(camera, True)
    im_proc = imageproc.pre_process(im_raw)
    return im_raw, im_proc

def save_image(im):
    highgui.cvSaveImage("/tmp/test.png", im)

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

def grade(model, decisions):
    answers = [1, 2, 1, 3, 4, 2, 3, 2, 1, 1, 1, 2, 2, 4, 2, 2, 3, 2, 3, 1]
    good = 0
    bad = 0
    undet = 0
    correct = []
    for i in range(0, len(decisions)):
        if decisions[i] > 0:
            if answers[i] == decisions[i]:
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
    return (good, bad, undet, correct)

fps = 8.0
pygame.init()
window = pygame.display.set_mode((640,480))
pygame.display.set_caption("WebCam Demo")
screen = pygame.display.get_surface()

while True:
    im_raw, im_proc = get_image()
#    im = imageproc.gray_ipl_to_rgb_pil(im_proc)
    success, decisions, bits, corners = \
        imageproc.detect(im_raw, im_proc, [[4,10],[4,10]], True)
    if success:
        model = decode_model_2x31(bits)
        if model is not None:
            good, bad, undet, correct = grade(model, decisions)
            text = "Model %s: %d / %d"%(chr(65 + model), good, bad)
            if undet > 0:
                color = (0, 0, 255)
                text = text + " / " + str(undet)
            else:
                color = (255, 0, 0)
            imageproc.draw_text(im_raw, text, color)
            imageproc.draw_answers(im_raw, corners, decisions, correct)
        else:
            success = False
    imageproc.draw_success_indicator(im_raw, success)

#    imageproc.detect_lines(im_proc)
    im = opencv.adaptors.Ipl2PIL(im_raw)

    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            sys.exit(0)
        elif event.type == KEYDOWN:
            save_image(im_proc)
    pg_img = pygame.image.frombuffer(im.tostring(), im.size, im.mode)
    screen.blit(pg_img, (0,0))
    pygame.display.flip()
    pygame.time.delay(int(1000 * 1.0/fps))

