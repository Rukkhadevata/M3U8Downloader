"""
本地缓存该如何命名？
要求：
1. 同一个 url，出现多次，只下载一次（已知同一个key可能出现多次）
2. segment 的命名必须能反映先后顺序
3. tag 中的 url，可能可以用tag名+第一次出现的位次命名，又希望尽可能保全原名名（url中给出的）
4. url给出的命名不一定安全，要检查


存在冲突：既希望用 url 中的原名（不安全，可能重复，但能反映原问题），又希望用本地的递增名（安全、保证不重复）

segments 有可能长这样：
/hls/1/video.ts
/hls/2/video.ts
所以不能只用原 url 中的 name. key 可能和 segments 不在同一个域名，所以它们的 path 理论上可以重复（虽然极少见到）

考虑到本地的两份 m3u8 文件已经足够反应远程和本地之间的关系了，我决定使用本地的递增名，但是要带一个分类前缀,
每个 tag 有自己独立的递增变量，Segments / Playlists 也有自己独立的递增变量

获取到m3u8后，扫描所有行，解析所有URI

对于同一个URI，要保证只下载一次，cache name需要统一管理，每次遇到URI，将类别传递进cache管理器，生成cache name

M3U8Line
    BlankLine
    CommentLine
    TagLine
    URILine

每个 M3U8 文件都应该纳入 CacheNameAssigner 中，所以CNA应该放到 Playlist 之外，之后统一由下载器下载
"""

from .tag import TagManager, TagWithAttrList
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from io import StringIO
import urllib.parse
from collections import defaultdict
import math
import copy
import logging

logger = logging.getLogger(__name__)


@dataclass
class URI:
    url: str

    @property
    def is_m3u(self):
        return self.url.endswith(".m3u8") or self.url.endswith(".m3u")

    @property
    def is_ts(self):
        return self.url.endswith(".ts")

    def urlparse(self):
        return urllib.parse.urlparse(self.url)

    @property
    def urlpath(self):
        return self.urlparse().path


@dataclass
class M3U8Line:
    line_text: str

    @staticmethod
    def parse(line_text: str):
        if len(line_text) == 0:
            return BlankLine(line_text)
        if line_text.startswith("#"):
            # Lines that start with the character '#' are either comments or tags.
            if line_text.startswith("#EXT"):
                return TagLine(line_text)
            else:
                return CommentLine(line_text)
        else:
            return URILine(line_text)

    def replace_uri_with(self, uri: str) -> "M3U8Line":
        raise NotImplementedError

    def get_uri(self) -> str:
        pass


class BlankLine(M3U8Line):
    pass


class CommentLine(M3U8Line):
    pass


class TagLine(M3U8Line):
    def __init__(self, line_text):
        super().__init__(line_text)
        self.tag = TagManager.build_tag(line_text)

    def replace_uri_with(self, uri) -> "TagLine":
        if isinstance(self.tag, TagWithAttrList):
            if "URI" in self.tag:
                self.tag["URI"] = uri
                self.line_text = str(self.tag)

    def get_uri(self):
        if isinstance(self.tag, TagWithAttrList):
            if "URI" in self.tag:
                return self.tag.attr_list["URI"]


class URILine(M3U8Line):
    def replace_uri_with(self, uri: str) -> "URILine":
        self.line_text = uri

    def get_uri(self) -> str:
        return self.line_text


class Playlist(URI):
    def __init__(self, m3u8_url: str, content: str = None):
        self.url = m3u8_url
        if content is None:
            logger.info(f"Download m3u8 content from {m3u8_url}")
            self.content = self.download()
        else:
            self.content = content

        self.lines: List[M3U8Line] = [
            M3U8Line.parse(line) for line in self.content.splitlines()
        ]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(m3u8_url={self.url!r})"

    def is_master_playlist(self):
        for line in self.lines:
            if isinstance(line, URILine):
                if not URI(line.line_text).is_m3u:
                    return False
        return True

    def is_media_playlist(self):
        for line in self.lines:
            if isinstance(line, URILine):
                if URI(line).is_m3u:
                    return False
        return True

    def download(self) -> str:
        from . import download_core

        with download_core.download(self.url, download_core.headers, 15, 1) as resp:
            return resp.content.decode("utf8")

    def to_abs_playlist(self) -> "Playlist":
        playlist = copy.deepcopy(self)
        for line in playlist.lines:
            uri = line.get_uri()
            if uri is not None:
                fq_uri = urllib.parse.urljoin(playlist.url, uri)
                line.replace_uri_with(fq_uri)
        return playlist


@dataclass
class Cache:
    idx: int
    url: str
    ext: str


class CacheNameAssigner:
    """register urls and gives them"""

    def __init__(self) -> None:
        self.url2cache: Dict[str, Cache] = dict()
        self.ext2cache_list: Dict[str, List[Cache]] = defaultdict(list)
        self.ext_counter: Dict[str, int] = defaultdict(int)

    def register_uri(self, uri: str, ext: Optional[str] = None):
        if ext is None:
            ext = Path(uri).suffix[1:]
        if not isinstance(ext, str) or len(ext) == 0:
            raise ValueError(f"{ext} is not a valid extension name")
        if uri in self.url2cache:
            return self.url2cache[uri]

        counter = self.ext_counter[ext]
        self.ext_counter[ext] += 1
        cache = Cache(counter, uri, ext)
        self.url2cache[uri] = cache
        self.ext2cache_list[ext].append(cache)
        return cache

    def register_playlist_uri(self, playlist: Playlist):
        self.register_uri(playlist.url, ext="m3u8")
        for line in playlist.to_abs_playlist().lines:
            uri = line.get_uri()
            if uri is not None:
                self.register_uri(uri)

    def get_cache(self, uri: str):
        return self.url2cache[uri]

    def cache_name(self, uri: str):
        # 必须先调用一次 register_uri, 才能调用 cache_name
        # 目的是得到同 ext 的总数量，方便计算前导零的数量
        cache = self.url2cache[uri]
        counter = self.ext_counter[cache.ext]
        if counter == 0:
            raise ValueError(f"suffix {cache.ext!r} is not registered")
        digit_num = math.floor(math.log10(counter)) + 1
        if URI(uri).is_m3u:
            return f"{cache.ext}/{cache.idx:0{digit_num}d}.local.{cache.ext}"
        else:
            return f"{cache.ext}/{cache.idx:0{digit_num}d}.{cache.ext}"


def to_local_playlist(playlist: Playlist, cna: CacheNameAssigner) -> Playlist:
    playlist = copy.deepcopy(playlist)
    for line in playlist.lines:
        uri = line.get_uri()
        if uri is not None:
            fq_uri = urllib.parse.urljoin(playlist.url, uri)
            cache_name = cna.cache_name(fq_uri)
            line.replace_uri_with(cache_name)
    return playlist
