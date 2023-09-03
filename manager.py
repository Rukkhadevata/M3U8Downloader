import download_core
import config
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
import mym3u8

headers = download_core.parse_header(config.header_file)


def launch_task(m3u8_url, task_name):
    task_dir = config.save_root / Path(task_name)
    save_arg(task_dir, m3u8_url, task_name)
    m3u8_file_remote = task_dir / f'{task_name}.old.m3u8'
    m3u8_file_local = task_dir / f'{task_name}.new.m3u8'