import pygame

# Local imports
import imageproc
import utils

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

statusbar_event_id = pygame.USEREVENT + 1
statusbar_display_time = 4000

save_icon_normal = pygame.image.load(utils.resource_path('save.png'))
save_icon_high = pygame.image.load(utils.resource_path('save_high.png'))
next_id_icon_normal = pygame.image.load(utils.resource_path('next_id.png'))
next_id_icon_high = pygame.image.load(utils.resource_path('next_id_high.png'))
edit_id_icon_normal = pygame.image.load(utils.resource_path('edit_id.png'))
edit_id_icon_high = pygame.image.load(utils.resource_path('edit_id_high.png'))
discard_icon_normal = pygame.image.load(utils.resource_path('discard.png'))
discard_icon_high = pygame.image.load(utils.resource_path('discard_high.png'))
snapshot_icon_normal = pygame.image.load(utils.resource_path('snapshot.png'))
snapshot_icon_high = pygame.image.load(utils.resource_path('snapshot_high.png'))
exit_icon_normal = pygame.image.load(utils.resource_path('exit.png'))
exit_icon_high = pygame.image.load(utils.resource_path('exit_high.png'))
correct_icon = pygame.image.load(utils.resource_path('correct.png'))
incorrect_icon = pygame.image.load(utils.resource_path('incorrect.png'))
unanswered_icon = pygame.image.load(utils.resource_path('unanswered.png'))

snapshot_help = 'Capture the current exam, when the ' + \
    'system does not recognise it'
exit_help = 'Exit the system'
save_help = 'Save current exam and looks for the next one'
next_id_help = 'Try another student ID'
edit_id_help = 'Insert the student ID manually using the keyboard'
discard_help = 'Discard this capture and try again'

icon_size = save_icon_normal.get_size()
toolbar_pos = (8, 10)
toolbar_sep = 10

# Vertical position of tools in the toolbar
tool_vpos = [toolbar_pos[1]]
for i in range(1, 10):
    tool_vpos.append(tool_vpos[i - 1] + toolbar_sep + icon_size[1])

