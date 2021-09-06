import os
import argparse

from football_pitch.annotator import FootballPitchAnnotator
from ui.confirmation import display_confirmation


DEFAULT_PITCH_IMAGE = 'football_pitch/assets/pitch_image.png'
DEFAULT_PITCH_MASK = 'football_pitch/assets/pitch_mask_nc4_hd.png'
DEFAULT_PITCH_POI = 'football_pitch/assets/template_pitch_points.json'
DEFAULT_PITCH_IMAGE_SIZE = (1920, 1080)
UI_CANVAS_SIZE = (1920, 1080)
DEFAULT_FRAMES_FOLDER = 'frames'
DEFAULT_PREDS_FOLDER= 'preds'
DEFAULT_PREDS_NAME='preds.json'
DEFAULT_OUTPUT_FOLDER='manual_anno'
DEFAULT_OUTPUT_NAME='manual_anno.json'
DEFAULT_TEMP_FILE_SUFFIX = '_processing_'
NUM_POINTS = 33
IGNORE_POINTS = [12, 13, 19, 20]


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('data_dir', default=None,
                        help='Data source. Must contain frames and preds folders')
    parser.add_argument('name',
                        help='Name of a specific game from data_dir')
    return parser.parse_args()

def get_paths(data_dir, name):
    img_dir = os.path.join(data_dir, DEFAULT_FRAMES_FOLDER, name)
    preds_path = os.path.join(data_dir, DEFAULT_PREDS_FOLDER, name, DEFAULT_PREDS_NAME)
    output_dir = os.path.join(data_dir, DEFAULT_OUTPUT_FOLDER, name)
    output_path = os.path.join(output_dir, DEFAULT_OUTPUT_NAME)
    temp_path = os.path.join(output_dir, DEFAULT_TEMP_FILE_SUFFIX + DEFAULT_OUTPUT_NAME)

    return img_dir, preds_path, output_dir, output_path, temp_path


def load(mapper, path):
    if display_confirmation('Load Confirmation',
                            'Load saved data? (y/n)'):
        mapper.load(path)
        print('Data has been loaded from {}'.format(path))
        return True
    return False

def restore(mapper, path):
    if display_confirmation('Restore Confirmation',
                            'Restore data from previous session? (y/n)'):
        mapper.restore(path)
        print('Data has been restored from {}'.format(path))
        return True
    return False

def save(mapper, output_path):
    if display_confirmation('Save Confirmation', 'Save final results? (y/n)'):
        mapper.save(output_path)
        print('Data has been saved to {}'.format(output_path))
        return True
    return False

def run_mapping():
    args = get_args()

    # Get paths:
    img_dir, preds_path, output_dir, output_path, temp_path = get_paths(args.data_dir, args.name)
    if not os.path.exists(preds_path):
        preds_path = None
    assert os.path.isdir(img_dir), '{}'.format(img_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create mapping:
    try:
        mapper = FootballPitchAnnotator(img_dir,
                                        preds_path,
                                        output_path,
                                        DEFAULT_PITCH_IMAGE,
                                        DEFAULT_PITCH_MASK,
                                        DEFAULT_PITCH_POI,
                                        DEFAULT_PITCH_IMAGE_SIZE,
                                        UI_CANVAS_SIZE,
                                        NUM_POINTS,
                                        IGNORE_POINTS,
                                        temp_path=temp_path)
    except IOError as e:
        print(str(e))
        return

    # Is there saved data file?
    if os.path.isfile(output_path):
        load(mapper, output_path)

    # Is there unsaved data (due to unexpected termination)?
    if os.path.isfile(temp_path):
        if not restore(mapper, temp_path):
            os.remove(temp_path)

    # Run mapping:
    try:
        mapper.run()
        save(mapper, output_path)
        print('Finished successfully.')

    except KeyboardInterrupt:
        save(mapper, output_path)
        print('Manual points mapping is interrupted!')

    if os.path.isfile(temp_path):
        os.remove(temp_path)

if __name__ == '__main__':
    run_mapping()
