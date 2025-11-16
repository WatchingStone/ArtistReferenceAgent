# 在 main.py 或单独的 dto.py 文件中定义
from dataclasses import dataclass
from typing import Optional, Dict, Any
from PyQt5.QtGui import QPixmap


@dataclass
class ImageInfoDTO:
    """图片信息数据传输对象"""
    url: str
    pixmap: Optional[QPixmap] = None
    title: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageInfoDTO':
        """从字典创建 DTO 实例"""
        return cls(
            url=data.get('url', ''),
            title=data.get('title'),
            source=data.get('source'),
            description=data.get('description'),
            tags=data.get('tags', []),
        )
