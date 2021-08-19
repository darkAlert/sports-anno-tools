import cv2
import numpy as np


def display_confirmation(title, text):
    image = np.zeros((200, 700, 3), np.uint8)
    cv2.putText(image, text,
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), thickness=2)
    cv2.imshow(title, image)
    while True:
        key = cv2.waitKey()
        ret = None
        if key in (ord('y'), ord('Y')):
            ret = True
        elif key in (ord('n'), ord('N')):
            ret = False

        if ret is not None:
            cv2.destroyWindow(title)
            #cv2.waitKey(0)
            return ret
