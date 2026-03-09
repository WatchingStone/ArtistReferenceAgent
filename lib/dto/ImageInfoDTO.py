# 在 main.py 或单独的 dto.py 文件中定义
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ImageInfoDTO:
    """图片信息数据传输对象"""
    url: str
    # image: Optional[Image] = None  # 图片数据由缓存类保存，无需在DTO中保存
    score: Optional[float] = None       # 图片与原本文的相似度得分
    # 不重要的部分
    local_path: Optional[str] = None    # 图片本地存储路径，主要用于本地向量数据集
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
            tags=data.get('tags'),
            local_path=data.get('local_path'),
            score=data.get('score')
        )

    def __init__(self, url: str = "", title: str = "", source: str = "",
                 description: str = "", tags: list = None,
                 local_path: str = None, score: float = None):
        super().__init__()
        self.url = url
        self.title = title
        self.source = source
        self.description = description
        self.tags = tags if tags is not None else []
        self.local_path = local_path
        self.score = score

    def to_dict(self) -> dict:
        """将 DTO 转换为字典"""
        return {
            'url': self.url,
            'title': self.title,
            'source': self.source,
            'description': self.description,
            'tags': self.tags,
            'local_path': self.local_path,
            'score': self.score
        }




