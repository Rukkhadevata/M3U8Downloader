from .tags.tag import Tag
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

@dataclass
class URI:
    text: str
    cache_path: Path
    tags: Dict[str, Tag]

    @property
    def is_m3u(self):
        assert self.text.endswith(".m3u8") or self.text.endswith(".m3u")

    @property
    def is_ts(self):
        assert self.text.endswith(".ts")

class Playlist(URI):
    uri_list: List[URI]