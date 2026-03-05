# /lib/Controller.py
# 用来控制ImageSearcher、KeywordExtractor、QueryGenerator类的交互
# 最终由外界ui来使用该Controller

from typing import Dict, List, Any
from lib.ImageSearchClass import *
from lib.QueryGenerator import *
from lib.KeywordExtractor import *
from lib.CacheManager import *
from lib.VisualEvaluator import *
from lib.dto.SearchResultDTO import *
from lib.dto.ImageInfoDTO import *

class Controller:
    def __init__(self, config : Dict[str, Any], feature_tags : Dict[str, Any], proxy = None):
        self.log_prefix = "Controller"
        self.config = config
        self.query_generator = QueryGenerator(config=config, proxy=proxy)
        self.keyword_extractor = KeywordExtractor(config=config, feature_tags=feature_tags, mod='jieba')
        self.image_searcher_factory = ImageSearchFactory(config=config, proxy=proxy)
        self.image_searchers = [self.image_searcher_factory.get_searcher("huabanwang")]     # 临时调试，固定使用花瓣网
        self.cache_manager = CacheManager()
        self.visual_evaluator = VisualEvaluator(cache_manager=self.cache_manager)

        # 各类当前状态
        self.current_input_text = ""
        self.current_keywords = None
        self.generated_queries = []  # 存储所有生成的查询
        self.current_query_index = 0  # 当前使用的查询索引
        self.search_results = {}

    def _log(self, function_name: str = "None", data: str = "-"):
        '''格式化输出'''
        print(f">> [{self.log_prefix}]-[{function_name}]: {data}")

    def process_search_request(self, input_text : str) -> SearchResultDTO:
        """
        用户搜索输入的主入口，在此完成提取关键词、构造请求、图片搜索等主要流程。
        返回字典形式的查询结果
        """
        try:
            self._log('process_search_request', f"开始处理搜索请求：{input_text}")
            self.current_input_text = input_text
            self.current_keywords = self.keyword_extractor.extract(input_text)
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0
            
            if not self.generated_queries:
                raise ValueError("未能生成有效的查询语句")
            
            # 默认使用第一个搜索网站和第一组查询语句
            current_query = self.generated_queries[self.current_query_index]
            self._log('process_search_request', f"执行搜索：{current_query}")
            self.search_results = self.image_searchers[0].search(current_query)

            # 用dto实例形式返回查询结果，方便前端显示
            result_dto = SearchResultDTO()
            result_dto.success = True
            result_dto.results = self.search_results
            result_dto.keywords = self.current_keywords
            result_dto.queries = current_query
            self._log('process_search_request', f"搜索完成，成功：{result_dto.success}")
            return result_dto

        except Exception as e:
            self._log('process_search_request', f"搜索失败：{str(e)}")
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
        self._log('prepare_search_context', f"准备搜索上下文：{input_text}")
        self.current_input_text = input_text
        self.current_keywords = self.keyword_extractor.extract(input_text)
        self.generated_queries = self.query_generator.generate_query(self.current_keywords)
        self.current_query_index = 0
        
        self._log('prepare_search_context', f"提取关键词：{self.current_keywords}, 生成查询数量：{len(self.generated_queries)}")
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

    def search_with_current_query(self) -> List[ImageInfoDTO]:
        """
        使用当前查询组合进行搜索
        """
        if not self.generated_queries or self.current_query_index < 0:
            self._log('search_with_current_query', "错误：没有可用的查询组合")
            raise ValueError("没有可用的查询组合")
            
        current_query = self.generated_queries[self.current_query_index]    # 获取当前的查询语句
        self._log('search_with_current_query', f"使用查询：{current_query}")
        urls = self.image_searchers[0].search(current_query)                # 在图像搜索器中使用查询语句进行搜索，返回图片 url 列表
        valid_urls = self.cache_manager.add_batch(urls)                     # 下载图片到缓存，返回有效的图片 url 列表
        query_text = " ".join(current_query)                                # 构造查询文本
        self._log('search_with_current_query', f"有效 URL 数量：{len(valid_urls)}, 查询文本：{query_text}")
        qualited_imageinfo_dtos: List[ImageInfoDTO] = self.visual_evaluator.filter_and_rank(query_text, valid_urls, threshold=self.config.get("similarity_threshold", 0.2))
        self._log('search_with_current_query', f"筛选后图片数量：{len(qualited_imageinfo_dtos)}")
        return qualited_imageinfo_dtos

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