# /lib/dto/SearchResultDTO.py
# 搜索结果DTO类
from typing import Dict, List, Any
from datetime import datetime

class SearchResultDTO:
    """搜索结果数据传输对象"""
    def __init__(self):
        self.success: bool = False                    # 搜索是否成功的标志
        self.keywords: Dict[str, List[str]] = {}      # 提取的关键词字典，按类别分类
        self.queries: List[str] = []                  # 生成的查询语句列表
        self.results: List[str] = []                  # 图片URL列表
        self.timestamp: datetime = datetime.now()     # 搜索结果创建时间戳
        self.error: str = ""                          # 错误信息字符串
        self.error_type: str = ""                     # 错误类型名称
        self.error_message: str = ""                  # 错误消息描述
        self.error_details: str = ""                  # 错误详细信息

    @classmethod
    def from_controller_result(cls, controller_result: Dict[str, Any]) -> 'SearchResultDTO':
        """从Controller返回的字典创建DTO实例"""
        # 被@classmethod装饰的方法是类方法，而不是实例方法
        # 第一个参数是类本身cls，代表类本身而不是实例
        # 可以直接通过类名调用，无需创建实例
        dto = cls()
        dto.success = controller_result.get("success", False)
        dto.keywords = controller_result.get("keywords", {})
        dto.queries = controller_result.get("queries", [])
        dto.results = controller_result.get("results", [])
        dto.error = controller_result.get("error", "")
        dto.error_type = controller_result.get("error_type", "")
        dto.error_message = controller_result.get("error_message", "")
        dto.error_details = controller_result.get("error_details", "")
        return dto

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化"""
        return {
            "success": self.success,
            "keywords": self.keywords,
            "queries": self.queries,
            "results": self.results,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "error": self.error,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "error_details": self.error_details
        }

