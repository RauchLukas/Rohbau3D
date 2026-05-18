# rohbau3d script
# author: lukas rauch
# date: 2025-09-02

import os
from os.path import join, exists
from pooch import DOIDownloader
from time import time

from rohbau3d.misc.helper import read_json_dict

import logging
log = logging.getLogger(__name__)


# DATAVERSE REGISTRY ---------------------------------------------

# Dedicated, determine registry from config set in rohbau3d_hub
# ---------------------------------------------------------------


class Dataverse:
    def __init__(self, cfg):
        self.cfg = cfg

        self.base_url = cfg.get("dataverse_base_url", None)
        self.output_dir = cfg["download_dir"]
        self.config_dir = cfg["config_dir"]

        self.feature_index_file = cfg.get("feature_index_file")
        self.feature_index = self._get_file_index(
            join(self.config_dir, self.feature_index_file))

        self.feature_selection = self._get_feature_selection()
        self.site_selection = self._get_site_selection()
        self.data_selection = self._get_data_selection()

        self.stats = {
            "path": self.output_dir,
            "num_files_downloaded": 0,
            "num_files_skipped": 0,
            "skipped_files": [],
            "corrupted_files": [],
            "total_time": 0,
        }

        log.info(">>> Dataverse hub initialized <<<")

    @staticmethod
    def summarize_data_selection(data_selection):
        summary = {}
        for feature, sites in data_selection.items():
            summary[feature] = {
                "num_sites": 0,
                "num_files": 0
            }
            for site_id, files in sites.items():
                summary[feature]["num_sites"] += 1
                summary[feature]["num_files"] += len(files)

        for key, value in summary.items():
            s = "sites" if value["num_sites"] > 1 else "site"
            p = "parts" if value["num_files"] > 1 else "part"
            log.info(
                f"{key:<20}: {value['num_sites']:<3} {s}, {value['num_files']:<3} {p}")

        log.info("-------------------------------------------------------------")
        log.info(
            f"Total number of download files: {sum(value['num_files'] for value in summary.values())}")
        log.info("-------------------------------------------------------------")

    def download(self):

        log.info("/" * 50)
        log.info("/// Starting download ...")

        log.info(f"Downloading files to {self.output_dir}")
        self.summarize_data_selection(self.data_selection)

        downloader = DOIDownloader(progressbar=True)

        start_time = time()
        for feature, sites in self.data_selection.items():
            for site_id, files in sites.items():
                for file_name in files:
                    # Construct the full URL for the file
                    url = f"{self.base_url}/{file_name}"

                    output_file = join(self.output_dir, feature, file_name)

                    if exists(output_file,):
                        log.info(
                            f"File {file_name} already exists, skipping download.")
                        self.stats["num_files_skipped"] += 1
                        self.stats["skipped_files"] = self.stats.get(
                            "skipped_files", []) + [file_name]
                        continue

                    os.makedirs(os.path.dirname(output_file), exist_ok=True)

                    # Download the file
                    try:
                        log.info(
                            f"🍕 Downloading {file_name} from {url} to {output_file}")
                        downloader(
                            url=url, output_file=output_file, pooch=None)
                        self.stats["num_files_downloaded"] += 1
                    except Exception as e:
                        log.error(f"Failed to download {file_name}: {e}")
                        self.stats["corrupted_files"].append(file_name)

        self.stats["total_time"] = time() - start_time

        log.info("/// Download completed.\n")
        return self.stats

    def _get_data_selection(self):
        database = self.feature_index

        # convert site_selection to id strings only for json indexing
        site_selection = [str(int(s.split("_")[-1]))
                          for s in self.site_selection]

        # compile a reduced dict
        data_selection = {}
        for feature in self.feature_selection:
            if feature not in database:
                log.warning(f"Feature '{feature}' not found in database.")
                continue
            data_selection[feature] = {}
            for site in site_selection:
                if site not in database[feature]:
                    log.warning(
                        f"Site '{site}' not found for feature '{feature}'.")
                    continue
                data_selection[feature][site] = database[feature][site]

        return data_selection

    @staticmethod
    def _get_file_index(path):
        try:
            database = read_json_dict(path)
            log.info(f"Dataverse File Index loaded from {path}:")
            return database
        except FileNotFoundError as e:
            log.error(e)
            return {}

    def _get_feature_selection(self):

        cfg_feature_selection = self.cfg.get("feature_selection", None)
        rohbau3d_feature_registry = self.cfg.get("rohbau3d_features", None)

        if cfg_feature_selection is None:
            log.warning("No feature selection provided, using all features.")
            return rohbau3d_feature_registry

        if cfg_feature_selection == "all" or next(
                iter(cfg_feature_selection)) == "all":
            return rohbau3d_feature_registry

        if type(cfg_feature_selection) is list:
            features = []
            for feature in cfg_feature_selection:
                if feature in rohbau3d_feature_registry:
                    features.append(feature)
                else:
                    log.warning(
                        f"Selected feature {feature} is not a valid feature. Skipping.")

            return features

    def _get_site_selection(self):
        cfg_site_selection = self.cfg.get("site_selection", None)
        rohbau3d_site_registry = self.cfg.get("rohbau3d_sites", None)

        if cfg_site_selection is None:
            log.warning("No site selection provided, using all sites.")
            return rohbau3d_site_registry

        if cfg_site_selection == "all" or next(
                iter(cfg_site_selection)) == "all":
            return rohbau3d_site_registry

        if type(cfg_site_selection) is list:
            sites = []
            for site in cfg_site_selection:
                if type(site) is int:
                    # convert to site_id string for lazy indexing
                    site = f"site_{site:02d}"
                if site in rohbau3d_site_registry:
                    sites.append(site)
                else:
                    log.warning(
                        f"Selected site {site} is not a valid site. Skipping.")

            return sites
