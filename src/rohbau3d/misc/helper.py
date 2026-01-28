

import os
from tqdm import tqdm
from pathlib import Path
import re
import tarfile
import zstandard as zstd
import json

import logging

log = logging.getLogger(__name__)


def read_json_dict(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


def session_summary(stats:dict):
    # Implement a function to summarize the current session
    log.info("/"*50)
    log.info("Session Summary:")
    log.info("="*50)
    for key, value in stats.items():
        
        path = value.pop("path", None)
        time = value.pop("total_time", None)
        log.info(f"{key.upper()} Summary:")
        log.info(f"  Total Time: {time:.2f} seconds" if time else "  Total Time: N/A")
        log.info(f"  Path: {path}" if path else "  Path: N/A")

        for key, val in value.items():
            log.info(f"    > {key}: {val}")

        log.info("="*50)   
    return None


def extract_tar_zstd(zst_path, output_dir):
    """Extract a .tar.zst file directly into a folder without saving the intermediate .tar."""
    name = Path(zst_path).name

    with open(zst_path, "rb") as compressed:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(compressed) as reader:
            with tarfile.open(fileobj=reader, mode='r|') as tar:
                with tqdm(desc=f"📂 Extracting {name}", unit=" files") as pbar:
                    for member in tar:
                        tar.extract(member, path=output_dir)
                        pbar.update(1)


def extract_all_tar_zstd_parts(root_dir, output_root, feature):
    pattern = re.compile(r"site_(\d+)\.(\w+)\.part(\d+)\.tar\.zst$")

    stats = {
        "num_files_extracted": 0,
        "num_files_failed": 0,
        "corrupted_files": [],

    }

    feature_dir = Path(root_dir)
    for file_name in sorted(os.listdir(feature_dir)):
        match = pattern.match(file_name)
        if not match:
            continue

        site_id, feature_name, part_id = match.groups()
        if feature_name != feature:
            continue

        zst_path = feature_dir / file_name
        output_dir = Path(output_root)

        try:
            extract_tar_zstd(zst_path, output_dir)
            stats["num_files_extracted"] += 1
            log.info(f"Extracted {zst_path} to {output_dir}", extra={"no_console": True})
        except Exception as e:
            log.error(f"Failed to extract {zst_path}: {e}")
            stats["num_files_failed"] += 1
            stats["corrupted_files"].append(str(zst_path))
    return stats



# prefix components:
space =  '    '
branch = '│   '
# pointers:
tee =    '├── '
last =   '└── '

def tree(dir_path: Path, prefix: str=''):
    """A recursive generator, given a directory Path object
    will yield a visual tree structure line by line
    with each line prefixed by the same characters
    """    
    contents = list(dir_path.iterdir())
    # contents each get pointers that are ├── with a final └── :
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents):
        yield prefix + pointer + path.name
        if path.is_dir(): # extend the prefix and recurse:
            extension = branch if pointer == tee else space 
            # i.e. space because last, └── , above so no more |
            yield from tree(path, prefix=prefix+extension)