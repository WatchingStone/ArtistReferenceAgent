# /lib/Controller.py
# 用来控制ImageSearcher、KeywordExtractor、QueryGenerator类的交互
# 最终由外界ui来使用该Controller

from typing import Dict, List, Any
from lib.ImageSearchClass import *
from lib.QueryGenerator import *
from lib.KeywordExtractor import *
from lib.dto.SearchResultDTO import *

class Controller:
    def __init__(self, config : Dict[str, Any], feature_tags : Dict[str, Any], proxy = None):
        self.config = config
        self.query_generator = QueryGenerator(config=config, proxy=proxy)
        # self.keyword_extractor = KeywordExtractor(config=config, feature_tags=feature_tags, mod='llm')
        self.keyword_extractor = KeywordExtractor(config=config, feature_tags=feature_tags, mod='jieba')
        self.image_searcher_factory = ImageSearchFactory(config=config, proxy=proxy)
        # self.image_searchers = self.image_searcher_factory.get_all_avaliable_sites()
        self.image_searchers = [self.image_searcher_factory.get_searcher("huabanwang")]     # 临时调试，固定使用花瓣网

        # 各类当前状态
        self.current_input_text = ""
        self.current_keywords = None
        self.generated_queries = []  # 存储所有生成的查询
        self.current_query_index = 0  # 当前使用的查询索引
        self.search_results = {}

    def process_search_request(self, input_text : str) -> SearchResultDTO:
        """
        用户搜索输入的主入口，在此完成提取关键词、构造请求、图片搜索等主要流程。
        返回字典形式的查询结果
        """
        try:
            self.current_input_text = input_text
            self.current_keywords = self.keyword_extractor.extract(input_text)
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0
            
            if not self.generated_queries:
                raise ValueError("未能生成有效的查询语句")
            
            # 默认使用第一个搜索网站和第一组查询语句
            current_query = self.generated_queries[self.current_query_index]
            self.search_results = self.image_searchers[0].search(current_query)

            # 用dto实例形式返回查询结果，方便前端显示
            result_dto = SearchResultDTO()
            result_dto.success = True
            result_dto.results = self.search_results
            result_dto.keywords = self.current_keywords
            result_dto.queries = current_query
            return result_dto

        except Exception as e:
            result_dto = SearchResultDTO()
            result_dto.success = False
            result_dto.error = str(e)
            result_dto.error_type = type(e).__name__
            result_dto.error_message = str(e)
            result_dto.error_details = repr(e)
            return result_dto

    def prepare_search_context(self, input_text: str):
        """
        准备搜索上下文，包括关键词提取和初始查询生成
        """
        self.current_input_text = input_text
        self.current_keywords = self.keyword_extractor.extract(input_text)
        self.generated_queries = self.query_generator.generate_query(self.current_keywords)
        self.current_query_index = 0
        
        return self.current_keywords, self.generated_queries

    def get_first_query(self) -> List[str]:
        """
        获取第一组查询关键词
        """
        if not self.generated_queries:
            return []
        self.current_query_index = 0
        return self.generated_queries[self.current_query_index]

    def get_next_query(self) -> List[str]:
        """
        获取下一个查询组合，如果需要则重新生成
        """
        # 如果还有未使用的查询组合，直接返回下一个
        if (self.current_query_index + 1) < len(self.generated_queries):
            self.current_query_index += 1
            return self.generated_queries[self.current_query_index]
        
        # 如果没有更多查询组合，重新生成一批
        if self.current_keywords:
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0 if self.generated_queries else -1
            if self.generated_queries:
                return self.generated_queries[self.current_query_index]
        
        return []

    def reset_query_generation(self):
        """
        重置查询生成状态，重新开始生成查询组合
        """
        if self.current_keywords:
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0

    def search_with_current_query(self) -> List[str]:
        """
        使用当前查询组合进行搜索
        """
        if not self.generated_queries or self.current_query_index < 0:
            raise ValueError("没有可用的查询组合")
            
        current_query = self.generated_queries[self.current_query_index]
        return self.image_searchers[0].search(current_query)

    def get_current_query(self) -> List[str]:
        """
        获取当前查询组合
        """
        if not self.generated_queries or self.current_query_index < 0:
            return []
        return self.generated_queries[self.current_query_index]

    def regenerate_queries(self) -> List[List[str]]:
        """
        重新生成查询组合
        """
        if self.current_keywords:
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0
            return self.generated_queries
        return []