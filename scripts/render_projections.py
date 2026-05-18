from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rohbau3d.render import render_from_config

ROHBAU3D_HEADER = """
    ____        __    __               _____ ____     __  __      __
   / __ \\____  / /_  / /_  ____ ___  _|__  // __ \\   / / / /_  __/ /_
  / /_/ / __ \\/ __ \\/ __ \\/ __ `/ / / //_ </ / / /  / /_/ / / / / __ \
 / _, _/ /_/ / / / / /_/ / /_/ / /_/ /__/ / /_/ /  / __  / /_/ / /_/ /
/_/ |_|\\____/_/ /_/_.___/\\__,_/\\__,_/____/_____/  /_/ /_/\\__,_/_.___/
>>> Rohbau3D Hub <<<
\n"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Rohbau3D point clouds to equirectangular panorama and/or cube map projections.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/render_projections.yaml"),
        help="Path to renderer YAML configuration.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s")
    log = logging.getLogger(__name__)
    log.info(f"\n{ROHBAU3D_HEADER}")
    log.info("/" * 50)
    log.info("/// Start rendering projections ...")

    render_from_config(args.config)

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
