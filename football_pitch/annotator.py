import cv2
import numpy as np
from timeit import default_timer as timer

from football_pitch.data_processor import DataProcessor
from football_pitch.ui_renderer import UIRenderer
from ui.confirmation import display_confirmation


class FootballPitchAnnotator(object):
    """UI for the (semi)manual points mapping"""

    class TimeCounter():
        def __init__(self):
            self.start_time = timer()

        def measure(self):
            if self.start_time is None:
                return 0
            end_time = timer()
            elapsed = (end_time - self.start_time)
            self.start_time = end_time
            return elapsed

        def pause(self):
            self.start_time = None

        def resume(self):
            self.start_time = timer()

    def __init__(self,
                 img_dir,
                 preds_path,
                 output_path,
                 court_img_path,
                 court_mask_path,
                 court_poi_path,
                 court_size,
                 canvas_size=(1920,1080),
                 num_points=33,
                 ignore_points=None,
                 temp_path=None):
        self.data = DataProcessor(img_dir, preds_path, court_mask_path, court_poi_path,
                                  court_size, num_points, ignore_points)
        window_name = 'Manual Mapping AI'# os.path.basename(img_dir)
        court_img = cv2.imread(court_img_path, cv2.IMREAD_COLOR)
        court_poi = self.data.court_poi[0]
        self.ui_renderer = UIRenderer(window_name, court_img, court_poi, canvas_size)
        self.output_path = output_path
        self.temp_path = temp_path
        self.paused = False
        self.time_counter = FootballPitchAnnotator.TimeCounter()

        print('Data loaded. Total frames: {}'.format(len(self.data)))

    def run(self):
        ''' Main loop '''
        num_data = len(self.data)
        self.ui_renderer.create_window(self.mouse_handler, self.trackbar_handler, num_data)
        self.ui_renderer.label.num_frames = num_data
        self.ui_renderer.label.frame_idx = 0
        running = True

        while True:
            if running == False:        # Closing window -> termination
                break
            if cv2.waitKey(30) == 27:   # Esc -> termination
                break

            running = self.process_frame()

        cv2.destroyAllWindows()
        del self.ui_renderer

    def process_frame(self):
        self.ui_renderer.render(self.data.get_frame())

        while True:
            if self.ui_renderer.is_window_visible() == False:
                self.data.add_elapsed_time(self.time_counter.measure())
                self.data.save_frame(self.temp_path)
                return False

            key = cv2.waitKey(10)

            if key == 27: # Esc -> termination
                if not self.paused:
                    self.data.add_elapsed_time(self.time_counter.measure())
                    self.data.save_frame(self.temp_path)
                return False
            elif key == 32:  # Space -> forward
                if not self.paused:
                    self.data.add_elapsed_time(self.time_counter.measure())
                    self.data.save_frame(self.temp_path)
                self.ui_renderer.label.frame_idx = self.data.next()
                self.ui_renderer.select_point(-1)
                self.ui_renderer.set_trackbar(self.ui_renderer.label.frame_idx)
                break
            elif key == 8:  # Backspace -> backward
                if not self.paused:
                    self.data.add_elapsed_time(self.time_counter.measure())
                    self.data.save_frame(self.temp_path)
                self.ui_renderer.label.frame_idx = self.data.prev()
                self.ui_renderer.select_point(-1)
                self.ui_renderer.set_trackbar(self.ui_renderer.label.frame_idx)
                break
            elif key == 13:  # Enter -> pause\resume processing
                paused = self.flip_state()
                if paused:
                    self.data.add_elapsed_time(self.time_counter.measure())
                    self.data.save_frame(self.temp_path)
                    self.time_counter.pause()
                else:
                    self.time_counter.resume()
                self.ui_renderer.label.paused = paused
                self.ui_renderer.render(self.data.get_frame())
            elif key == ord('v'):
                self.ui_renderer.change_blending_alpha()
                self.ui_renderer.render(self.data.get_frame())
            elif key == ord('z'):   # undo
                self.data.undo_last()
                self.ui_renderer.select_point(-1)
                self.ui_renderer.render(self.data.get_frame())
            elif key == ord('s'):   # save
                self.save()
                print('Data has been saved to {}!'.format(self.output_path))
                self.ui_renderer.label.saved = True
                self.ui_renderer.render(self.data.get_frame())
                self.ui_renderer.label.saved = False
            elif key == ord('p'):   # change point brush
                self.ui_renderer.set_poi_brush()
                self.ui_renderer.render(self.data.get_frame())
            elif key == ord('c'):   # clear the points
                if display_confirmation('Clear Confirmation',
                                        'Clear the Points of Interest? (y/n)'):
                    self.data.clear_poi()
                    self.ui_renderer.render(self.data.get_frame())
            elif key == ord('1'):
                point_idx = self.data.get_prev_point_idx(self.ui_renderer.select_point())
                self.data.set_point_state(point_idx, hot=True)
                self.ui_renderer.select_point(point_idx)
                self.ui_renderer.render(self.data.get_frame())
            elif key == ord('2'):
                point_idx = self.data.get_next_point_idx(self.ui_renderer.select_point())
                self.data.set_point_state(point_idx, hot=True)
                self.ui_renderer.select_point(point_idx)
                self.ui_renderer.render(self.data.get_frame())

        return True

    def save(self, dst_path=None):
        if dst_path is None:
            dst_path = self.output_path
        if self.data:
            self.data.save(dst_path)

    def load(self, path):
        assert self.data is not None
        self.data.load(path)

    def restore(self, path):
        assert self.data is not None
        self.data.restore(path)

    def flip_state(self):
        self.paused = not self.paused
        return self.paused

    ''' Handler functions '''
    def mouse_handler(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONUP:
            self.mouse_left_click_handler(x, y)
        elif event == cv2.EVENT_RBUTTONUP:
            self.mouse_right_click_handler(x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            self.mouse_move_handler(x, y)
        elif event == cv2.EVENT_LBUTTONDBLCLK:
            self.mouse_left_double_click_handler(x, y)

    def mouse_left_click_handler(self, x, y):
        '''
        Determines the subcanvas by click coordinates and
        performs specific actions based on this selection
        '''
        frame = self.data.get_frame()

        # Frame layer:
        if self.check_hit(x, y, self.ui_renderer.frame_layer_pos):
            pos = self.ui_renderer.frame_layer_pos
            x, y = self.normalize_coords(x, y, pos)
            point_idx = self.determine_point_by_coords(x, y, frame.poi, pos[2:4], threshold=0.004)
            selected_point_idx = self.ui_renderer.select_point()

            # Mark the clicked point as selected:
            if point_idx > -1 and selected_point_idx != point_idx and \
                    self.data.is_point_hot(point_idx):
                self.ui_renderer.select_point(point_idx)
            # Or change the position of the previously selected point:
            elif selected_point_idx > -1:
                self.data.set_point_coords(selected_point_idx, (x,y))
                # Resume:
                if self.paused:
                    self.time_counter.resume()
                    self.ui_renderer.label.paused = self.flip_state()

        # Court layer:
        elif self.check_hit(x, y, self.ui_renderer.court_layer_pos):
            pos = self.ui_renderer.court_layer_pos
            x, y = self.normalize_coords(x, y, pos)
            point_idx = self.determine_point_by_coords(x, y, self.data.court_poi[0], pos[2:4], threshold=0.009)
            selected_point_idx = self.ui_renderer.select_point()

            # Mark the clicked point as selected:
            if point_idx > -1 and selected_point_idx != point_idx and \
                    self.data.is_point_hot(point_idx):
                self.ui_renderer.select_point(point_idx)

        self.ui_renderer.render(frame)

    def mouse_right_click_handler(self, x, y):
        frame = self.data.get_frame()

        # Frame layer:
        if self.check_hit(x, y, self.ui_renderer.frame_layer_pos):
            if self.ui_renderer.select_point() > -1:
                # Remove selection:
                self.ui_renderer.select_point(-1)
            else:
                pos = self.ui_renderer.frame_layer_pos
                x, y = self.normalize_coords(x, y, pos)
                point_idx = self.determine_point_by_coords(x, y, frame.poi, pos[2:4], threshold=0.004)

                if point_idx > -1 and self.data.is_point_hot(point_idx):
                    # Disable the hot point:
                    self.data.set_point_state(point_idx, False)
                else:
                    # Enable the projected point:
                    point_idx = self.determine_point_by_coords(x, y, frame.proj_poi, pos[2:4], threshold=0.004)
                    if point_idx > -1 and not self.data.is_point_hot(point_idx):
                        self.data.set_point_state(point_idx, True)
                        self.ui_renderer.select_point(point_idx)

        # Court layer:
        elif self.check_hit(x, y, self.ui_renderer.court_layer_pos):
            pos = self.ui_renderer.court_layer_pos
            x, y = self.normalize_coords(x, y, pos)
            point_idx = self.determine_point_by_coords(x, y, self.data.court_poi[0], pos[2:4], threshold=0.009)

            if point_idx > -1:
                if self.data.is_point_hot(point_idx):
                    if self.ui_renderer.select_point() > -1:
                        # Remove selection:
                        self.ui_renderer.select_point(-1)
                    else:
                        # Disable the hot point:
                        self.data.set_point_state(point_idx, False)
                else:
                    # Enable the hot point:
                    self.data.set_point_state(point_idx, True)
                    self.ui_renderer.select_point(point_idx)
            else:
                # Remove selection:
                self.ui_renderer.select_point(-1)

        self.ui_renderer.render(frame)

    def mouse_left_double_click_handler(self, x, y):
        pass

    def mouse_move_handler(self, x, y):
        pass

    def trackbar_handler(self, value):
        if not self.paused:
            self.data.add_elapsed_time(self.time_counter.measure())
            self.data.save_frame(self.temp_path)
        self.ui_renderer.label.frame_idx = self.data.set_frame_idx(value-1)
        self.ui_renderer.select_point(-1)
        self.ui_renderer.render(self.data.get_frame())

    @staticmethod
    def check_hit(x, y, box):
        x1, y1, x2, y2 = box[0], box[1], box[0] + box[2], box[1] + box[3]
        return not(x < x1 or x > x2 or y < y1 or y > y2)

    @staticmethod
    def normalize_coords(x, y, box):
        return (x - box[0]) / box[2], (y - box[1]) / box[3]

    @staticmethod
    def determine_point_by_coords(x, y, poi, size, threshold=0.004):
        if poi is None:
            return -1

        max_v = max(size[0], size[1])
        rx, ry = size[0] / max_v, size[1] / max_v
        dists = [np.linalg.norm(((px - x)*rx, (py-y)*ry)) for px,py in poi]
        min_dist = min(dists)
        if min_dist < threshold:
            return dists.index(min_dist)
        else:
            return -1