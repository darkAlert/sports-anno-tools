import cv2
import numpy as np
from enum import Enum


class PoIBrush(Enum):
    NORMAL = 1
    NORMAL_WO_PROJ = 2
    BIG = 3
    BIG_WO_PROJ = 4

    @staticmethod
    def get_next_brush(brush):
        if brush == PoIBrush.NORMAL:
            brush = PoIBrush.NORMAL_WO_PROJ
        elif brush == PoIBrush.NORMAL_WO_PROJ:
            brush = PoIBrush.BIG
        elif brush == PoIBrush.BIG:
            brush = PoIBrush.BIG_WO_PROJ
        elif brush == PoIBrush.BIG_WO_PROJ:
            brush = PoIBrush.NORMAL

        return brush


class FrameLayer:
    ''' Layer containing the main frame image and the projected PoI '''

    def __init__(self):
        self.canvas = None
        self.blend_alpha = 0.25

    def draw(self, frame=None, selected_pt_idx=-1, poi_brush=PoIBrush.NORMAL, show_poi_names=False):
        if frame is not None:
            assert frame.img is not None
            self.canvas = np.copy(frame.img)
            h, w = self.canvas.shape[0:2]

            # Overlay the projected court image onto the frame image:
            if frame.proj_court is not None:
                self.canvas = UIRenderer.overlay(self.canvas, frame.proj_court, self.blend_alpha)

            # Draw the projected PoI:
            if frame.proj_poi is not None \
                    and any(poi_brush == b for b in [PoIBrush.NORMAL, PoIBrush.BIG]):
                for i, (pt, hot) in enumerate(zip(frame.proj_poi, frame.hot_poi)):
                    if hot:
                        continue
                    if poi_brush == PoIBrush.NORMAL:
                        r_outer = int(round(w * 0.003))
                        color = (0, 200, 250)
                        thickness = 1
                    elif poi_brush == PoIBrush.BIG:
                        r_outer = int(round(w * 0.002))
                        color = (0, 200, 250)
                        thickness = -1
                    else:
                        raise NotImplementedError
                    x, y = int(round(pt[0] * w)), int(round(pt[1] * h))

                    self.canvas = cv2.circle(self.canvas, (x, y), r_outer, color,
                                             thickness=thickness, lineType=cv2.LINE_AA)

            # Draw the PoI:
            if frame.poi is not None:
                for i, (pt, hot) in enumerate(zip(frame.poi, frame.hot_poi)):
                    if hot == False:
                        continue
                    x, y = int(round(pt[0] * w)), int(round(pt[1] * h))

                    if poi_brush == PoIBrush.NORMAL or poi_brush == PoIBrush.NORMAL_WO_PROJ:
                        r_outer = int(round(w * 0.005))
                        r_inner = int(round(w * 0.001))
                        color = (0, 0, 255)
                        if i == selected_pt_idx:
                            color = (255, 0, 255)
                            r_outer += int(round(r_outer * 0.20))
                        self.canvas = cv2.circle(self.canvas, (x, y), r_outer, color,
                                                 thickness=2, lineType=cv2.LINE_AA)
                        self.canvas = cv2.circle(self.canvas, (x, y), r_inner, color=(0, 255, 0),
                                                 thickness=-1, lineType=cv2.LINE_AA)
                    elif poi_brush == PoIBrush.BIG or poi_brush == PoIBrush.BIG_WO_PROJ:
                        r_outer = int(round(w * 0.005))
                        r_inner = int(round(w * 0.002))
                        color = (0, 0, 255)
                        if i == selected_pt_idx:
                            color = (255, 0, 255)
                            r_outer += int(round(r_outer * 0.20))
                        self.canvas = cv2.circle(self.canvas, (x, y), r_outer, color=color,
                                                 thickness=-1, lineType=cv2.LINE_AA)
                        self.canvas = cv2.circle(self.canvas, (x, y), r_inner, color=(0, 255, 0),
                                                 thickness=-1, lineType=cv2.LINE_AA)

                    if show_poi_names:
                        UIRenderer.draw_text(self.canvas, str(i), (x, y), (255, 0, 255))


        return self.canvas


class CourtLayer:
    ''' Layer containing the court image and the court PoI '''

    def __init__(self, court_img, court_poi, canvas_size):
        self.court_img_orig = court_img
        self.court_poi = court_poi
        w, h = canvas_size[:]
        inter = cv2.INTER_AREA if self.court_img_orig.shape[1] > w else cv2.INTER_CUBIC
        self.court_img = cv2.resize(self.court_img_orig, (w, h), interpolation=inter)
        self.canvas = np.copy(self.court_img)

    def draw(self, hot_poi=None, selected_pt_idx=-1, show_poi_names=False):
        if hot_poi is not None:
            self.canvas = np.copy(self.court_img)
            h, w = self.court_img.shape[0:2]
            radius = int(round(w * 0.005))

            for i, (pt, hot) in enumerate(zip(self.court_poi, hot_poi)):
                x, y = int(round(pt[0] * w)), int(round(pt[1] * h))
                color = (0, 255, 0) if hot else (128, 128, 128)
                r = radius
                if selected_pt_idx == i:
                    color = (255, 0, 255)
                    r += int(round(radius * 0.3))
                self.canvas = cv2.circle(self.canvas, (x, y), r, color, lineType=cv2.LINE_AA, thickness=-1)
                if show_poi_names:
                    UIRenderer.draw_text(self.canvas, str(i), (x, y), (255, 0, 255))

        return self.canvas


