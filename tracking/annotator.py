import cv2
from enum import Enum

from tracking.data_processor import DataProcessor
from tracking.ui_renderer import UIRenderer


class State(Enum):
    play = 1
    pause = 2

class TrackingAnnotator:
    def __init__(self, clip_paths, output_path, temp_path=None, canvas_size=(1920,1080)):
        self.data = DataProcessor(clip_paths)
        self.ui_renderer = UIRenderer('Manual Tracks Editing', canvas_size)
        self.output_path = output_path
        self.temp_path = temp_path
        self.state = State.play

        print('Data loaded. Total frames: {}'.format(len(self.data)))

    def run(self):
        ''' Main loop '''
        self.ui_renderer.create_window(self.mouse_handler, self.trackbar_handler,
                                       self.data.num_frames, self.ui_renderer.canvas_size)
        running = True

        while True:
            if running == False:        # Closing window -> termination
                break
            if cv2.waitKey(30) == 27:   # Esc -> termination
                break

            running = self._process_frame()

        cv2.destroyAllWindows()
        del self.ui_renderer

    def _process_frame(self):
        # Render current frame:
        self.ui_renderer.render(self._make_rendering_data())

        # Handle keyboard events:
        while True:
            if self.ui_renderer.is_window_visible() == False:
                self.save()
                self.ui_renderer.set_saved_counter(30)
                return False

            key = cv2.waitKey(20)

            if key == 27: # Esc -> termination
                return False
            elif key == 32:  # Space -> forward
                frame_id = self.data.next_frame()
                self.state = State.pause
                self.ui_renderer.set_trackbar(frame_id, self.data.num_frames)
                self.ui_renderer.set_saved_counter()
                break
            elif key == 8:  # Backspace -> backward
                frame_id = self.data.prev_frame()
                self.state = State.pause
                self.ui_renderer.set_trackbar(frame_id, self.data.num_frames)
                self.ui_renderer.set_saved_counter()
                break
            elif key == 13:  # Enter -> pause\resume processing
                if self.state == State.play:
                    self.state = State.pause
                elif self.state == State.pause:
                    self.state = State.play
                self.ui_renderer.set_saved_counter()
                break
            elif key == ord('['):    # [ -> prev clip
                self.data.prev_clip()
                self.ui_renderer.set_trackbar(self.data.frame_pos, self.data.num_frames)
                self.ui_renderer.set_saved_counter()
                break
            elif key == ord(']'):    # ] -> next clip
                self.data.next_clip()
                self.ui_renderer.set_trackbar(self.data.frame_pos, self.data.num_frames)
                self.ui_renderer.set_saved_counter()
                break
            elif key == ord('s'):   # save -> clean text
                self.save()
                self.ui_renderer.set_saved_counter(30)
                print('Data has been saved to {}!'.format(self.output_path))
                break
            elif key == ord('f'):    # set frame state to false
                self.data.get_clip().set_frame_anno(key='label', value=False)
                self.data.get_clip().set_frame_anno(key='pos', value=None)  # unset a player position
                break
            elif key == ord('t'):    # set frame state to true
                self.data.get_clip().set_frame_anno(key='label', value=True)
                break

            # Play:
            if self.state == State.play:
                frame_id = self.data.next_frame()
                self.ui_renderer.set_trackbar(frame_id, self.data.num_frames)
                break

        return True

    def _make_rendering_data(self):
        cur_clip_id = self.data.current_clip_id
        clip = self.data.get_clip()
        data = {
            'image': self.data.get_frame(),
            'frame_id': self.data.frame_pos,
            'num_frames': self.data.num_frames,
            'clip_id': self.data.current_clip_id,
            'num_clips': len(self.data),
            'frame_label': clip.get_frame_anno()['label'],
            'player_pos': clip.get_frame_anno()['pos'],
            'cur_clip_name': clip.name,
            'prev_clip_name': self.data.get_clip(cur_clip_id - 1).name if cur_clip_id > 0 else 'None',
            'next_clip_name': self.data.get_clip(cur_clip_id + 1).name if cur_clip_id + 1 < len(self.data) else 'None'
        }

        return data

    def save(self, dst_path=None):
        if dst_path is None:
            dst_path = self.output_path
        if self.data:
            self.data.save(dst_path)

    def load(self, path):
        assert self.data is not None
        self.data.load(path)

    def restore(self, path):
        raise NotImplementedError
        # assert self.data is not None
        # self.data.restore(path)


    ''' Handler functions '''
    def mouse_handler(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONUP:
            self.mouse_left_click_handler(x, y)
        elif event == cv2.EVENT_RBUTTONUP:
            self.mouse_right_click_handler(x, y)

    def mouse_left_click_handler(self, x, y):
        '''
        Determines the layer by click coordinates and performs specific actions on this layer
        '''
        if self.check_hit(x, y, self.ui_renderer.frame_layer_pos):
            # Set a new player position:
            if self.data.get_clip().get_frame_anno()['label']:
                x, y = self.normalize_coords(x, y, self.ui_renderer.frame_layer_pos)
                self.data.get_clip().set_frame_anno(key='pos', value=(x,y))

        self.ui_renderer.render(self._make_rendering_data())

    def mouse_right_click_handler(self, x, y):
        if self.check_hit(x, y, self.ui_renderer.frame_layer_pos):
            # Unset a player position:
            self.data.get_clip().set_frame_anno(key='pos', value=None)

        self.ui_renderer.render(self._make_rendering_data())

    def trackbar_handler(self, value):
        # self.data.save_frame(self.temp_path)
        frame_id = value - 1
        self.data.set_current_frame_id(frame_id)
        self.ui_renderer.render(self._make_rendering_data())

    @staticmethod
    def check_hit(x, y, box):
        x1, y1, x2, y2 = box[0], box[1], box[0] + box[2], box[1] + box[3]
        return not (x < x1 or x > x2 or y < y1 or y > y2)

    @staticmethod
    def normalize_coords(x, y, box):
        return (x - box[0]) / box[2], (y - box[1]) / box[3]
