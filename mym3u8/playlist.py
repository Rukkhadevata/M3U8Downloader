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
    Tag
    Segment
"""

from .tag import tag_manager, TagWithAttrList
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple
from io import StringIO
import urllib.parse
from collections import defaultdict
import math
import copy


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
class Cache:
    idx: int
    suffix: str
    category: str


class CacheNameAssigner:
    def __init__(self, root: str) -> None:
        self.root = root
        self.url2cache: Dict[str, Cache] = dict()
        self.cat2cache_list: Dict[str, List[Cache]] = defaultdict(list)
        self.category_counter: Dict[str, int] = defaultdict(int)

    def abs_uri(self, uri: str) -> str:
        return urllib.parse.urljoin(self.root, uri)

    def register_uri(self, uri: str, category: str):
        if not isinstance(category, str) or len(category) == 0:
            raise ValueError(f"{category} is not a category name")
        abs_uri = self.abs_uri(uri)
        if abs_uri in self.url2cache:
            return abs_uri, self.url2cache[abs_uri]

        counter = self.category_counter[category]
        self.category_counter[category] += 1
        suffix = Path(urllib.parse.urlparse(abs_uri).path).suffix
        cache = Cache(counter, suffix, category)
        self.url2cache[abs_uri] = cache
        self.cat2cache_list[category].append(category)

    def cache_name(self, uri: str, category: str):
        # 必须先调用一次 register_uri, 才能调用 cache_name
        # 目的是得到同类 category 的总数量，方便计算前导零的数量
        abs_uri = self.abs_uri(uri)
        cache = self.url2cache[abs_uri]
        counter = self.category_counter[category]
        if counter == 0:
            raise ValueError(f"category {category!r} is not registered")
        digit_num = math.floor(math.log10(counter)) + 1
        return f"{cache.idx:0{digit_num}d}{cache.suffix}"


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

    def fully_qualified(self, cache_name_assigner: CacheNameAssigner) -> str:
        return self.line_text

    def local(self, cache_name_assigner: CacheNameAssigner) -> str:
        return self.line_text

    def dump_uri(self, cache_name_assigner: CacheNameAssigner):
        pass


class BlankLine(M3U8Line):
    pass


class CommentLine(M3U8Line):
    pass


class TagLine(M3U8Line):
    def __init__(self, line_text):
        super().__init__(line_text)
        self.tag = tag_manager.get(line_text)

    def copy(self):
        return copy.deepcopy(self)

    def fully_qualified(self, cache_name_assigner: CacheNameAssigner) -> str:
        if isinstance(self.tag, TagWithAttrList):
            if 'URI' in self.tag:
                tag_line = self.copy()
                tag_line['URI'] = cache_name_assigner.abs_uri(self.tag['URI'])
                return str(tag_line)
        else:
            return self.line_text

    def local(self, cache_name_assigner: CacheNameAssigner) -> str:
        if isinstance(self.tag, TagWithAttrList):
            if 'URI' in self.tag:
                tag_line = self.copy()
                tag_line['URI'] = cache_name_assigner.cache_name(self.tag['URI'])
                return str(tag_line)
        else:
            return self.line_text

    def dump_uri(self, cache_name_assigner: CacheNameAssigner):
        if isinstance(self.tag, TagWithAttrList):
            if 'URI' in self.tag:
                cache_name_assigner.register_uri(self.tag.attr_list['URI'])


class URILine(M3U8Line):
    category = "uri_line"

    def fully_qualified(self, cache_name_assigner: CacheNameAssigner) -> str:
        return cache_name_assigner.abs_uri(self.line_text)

    def local(self, cache_name_assigner: CacheNameAssigner) -> str:
        return cache_name_assigner.cache_name(self.line_text, self.category)

    def dump_uri(self, cache_name_assigner: CacheNameAssigner):
        return cache_name_assigner.register_uri(self.line_text, self.category)


class Playlist(URI):
    def __init__(self, m3u8_url: str, content: str=None):
        self.url = m3u8_url
        if content is None:
            self.content = self.download()
        else:
            self.content = content
        self.lines: List[M3U8Line] = [M3U8Line.parse(line) for line in self.content.splitlines()]
        self.cache_name_assigner = CacheNameAssigner(m3u8_url)
        for line in self.lines:
            line.dump_uri(self.cache_name_assigner)
        self.lines_fully_qualified = [
            line.fully_qualified(self.cache_name_assigner) for line in self.lines
        ]
        self.lines_local = [line.local(self.cache_name_assigner) for line in self.lines]

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

    def download(self):
        from .import download_core
        with download_core.download(self.url, download_core.headers, 15, 1) as resp:
            return resp.content.decode('utf8')

