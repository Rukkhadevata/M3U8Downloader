from dataclasses import dataclass
from typing import Mapping, Optional, Any, List, Dict
import string
import re
from io import StringIO


@dataclass
class Attribute:
    key: str
    value: Any

    def __str__(self):
        return f"{self.key}={self.value}"


class AttributeList:
    name_charset = string.ascii_uppercase + string.digits + "-"

    def __init__(self, attr_text: str) -> None:
        self.attr_text = attr_text
        self.attr_list: List[Attribute] = []
        self.parse(attr_text)

    def parse(self, attr_text: str):
        pivot = 0
        state = "KEY"
        while pivot < len(attr_text):
            c = attr_text[pivot]
            if state == "KEY":
                attr_obj = Attribute(None, None)
                attr_obj.key, pivot = self.get_until_assigner(pivot)
                state = "KEY_END"
            elif state == "KEY_END":
                if c != "=":
                    self.__error_position(pivot, "Here should be a assigner")
                state = "VALUE"
            elif state == "VALUE":
                if c == '"':
                    attr_obj.value, pivot = self.get_quoted_str(pivot)
                else:
                    attr_obj.value, pivot = self.get_until_comma(pivot)
                self.attr_list.append(attr_obj)
                state = "VALUE_END"
            elif state == "VALUE_END":
                if c != ",":
                    self.__error_position(pivot, "Here should be a comma.")
                state = "KEY"
            pivot += 1

    def __error_position(self, reason, start, end=None):
        if end is None or end - start <= 0:
            end = start
        before_start_len = 0
        for c in self.attr_text[:start]:
            before_start_len += len(repr(c)) - 2  # minus 2 for quotation mark of repr
        error_len = 0
        for c in self.attr_text[start : end + 1]:
            error_len += len(repr(c)) - 2
        highlight_line = (
            " " * (before_start_len + 1) + "~" * error_len
        )  # plus 1 for first quotation mark
        raise ValueError(f"{self.attr_text!r}\n{highlight_line}\n{reason}")

    def get_quoted_str(self, pivot: int) -> str:
        """
        Return text and end pivot.
        text starts from the first quote to the first close quote
        pivot is pointing at the close quote.
        """
        buf = StringIO()
        c = self.attr_text[pivot]
        assert c == '"'
        buf.write(c)
        pivot += 1
        forbidden_char = {"\x0A", "\x0D"}
        while pivot < len(self.attr_text):
            c = self.attr_text[pivot]
            if c in forbidden_char:
                self.__error_position("forbidden character", pivot)
            else:
                buf.write(c)
                if c == '"':
                    break
            pivot += 1
        return buf.getvalue(), pivot

    def get_until_comma(self, pivot: int):
        """
        Return text and end pivot.
        text starts from the pivot to (the position that just
        before the first comma) or (the end of the text)
        pivot is pointing at the last character of the text.
        """
        buf = StringIO()
        while pivot < len(self.attr_text):
            c = self.attr_text[pivot]
            if c == ",":
                pivot -= 1
                break
            else:
                buf.write(c)
            pivot += 1
        return buf.getvalue(), pivot

    def get_until_assigner(self, pivot: int):
        """
        Return text and end pivot.
        text starts from the pivot to (the position that just
        before the first assignment sign)
        pivot is pointing at the last character of the text.
        """
        buf = StringIO()
        while pivot < len(self.attr_text):
            c = self.attr_text[pivot]
            if c == "=":
                pivot -= 1
                break
            else:
                if c not in self.name_charset:
                    self.__error_position(
                        f"{c!r} is not a valid character in attribute name", pivot
                    )
                buf.write(c)
            pivot += 1
        return buf.getvalue(), pivot

    def __str__(self):
        attr_list = []
        for attr in self.attr_list:
            attr_list.append(str(attr))
        return f'{",".join(attr_list)}'

    def __getitem__(self, key: str):
        for attr in self.attr_list:
            if attr.key == key:
                return attr.value
        raise KeyError(f"{key} does not exists in attribute list")

    def __setitem__(self, key: str, value: str):
        attr_list = self.attr_list
        for attr in attr_list:
            if attr.key == key:
                attr.value = value
                return
        raise KeyError(f"{key} does not exists in attribute list")

    def __contains__(self, key: str):
        for attr in self.attr_list:
            if attr.key == key:
                return True
        return False


