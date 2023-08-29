from dataclasses import dataclass
from typing import Optional, Any, List

@dataclass
class Attribute:
    key: str
    value: Any

@dataclass
class Tag:
    name: str
    value: Optional[str]
    attr_list: List[Attribute]
    is_global: bool