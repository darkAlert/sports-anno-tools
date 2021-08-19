import json
import numpy as np
import cv2

from court.data_processor import DataProcessor
from court.ui_renderer import UIRenderer
from court.utils import reprojection_loss


def load_preds(path):
    preds = json.load(open(path, 'r'))

    for k,v in preds.items():
        preds[k]['poi'] = np.array(v['poi'])
        preds[k]['theta'] = np.array(v['theta'])[0]
        preds[k]['theta'] = np.linalg.inv(v['theta'])

    return preds

def draw(img, poi, hot_poi=None, only_hot=False):
    if hot_poi is None:
        hot_poi = np.ones(poi.shape[0], dtype=bool)

    canvas = np.copy(img)
    h, w = img.shape[0:2]
    r_outer = int(round(w * 0.0035))
    r_inner = int(round(w * 0.0015))

    for i, (pt, hot) in enumerate(zip(poi, hot_poi)):
        x, y = int(round(pt[0] * w)), int(round(pt[1] * h))
        if hot:
            color = (255, 0, 255)
        else:
            color = (0, 0, 255)
            if only_hot:
                continue
        canvas = cv2.circle(canvas, (x, y), r_outer, color=color, thickness=-1)
        canvas = cv2.circle(canvas, (x, y), r_inner, color=(0, 255, 0), thickness=-1)

    return canvas

def find_theta(court_poi, frame_poi, hot_poi=None):
    if hot_poi is None:
        hot_poi = np.ones(frame_poi.shape[0], dtype=bool)

    pts_from, pts_to = [], []
    for i, hot in enumerate(hot_poi):
        if hot:
            pts_from.append(court_poi[i])
            pts_to.append(frame_poi[i])
    assert len(pts_from) >= 5

    theta, _ = cv2.findHomography(np.array(pts_from), np.array(pts_to))

    return theta

def transform_poi(theta, poi, normalize=False):
    if poi.ndim == 3:
        proj_poi = cv2.perspectiveTransform(poi, theta)[0]
    else:
        proj_poi = cv2.perspectiveTransform(np.expand_dims(poi, axis=0), theta)[0]
    if normalize:
        proj_poi = proj_poi / 2.0 + 0.5
    return proj_poi

def warp(img, theta, w=1280, h=720, rescale=True):
    # Rescale theta (homography) to the image size:
    if rescale:
        src_h, src_w = img.shape[0:2]
        dst_h, dst_w = h, w
        src_scale = np.array([[dst_w, 0, 0], [0, dst_h, 0], [0, 0, 1]], dtype=np.float64)
        dst_scale_inv = np.array([[1 / src_w, 0, 0], [0, 1 / src_h, 0], [0, 0, 1]], dtype=np.float64)
        scaled_theta = np.matmul(np.matmul(src_scale, theta), dst_scale_inv)
    else:
        scaled_theta = theta

    return cv2.warpPerspective(img, scaled_theta, (w, h))


def determine_visible_poi(poi, hot_poi=None):
    ''' Determines which points are active '''
    if hot_poi is None:
        hot_poi = np.ones(poi.shape[0], dtype=bool)
    for i, pt in enumerate(poi):
        if pt[0] < 0 or pt[0] > 1.0 or pt[1] < 0 or pt[1] > 1:
            hot_poi[i] = False

    return hot_poi

def find_reduced_hot_poi(court_poi, poi, target_num=5, norm_size=(1280, 720)):
    hot_poi = determine_visible_poi(poi)
    num_nonzero = np.count_nonzero(hot_poi, axis=0)

    while num_nonzero > target_num:
        errors = []
        for i in range(hot_poi.shape[0]):
            if not hot_poi[i]:
                continue
            hot_poi[i] = False
            theta_new = find_theta(court_poi, poi, hot_poi)
            proj_poi = transform_poi(theta_new, court_poi)
            errors.append((i, reprojection_loss(poi, proj_poi, norm_size=norm_size)))
            hot_poi[i] = True

        errors.sort(key=lambda tup: tup[1])
        index_min, error_min = errors[0]
        hot_poi[index_min] = False
        num_nonzero = np.count_nonzero(hot_poi, axis=0)
        # print ('excluded #{}, error={}'.format(index_min, error_min))

    return hot_poi


def find_optimal_poi(theta_orig, poi_orig, court_poi, court_mask=None, img=None, target_num_poi=5):
    # Find the reduced number of hot PoI:
    court_poi_norm = (court_poi - 0.5) * 2.0
    poi = transform_poi(theta_orig, court_poi_norm, normalize=True)
    hot_poi = find_reduced_hot_poi(court_poi, poi, target_num=target_num_poi)

    # Find homography using the reduced hot PoI:
    theta = find_theta(court_poi, poi_orig, hot_poi)
    proj_poi = transform_poi(theta, court_poi)
    reproj_error = reprojection_loss(poi_orig, proj_poi, norm_size=(1280, 720))

    if court_mask is not None and img is not None:
        proj_court = warp(court_mask, theta)

        # Draw:
        canvas = UIRenderer.overlay(img, proj_court)
        canvas = draw(canvas, poi_orig, hot_poi=np.zeros(poi.shape[0], dtype=bool))
        canvas = draw(canvas, proj_poi, hot_poi, only_hot=True)
        text = '{:3f}'.format(reproj_error)
        UIRenderer.draw_text(canvas, text, (50, 50), color = (64, 64, 255), scale=2, lineType=2)

        cv2.imshow('optimal poi', canvas)
        cv2.waitKey()
        cv2.destroyAllWindows()

    return hot_poi, theta, reproj_error


if __name__ == '__main__':
    COURT_MASK_PATH = 'court/assets/mask_ncaa_v4_nc4_m.png'
    COURT_POI_PATH = 'court/assets/template_ncaa_v4_points.json'
    COURT_IMAGE_SIZE = (1920, 1080)

    preds_path = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/boost/experiments/court_mapping_tool/NCAA-2020-21/preds/2020_12_31_Nevada_at_NewMexico/preds.json'
    img_path = '/media/darkalert/c02b53af-522d-40c5-b824-80dfb9a11dbb/boost/experiments/court_mapping_tool/NCAA-2020-21/frames/2020_12_31_Nevada_at_NewMexico/2020_12_31_Nevada_at_NewMexico_094322.jpeg'

    # Load the court template:
    court_mask = DataProcessor.load_court_mask(COURT_MASK_PATH, COURT_IMAGE_SIZE)
    court_poi = DataProcessor.load_court_poi(COURT_POI_PATH)[0]

    # Load image and predictions:
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    preds = load_preds(preds_path)
    name = img_path.split('/')[-1].split('.')[0]
    theta = preds[name]['theta']
    poi = preds[name]['poi']

    find_optimal_poi(theta, poi, court_poi, court_mask, img)