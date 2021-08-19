import os
import cv2
import json
from pathlib import PurePath


class DataProcessor:
    ''' Loads, prepares and manages data (images and points) '''

    class DPFrame:
        ''' Represents a frame as an image and text '''
        def __init__(self, img_path, text=None):
            self.img_path = img_path
            self.img = None
            self.text = text
            self.saved = True

        def set_text(self, text):
            self.text = text
            self.saved = False

    def __init__(self, img_dir, preds_path, max_text_len=4):
        self. max_text_len = max_text_len

        # Parse image paths and read predictions json:
        self.frames = []
        self.name_to_idx_map = {}
        if os.path.isdir(img_dir) and os.path.isfile(preds_path):
            img_paths = [os.path.join(img_dir, file) for file in os.listdir(img_dir) if not file.endswith('.')]
            img_paths.sort()
            preds = json.load(open(preds_path, 'r'))
            for idx, path in enumerate(img_paths):
                name = PurePath(path).parts[-1]
                # name = os.path.split(path).split('.')[0]
                text = None
                if name in preds:
                    text = preds[name]['text']
                else:
                    print ('No predictions found for image \'{}\''.format(path))
                if text is None:
                    text = ''
                self.frames.append(DataProcessor.DPFrame(path, text))
                self.name_to_idx_map[name] = idx
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
        self._validate_frame_idx(idx)

        return self.get_frame(idx)

    def get_frame(self, idx=None):
        '''
        Takes a Frame at a given index and performs some computations if required
        '''
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)

        frame = self.frames[idx]
        if frame.img is None:
            frame.img = cv2.imread(frame.img_path, cv2.IMREAD_COLOR)

        return frame

    def set_char_in_text(self, char, pos, idx=None):
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)
        assert pos > -1 and pos < self.max_text_len

        text = list(self.frames[idx].text)
        if pos >= len(text):
            for i in range(len(text),pos):
                text.append(' ')
            text.append(chr(char))
        else:
            text[pos] = chr(char)
        text = ''.join(text)

        self.frames[idx].set_text(text)

    def remove_char_from_text(self, pos, idx=None):
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)
        assert pos > -1 and pos < self.max_text_len
        if len(self.frames[idx].text) <= 0:
            return

        text = self.frames[idx].text
        if pos < len(text):
            text = list(text)
            text.pop(pos)
            text = ''.join(text)
            self.frames[idx].set_text(text)

    def clean_text(self, idx=None):
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)
        self.frames[idx].set_text('')

    def set_text(self, text, idx=None):
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)
        self.frames[idx].set_text(text)

    def get_text(self, idx=None):
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)

        return (self.frames[idx].text + '.')[:-1]

    def _validate_frame_idx(self, idx):
        assert idx is not None and idx > -1 and idx < self.num_frames

    def set_frame_idx(self, idx):
        self.cur_idx = idx
        if self.cur_idx >= self.num_frames:
            self.cur_idx = self.num_frames - 1
        elif self.cur_idx < 0:
            self.cur_idx = 0

        return self.cur_idx

    def next(self):
        self.cur_idx += 1
        if self.cur_idx >= self.num_frames:
            self.cur_idx = self.num_frames - 1

        return self.cur_idx

    def prev(self):
        self.cur_idx -= 1
        if self.cur_idx < 0:
            self.cur_idx = 0

        return self.cur_idx

    def save(self, dst_path):
        output = {}
        for frame in self.frames:
            name = PurePath(frame.img_path).parts[-1]
            # name = frame.img_path.split('/')[-1]
            out = {'text': frame.text}
            output[name] = out

        with open(dst_path, 'w') as file:
            json.dump(output, file, indent=2)

    def save_frame(self, dst_path, idx=None):
        if idx is None:
            idx = self.cur_idx
        self._validate_frame_idx(idx)

        frame = self.frames[idx]

        if not frame.saved:
            output = {'text': frame.text}
            name = PurePath(frame.img_path).parts[-1]
            # name = frame.img_path.split('/')[-1]
            with open(dst_path, 'a+') as file:
                json.dump({name: output}, file)
                file.write('\n')
            frame.saved = True

    def load(self, path):
        assert self.frames
        loaded_frames = json.load(open(path, 'r'))

        for idx,(k,v) in enumerate(loaded_frames.items()):
            if 'text' in v:
                text = v['text'] if v['text'] is not None else ''
                self.frames[self.name_to_idx_map[k]].set_text(text)

    def restore(self, path):
        assert self.frames
        restored_frames = {k: v for line in open(path, 'r') for k, v in json.loads(line).items()}
        os.remove(path)

        for k,v in restored_frames.items():
            idx = self.name_to_idx_map[k]
            if 'text' in v:
                self.frames[idx].set_text(v['text'])
            self.save_frame(path, idx)