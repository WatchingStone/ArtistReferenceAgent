# \lib\QueryGenerator.py
# 对由KeywordExtractor提取得到的关键词列表生成查询语句
from typing import List, Any, Dict
import random
from lib.TagTranslator import TagTranslator

class QueryGenerator:
    def __init__(self, config, proxy=None):
        self.config = config
        self.query_generate_max = config.get("single_query_generate_max", 5)
        self.max_categories = config.get("single_query_by_many_categories", 3)
        self.max_elements_per_category = config.get("single_query_by_many_element_per_category", 2)
        self.translator = TagTranslator(config, proxy=proxy)

    def generate_query(self, keywords : Dict[str, Any]) -> List[List[str]]:
        """
        根据关键词生成查询语句，后续需要考虑翻译问题
        """
        query_list = []
        categories = list(keywords.keys())

        keywords = self.translator.translate(keywords, "en")                # 默认开启关键词翻译

        # 随机选择一个键值对，生成多组不同的查询组合
        for _ in range(self.query_generate_max):
            query_elements = self.generate_single_query(keywords, categories)
            query_list.append(query_elements)
        return query_list


    def generate_single_query(self, keywords : Dict[str, Any], categories : List[str]) -> List[str]:
        """
        生成单个查询语句，构造逻辑如下：
        检查有多少个键值对，通常用户一次自然语言询问只会有2-4条大类键值对，每个值List[str]只会有1-4个元素
        那么每次随机选择2-3个大类中的1-2个元素组合在一起，作为一个查询前体语句List[str]，多次查询构造多条查询前体语句
        """

        # 随机选择几个大类
        num_categories = min(random.randint(2, self.max_categories), len(categories))
        select_categories = random.sample(categories, num_categories)

        # 从这些大类中随机选择几个元素
        query_elements = []
        for c in select_categories:
            e = keywords.get(c, [])
            if e:
                num_elements = min(random.randint(1, self.max_elements_per_category), len(e))
                selecetted_elements = random.sample(e, num_elements)
                query_elements.extend(selecetted_elements)
        return query_elements
