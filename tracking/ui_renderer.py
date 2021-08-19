import cv2
import numpy as np


class FrameLayer:
    ''' Layer containing the frame image '''
    def __init__(self, size=(1280, 720)):
        self.size = size
        self.canvas = None

    def draw(self, data):
        player_pos = data['player_pos']
        self.canvas = data['image']

        # Draw a new player position on the frame:n
        if player_pos is not None:
            x = int(round(player_pos[0] * self.size[0]))
            y = int(round(player_pos[1] * self.size[1]))
            self.canvas = cv2.circle(self.canvas, (x, y), 7, color=(0, 0, 255), thickness=-1)
            self.canvas = cv2.circle(self.canvas, (x, y), 5, color=(0, 255, 0), thickness=-1)

        return self.canvas

class InfoLayer:
    ''' Layer containing various information about the current clip '''
    def __init__(self, size=(1280, 720)):
        self.canvas = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        self.font = cv2.FONT_HERSHEY_COMPLEX
        self.dh = 30
        self.saved_counter = 0

    def draw(self, data) -> np.array:
        frame_id = data['frame_id']
        num_frames = data['num_frames']
        cur_clip_name = data['cur_clip_name']
        prev_clip_name = data['prev_clip_name']
        next_clip_name = data['next_clip_name']
        frame_label  = data['frame_label']
        player_pos = data['player_pos']

        self.canvas.fill(0)

        # Clips name:
        x, y = 50, self.dh
        color = (255, 255, 255)
        text = 'Clip: '
        (text_w, text_h), _ = cv2.getTextSize(text, self.font, 1, 1)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=1, lineType=1, font=self.font)

        x += text_w
        color = (128, 128, 128) if prev_clip_name != 'None' else (128, 128, 180)
        text = '{} -> '.format(prev_clip_name)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=0.75, lineType=2, font=self.font)
        (text_w, text_h), _ = cv2.getTextSize(text, self.font, 0.75, 2)

        x += text_w
        color = (128, 255, 128)
        text = '{}'.format(cur_clip_name)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=1, lineType=2, font=self.font)
        (text_w, text_h), _ = cv2.getTextSize(text, self.font, 1, 2)

        x += text_w
        color = (128, 128, 128) if next_clip_name != 'None' else (128, 128, 180)
        text = ' -> {}'.format(next_clip_name)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=0.75, lineType=2, font=self.font)


        # Frame id:
        x, y = 50, self.dh + 50
        text = 'Frame: '
        color = (255, 255, 255)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=1, lineType=1, font=self.font)
        (text_w, text_h), _ = cv2.getTextSize(text, self.font, 1, 1)

        x += text_w
        text = '{}/{}'.format(frame_id + 1, num_frames)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=1, lineType=2, font=self.font)


        # State:
        x, y = x + 640, self.dh
        text = 'Label: '
        color = (255, 255, 255)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=1, lineType=1, font=self.font)
        (text_w, text_h), _ = cv2.getTextSize(text, self.font, 1, 1)

        if frame_label == True and player_pos is None:
            color = (128, 255, 128)
            text = 'true'
        elif frame_label == True and player_pos is not None:
            color = (255, 128, 128)
            text = 'edited'
        elif frame_label == False:
            color = (128, 128, 255)
            text = 'false'
        else:
            raise NotImplementedError
        UIRenderer.draw_text(self.canvas, text, (x+text_w, y), color, scale=1, lineType=2, font=self.font)


        # Saved:
        if self.saved_counter > 0:
            y = self.dh + 50
            color = (64, 255, 64)
            UIRenderer.draw_text(self.canvas, 'Results saved!', (x, y), color, scale=1, lineType=2, font=self.font)
            self.saved_counter -= 1

        return self.canvas

class UIRenderer:
    '''  Implements a Graphical User Interface '''
    def __init__(self, window_name, canvas_size=(1920, 1080)):
        self.window_name = window_name
        self.canvas_size = canvas_size
        self.info_layer_pos = UIRenderer.calc_pos_on_canvas((0.0, 0, 1.0, 0.1), self.canvas_size)
        self.frame_layer_pos = UIRenderer.calc_pos_on_canvas((0.0, 0.1, 1.0, 0.9), self.canvas_size)
        self.info_layer = InfoLayer(size=(self.canvas_size[0], int(round(self.canvas_size[1]*0.1))))
        self.frame_layer = FrameLayer()

    def create_window(self, mouse_handler, trackbar_handler, count, window_size=(1280, 720)):
        cv2.namedWindow(self.window_name, cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback(self.window_name, mouse_handler)
        cv2.resizeWindow(self.window_name, window_size[0], window_size[1])
        cv2.createTrackbar('frames', self.window_name, 1, count, trackbar_handler)

    def render(self, data: dict) -> None:
        ''' Renders GUI and returns the canvas '''
        if not self.is_window_visible():
            return

        canvas = np.zeros((self.canvas_size[1], self.canvas_size[0], 3), dtype=np.uint8)
        frame_canvas = self.frame_layer.draw(data)
        info_canvas = self.info_layer.draw(data)
        UIRenderer.insert_into_canvas(canvas, frame_canvas, self.frame_layer_pos)
        UIRenderer.insert_into_canvas(canvas, info_canvas, self.info_layer_pos)
        cv2.imshow(self.window_name, canvas)

    def is_window_visible(self):
        if self.window_name is None:
            print ('No windows have been created yet!')
            return False

        if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) > 0:
            return True
        else:
            return False

    def set_trackbar(self, value, count=None):
        if count is not None:
            cv2.setTrackbarMax('frames', self.window_name, count)
        cv2.setTrackbarPos('frames', self.window_name, value+1)

    def set_saved_counter(self, counter=0):
        assert counter >= 0
        self.info_layer.saved_counter = counter


    @staticmethod
    def calc_pos_on_canvas(box, canvas_size):
        return (
            int(round(box[0] * canvas_size[0])),   # x
            int(round(box[1] * canvas_size[1])),   # y
            int(round(box[2] * canvas_size[0])),   # w
            int(round(box[3] * canvas_size[1]))    # h
        )

    @staticmethod
    def insert_into_canvas(canvas, img, pos):
        x1,y1,w,h = pos[:]
        x2,y2 = x1+w, y1+h
        if img.shape[1] != w or img.shape[0] != h:
            inter = cv2.INTER_AREA if img.shape[1] > w else cv2.INTER_CUBIC
            img = cv2.resize(img, (w,h), interpolation=inter)
        canvas[y1:y2, x1:x2, :] = img

    @staticmethod
    def draw_text(img, text, pos, color=(255, 255, 255), scale=0.75, lineType=1,
                  font=cv2.FONT_HERSHEY_COMPLEX_SMALL):
        cv2.putText(img, text, pos, font, scale, color, lineType)