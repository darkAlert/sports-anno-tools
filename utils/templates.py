import os
import cv2
import json


def draw_text(img, text, pos, color=(255,255,255), scale=0.75, lineType=1, font=cv2.FONT_HERSHEY_COMPLEX_SMALL):
    '''
    :pos: (x,y) position of the text in the image
    '''
    cv2.putText(img, text, pos, font, scale, color, lineType)

    return img


def mark_template_pts(template_path, dst_pts_path, num_pts):
    template_img = cv2.imread(template_path, 1)
    H, W = template_img.shape[:2]
    points = []

    for i in range(num_pts):
        x, y, w, h = cv2.selectROI('template_img', template_img)
        points.append({'coords': (x/W,y/H), 'label': str(i)})
        print('pts {}: ({}, {})'.format(i, x, y))

        # Draw:
        cv2.circle(template_img, (x,y), 2, (255,0,0), thickness=2, lineType=8)
        tx, ty = x+10, y-10
        if ty - 40 < 0:
            ty += 40
        if ty + 20 >= H:
            ty -= 20
        if tx - 10 < 0:
            tx += 10
        if tx + 25 >= W:
            tx -= 25
        draw_text(template_img, str(i), (tx,ty), color=(255,0,0), scale=2, lineType=2)


    data = {
        'template_image': os.path.basename(template_path),
        'template_size': (W,H),
        'ranges': [1.0, 1.0],
        'points': points
    }

    with open(dst_pts_path, 'w') as f:
        json.dump(data, f, indent=2)
    print ('Done! Saved to {}'.format(dst_pts_path))

    cv2.destroyAllWindows()


if __name__ == '__main__':
    template_path = '/home/darkalert/builds/sports-anno-tools/football_pitch/assets/pitch_template.png'
    dst_pts_path = '/home/darkalert/builds/sports-anno-tools/football_pitch/assets/template_points.json'
    mark_template_pts(template_path, dst_pts_path, num_pts=31)