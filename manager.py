import mym3u8.download_core as download_core
import config
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
import mym3u8
import json
from mym3u8.download_core import download
from urllib.parse import urljoin
download_core.headers = download_core.parse_header(config.header_file)


def save_arg(task_dir: Path, m3u8_url: str, task_name: str):
    task_dir.mkdir(exist_ok=True)
    (task_dir / "launch_args.json").write_text(
        json.dumps({"task_name": task_name, "m3u8_url": m3u8_url})
    )


def select_playlist(playlist: mym3u8.Playlist):
    m3u8_urls = []
    for line in playlist.lines:
        if isinstance(line, mym3u8.URILine):
            print(f"[{len(m3u8_urls)}] {line.line_text}")
            m3u8_urls.append(line.line_text)
        else:
            print(line.line_text)

    while True:
        try:
            user_choice = int(input(f"Please choose a url(0~{len(m3u8_urls)-1}):"))
            if 0 <= user_choice < len(m3u8_urls):
                return urljoin(playlist.url, m3u8_urls[user_choice])
        except Exception:
            continue


def launch_task(m3u8_url, task_name):
    task_dir = config.save_root / Path(task_name)
    save_arg(task_dir, m3u8_url, task_name)
    m3u8_file_original = task_dir / f"{task_name}.original.m3u8"
    m3u8_file_local = task_dir / f"{task_name}.local.m3u8"
    m3u8_file_abs = task_dir / f"{task_name}.abs.m3u8"
    while (playlist := mym3u8.Playlist(m3u8_url)).is_master_playlist():
        m3u8_url = select_playlist(playlist)
    print(playlist)

launch_task(
    'https://d3b4hd2s3d140t.cloudfront.net/douyin/20210921/GW8B8vC6/index.m3u8',
    'asd'
)