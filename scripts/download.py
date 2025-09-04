# rohbau3d script
# author: lukas rauch
# date: 2025-09-02

from rohbau3d.misc.config import load_config
from rohbau3d.misc.helper import session_summary
from rohbau3d.core.rohbau3d_hub import Rohbau3DHub

from rohbau3d.misc._logging import setup_logging
import logging
import argparse

def _argparse():
    parser = argparse.ArgumentParser(description="Rohbau3D Download Script")
    parser.add_argument("--config", type=str, required=True, help="Path to the config file")
    parser.add_argument("--download", action="store_true", help="Enable download")
    parser.add_argument("--extract", action="store_true", help="Enable extraction")
    args = parser.parse_args()

    return args


def main():

    args = _argparse()
    config = load_config(args.config)

    log_file = config.get("log_file", "logs") + "/rohbau3d.log"
    log_level = config.get("log_level", "DEBUG")

    setup_logging(log_file=log_file, level=log_level, to_console=True)
    log = logging.getLogger(__name__)
    log.info("/"*50)
    log.info(">>> Starting Rohbau3D download script ...")

    # LOGIT -----------------------------------------------------------
    rohbau3d = Rohbau3DHub(config)
    stats = {}

    # RUN ------------------------------------------------------------
    if not args.download and not args.extract:
        log.warning("No action specified. Use --download and/or --extract flags.")
        return
    else:
        if args.download:
            stats["download"] = rohbau3d.download()
        if args.extract:
            stats["extraction"] = rohbau3d.extract()

        # Exit
        if config.clean_download_files: 
            rohbau3d.clean_download_files()

        session_summary(stats)

    log.info("Done ...")



if __name__ == "__main__":
    main()