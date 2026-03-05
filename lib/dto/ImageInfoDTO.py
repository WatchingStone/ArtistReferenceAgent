# 在 main.py 或单独的 dto.py 文件中定义
from dataclasses import dataclass
from typing import Optional, Dict, Any
from PyQt5.QtGui import QPixmap
from PIL import Image


@dataclass
class ImageInfoDTO:
    """图片信息数据传输对象"""
    url: str
    # pixmap: Optional[QPixmap] = None
    # image: Optional[Image] = None  # 图片数据由缓存类保存，无需在DTO中保存
    score: Optional[float] = None  # 图片与原本文的相似度得分
    # 不重要的部分
    tags: Optional[list] = None  # 图片标签
    title: Optional[str] = None
    source: Optional[str] = None        # 图片来源
    description: Optional[str] = None   # 图片描述

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
