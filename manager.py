"""
对于m3u8文件，我希望将3种形式都保存成cache（3种内容，3种文件名）
对于ts、key文件，我只希望保存它们原本的形式（仅本地文件名）
m3u8的local形式需要指向本地文件名，不仅是ts、key文件，还有m3u8文件

media playlist 内部出现的 URI 以 media playlist 的 URI 为 root
master playlist 可以和 media playlist 处于不同的目录，所以不能以最外层、最原始的 master playlist 作为所有 URI 的 root
每个 media playlist 内部必须自己维护一个 cache name assigner


"""
import mym3u8.download_core as download_core
import config
from pathlib import Path
from typing import List, Dict, Tuple
import mym3u8
import json
import logging
import copy
import urllib.parse

download_core.headers = download_core.parse_header(config.header_file)
logger = logging.getLogger(__name__)


def save_arg(task_dir: Path, m3u8_url: str, task_name: str):
    task_dir.mkdir(exist_ok=True)
    (task_dir / "launch_args.json").write_text(
        json.dumps({"task_name": task_name, "m3u8_url": m3u8_url})
    )


def dump_m3u8(task_dir: Path,
    playlist: mym3u8.Playlist,  assigner: mym3u8.CacheNameAssigner
):
    (task_dir / 'm3u8').mkdir(exist_ok=True)
    cache = assigner.get_cache(playlist.url)
    original = task_dir / f"m3u8/{cache.idx}.original.{cache.ext}"
    original.write_text(
        "".join(line.line_text + "\n" for line in playlist.lines),
        encoding="utf8",
    )

    absolute = task_dir / f"m3u8/{cache.idx}.absolute.{cache.ext}"
    absolute.write_text(
        "".join(line.line_text + "\n" for line in playlist.to_abs_playlist().lines),
        encoding="utf8",
    )

    local = task_dir / f"m3u8/{cache.idx}.local.{cache.ext}"
    local.write_text(
        "".join(
            line.line_text + "\n" for line in mym3u8.to_local_playlist(playlist, assigner).lines
        ),
        encoding="utf8",
    )

def download_resources(cna: mym3u8.CacheNameAssigner):
    pass


def launch_task(m3u8_url, task_name):
    task_dir = config.save_root / task_name
    save_arg(task_dir, m3u8_url, task_name)
    logger.info(f"task dir: {task_dir}")
    config.dictConfig(task_dir)
    playlists: List[mym3u8.Playlist] = []
    cna = mym3u8.CacheNameAssigner()
    while True:
        playlist = mym3u8.Playlist(m3u8_url)
        playlists.append(playlist)
        cna.register_playlist_uri(playlist)
        if playlist.is_master_playlist():
            logger.info(
                f"{playlist!r} is a master playlist. Ask user to select a sub playlist"
            )
            playlist = mym3u8.MasterPlaylist(playlist)
            m3u8_url = playlist.select_playlist()
        else:
            break

    for playlist in playlists:
        dump_m3u8(task_dir, playlist, cna)
    download_resources(cna)

