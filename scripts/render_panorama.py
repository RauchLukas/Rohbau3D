
import os
from pathlib import Path
from os.path import join
from glob import glob
from tqdm import tqdm
import numpy as np
from concurrent.futures import ProcessPoolExecutor

from rohbau3d.misc.transformation import SphericalProjection

import argparse


RHOBAU3D_HEADER = """
    ____        __    __               _____ ____     __  __      __  
   / __ \____  / /_  / /_  ____ ___  _|__  // __ \   / / / /_  __/ /_ 
  / /_/ / __ \/ __ \/ __ \/ __ `/ / / //_ </ / / /  / /_/ / / / / __ \ 
 / _, _/ /_/ / / / / /_/ / /_/ / /_/ /__/ / /_/ /  / __  / /_/ / /_/ /
/_/ |_|\____/_/ /_/_.___/\__,_/\__,_/____/_____/  /_/ /_/\__,_/_.___/ 
>>> Rohbau3D Hub <<<
"""

ROHBAU3D_FEATURES = ["depth", "color", "intensity", "normal"]

def _argparse():
    parser = argparse.ArgumentParser(description="Rohbau3D Panorama Rendering Script")
    parser.add_argument("--data", type=str, required=True, help="Path to the directory which contains the site or scan folders")
    parser.add_argument("--output", type=str, required=True, help="Path to the output directory")
    parser.add_argument("--features", default="all", help="Features list to render: all, depth, color, intensity, normal")
    parser.add_argument("--upscale", type=int, default=4, help="Upscale factor for rendering")
    parser.add_argument("--crop", type=bool, default=True, help="Whether to crop the output images")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel workers")

    args = parser.parse_args()

    return args

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
        segment = np.load(join(folder, "segment.npy"))
    except:
        segment = None
    try:
        instance = np.load(join(folder, "instance.npy"))
    except:
        instance = None

    # create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Render the point cloud to an image
    renderer = SphericalProjection(coord, color=color, intensity=intensity, normal=normal, segment=segment, instance=instance)

    feature_selection = parse_feature_selection(args.features)
    if coord is not None and "depth" in feature_selection:
        img_depth = renderer.depth_image(normalize=True, upscale=args.upscale, crop=args.crop)
        img_depth.save(join(output_dir, f"{filename}_depth.png"))

    if intensity is not None and "intensity" in feature_selection:
        img_intensity = renderer.intensity_image(upscale=args.upscale, crop=args.crop)
        img_intensity.save(join(output_dir, f"{filename}_intensity.png"))

    if color is not None and "color" in feature_selection:
        img_color = renderer.color_image(upscale=args.upscale, crop=args.crop)
        img_color.save(join(output_dir, f"{filename}_color.png"))
    
    if normal is not None and "normal" in feature_selection:
        img_normal = renderer.normal_image(upscale=args.upscale, crop=args.crop)
        img_normal.save(join(output_dir, f"{filename}_normal.png"))

    # TODO: Add segment and instance images

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

    # traverse the input dir and list all folders starting with "scene"
    scenes = [f for f in glob(os.path.join(input_dir, "*")) if os.path.isdir(f) and os.path.basename(f).startswith("scene")]

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
    print(RHOBAU3D_HEADER)
    main()

    print("\nDone ...")

