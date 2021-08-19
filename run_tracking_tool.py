import os
import argparse

from tracking.annotator import TrackingAnnotator
from ui.confirmation import display_confirmation


DEFAULT_OUTPUT_FILE ='edited_tracks.json'
DEFAULT_TEMP_FILE_SUFFIX = '_processing_'
UI_CANVAS_SIZE = (1920, 1080)

def get_paths(data_dir):
    output_path = os.path.join(data_dir, DEFAULT_OUTPUT_FILE)
    temp_path = os.path.join(data_dir, DEFAULT_TEMP_FILE_SUFFIX + DEFAULT_OUTPUT_FILE)

    # Get available video clips:
    clip_paths = [os.path.join(data_dir, file) for file in os.listdir(data_dir) if file.endswith('.mp4')]
    clip_paths.sort()

    return clip_paths, output_path, temp_path

def load(annotator, path):
    if display_confirmation('Load Confirmation',
                            'Load saved data? (y/n)'):
        annotator.load(path)
        print('Data has been loaded from {}'.format(path))
        return True
    return False

def restore(annotator, path):
    if display_confirmation('Restore Confirmation',
                            'Restore data from previous session? (y/n)'):
        annotator.restore(path)
        print('Data has been restored from {}'.format(path))
        return True
    return False

def save(annotator, output_path):
    if display_confirmation('Save Confirmation', 'Save final results? (y/n)'):
        annotator.save(output_path)
        print('Data has been saved to {}'.format(output_path))
        return True
    return False

def run_annotator(data_dir):
    # Get paths:
    clip_paths, output_path, temp_path = get_paths(data_dir)
    print ('Total clips:', len(clip_paths))

    # Create annotator:
    try:
        annotator = TrackingAnnotator(clip_paths, output_path, temp_path, UI_CANVAS_SIZE)
        print('Results saved to:', output_path)

    except IOError as e:
        print(str(e))
        return

    # Is there saved data file?
    if os.path.isfile(output_path):
        load(annotator, output_path)

    # Is there unsaved data (due to unexpected termination)?
    if os.path.isfile(temp_path):
        if not restore(annotator, temp_path):
            os.remove(temp_path)

    # Run mapping:
    try:
        annotator.run()
        save(annotator, output_path)
        print('Finished successfully.')

    except KeyboardInterrupt:
        save(annotator, output_path)
        print('Annotating is interrupted!')

    if os.path.isfile(temp_path):
        os.remove(temp_path)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', '-d', default=None,
                        help='The directory where input videos are stored and where the results will be saved to.')

    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    assert args.data_dir
    run_annotator(args.data_dir)
