from pathlib import Path
import logging.config
import logging.handlers

save_root = Path("cache")
header_file = Path("headers.txt")

m3u8_timeout = 5
m3u8_retry_times = 3
segment_timeout = 10
segment_retry_times = 3

editor = "vim"

config = {}


def dictConfig(dir):
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "simple": {
                    "format": "%(asctime)s [%(levelname)s] [%(module)s.%(funcName)s: %(lineno)d] - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "stream": "ext://sys.stdout",
                    "formatter": "simple",
                },
                "file_debug": {
                    "class": "logging.FileHandler",
                    "level": "DEBUG",
                    "filename": dir / 'debug.log',
                    "formatter": "simple",
                },
                "file_info": {
                    "class": "logging.FileHandler",
                    "level": "INFO",
                    "filename": dir / 'info.log',
                    "formatter": "simple",
                },
            },
            "loggers": {
                "fuck": {"level": "DEBUG", "handlers": ["console", "file_info", "file_debug"]},
            },
            "root": {"level": "DEBUG", "handlers": ["console", "file_info", "file_debug"]},
        }
    )
