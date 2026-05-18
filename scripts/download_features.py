# date: 2026-01-28

import os
from zipfile import Path
import pathlib

from pooch import DOIDownloader

from rohbau3d.misc._logging import setup_logging
import logging
import argparse
from rohbau3d.misc.helper import tree

ROHBAU3D_HEADER = """
    ____        __    __               _____ ____     __  __      __
   / __ \\____  / /_  / /_  ____ ___  _|__  // __ \\   / / / /_  __/ /_
  / /_/ / __ \\/ __ \\/ __ \\/ __ `/ / / //_ </ / / /  / /_/ / / / / __ \
 / _, _/ /_/ / / / / /_/ / /_/ / /_/ /__/ / /_/ /  / __  / /_/ / /_/ /
/_/ |_|\\____/_/ /_/_.___/\\__,_/\\__,_/____/_____/  /_/ /_/\\__,_/_.___/
>>> Rohbau3D Hub <<<
"""

FILE_LIST = [
    "site_00_feature_compendium.pdf",
    "site_01_feature_compendium.pdf",
    "site_02_feature_compendium.pdf",
    "site_03_feature_compendium.pdf",
    "site_04_feature_compendium.pdf",
    "site_05_feature_compendium.pdf",
    "site_06_feature_compendium.pdf",
    "site_07_feature_compendium.pdf",
    "site_08_feature_compendium.pdf",
    "site_09_feature_compendium.pdf",
    "site_10_feature_compendium.pdf",
    "site_11_feature_compendium.pdf",
    "site_12_feature_compendium.pdf",
    "site_13_feature_compendium.pdf",
]


def _argparse():
    parser = argparse.ArgumentParser(
        description="Rohbau3D: Feature Compendium Download Script")
    parser.add_argument(
        "--dir",
        type=str,
        required=True,
        help="Output directory for downloaded features")
    args = parser.parse_args()

    return args


def main():
    args = _argparse()

    output_dir = args.dir

    # create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # initialize Dataverse API downloader
    print(
        "connecting to \033[38;5;208mDataverse @ Open Data UniBw Munich\033[0m ...")
    downloader = DOIDownloader()

    counter = 0
    for i, file_name in enumerate(FILE_LIST):
        url = f"doi:10.60776/ZWJFI4/{file_name}"
        output_file = os.path.join(output_dir, file_name)

        print(
            f"Downloading file {i + 1}/{len(FILE_LIST)}: {file_name} ... \r", end="")
        try:
            # fetch the file
            downloader(url=url, output_file=output_file, pooch=None)
            counter += 1
        except Exception as e:
            print(f"Failed to download {file_name}: {e}")
            continue

    print(f"\nSuccessfully downloaded {counter}/{len(FILE_LIST)} files.")
    print("\nDirectory structure:")
    print(output_dir + "/")
    for line in tree(pathlib.Path(output_dir)):
        print(line)


if __name__ == "__main__":
    print(ROHBAU3D_HEADER)
    main()

    print("\nDone ...")
