import pygame

# Local imports
import imageproc

pygame.init()

param_background_color = pygame.Color(0, 0, 0)
param_font_name = 'arial'
param_font_size = 16
param_font_color = pygame.Color(255, 255, 255)

# Event constants
event_quit = 1
event_debug_proc = 2
event_debug_lines = 3
event_snapshot = 4
event_lock = 5
event_cancel_frame = 6
event_save = 7
event_manual_id = 8
event_next_id = 9
event_id_digit = 10
event_click = 11

class PygameInterface(object):
    """Implements the user interface of the system using pygame."""

    def __init__(self, capture_size):
        self.capture_size = capture_size
        self.size = (capture_size[0] + 40, capture_size[1] + 40)
        pygame.display.set_mode(self.size)
        pygame.display.set_caption('eyegrade')
        self.screen = pygame.display.get_surface()
        self.surface_bottom = pygame.Surface((capture_size[0],
                                              self.size[1] - capture_size[1]))
        self.surface_bottom.fill(param_background_color)
        self.normal_font = pygame.font.SysFont(param_font_name,
                                               param_font_size)

    def show_capture(self, image):
        pg_img = imageproc.cvimage_to_pygame(image)
        self.screen.blit(pg_img, (0,0))
        pygame.display.flip()

    def update_text(self, text):
        self.screen.blit(self.surface_bottom, (0, self.capture_size[1]))
        if text is not None:
            surface = self.normal_font.render(text, True, param_font_color,
                                              param_background_color)
            self.screen.blit(surface, (10, 10 + self.capture_size[1]))
        pygame.display.flip()

    def wait_event_review_mode(self):
        return self.__parse_event_review_mode(pygame.event.wait())

    def events_search_mode(self):
        return [self.__parse_event_search_mode(e) for e in pygame.event.get()]

    def delay(self, time):
        """Blocks for a given amount of time (in seconds)."""
        pygame.time.wait(int(1000 * time))

    def wait_key(self):
        event = pygame.event.wait()
        while event.type != pygame.QUIT and event.type != pygame.KEYDOWN:
            event = pygame.event.wait()

    def __parse_event_search_mode(self, event):
        if event.type == pygame.QUIT:
            return (event_quit, None)
        elif event.type == pygame.KEYDOWN:
            if event.key == 27:
                return (event_quit, None)
            elif event.key == ord('p'):
                return (event_debug_proc, None)
            elif event.key == ord('l'):
                return (event_debug_lines, None)
            elif event.key == ord('s'):
                return (event_snapshot, None)
            elif event.key == 32:
                return (event_lock, None)
        return (None, None)

    def __parse_event_review_mode(self, event):
        if event.type == pygame.QUIT:
            return (event_quit, None)
        elif event.type == pygame.KEYDOWN:
            if event.key == 27:
                return (event_quit, None)
            elif event.key == 8:
                return (event_cancel_frame, None)
            elif event.key == 32:
                return (event_save, None)
            elif event.key == ord('i'):
                return (event_manual_id, None)
            elif event.key == 9:
                return (event_next_id, None)
            elif event.key == ord('p'):
                return (event_debug_proc, None)
            elif event.key == ord('l'):
                return (event_debug_lines, None)
            elif event.key >= ord('0') and event.key <= ord('9'):
                return (event_id_digit, chr(event.key))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return (event_click, event.pos)
        return (None, None)
