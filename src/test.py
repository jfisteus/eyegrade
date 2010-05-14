import pygame
import Image
from pygame.locals import *
import sys

import opencv
#this is important for capturing/displaying images
from opencv import highgui 
import imageproc

capturer = imageproc.Capturer(1)

def get_image():
    return capturer.capture()

def save_image(im):
    highgui.cvSaveImage("/tmp/test.png", im)

fps = 30.0
pygame.init()
window = pygame.display.set_mode((640,480))
pygame.display.set_caption("WebCam Demo")
screen = pygame.display.get_surface()

while True:
    ipl_im = get_image()
    im = imageproc.gray_ipl_to_rgb_pil(ipl_im)

    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            sys.exit(0)
        elif event.type == KEYDOWN:
            save_image(ipl_im)
    pg_img = pygame.image.frombuffer(im.tostring(), im.size, im.mode)
    screen.blit(pg_img, (0,0))
    pygame.display.flip()
    pygame.time.delay(int(1000 * 1.0/fps))
