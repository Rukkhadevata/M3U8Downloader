import download_core
import config
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
import mym3u8

headers = download_core.parse_header(config.header_file)

@dataclass
class RemoteFile:
    idx: int
    url_remote: str
    file_local: Path
    tag_list: List[str]


@dataclass
class M3U8File:
    m3u8_url: str
    segment_list: List[RemoteFile]
    m3u8_list: List[RemoteFile]

    @property
    def is_m3u8_list(self):
        return len(self.m3u8_list) > 0

    @property
    def is_segment_list(self):
        return len(self.segment_list) > 0

    def check_weird(self):
        if self.is_m3u8_list and self.is_segment_list:
            raise ValueError('Both m3u8_list and segment list exist, which is a weird file')
        elif not self.is_m3u8_list and not self.is_segment_list:
            raise ValueError('Both m3u8_list and segment list not exist, which is a weird file')

def launch_task(m3u8_url, task_name):
    task_dir = config.save_root / Path(task_name)
    save_arg(task_dir, m3u8_url, task_name)
    m3u8_file_remote = task_dir / f'{task_name}.old.m3u8'
    m3u8_file_local = task_dir / f'{task_name}.new.m3u8'