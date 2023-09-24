from dataclasses import dataclass
from . import playlist, media_playlist
from .playlist import CacheNameAssigner, Playlist, URILine
from urllib.parse import urljoin
from pathlib import Path
import logging
import copy

logger = logging.getLogger(__name__)


@dataclass
class VariantStream:
    pass


@dataclass
class MasterPlaylist:
    def __init__(self, playlist: Playlist):
        self.playlist = playlist

    def select_playlist(self):
        m3u8_urls = []
        for line in self.playlist.lines:
            if isinstance(line, URILine):
                abs_line = urljoin(self.playlist.url, line.line_text)
                print(f"[{len(m3u8_urls)}] {abs_line}")
                m3u8_urls.append(abs_line)
            else:
                print(line.line_text)

        while True:
            try:
                user_choice = int(
                    input(f"Please choose a url [0 ~ {len(m3u8_urls)-1}]:")
                )
                if 0 <= user_choice < len(m3u8_urls):
                    return m3u8_urls[user_choice]
                else:
                    logger.info(f"User enter [{user_choice}], which is out of index.")
            except Exception as e:
                logger.exception("Exception happended.")
                continue
