import cv2
import numpy as np


class FrameLayer:
    ''' Layer containing the main frame image and the projected PoI '''
    def __init__(self, size=(600, 600), align_by_width=True):
        self.size = size
        self.align_by_width = True

    def draw(self, frame=None):
        if frame is not None:
            assert frame.img is not None
            img_h, img_w = frame.img.shape[0:2]
            H, W = self.size[0], self.size[1]

            if self.align_by_width:
                if img_w != W:
                    inter = cv2.INTER_AREA if img_w > W else cv2.INTER_CUBIC
                    r = W/img_w
                    new_w = W
                    new_h = int(round(img_h*r))
                    frame.img = cv2.resize(frame.img, (new_w, new_h), interpolation=inter)
            else:
                raise NotImplementedError

            img_h, img_w = frame.img.shape[0:2]
            self.canvas = np.zeros((H, W, 3), dtype=np.uint8)
            dx = int(round((W - img_w) * 0.5))
            dy = int(round((H - img_h) * 0.5))
            if dx+img_w > W:
                dx = (dx+img_w) - W
            if dy+img_h > H:
                dy = (dy+img_h) - H
            self.canvas[dy:dy+img_h, dx:dx+img_w, :] = frame.img

        return self.canvas

class TextEditLayer:
    ''' Layer allows to display, type and edit text data '''

    def __init__(self, size=(600, 600), num_cells=4):
        self.canvas = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        self.font = cv2.FONT_HERSHEY_COMPLEX
        self.text_color = (0,255,0)
        self.highlighted_text_color = (255, 0, 0)
        self.cell_width = 100
        self.cell_height = 150
        self.cell_margin = 25
        self.origin_x = 50
        self.origin_y = 25
        self.num_cells = num_cells
        self.cell_boxes = []
        self.selected_cell_idx = -1

        # Calculate the coordinates of cells:
        x1, y1 = self.origin_x, self.origin_y
        x2, y2 = x1-self.cell_margin, y1 + self.cell_height
        for i in range(num_cells):
            x1, y1 = x2 + self.cell_margin, self.origin_y
            x2, y2 = x1 + self.cell_width, y1 + self.cell_height
            self.cell_boxes.append((x1,y1,x2,y2))

    def draw(self, text=None):
        self.canvas.fill(0)
        for i, (x1,y1,x2,y2) in enumerate(self.cell_boxes):
            self.canvas = cv2.rectangle(self.canvas, (x1, y1), (x2, y2), (255, 255, 255), -1)
            if self.selected_cell_idx == i:
                self.canvas = cv2.rectangle(self.canvas, (x1-1, y1-1), (x2+2, y2+2), (255, 0, 0), 7)

        if text is not None:
            chars = list(text)
            for i in range(len(chars)):
                if i >= self.num_cells:
                    break
                color = self.text_color
                if self.selected_cell_idx == i:
                    color= self.highlighted_text_color
                x, y = self.cell_boxes[i][0]+10, self.cell_boxes[i][3]-20
                UIRenderer.draw_text(self.canvas, chars[i], (x, y), color, scale=4, font=self.font)

        return self.canvas

    def select_cell(self, idx=None, change_to=None):
        if idx is not None:
            self.selected_cell_idx = idx
        if change_to is not None:
            if change_to == 'next':
                self.selected_cell_idx += 1
            elif change_to == 'prev':
                self.selected_cell_idx -= 1
        if self.selected_cell_idx >= self.num_cells:
            self.selected_cell_idx = 0
        elif self.selected_cell_idx < 0:
            self.selected_cell_idx = self.num_cells-1

        return self.selected_cell_idx

class UIRenderer:
    '''  Implements a Graphical User Interface '''
    def __init__(self, window_name, canvas_size=(1920, 1080)):
        self.window_name = window_name
        self.canvas_size = canvas_size
        self.frame_layer_pos = UIRenderer.calc_pos_on_canvas((0.3, 0.0, 0.40, 0.40), self.canvas_size)
        self.text_layer_pos = UIRenderer.calc_pos_on_canvas((0.25, 0.4, 0.50, 0.50), self.canvas_size)
        self.frame_layer = FrameLayer()
        self.text_layer = TextEditLayer(size=(600,600))

    def create_window(self, mouse_handler, trackbar_handler, num_data, window_size=(1280,720)):
        cv2.namedWindow(self.window_name, cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback(self.window_name, mouse_handler)
        cv2.resizeWindow(self.window_name, window_size[0], window_size[1])
        cv2.createTrackbar('frames', self.window_name, 1, num_data, trackbar_handler)

    def render(self, frame=None):
        ''' Renders GUI and returns the main canvas '''
        if self.window_name is None:
            print ('No windows have been created yet!')
            return

        canvas = np.zeros((self.canvas_size[1], self.canvas_size[0], 3), dtype=np.uint8)
        frame_canvas = self.frame_layer.draw(frame)
        text_canvas = self.text_layer.draw(frame.text)
        UIRenderer.insert_into_canvas(canvas, frame_canvas, self.frame_layer_pos)
        UIRenderer.insert_into_canvas(canvas, text_canvas, self.text_layer_pos)
        cv2.imshow(self.window_name, canvas)

    def is_window_visible(self):
        if self.window_name is None:
            print ('No windows have been created yet!')
            return False

        if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) > 0:
            return True
        else:
            return False

    def set_trackbar(self, value):
        cv2.setTrackbarPos('frames', self.window_name, value+1)

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
    def draw_text(img, text, pos, color=(255, 255, 255), scale=0.75, lineType=cv2.LINE_AA,
                  font=cv2.FONT_HERSHEY_COMPLEX_SMALL):
        cv2.putText(img, text, pos, font, scale, color, lineType)