# rohbau3d script
# author: lukas rauch
# date: 2025-09-02

from os.path import join, exists
from pathlib import Path
import shutil
from time import time

from rohbau3d.misc.helper import extract_all_tar_zstd_parts

import logging
log = logging.getLogger(__name__)


ROHBAU3D_HEADER = """
    ____        __    __               _____ ____     __  __      __
   / __ \\____  / /_  / /_  ____ ___  _|__  // __ \\   / / / /_  __/ /_
  / /_/ / __ \\/ __ \\/ __ \\/ __ `/ / / //_ </ / / /  / /_/ / / / / __ \
 / _, _/ /_/ / / / / /_/ / /_/ / /_/ /__/ / /_/ /  / __  / /_/ / /_/ /
/_/ |_|\\____/_/ /_/_.___/\\__,_/\\__,_/____/_____/  /_/ /_/\\__,_/_.___/
>>> Rohbau3D Hub <<<
\n"""


# DATAVERSE REGISTRY ---------------------------------------------

DATAVERSE_BASE_URL = "doi:10.60776/ZWJFI4"

ROHBAU3D_FEATURES = [
    "coord",
    "color",
    "intensity",
    "normal",
    "class",
    "instance",
    "sample_idx",
    "inv_sample_idx",
    "metadata",
]

ROHBAU3D_SITES = [
    "site_00", "site_01", "site_02", "site_03",
    "site_04", "site_05", "site_06", "site_07",
    "site_08", "site_09", "site_10", "site_11",
    "site_12", "site_13",
]
# ---------------------------------------------------------------


class Rohbau3DHub:
    def __init__(self, cfg):
        print(ROHBAU3D_HEADER)

        self.cfg = cfg

        # log the configuration settings
        log.info(">>> Rohbau3D Hub Configuration <<<")
        log.info("-" * 50)
        for key, value in self.cfg.items():
            log.info(f"   {key:<25}: {value}")

        log.info("-" * 50 + "\n")

        self.cfg["dataverse_base_url"] = DATAVERSE_BASE_URL
        self.cfg["rohbau3d_features"] = ROHBAU3D_FEATURES
        self.cfg["rohbau3d_sites"] = ROHBAU3D_SITES

        self.feature_selection = cfg.get("feature_selection")
        if self.feature_selection == "all" or self.feature_selection == [
                "all"]:
            self.feature_selection = ROHBAU3D_FEATURES

        self.hub = self.get_hub(cfg["download_hub"])
        self.download = self.hub.download

    def get_hub(self, hub: str):
        if hub.lower() == "default":
            from rohbau3d.core.dataverse import Dataverse
            hub = Dataverse(self.cfg)

        if hub.lower() == "dataverse":
            from rohbau3d.core.dataverse import Dataverse
            hub = Dataverse(self.cfg)

        return hub

    def extract(self):

        download_dir = self.cfg["download_dir"]
        extract_dir = self.cfg["extract_dir"] + "/rohbau3d"

        log.info("/" * 50)
        log.info("/// Starting extraction ...")
        log.info(f"Extracting files to PATH: {extract_dir}")

        stats = {
            "path": extract_dir,
            "num_files_extracted": 0,
            "num_files_failed": 0,
            "total_time": 0
        }

        start_time = time()
        for feature in self.feature_selection:
            feature_dir = Path(download_dir, feature)
            if not feature_dir.exists():
                log.warning(
                    f"Feature directory {feature_dir} does not exist, skipping extraction.")
                continue

            temp_stats = extract_all_tar_zstd_parts(
                feature_dir, Path(extract_dir), feature=feature)

            stats["num_files_extracted"] += temp_stats["num_files_extracted"]
            stats["num_files_failed"] += temp_stats["num_files_failed"]
            stats["corrupted_files"] = stats.get(
                "corrupted_files", []) + temp_stats.get("corrupted_files", [])

        stats["total_time"] = time() - start_time

        log.info("/// Extraction completed.\n")
        return stats

    def clean_download_files(self):
        # Implement file cleanup logic here
        download_dir = Path(self.cfg["download_dir"])

        if download_dir.exists():
            log.info(
                f"Cleaning downloaded features {ROHBAU3D_FEATURES} in PATH: {download_dir}")

            for feature in ROHBAU3D_FEATURES:
                path = join(download_dir, feature)
                if exists(path):
                    log.info(f"Removing {path}")
                    shutil.rmtree(path)

        return True