class Label:
    def __init__(self):
        self.num_frames = -1
        self.frame_idx = -1
        self.point_idx = -1
        self.paused = False
        self.saved = False
        self.reproj_error = 0


class InfoLayer:
    ''' Layer containing various information about the current frame '''

    def __init__(self, size=(1280, 720)):
        self.canvas = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        self.font = cv2.FONT_HERSHEY_COMPLEX

    def draw(self, label=None):
        if label is None:
            return self.canvas

        self.canvas.fill(0)
        dh = 75

        # State:
        text = 'State:'
        x, y = 50, dh
        color = (255, 255, 255)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=2, lineType=2, font=self.font)
        x = x + 250
        if not label.paused:
            color = (0, 128, 0)
            text = 'RAN'
        else:
            color = (0, 0, 128)
            text = 'PAUSED'
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=1.8, lineType=3, font=self.font)

        # The number of frames:
        text = 'Frame: {}/{}'.format(label.frame_idx + 1, label.num_frames)
        x, y = 50, y + dh
        color = (255, 255, 255)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=2, lineType=2, font=self.font)

        # Point number:
        text = 'Point: {}'.format(label.point_idx if label.point_idx > -1 else '-')
        x, y = 50, y + dh
        color = (255, 255, 255)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=2, lineType=2, font=self.font)

        # Reprojection error:
        text = 'Error: {:8f}'.format(label.reproj_error)
        x, y = 50, y + dh
        color = (255, 255, 255)
        UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=2, lineType=2, font=self.font)

        # Saved:
        if label.saved:
            text = 'Data saved!'
            x, y = 50, y + dh * 2
            color = (64, 64, 255)
            UIRenderer.draw_text(self.canvas, text, (x, y), color, scale=2, lineType=2, font=self.font)

        return self.canvas


class UIRenderer:
    '''  Implements a Graphical User Interface '''

    def __init__(self, window_name, court_img, court_poi, canvas_size=(1920, 1080)):
        self.window_name = window_name
        self.canvas_size = canvas_size
        self.frame_layer_pos = UIRenderer.calc_pos_on_canvas((0.15, 0.3, 0.7, 0.7), self.canvas_size)
        self.court_layer_pos = UIRenderer.calc_pos_on_canvas((0.35, 0, 0.3, 0.3), self.canvas_size)
        self.info_layer_pos = UIRenderer.calc_pos_on_canvas((0.65, 0, 0.3, 0.3), self.canvas_size)
        self.frame_layer = FrameLayer()
        self.court_layer = CourtLayer(court_img, court_poi, self.court_layer_pos[2:4])
        self.info_layer = InfoLayer()
        self.label = Label()
        self.selected_point_idx = -1
        self.poi_brush = PoIBrush.NORMAL

    def create_window(self, mouse_handler, trackbar_handler, num_data, window_size=(1280,720)):
        cv2.namedWindow(self.window_name, cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback(self.window_name, mouse_handler)
        cv2.resizeWindow(self.window_name, window_size[0], window_size[1])
        cv2.createTrackbar('frames', self.window_name, 1, num_data, trackbar_handler)

    def render(self, frame=None):
        ''' Renders the layers and returns the main canvas '''
        if self.window_name is None:
            print ('No windows have been created yet!')
            return

        canvas = np.zeros((self.canvas_size[1], self.canvas_size[0], 3), dtype=np.uint8)
        hot_poi = frame.hot_poi if frame is not None else None
        self.label.reproj_error = frame.reproj_error

        frame_canvas = self.frame_layer.draw(frame, self.selected_point_idx, self.poi_brush)
        court_canvas = self.court_layer.draw(hot_poi, self.selected_point_idx)
        info_canvas = self.info_layer.draw(self.label if frame is not None else None)
        UIRenderer.insert_into_canvas(canvas, frame_canvas, self.frame_layer_pos)
        UIRenderer.insert_into_canvas(canvas, court_canvas, self.court_layer_pos)
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

    def select_point(self, idx=None):
        if idx is not None:
            self.selected_point_idx = idx
            self.label.point_idx = idx

        return self.selected_point_idx

    def change_blending_alpha(self, step=0.25):
        self.frame_layer.blend_alpha += step
        if self.frame_layer.blend_alpha > 0.5:
            self.frame_layer.blend_alpha = 0

    def set_trackbar(self, value):
        cv2.setTrackbarPos('frames', self.window_name, value+1)

    def set_poi_brush(self, brush=None):
        if brush is None:
            brush = PoIBrush.get_next_brush(self.poi_brush)
        self.poi_brush = brush

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
    def overlay(img1, img2, alpha=0.3):
        m = cv2.inRange(img2, (0, 0, 0), (0, 0, 0))
        m = cv2.merge([m, m, m])
        overlaid = (img1 & m) + img2 * alpha + (img1 & (255 - m)) * (1 - alpha)

        return np.ascontiguousarray(overlaid.astype('uint8'))

    @staticmethod
    def draw_text(img, text, pos, color=(255, 255, 255), scale=0.75, lineType=1,
                  font=cv2.FONT_HERSHEY_COMPLEX_SMALL):
        cv2.putText(img, text, pos, font, scale, color, lineType)