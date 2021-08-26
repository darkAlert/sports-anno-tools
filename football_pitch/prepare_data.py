import os
import json
from shutil import copyfile

from football_pitch.data_processor import DataProcessor
from court.optimal_poi import find_optimal_poi, load_preds
from football_pitch.utils import NumpyEncoder


def prepare_data(court_poi_path, images_dir, preds_dir, dst_dir=None, target_num_poi=5, pieces_per_video=None):
    # Load court image and court PoI:
    court_poi = DataProcessor.load_court_poi(court_poi_path)[0]

    # Parse names of videos:
    video_names = [d.name for d in os.scandir(images_dir) if d.is_dir()]

    for name in video_names:
        print ('Processing {}...'.format(name))
        if dst_dir is not None:
            dst_frames_dir = os.path.join(dst_dir, 'frames', name)
            dst_preds_dir = os.path.join(dst_dir, 'preds', name)
            if not os.path.exists(dst_frames_dir):
                os.makedirs(dst_frames_dir)
            if not os.path.exists(dst_preds_dir):
                os.makedirs(dst_preds_dir)

        img_dir = os.path.join(images_dir, name)
        img_paths = [os.path.join(img_dir, file) for file in os.listdir(img_dir) if not file.endswith('.')]
        preds_path = os.path.join(preds_dir, name, 'preds.json')
        preds = load_preds(preds_path)
        output = {}

        if pieces_per_video is not None:
            img_paths = img_paths[:pieces_per_video]

        for i, path in enumerate(img_paths):
            key = os.path.splitext(os.path.basename(path))[0]
            p = preds[key]

            # Find optimal PoI:
            hot_poi, theta, _ = find_optimal_poi(p['theta'], p['poi'], court_poi, target_num_poi=target_num_poi)

            # Postprocess:
            p['poi'][hot_poi == False] = (-1, -1)
            output[key] = {'theta': theta, 'poi': p['poi'], 'score': p['score']}

            if dst_dir is not None:
                dst_img_path = os.path.join(dst_frames_dir, key + '.jpeg')
                copyfile(path, dst_img_path)

        if dst_dir is not None:
            dst_preds_path = os.path.join(dst_preds_dir, 'preds.json')
            with open(dst_preds_path, 'w') as file:
                json.dump(output, file, cls=NumpyEncoder, indent=2)


if __name__ == '__main__':
    court_poi_path = 'court/assets/template_ncaa_v4_points.json'
    images_dir = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/boost/experiments/court_mapping_tool/NCAA-2020-21/frames/'
    preds_dir = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/boost/experiments/court_mapping_tool/NCAA-2020-21/preds/'
    dst_dir = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/boost/experiments/court_mapping_tool/test_NCAA-2020-21_only23/'

    prepare_data(court_poi_path, images_dir, preds_dir, dst_dir=dst_dir, pieces_per_video=23)