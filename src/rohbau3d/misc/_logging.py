from __future__ import annotations
from pathlib import Path
import logging
import logging.config


_DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s:%(lineno)d — %(message)s"

class SkipConsoleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # If a record carries no_console=True, drop it from the console handler
        return not getattr(record, "no_console", False)

def setup_logging(
    log_file: str | Path,
    level: str = "INFO",
    *,
    to_console: bool = False,
    rotate: bool = True,
    max_bytes: int = 10_000_000,
    backup_count: int = 5,
) -> None:
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Choose file handler class
    file_handler_class = (
        "logging.handlers.RotatingFileHandler" if rotate else "logging.FileHandler"
    )

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "std": {"format": _DEFAULT_FORMAT},
        },
        "filters": {
            # IMPORTANT: use your package path here
            "skip_console": {"()": "rohbau3d.misc._logging.SkipConsoleFilter"},
        },
        "handlers": {
            "file": {
                "class": file_handler_class,
                "level": level,
                "formatter": "std",
                "filename": str(log_path),
                "encoding": "utf-8",
                **({"maxBytes": max_bytes, "backupCount": backup_count} if rotate else {}),
            },
        },
        "root": {
            "level": level,
            "handlers": ["file"],
        },
    }

    if to_console:
        # Send console output to stderr to play nicely with tqdm
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": level,
            "formatter": "std",
            "filters": ["skip_console"],
            "stream": "ext://sys.stderr",
        }
        config["root"]["handlers"].append("console")

    logging.config.dictConfig(config)
