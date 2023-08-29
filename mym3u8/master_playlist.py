from dataclasses import dataclass
from . import playlist, media_playlist

@dataclass
class VariantStream:
    pass

@dataclass
class MasterPlaylist(playlist.Playlist):
    pass