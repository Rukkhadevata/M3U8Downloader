from dataclasses import dataclass
from typing import List, Optional, Tuple
from .tag import Tag
from pathlib import Path
from .playlist import CacheNameAssigner, Playlist


@dataclass
class MediaPlaylist(Playlist):
    @staticmethod
    def check_http_content_type(content_type: str):
        content_type = content_type.lower()
        assert (
            content_type == "application/vnd.apple.mpegurl"
            or content_type == "audio/mpegurl"
        )

    def as_local(self, assigner: CacheNameAssigner):
        for line in self.lines:
            uri = line.get_uri()
            if uri:
                assigner.register_uri(uri)
        lines = []
        for line in self.lines:
            uri = line.get_uri()
            if uri:
                cache = assigner.get_cache(uri)
                local_uri = f"{cache.ext}/{assigner.cache_name(uri)}"
                local_line = line.replace_uri_with(local_uri)
            else:
                local_line = line.line_text
            lines.append(local_line)
        return lines
