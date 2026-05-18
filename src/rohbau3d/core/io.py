

import numpy as np
from os.path import join
from pypcd4 import PointCloud
import os

ROHBAU3D_REGISTRY = {
    "coord": {
        "fields": ("x", "y", "z"),
        "types": (np.float32, np.float32, np.float32)
    },
    "color": {
        "fields": ("rgb",),
        "types": (np.float32,)
    },
    "intensity": {
        "fields": ("intensity",),
        "types": (np.float32,)
    },
    "normal": {
        "fields": ("normal_x", "normal_y", "normal_z"),
        "types": (np.float32, np.float32, np.float32)
    },
    # "semantics": {
    #     "fields": ("semantic",),
    #     "types": (np.uint16,)
    # },
    # "instances": {
    #     "fields": ("instance",),
    #     "types": (np.uint16,)
    # }
}


def pack_rgb(r, g, b):
    """Pack 3 uint8 color channels into a single float32 using PCL/PCD layout"""
    rgb_uint32 = (
        r.astype(
            np.uint32) << 16) | (
        g.astype(
            np.uint32) << 8) | b.astype(
        np.uint32)
    rgb_float32 = rgb_uint32.view(np.float32)
    return rgb_float32


def save_feature_dict_pcd(path, data_dict):

    os.makedirs(os.path.dirname(path), exist_ok=True)

    points = ()
    fields = ()
    types = ()

    for key, array in data_dict.items():

        if key in ROHBAU3D_REGISTRY:
            points += (array,)
            fields += ROHBAU3D_REGISTRY[key]["fields"]
            types += ROHBAU3D_REGISTRY[key]["types"]
        else:
            raise ValueError(
                f"Feature '{key}' not recognized. Available features: {
                    list(
                        ROHBAU3D_REGISTRY.keys())}")

    points = np.column_stack(points)

    pc = PointCloud.from_points(points, fields=fields, types=types)
    pc.save(fp=path)
