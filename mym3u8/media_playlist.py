from dataclasses import dataclass
from typing import List, Optional, Tuple
from .tags.tag import Tag
from pathlib import Path
from . import playlist

    

@dataclass
class MediaSegment(playlist.URI):
    sequence_number: int

    @property
    def duration(self):
        return self.tags['EXTINF'].value


@dataclass
class MediaPlaylist(playlist.Playlist):
    uri_list: List[MediaSegment]

    @staticmethod
    def check_http_content_type(content_type: str):
        content_type = content_type.lower()
        assert (
            content_type == "application/vnd.apple.mpegurl"
            or content_type == "audio/mpegurl"
        )

    @property
    def duration(self):
        return sum(uri.duration for uri in self.uri_list)


