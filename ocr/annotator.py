import cv2

from ocr.data_processor import DataProcessor
from ocr.ui_renderer import UIRenderer


class OCRTimerAnnotator:
    def __init__(self, img_dir, preds_path, output_path, canvas_size=(1920,1080), temp_path=None):
        self.data = DataProcessor(img_dir, preds_path)
        window_name = 'Manual OCR Annotating'
        self.ui_renderer = UIRenderer(window_name, canvas_size)
        self.output_path = output_path
        self.temp_path = temp_path
        self.prev_text = ''

        print('Data loaded. Total frames: {}'.format(len(self.data)))

    def run(self):
        ''' Main loop '''
        num_data = len(self.data)
        self.ui_renderer.create_window(self.mouse_handler, self.trackbar_handler, num_data, window_size=(600, 600))
        self.ui_renderer.text_layer.select_cell(0)
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
                self.data.save_frame(self.temp_path)
                return False

            key = cv2.waitKey(10)

            if key == 27: # Esc -> termination
                self.data.save_frame(self.temp_path)
                return False
            elif key == 32:  # Space -> forward
                self.prev_text = self.data.get_text()
                self.data.save_frame(self.temp_path)
                frame_idx = self.data.next()
                self.ui_renderer.set_trackbar(frame_idx)
                self.ui_renderer.text_layer.select_cell(0)
                break
            elif key == 8:  # Backspace -> backward
                self.prev_text = self.data.get_text()
                self.data.save_frame(self.temp_path)
                frame_idx = self.data.prev()
                self.ui_renderer.set_trackbar(frame_idx)
                self.ui_renderer.text_layer.select_cell(0)
                break
            elif key == 13:  # Enter -> pause\resume processing
                self.data.clean_text()
                break
            elif key == ord('s'):   # save -> clean text
                self.save()
                print('Data has been saved to {}!'.format(self.output_path))
                self.ui_renderer.render(self.data.get_frame())
                break
            elif key == ord('c'):   # clean
                cell_idx = self.ui_renderer.text_layer.select_cell()
                self.data.remove_char_from_text(pos=cell_idx)
                break
            elif key >= ord('0') and key <= ord('9') or key == ord('.'):
                cell_idx = self.ui_renderer.text_layer.select_cell()
                self.data.set_char_in_text(char=key, pos=cell_idx)
                self.ui_renderer.text_layer.select_cell(change_to='next')
                break
            elif key == ord('['):    # [ -> left
                self.ui_renderer.text_layer.select_cell(change_to='prev')
                break
            elif key == ord(']'):    # ] -> right
                self.ui_renderer.text_layer.select_cell(change_to='next')
                break
            elif key == ord('q'):   # q -> copy first two chars from previous frame
                if len(self.prev_text) > 0:
                    chars = list(self.prev_text)[0:2]
                    for i, char in enumerate(chars):
                        self.data.set_char_in_text(char=ord(char), pos=i)
                    self.ui_renderer.text_layer.select_cell(change_to='next')
                    self.ui_renderer.text_layer.select_cell(change_to='next')
                break
            elif key == ord('e'):   # e -> copy text from previous frame'
                if len(self.prev_text) > 0:
                    self.data.set_text(self.prev_text)
                break

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


    ''' Handler functions '''
    def mouse_handler(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONUP:
            self.mouse_left_click_handler(x, y)
        elif event == cv2.EVENT_RBUTTONUP:
            self.mouse_right_click_handler(x, y)

    def mouse_left_click_handler(self, x, y):
        '''
        Determines the TextEditor cell by click coordinates and
        performs specific actions based on this selection
        '''
        frame = self.data.get_frame()

        # TextEditor layer:
        if self.check_hit(x, y, self.ui_renderer.text_layer_pos):
            x, y = self.normalize_coords(x, y, self.ui_renderer.text_layer_pos)
            h, w = self.ui_renderer.text_layer.canvas.shape[0:2]
            x, y = int(round(x*w)), int(round(y*h))
            cell_idx = self.determine_box_by_coords(x, y, self.ui_renderer.text_layer.cell_boxes)
            self.ui_renderer.text_layer.select_cell(cell_idx)

        self.ui_renderer.render(frame)

    def mouse_right_click_handler(self, x, y):
        pass

    def trackbar_handler(self, value):
        self.data.save_frame(self.temp_path)
        self.data.set_frame_idx(value-1)
        self.ui_renderer.render(self.data.get_frame())

    @staticmethod
    def check_hit(x, y, box):
        x1, y1, x2, y2 = box[0], box[1], box[0] + box[2], box[1] + box[3]
        return not (x < x1 or x > x2 or y < y1 or y > y2)

    @staticmethod
    def normalize_coords(x, y, box):
        return (x - box[0]) / box[2], (y - box[1]) / box[3]

    @staticmethod
    def determine_box_by_coords(x, y, boxes):
        for i, box in enumerate(boxes):
            if x >= box[0] and x < box[2] and y >= box[1] and y < box[3]:
                return i
        return -1
