import os
import numpy as np
import cv2
from shutil import copy
import json
from tqdm import tqdm
from skimage.metrics import structural_similarity as ssim


def prepare_scorebug_template(img_path, dst_dir):
    template_img_path = os.path.join(dst_dir, 'template.jpeg')
    template_meta_path = os.path.join(dst_dir, 'template.json')

    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    # Select ROI (template area) on the image:
    img = cv2.imread(img_path, 1)
    x, y, w, h = cv2.selectROI(str(img_path), img)
    if x == 0 and y == 0 and w == 0 and h == 0:
        return
    meta = {
        'img_name': template_img_path.split('/')[-1],
        'x': x, 'y': y, 'w': w, 'h': h
    }

    # Save:
    with open(template_meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    copy(img_path, template_img_path)

    print(meta)
    print ('Done!')


def get_frames_with_scorebug(data_dir, threshold=0.4):
    frames_dir = os.path.join(data_dir, 'frames')
    target_dir = os.path.join(data_dir, 'frames_target')
    dropped_dir = os.path.join(data_dir, 'frames_dropped')

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    if not os.path.exists(dropped_dir):
        os.makedirs(dropped_dir)

    # Open a template:
    template_meta_path = os.path.join(data_dir, 'scorebug_templates/template.json')
    with open(template_meta_path, 'r') as f:
        meta = json.load(f)
    template_img_path = os.path.join(data_dir, 'scorebug_templates', meta['img_name'])
    template_img = cv2.imread(template_img_path, 0)
    x1, y1 = meta['x'], meta['y']
    x2, y2 = x1 + meta['w'], y1 + meta['h']
    scorebug_template = template_img[y1:y2, x1:x2]
    scorebug_template = cv2.resize(scorebug_template, (0,0), fx=0.25, fy=0.5)
    H, W = scorebug_template.shape[:2]

    # Get src frame names:
    paths = [os.path.join(frames_dir, file) for file in os.listdir(frames_dir) if not file.endswith('.')]
    paths = sorted(paths)
    # paths = paths[143000:144000]
    dropped_count, target_count = 0, 0

    with tqdm(total=len(paths), desc=f'Processing', unit='img') as pbar:
        for img_path in paths:
            name = img_path.split('/')[-1]
            img = cv2.imread(img_path, 0)[y1:y2, x1:x2]
            img = cv2.resize(img, (W, H))
            score = ssim(scorebug_template, img)
            # print (name, score)

            if score > threshold:
                dst_path = os.path.join(target_dir, name)
                target_count += 1
            else:
                dst_path = os.path.join(dropped_dir, name)
                dropped_count += 1

            copy(img_path, dst_path)

            pbar.update(1)

    print ('Done! Target frames: {}, dropped frames: {}'.format(target_count, dropped_count))



if __name__ == '__main__':
    img_path = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/sota/football/video/VTB_mol_Ural_at_Dinamo/frames/image-37001.jpeg'
    dst_dir = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/sota/football/video/VTB_mol_Ural_at_Dinamo/scorebug_templates'
    # prepare_scorebug_template(img_path, dst_dir)


    data_dir = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/sota/football/video/VTB_mol_Ural_at_Dinamo'
    get_frames_with_scorebug(data_dir)