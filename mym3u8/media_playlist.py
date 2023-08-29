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


    def parse(content: str):
        lines = content.splitlines()
        lid = 0
        global_tags = []
        temporary_tags = []
        sequence_number = 0
        uri_list = []
        while lid < len(lines):
            line = lines[lid]
            if len(line) == 0: continue # Blank lines are ignored
            if line.startswith('#'):
                if line.startswith('#EXT'):
                    tag = Tag(line)
                else:
                    continue
            else:
                uri_list.append(URI(line, None, global_tags+temporary_tags))
                temporary_tags.clear()
