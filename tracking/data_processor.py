import cv2
import json
from pathlib import PurePath


class DPClip:
    ''' Represents a video clip'''

    def __init__(self, path):
        self.path = path
        self.name = PurePath(path).parts[-1]
        self.current_frame_id = 0
        self.num_frames = int(cv2.VideoCapture(path).get(cv2.CAP_PROP_FRAME_COUNT))
        self.annos = {i: {'label': True, 'pos': None} for i in range(self.num_frames)}

    def get_frame_anno(self):
        return self.annos[self.current_frame_id]

    def set_frame_anno(self, key, value):
        self.annos[self.current_frame_id][key] = value


class DataProcessor:
    ''' Loads, prepares and manages data (video clips and editing results) '''

    def __init__(self, clip_paths):
        self.clips = []
        for path in clip_paths:
            self.clips.append(DPClip(path))
        self.current_clip_id = 0
        self.open_clip_id = -1
        self.video_cap = None

    def __len__(self):
        return len(self.clips)

    def get_frame(self):
        '''
        Reads the current frame from the current clip and return its image
        '''
        if self.open_clip_id != self.current_clip_id:
            self._open_video()

        frame = self._read_frame()

        return frame

    def next_clip(self):
        return self.set_current_clip_id(self.current_clip_id+1)

    def prev_clip(self):
        return self.set_current_clip_id(self.current_clip_id-1)

    def set_current_clip_id(self, clip_id):
        if clip_id >= self.__len__():
            clip_id = self.__len__() - 1
        elif clip_id < 0:
            clip_id = 0
        self.current_clip_id = clip_id

        return self.current_clip_id

    def get_clip(self, clip_id=None) -> DPClip:
        if clip_id is None:
            clip_id = self.current_clip_id
        else:
            assert clip_id >= 0 and clip_id < self.__len__()

        return self.clips[clip_id]

    def next_frame(self):
        frame_id = self.clips[self.current_clip_id].current_frame_id + 1

        return self.set_current_frame_id(frame_id)

    def prev_frame(self):
        frame_id = self.clips[self.current_clip_id].current_frame_id - 1

        return self.set_current_frame_id(frame_id)

    def set_current_frame_id(self, frame_id):
        clip = self.clips[self.current_clip_id]

        if frame_id >= clip.num_frames:
            frame_id = clip.num_frames - 1
        elif frame_id < 0:
            frame_id = 0

        clip.current_frame_id = frame_id

        return clip.current_frame_id

    def save(self, dst_path):
        output = {}
        for clip in self.clips:
            clip_output = {}
            for frame_id, frame_anno in clip.annos.items():
                if frame_anno['label'] == False:
                    clip_output[str(frame_id).zfill(6)] = {'label': False}
                elif frame_anno['pos'] is not None:
                    clip_output[str(frame_id).zfill(6)] = {'label': True, 'pos': frame_anno['pos']}
            output[clip.name] = clip_output

        with open(dst_path, 'w') as file:
            json.dump(output, file, indent=2)

    def load(self, path):
        assert self.clips
        loaded_data = json.load(open(path, 'r'))

        for clip_name, loaded_clip in loaded_data.items():
            found = False
            for clip in self.clips:
                if clip.name == clip_name:
                    for frame_id, frame_annos in loaded_clip.items():
                        frame_id = int(frame_id)
                        pos = None
                        if 'pos' in frame_annos:
                            pos = frame_annos['pos']
                        clip.annos[frame_id] = {'label': frame_annos['label'], 'pos': pos}
                    found = True
                    break
            assert found

    @property
    def frame_pos(self):
        return self.clips[self.current_clip_id].current_frame_id

    @property
    def num_frames(self):
        return self.clips[self.current_clip_id].num_frames

    def _open_video(self):
        clip = self.clips[self.current_clip_id]
        self.video_cap = cv2.VideoCapture(clip.path)

    def _read_frame(self):
        assert self.video_cap

        clip = self.clips[self.current_clip_id]
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, clip.current_frame_id)
        _, frame = self.video_cap.read()

        return frame
