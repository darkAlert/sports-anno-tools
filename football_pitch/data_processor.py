import os
import cv2
import json
import numpy as np

from football_pitch.utils import NumpyEncoder, reprojection_loss

NUM_POINTS = 33


class DataProcessor:
    ''' Loads, prepares and manages data (images and points) '''

    class DLFrame:
        ''' Represents a frame as an image, points of interest and other meta information '''
        def __init__(self, img_path, poi=None, score=None, theta=None):
            self.img_path = img_path
            self.poi = poi
            self.orig_poi = np.copy(poi)
            self.score = score
            self.img = None
            self.theta = theta
            self.proj_poi = None
            self.proj_court = None
            self.hot_poi = np.ones(self.poi.shape[0], dtype=bool)
            self.reproj_error = 0
            self.modified = True
            self.saved = True
            self.reset = False
            self.elapsed = 0

            self.determine_visible_poi()

        def _validate_point_idx(self, idx):
            assert idx is not None and idx >= 0 and idx < self.poi.shape[0]

        def set_poi(self, poi):
            assert poi
            self.poi = np.copy(poi)
            self.modified = True
            self.saved = False
            self.determine_visible_poi()

        def set_point_coords(self, idx, coords):
            self._validate_point_idx(idx)
            self.poi[idx] = coords
            self.modified = True
            self.saved = False
            self.determine_visible_poi()

        def add_elapsed_time(self, elapsed):
            self.elapsed += elapsed
            self.saved = False

        def get_point_coords(self, idx):
            self._validate_point_idx(idx)
            return (self.poi[idx][0], self.poi[idx][1])

        def determine_visible_poi(self):
            ''' Determines which points are active '''
            for i, pt in enumerate(self.poi):
                if pt[0] < 0 or pt[0] > 1.0 or pt[1] < 0 or pt[1] > 1:
                    self.hot_poi[i] = False
                else:
                    self.hot_poi[i] = True

        def set_point_state(self, idx, hot=None, use_proj=True):
            self._validate_point_idx(idx)
            prev_state = self.hot_poi[idx]

            # Enable / disable the point:
            if hot is None:
                self.hot_poi[idx] = not self.hot_poi[idx]      # invert state
            else:
                self.hot_poi[idx] = hot

            # Take the point's coordinates from the corresponding projected point:
            if use_proj and prev_state == False and \
                    self.hot_poi[idx] == True and self.proj_poi is not None:
                self.poi[idx] = self.proj_poi[idx]

            self.modified = True
            self.saved = False

        def get_point_state(self, idx):
            self._validate_point_idx(idx)
            return self.hot_poi[idx]

        def clear(self):
            self.hot_poi.fill(False)
            self.modified = True
            self.saved = False
            self.reset = True

    def __init__(self, img_dir, preds_path, court_mask_path, court_poi_path, court_size=(1920,1080)):
        self.poi_buffer = []     # for keeping PoI changes

        # Load court image and court PoI:
        self.court_mask = DataProcessor.load_court_mask(court_mask_path, court_size)
        self.court_poi = DataProcessor.load_court_poi(court_poi_path)

        # Parse image paths and read predictions json:
        self.frames = []
        self.name_to_idx_map = {}
        if os.path.isdir(img_dir):
            img_paths = [os.path.join(img_dir, file) for file in os.listdir(img_dir) if not file.endswith('.')]
            img_paths = sorted(img_paths)
            preds = None
            if preds_path is not None:
                preds = json.load(open(preds_path, 'r'))
            for path in img_paths:
                _,filename = os.path.split(path)
                name = filename.split('.')[0]
                poi, theta, score = None, None, None
                if preds is not None and name in preds:
                    p = preds[name]
                    poi = np.array(p['poi'])
                    theta = np.array(p['theta'])[0]
                    # score = p['score']
                else:
                    poi = np.array([(-1,-1)]*NUM_POINTS, dtype=np.float32)
                self.frames.append(DataProcessor.DLFrame(path, poi, score, theta))
                self.name_to_idx_map[name] = len(self.frames)-1
        else:
            raise FileNotFoundError

        self.num_frames = len(self.frames)
        if self.num_frames > 0:
            self.cur_idx = 0
        else:
            self.cur_idx = None

    def __len__(self):
        return self.num_frames

    def __getitem__(self, idx):
        assert idx is not None and \
               idx >= 0 and \
               idx < self.num_frames
        return self.get_frame(idx)

    def update_frame(self, idx):
        assert idx is not None and \
               idx >= 0 and \
               idx < self.num_frames

        frame = self.frames[idx]

        if frame.img is None:
            frame.img = cv2.imread(frame.img_path, cv2.IMREAD_COLOR)

        if frame.modified:
            frame.modified = False

            # Choose hot points for finding homography:
            pts_from, pts_to = [], []
            for i, hot in enumerate(frame.hot_poi):
                if hot:
                    pts_from.append(self.court_poi[0][i])
                    pts_to.append(frame.poi[i])

            if len(pts_from) < 4:
                # frame.proj_poi = None
                # frame.theta = None
                frame.proj_court = None
                return frame

            # Find the homography and transform the coiurt PoI:
            frame.theta, r = cv2.findHomography(np.array(pts_from), np.array(pts_to))
            if frame.theta is None:
                frame.proj_court = None
                return frame
            frame.proj_poi = cv2.perspectiveTransform(self.court_poi, frame.theta)[0]
            frame.reproj_error = reprojection_loss(frame.poi, frame.proj_poi, frame.hot_poi, (1280,720))

            # Rescale theta (homography) to the image size:
            src_h, src_w = self.court_mask.shape[0:2]
            dst_h, dst_w = frame.img.shape[0:2]
            src_scale = np.array([[dst_w,0,0],[0,dst_h,0],[0,0,1]], dtype=np.float64)
            dst_scale_inv = np.array([[1/src_w, 0, 0], [0, 1/src_h, 0], [0, 0, 1]], dtype=np.float64)
            scaled_theta = np.matmul(np.matmul(src_scale, frame.theta), dst_scale_inv)

            # Warp the court image with rescaled theta:
            frame.proj_court = cv2.warpPerspective(self.court_mask, scaled_theta, (dst_w,dst_h))

        return frame

    def _validate_frame_idx(self, idx):
        assert idx is not None and idx > -1 and idx < self.num_frames

    def get_frame(self, idx=None):
        '''
        Takes a Frame at a given index and performs some computations if required
        '''
        if idx is None:
            idx = self.cur_idx

        self._validate_frame_idx(idx)

        return self.update_frame(idx)

    def get_idx(self):
        return self.cur_idx

    def get_point(self, point_idx, frame_idx=None):
        if frame_idx is None:
            frame_idx = self.cur_idx

        self._validate_frame_idx(frame_idx)

        return self.frames[frame_idx].get_point_coords(point_idx)

    def clear_poi(self, frame_idx=None):
        if frame_idx is None:
            frame_idx = self.cur_idx

        self._validate_frame_idx(frame_idx)
        self.frames[frame_idx].clear()

    def set_frame_idx(self, idx):
        self.cur_idx = idx
        if self.cur_idx >= self.num_frames:
            self.cur_idx = self.num_frames - 1
        elif self.cur_idx < 0:
            self.cur_idx = 0

        self.poi_buffer.clear()

        return self.cur_idx

    def next(self):
        self.cur_idx += 1
        if self.cur_idx >= self.num_frames:
            self.cur_idx = self.num_frames - 1

        self.poi_buffer.clear()

        return self.cur_idx

    def prev(self):
        self.cur_idx -= 1
        if self.cur_idx < 0:
            self.cur_idx = 0

        self.poi_buffer.clear()

        return self.cur_idx

    def set_point_coords(self, point_idx, coords):
        frame = self.frames[self.cur_idx]
        prev_coords = frame.get_point_coords(point_idx)
        state = frame.get_point_state(point_idx)
        self.poi_buffer.append((point_idx, prev_coords, state))
        if len(self.poi_buffer) > 50:
            self.poi_buffer.pop(0)

        frame.set_point_coords(point_idx, coords)
        self.update_frame(self.cur_idx)

    def undo_last(self):
        if not self.poi_buffer:
            return
        idx, coords, state = self.poi_buffer.pop()
        frame = self.frames[self.cur_idx]
        frame.set_point_coords(idx, coords)
        frame.set_point_state(idx, state, use_proj=False)

        self.update_frame(self.cur_idx)

    def set_point_state(self, point_idx, hot=None):
        frame = self.frames[self.cur_idx]
        prev_state = frame.get_point_state(point_idx)
        coord = frame.get_point_coords(point_idx)
        frame.set_point_state(point_idx, hot)

        self.poi_buffer.append((point_idx, coord, prev_state))
        if len(self.poi_buffer) > 50:
            self.poi_buffer.pop(0)

        self.update_frame(self.cur_idx)

    def is_point_hot(self, point_idx):
        return self.frames[self.cur_idx].get_point_state(point_idx)

    def get_next_point_idx(self, point_idx=0, frame_idx=None):
        if frame_idx is None:
            frame_idx = self.cur_idx

        point_idx += 1
        num = self.frames[frame_idx].poi.shape[0]
        if point_idx >= num:
            point_idx = 0
        elif point_idx < 0:
            point_idx = num - 1

        return point_idx

    def get_prev_point_idx(self, point_idx=0, frame_idx=None):
        if frame_idx is None:
            frame_idx = self.cur_idx

        point_idx -= 1
        num = self.frames[frame_idx].poi.shape[0]
        if point_idx >= num:
            point_idx = 0
        elif point_idx < 0:
            point_idx = num - 1

        return point_idx

    def add_elapsed_time(self, elapsed, idx=None):
        if idx is not None:
            self._validate_frame_idx(idx)
        else:
            idx = self.cur_idx
        self.frames[idx].add_elapsed_time(elapsed)

    def save(self, dst_path):
        output = {}
        for frame in self.frames:
            name = frame.img_path.split('/')[-1].split('.')[0]
            poi = np.copy(frame.poi)
            poi[frame.hot_poi == False] = (-1,-1)
            elapsed = float('{:.3f}'.format(frame.elapsed))
            out = {'theta': frame.theta, 'poi': poi, 'elapsed': elapsed}
            if frame.reset:
                out['reset'] = True
            output[name] = out

        with open(dst_path, 'w') as file:
            json.dump(output, file, cls=NumpyEncoder, indent=2)

    def save_frame(self, dst_path, idx=None):
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)

        frame = self.frames[idx]

        if not frame.saved:
            output = {}
            if not np.array_equal(frame.poi, frame.orig_poi):
                poi = np.copy(frame.poi)
                poi[frame.hot_poi == False] = (-1, -1)
                output['poi'] = poi
            if frame.elapsed > 0:
                output['elapsed'] = float('{:.3f}'.format(frame.elapsed))
            if frame.reset:
                output['reset'] = True
            if output:
                with open(dst_path, 'a+') as file:
                    json.dump({idx: output}, file, cls=NumpyEncoder)
                    file.write('\n')
            frame.saved = True

    def load(self, path):
        assert self.frames
        loaded_frames = json.load(open(path, 'r'))

        for k,v in loaded_frames.items():
            idx = self.name_to_idx_map[k]
            if 'poi' in v:
                self.frames[idx].set_poi(v['poi'])
            if 'elapsed' in v:
                self.frames[idx].add_elapsed_time(v['elapsed'])
            if 'reset' in v:
                self.frames[idx].reset = v['reset']

    def restore(self, path):
        assert self.frames
        restored_frames = {k: v for line in open(path, 'r') for k, v in json.loads(line).items()}
        os.remove(path)

        for k,v in restored_frames.items():
            idx = self.name_to_idx_map[k]
            if 'poi' in v:
                self.frames[idx].set_poi(v['poi'])
            if 'elapsed' in v:
                self.frames[idx].add_elapsed_time(v['elapsed'])
            if 'reset' in v:
                self.frames[idx].reset = v['reset']
            self.save_frame(path, idx)

    @staticmethod
    def load_court_mask(path, court_size):
        ''' Loads the court template image that will be warped by homography'''
        court_mask = cv2.imread(path, cv2.IMREAD_COLOR)
        if court_mask.shape[0] != court_size[1] or court_mask.shape[1] != court_size[0]:
            inter = cv2.INTER_AREA if court_mask.shape[1] > court_size[0] else cv2.INTER_CUBIC
            court_mask = cv2.resize(court_mask, court_size, interpolation=inter)

        return court_mask

    @staticmethod
    def load_court_poi(path, normalize=False):
        ''' Load the points of interest of court template '''
        poi = None

        with open(path) as f:
            try:
                points_data = json.load(f)
                points_raw = points_data['points']
                ranges = points_data['ranges']
                assert ranges[0] == 1.0 and ranges[1] == 1.0
                poi = []

                for p in points_raw:
                    poi.append((p['coords'][0], p['coords'][1]))
                poi = np.array([poi])
                if normalize:
                    poi = (poi - 0.5) * 2.0

            except Exception as e:
                raise ValueError(f'Cannot read {path}: {str(e)}')

        return poi