class PygameInterface(object):
    """Implements the user interface of the system using pygame."""

    def __init__(self, capture_size, id_enabled, id_list_enabled):
        self.capture_size = capture_size
        self.size = (capture_size[0] + 48, capture_size[1] + 64)
        pygame.display.set_mode(self.size)
        pygame.display.set_caption('eyegrade')
        self.screen = pygame.display.get_surface()
        self.surface_bottom_1 = pygame.Surface((capture_size[0], 32))
        self.surface_bottom_2 = pygame.Surface((capture_size[0], 32))
        self.surface_toolbar = pygame.Surface((self.size[0] - capture_size[0],
                                               self.size[1]))
        self.surface_bottom_1.fill(param_background_color)
        self.surface_toolbar.fill(param_background_color)
        self.normal_font = pygame.font.SysFont(param_font_name,
                                               param_font_size)
        self.toolbar = []
        self.tool_over = None
        self.id_enabled = id_enabled
        self.id_list_enabled = id_list_enabled
        self.last_score = None
        self.statusbar_active = None

    def show_capture(self, image, flip=True):
        pg_img = imageproc.cvimage_to_pygame(image)
        self.screen.blit(pg_img, (0,0))
        if flip:
            pygame.display.flip()

    def update_text(self, text, flip=True):
        self.screen.blit(self.surface_bottom_1, (0, self.capture_size[1]))
        if text is not None:
            self.__render_text(text, (8, 8 + self.capture_size[1]))
        if flip:
            pygame.display.flip()

    def update_status(self, score, flip=True):
        self.last_score = score
        self.__stop_statusbar_timer()
        self.screen.blit(self.surface_bottom_2, (0, self.capture_size[1] + 32))
        if score is not None:
            correct, incorrect, blank, indet, score, max_score = score
            if correct is not None and incorrect is not None and \
                    blank is not None:
                vpos = self.capture_size[1] + 40
                self.screen.blit(correct_icon, (8, vpos))
                self.screen.blit(incorrect_icon, (72, vpos))
                self.screen.blit(unanswered_icon, (136, vpos))
                vpos = self.capture_size[1] + 60 - self.normal_font.get_height()
                self.__render_text(str(correct), (36, vpos))
                self.__render_text(str(incorrect), (100, vpos))
                self.__render_text(str(blank), (164, vpos))
                if score is not None and max_score is not None:
                    text = 'Score: %.2f / %.2f'%(score, max_score)
                    self.__render_text(text, (210, vpos))
        if flip:
            pygame.display.flip()

    def set_statusbar_message(self, text, flip=True):
        self.screen.blit(self.surface_bottom_2, (0, self.capture_size[1] + 32))
        self.__render_text(text, (8, self.capture_size[1] + 60 - \
                                      self.normal_font.get_height()))
        if flip:
            pygame.display.flip()
        self.__start_statusbar_timer()
        self.statusbar_active = True

    def cancel_statusbar_message(self, flip=True):
        if self.statusbar_active:
            self.update_status(self.last_score, flip)
            self.statusbar_active = False

    def set_search_toolbar(self, flip=True):
        self.toolbar = []
        self.tool_over = None
        self.toolbar.append(((snapshot_icon_normal, snapshot_icon_high),
                             event_snapshot, snapshot_help))
        self.toolbar.append((None, None))
        self.toolbar.append(((exit_icon_normal, exit_icon_high),
                             event_quit, exit_help))
        self.draw_toolbar(flip)

    def set_review_toolbar(self, flip=True):
        self.toolbar = []
        self.tool_over = None
        self.toolbar.append(((save_icon_normal, save_icon_high),
                             event_save, save_help))
        if self.id_enabled:
            if self.id_list_enabled:
                self.toolbar.append(((next_id_icon_normal, next_id_icon_high),
                                     event_next_id, next_id_help))
            self.toolbar.append(((edit_id_icon_normal, edit_id_icon_high),
                                 event_manual_id, edit_id_help))
        self.toolbar.append(((discard_icon_normal, discard_icon_high),
                             event_cancel_frame, discard_help))
        self.toolbar.append((None, None))
        self.toolbar.append(((exit_icon_normal, exit_icon_high),
                             event_quit, exit_help))
        self.draw_toolbar(flip)

    def draw_toolbar(self, flip):
        self.screen.blit(self.surface_toolbar, (self.capture_size[0], 0))
        for i, tool in enumerate(self.toolbar):
            if tool[0] is not None:
                self.draw_icon(tool[0][0], i, False)
        if flip:
            pygame.display.flip()

    def flip_display(self):
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

    def draw_icon(self, icon, index, flip=True):
        pos = (toolbar_pos[0] + self.capture_size[0], tool_vpos[index])
        self.screen.blit(icon, pos)
        if flip:
            pygame.display.flip()

    def __start_statusbar_timer(self):
        pygame.time.set_timer(statusbar_event_id, statusbar_display_time)

    def __stop_statusbar_timer(self):
        pygame.time.set_timer(statusbar_event_id, 0)

    def __render_text(self, text, pos):
        surface = self.normal_font.render(text, True, param_font_color,
                                          param_background_color)
        self.screen.blit(surface, pos)


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
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.__process_mouse_click(event)
        elif event.type == pygame.MOUSEMOTION:
            self.__process_mouse_motion(event)
        elif event.type == statusbar_event_id:
            self.cancel_statusbar_message()
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
            return self.__process_mouse_click(event)
        elif event.type == pygame.MOUSEMOTION:
            self.__process_mouse_motion(event)
        elif event.type == statusbar_event_id:
            self.cancel_statusbar_message()
        return (None, None)

    def __process_mouse_motion(self, event):
        tool_pos = self.__tool_at_position(event.pos)
        if self.tool_over is not None and tool_pos != self.tool_over:
            self.cancel_statusbar_message(False)
            self.draw_icon(self.toolbar[self.tool_over][0][0], self.tool_over)
            self.tool_over = None
        if self.tool_over is None and tool_pos is not None:
            self.set_statusbar_message(self.toolbar[tool_pos][2], False)
            self.draw_icon(self.toolbar[tool_pos][0][1], tool_pos)
            self.tool_over = tool_pos

    def __process_mouse_click(self, event):
        if event.pos[0] < self.capture_size[0] and \
                event.pos[1] < self.capture_size[1]:
            return (event_click, event.pos)
        else:
            tool_pos = self.__tool_at_position(event.pos)
            if tool_pos is not None:
                return (self.toolbar[tool_pos][1], None)
            else:
                return (None, None)

    def __tool_at_position(self, pos):
        # Normalize to toolbar coordinates
        pos = (pos[0] - self.capture_size[0], pos[1])
        if pos[0] >= toolbar_pos[0] and \
                pos[0] <= toolbar_pos[0] + icon_size[0] and \
                pos[1] >= toolbar_pos[1]:
            div, mod = divmod(pos[1] - toolbar_pos[1],
                              toolbar_sep + icon_size[1])
            if mod < icon_size[1] and div < len(self.toolbar) and \
                    self.toolbar[div][0] is not None:
                return div
        return None
