from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from rohbau3d.core.io import save_feature_dict_pcd, pack_rgb
from rohbau3d.misc._logging import setup_logging


# -----------------------------
# Worker
# -----------------------------

def _parse_scene_worker(args: Tuple[int, Path, Path, Path]) -> Tuple[int, str, bool, str]:
    """Parse a single scene directory into a .pcd file.

    Returns (idx, scene_name, success, message)
    """
    idx, scene_dir, source_dir, target_dir = args

    try:
        # Ensure paths
        scene_dir = Path(scene_dir)
        source_dir = Path(source_dir)
        target_dir = Path(target_dir)

        # Source/target paths
        source_path = scene_dir  # scene_dir is absolute within source tree
        site_name = scene_dir.parent.name
        scene_name = scene_dir.name
        out_dir = target_dir / site_name
        out_dir.mkdir(parents=True, exist_ok=True)
        target_path = out_dir / f"{scene_name}.pcd"

        # Mandatory coord
        coord_path = source_path / "coord.npy"
        if not coord_path.exists():
            return idx, scene_name, False, f"No coord.npy in {source_path}"
        coord = np.load(coord_path)

        # Optional features
        def _try_load(name: str) -> Optional[np.ndarray]:
            p = source_path / f"{name}.npy"
            if p.exists():
                try:
                    return np.load(p)
                except Exception as e:
                    return None
            return None

        color = _try_load("color")
        intensity = _try_load("intensity")
        normal = _try_load("normal")
        semantics = _try_load("semantics")
        instances = _try_load("instances")

        # Pack color if present
        if color is not None:
            if color.dtype != np.uint8 or color.max() <= 1.0:
                # If values are in [0,1], scale to [0,255]
                if color.max() <= 1.0:
                    color = (color * 255.0).astype(np.uint8)
                else:
                    color = color.astype(np.uint8)
            # Expect shape (N,3)
            if color.ndim != 2 or color.shape[1] != 3:
                return idx, scene_name, False, f"color.npy has invalid shape {color.shape}"
            rgb = pack_rgb(color[:, 0], color[:, 1], color[:, 2])
        else:
            rgb = None

        feature_dict = {"coord": coord}
        if rgb is not None:
            feature_dict["color"] = rgb
        if intensity is not None:
            feature_dict["intensity"] = intensity
        if normal is not None:
            feature_dict["normal"] = normal
        if semantics is not None:
            feature_dict["semantics"] = semantics
        if instances is not None:
            feature_dict["instances"] = instances

        # Save PCD
        save_feature_dict_pcd(str(target_path), feature_dict)
        return idx, scene_name, True, f"Saved {target_path}"

    except Exception as e:
        return idx, str(scene_dir.name), False, f"Error: {e}"


# -----------------------------
# Main
# -----------------------------

def main():
    """Multiprocess converter.

    Adjust `source_dir`, `target_dir`, and `max_workers` below or hook this up to argparse.
    """
    setup_logging(log_file="logs/parse_rb3d_to_pcd.log", level="INFO", to_console=True)
    log = logging.getLogger(__name__)

    # --- CONFIG ---
    source_dir = Path(r"Q:\PunktWolken\rohbau3d_v2")
    target_dir = Path(r"D:\PunktWolken\rohbau3d_v2\basic ai\20250916_datatransfer\rohbau3d")
    # max_workers = max(1, (os.cpu_count() or 4) - 1)  # leave one core free
    max_workers = 2
    # -------------

    log.info("/" * 50)
    log.info("Starting converting Rohbau3D to .pcd ...")
    log.info("/" * 50)
    log.info(f"Source: {source_dir}")
    log.info(f"Target: {target_dir}")
    log.info(f"Workers: {max_workers}")

    # Find sites and scenes
    site_list = [p for p in source_dir.iterdir() if p.is_dir() and p.name.startswith("site_")]
    scenes_list = []
    for site_path in site_list:
        scenes_list.extend([p for p in site_path.iterdir() if p.is_dir() and p.name.startswith("scene_")])

    num_scenes = len(scenes_list)
    log.info(f"Parsing {num_scenes} scenes from source directory.")
    log.info("-" * 50)

    if num_scenes == 0:
        log.warning("No scenes found. Exiting.")
        return

    # Build task args
    tasks = [(i, scenes_list[i], source_dir, target_dir) for i in range(num_scenes)]

    # Submit to process pool
    completed = 0
    ok = 0
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=None) as ex:
        futures = [ex.submit(_parse_scene_worker, t) for t in tasks]
        for fut in as_completed(futures):
            idx, scene_name, success, message = fut.result()
            completed += 1
            ok += int(success)
            if success:
                log.info(f"[{completed}/{num_scenes}] OK - {scene_name} -> {message}")
            else:
                log.warning(f"[{completed}/{num_scenes}] FAIL - {scene_name} -> {message}")

    log.info("-" * 50)
    log.info(f"Done. {ok}/{num_scenes} scenes converted.")
    log.info("/" * 50)


if __name__ == "__main__":
    main()
