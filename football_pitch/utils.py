import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    '''
    Encoder for packing / unpacking NumPy arrays to / from json
    '''
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def reprojection_loss(pts1, pts2, nonzero=None, norm_size=None):
    '''
    Calculate the distance between the points
    '''
    p1 = np.copy(pts1)
    p2 = np.copy(pts2)
    if norm_size is not None:
        p1[:, 0] *= norm_size[0]
        p1[:, 1] *= norm_size[1]
        p2[:, 0] *= norm_size[0]
        p2[:, 1] *= norm_size[1]

    if nonzero is None:
        nonzero = np.ones(p1.shape[0], dtype=bool)

    dist = np.sqrt(np.sum(np.power(p1-p2,2), axis=1))
    num_nonzero = np.count_nonzero(nonzero, axis=0)
    loss = np.sum(dist * nonzero, axis=0) / num_nonzero

    return loss