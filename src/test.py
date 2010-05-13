import pygame
import Image
from pygame.locals import *
import sys

import opencv
#this is important for capturing/displaying images
from opencv import highgui 

camera = highgui.cvCreateCameraCapture(1)
def get_image():
    im = highgui.cvQueryFrame(camera)
    # Add the line below if you need it (Ubuntu 8.04+)
    #im = opencv.cvGetMat(im)
    #convert Ipl image to PIL image
    return opencv.adaptors.Ipl2PIL(im) 

def save_image():
    im = highgui.cvQueryFrame(camera)
    highgui.cvSaveImage("/tmp/test.png", im)

fps = 30.0
pygame.init()
window = pygame.display.set_mode((640,480))
pygame.display.set_caption("WebCam Demo")
screen = pygame.display.get_surface()

while True:
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            sys.exit(0)
        elif event.type == KEYDOWN:
            save_image()
    im = get_image()
    pg_img = pygame.image.frombuffer(im.tostring(), im.size, im.mode)
    screen.blit(pg_img, (0,0))
    pygame.display.flip()
    pygame.time.delay(int(1000 * 1.0/fps))
