
import os
from pathlib import Path
from os.path import join
from glob import glob
from matplotlib import colors
from tqdm import tqdm
import numpy as np
from matplotlib.colors import ListedColormap
from concurrent.futures import ProcessPoolExecutor

from rohbau3d.misc.transformation import SphericalProjection

import argparse
import sys


ROHBAU3D_HEADER = """
    ____        __    __               _____ ____     __  __      __  
   / __ \____  / /_  / /_  ____ ___  _|__  // __ \   / / / /_  __/ /_ 
  / /_/ / __ \/ __ \/ __ \/ __ `/ / / //_ </ / / /  / /_/ / / / / __ \ 
 / _, _/ /_/ / / / / /_/ / /_/ / /_/ /__/ / /_/ /  / __  / /_/ / /_/ /
/_/ |_|\____/_/ /_/_.___/\__,_/\__,_/____/_____/  /_/ /_/\__,_/_.___/ 
>>> Rohbau3D Hub <<<
"""



ROHBAU3D_FEATURES = ["depth", "color", "intensity", "normal", "class", "instance"]

def _argparse():
    parser = argparse.ArgumentParser(description="Rohbau3D Panorama Rendering Script")
    parser.add_argument("--data", type=str, required=True, help="Path to the directory which contains the site or scan folders")
    parser.add_argument("--output", type=str, required=True, help="Path to the output directory")
    parser.add_argument("--features", default="all", help="Features list to render: all, depth, color, intensity, normal, class, instance")
    parser.add_argument("--upscale", type=int, default=4, help="Upscale factor for rendering")
    parser.add_argument("--crop", type=bool, default=True, help="Whether to crop the output images")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel workers")

    args = parser.parse_args()

    return args

def hex_to_rgb(hex_string):
    value = hex_string.lstrip('#')
    lv = len(value)
    return [int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3)]

def get_rohbau3d_class_cmap():
    ROHBAU3D_COLOR_MAP = {
        0: "#727274",
        1: "#FDA9A9",
        2: "#C78282",
        3: "#007AFF",
        4: "#3B9148",
        5: "#8686C0",
        6: "#89D6E4",
        7: "#911EB4",
        8: "#FF7300",
        9: "#2121E2",
        10: "#FF2D5A",
        11: "#93E09B",
        12: "#990000",
        13: "#FAA940",
        14: "#FF18E0",
        15: "#FFE119",
        16: "#B6CA00",
        17: "#00FF0D",
    }

    colors = [ROHBAU3D_COLOR_MAP[i] for i in sorted(ROHBAU3D_COLOR_MAP)]
    return ListedColormap(colors, name="rohbau3d")


def parse_feature_selection(feature_selection):
    if "all" in feature_selection:
        return ROHBAU3D_FEATURES
    
    valid_features = []
    for feature in ROHBAU3D_FEATURES:
        if feature in feature_selection:
            valid_features.append(feature)

    return valid_features


# Function to process one folder
def process_folder(folder_info, args):
    folder, output_dir = folder_info
    
    # Ensure that foldername starts with "scan"
    filename = os.path.basename(folder)
    if not filename.startswith("scene"):
        return


    # Attempt to load the files
    try:
        coord = np.load(join(folder, "coord.npy"))
    except Exception as e:
        print(f"Failed to load coord.npy in {folder}: {e}")
        return
    try:
        color = np.load(join(folder, "color.npy"))
    except:
        color = None
    try:
        intensity = np.load(join(folder, "intensity.npy"))
    except:
        intensity = None
    try:
        normal = np.load(join(folder, "normal.npy"))
    except:
        normal = None
    try:
        classes = np.load(join(folder, "class.npy"))
    except:
        classes = None
        print(f"Failed to load class.npy in {folder}, class image will not be rendered.")
    try:
        instance = np.load(join(folder, "instance.npy"))
    except:
        instance = None
        print(f"Failed to load instance.npy in {folder}, instance image will not be rendered.")

    # create output directory if it doesn't exist
    output_dir = join(output_dir, "panorama")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Render the point cloud to an image
    cmap = get_rohbau3d_class_cmap() if classes is not None else None
    renderer = SphericalProjection(coord, color=color, intensity=intensity, normal=normal, classes=classes, instance=instance, class_cmap=cmap)

    feature_selection = parse_feature_selection(args.features)
    if coord is not None and "depth" in feature_selection:
        img_depth = renderer.depth_image(normalize=True, upscale=args.upscale, crop=args.crop)
        img_depth.save(join(output_dir, f"depth.png"))

    if intensity is not None and "intensity" in feature_selection:
        img_intensity = renderer.intensity_image(upscale=args.upscale, crop=args.crop)
        img_intensity.save(join(output_dir, f"intensity.png"))

    if color is not None and "color" in feature_selection:
        img_color = renderer.color_image(upscale=args.upscale, crop=args.crop)
        img_color.save(join(output_dir, f"color.png"))
    
    if normal is not None and "normal" in feature_selection:
        img_normal = renderer.normal_image(upscale=args.upscale, crop=args.crop)
        img_normal.save(join(output_dir, f"normal.png"))

    if classes is not None and "class" in feature_selection:
        img_class = renderer.class_image(upscale=args.upscale, crop=args.crop)
        img_class.save(join(output_dir, f"class.png"))

    if instance is not None and "instance" in feature_selection:
        img_instance = renderer.instance_image(upscale=args.upscale, crop=args.crop)
        img_instance.save(join(output_dir, f"instance.png"))

    return filename



def main():

    args = _argparse()  

    input_dir = args.data
    output_dir = args.output
    num_workers = args.workers
    feature_selection = parse_feature_selection(args.features)    

    print("--- CONFIGURATION ------------------------------")
    print("  Input Directory:    ", input_dir)
    print("  Output Directory:   ", output_dir)
    print("  Features to Render: ", feature_selection)
    print("  Upscale Factor:     ", args.upscale)
    print("  Crop Images:        ", args.crop)
    print("  Number of Workers:  ", num_workers)
    print("------------------------------------------------")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # traverse the input dir and its subdirectories to list all folders starting with "scene"
    scenes = [p for p in Path(input_dir).rglob("scene*") if p.is_dir()]

    print(f"\nNumber of scans found: {len(scenes)}")

    # # Prepare arguments for parallel processing
    folder_info_list = []

    for scene_path in scenes:
        scene_name = os.path.basename(scene_path)

        site_path = Path(scene_path).parents[0]
        site_name = os.path.basename(site_path)
        site_output_dir = join(output_dir, site_name, scene_name)
        folder_info_list.append((scene_path, site_output_dir))

    # Use ProcessPoolExecutor for parallel processing
    print("Start rendering panoramas in parallel ...")
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(tqdm(executor.map(process_folder, folder_info_list, [args]*len(folder_info_list)), 
                            total=len(folder_info_list), 
                            desc="Rendering point clouds to panoramas"))

if __name__ == "__main__":
    print(ROHBAU3D_HEADER)

    print("/"*50)
    print(f"WARNING: File Deprecated!")
    print(f"WARNING: Please use the new script 'render_projections.py' to render Panoramic and CubeMap Feature representations.")
    print("/"*50)

    main()

    print("\nDone ...")