class Tag:
    pattern: str

    def __init__(self, line_text: str) -> None:
        self.line_text: str = line_text

    @property
    def tag_name(self):
        return self.line_text.split(":", 1)[0]

    def __str__(self):
        return self.line_text


@dataclass
class TagManager:
    name2class: Dict[str, Tag]

    def get(self, line: str) -> Tag:
        tag_name = line.split(":", 1)[0]
        clazz = self.name2class.get(tag_name)
        if clazz is None:
            return Tag(line)
        else:
            return clazz(line)

    def register(self, clazz: Tag):
        tag_name, _ = clazz.pattern.split(":", 1)
        self.name2class[tag_name] = clazz
        return clazz


tag_manager = TagManager(dict())


class TagWithAttrList(Tag):
    attribute_list_placeholder = "<attribute-list>"

    def __init__(self, line_text):
        tag_name, tail_text = self.pattern.split(":", 1)
        assert (
            tail_text == self.attribute_list_placeholder
        ), f"{tag_name} has no attribute list"
        re_pattern = self.pattern.replace(
            self.attribute_list_placeholder, "(?P<attr_list>.*)"
        )
        attr_text = re.match(re_pattern, line_text, re.S).group("attr_list")
        self.attr_list = AttributeList(attr_text)
    
    def __getitem__(self, key: str):
        return self.attr_list[key]

    def __setitem__(self, key: str, value: str):
        self.attr_list[key] = value

    def __contains__(self, key: str):
        return key in self.attr_list

    def __str__(self):
        return re.sub(
            self.attribute_list_placeholder, str(self.attr_list), self.pattern
        )

    @property
    def line_text(self):
        return str(self)

@tag_manager.register
class EXT_X_KEY(TagWithAttrList):
    pattern = "#EXT-X-KEY:<attribute-list>"


@tag_manager.register
class EXT_X_MAP(TagWithAttrList):
    pattern = "#EXT-X-MAP:<attribute-list>"


@tag_manager.register
class EXT_X_DATERANGE(TagWithAttrList):
    pattern = "#EXT-X-DATERANGE:<attribute-list>"


@tag_manager.register
class EXT_X_MEDIA(TagWithAttrList):
    pattern = "#EXT-X-MEDIA:<attribute-list>"


@tag_manager.register
class EXT_X_STREAM_INF(TagWithAttrList):
    pattern = "#EXT-X-STREAM-INF:<attribute-list>"


@tag_manager.register
class EXT_X_I_FRAME_STREAM_INF(TagWithAttrList):
    pattern = "EXT-X-I-FRAME-STREAM-INF:<attribute-list>"


@tag_manager.register
class EXT_X_SESSION_DATA(TagWithAttrList):
    pattern = "#EXT-X-SESSION-DATA:<attribute-list>"


@tag_manager.register
class EXT_X_SESSION_KEY(TagWithAttrList):
    pattern = "#EXT-X-SESSION-KEY:<attribute-list>"


@tag_manager.register
class EXT_X_START(TagWithAttrList):
    pattern = "#EXT-X-START:<attribute-list>"


if __name__ == "__main__":
    tag3 = tag_manager.get(
        '#EXT-X-KEY:FUCK=123,GIRL=44.32,BOY=-334.2,MAIN=-4,YOU="ab3=e,r3,r",BABY=eNU3,RESOLUTION=1920x1080'
    )
    print(tag3)
    tag3["YOU"] = '"https://baidu.com"'
    print(tag3.line_text)

    try:
        tag3 = tag_manager.get(
            '#EXT-X-KEY:FUCK=12\t3,GIRL=44.32,BOY=-334.2,MAIN=-4,YOU="ab\n\r3=e",R3,r",BABY=eNU3,RESOLUTION=1920x1080'
        )
    except Exception as e:
        print(e)
