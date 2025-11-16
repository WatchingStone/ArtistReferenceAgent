# /lib/Translator.py
# 由QueryGeneration调用，将关键词翻译为英文
import os
import json
from typing import Dict, List, Any
from functools import singledispatchmethod
# from googletrans import Translator
# from translate import Translator
from pygtrans import Translate
import atexit

class TagTranslator:
    def __init__(self, config, proxy=None):
        self.config = config
        self.cache_path = config.get("translation_cache_path", "./translation_dictionary.json")
        self.cache = self._load_translation_dictionary()
        self.translator = Translate()
        if proxy:
            self.translator = Translate(proxies=proxy)
        self.proxy = proxy

        atexit.register(self.save_translation_dictionary)  # 注册退出处理函数，在程序退出时自动运行，保存字典缓存

    def _load_translation_dictionary(self):
        """加载翻译字典缓存"""
        cache = {}
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as f:
                cache = json.load(f)
        else:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        self.cache = cache
        return cache

    @singledispatchmethod               # 用修饰符实现根据传入参数的类型不同，自动跳转至不同的方法
    def translate(self, keywords, target_language : str):      # 默认方法，在其余所有可用方法中找不到匹配的参数类型时，调用此方法
        """翻译整个关键词字典，形如｛“人体结构”：[...], ... ｝"""
        raise NotImplementedError("Unsupported type")

    @translate.register                 # 跟随@singledispatchmethod修饰的函数，根据传入参数的类型进行注册，函数名为“_”表示匿名函数
    def _(self, keywords : dict, target_language : str) -> Dict[str, Any]:
        """传入Dict[str]"""
        translated_dict = {}
        for k, v in keywords.items():
            translated_dict[k] = self.translate(v, target_language)
        return translated_dict

    @translate.register
    def _(self, keyword : list, target_language : str) -> List[str]:
        """传入List[str]"""
        translated_list = []
        for k in keyword:
            translated_list.append(self.translate(k, target_language))
        return translated_list

    @translate.register
    def _(self, keyword : str, target_language : str) -> str:
        """传入str"""
        if keyword in self.cache:
            return self.cache[keyword]
        else:
            try:
                translated_result = self.translator.translate(
                    keyword,
                    target=target_language,
                    source='auto'
                ).translatedText

                print(f"翻译结果：{keyword} -> {translated_result}")
                self.cache[keyword] = translated_result         # 写入缓存
                return translated_result
            except Exception as e:
                print(f"翻译出错：{keyword} - {e}")
                return keyword


    def save_translation_dictionary(self):
        """保存翻译字典缓存"""
        with open(self.cache_path, "w") as f:
            json.dump(self.cache, f, indent=4)
        print(f"本次翻译字典已保存至：{self.cache_path}")



    #
    # @translate.register
    # def _(self, keyword : str, target_language : str) -> str:
    #     """传入str"""
    #     print(f"正在翻译str：{keyword}")
    #
    #
    #
    #     if keyword in self.cache:
    #         return self.cache[keyword]
    #     else:
    #         # 利用googletrans中检测源语言的方法，自动检测源语言
    #         source_language = self.translator.detect(keyword).lang  # .detect()返回的是Dectected对象，可以用.detect().confidence 获取语言的相似度
    #         if source_language == target_language:                  # 如果源语言和目标语言相同，则返回原字符串
    #             return keyword
    #         else:
    #             translated_result = self.translator.translate(keyword, dest=target_language)
    #             self.cache[keyword] = translated_result.text        # 写入缓存
    #             return translated_result.text



    # @translate.register
    # def _(self, keyword : str, target_language : str) -> str:
    #     """传入str"""
    #     print(f"正在翻译str：{keyword}")
    #     print(f"代理为：{self.proxy}")
    #
    #
    #
    #
    #
    #
    #     if keyword in self.cache:
    #         return self.cache[keyword]
    #     else:
    #         try:
    #             translator = Translator(
    #                 to_lang=target_language,
    #                 from_lang='zh',
    #                 # provider='mymemory',
    #                 # headers={'User-Agent': 'Mozilla/5.0'},
    #                 # proxies=self.proxy
    #             )
    #             translated_result = translator.translate(keyword)
    #             print(f"翻译结果：{keyword} -> {translated_result}")
    #             self.cache[keyword] = translated_result         # 写入缓存
    #             return translated_result
    #         except Exception as e:
    #             print(f"翻译出错：{keyword} - {e}")
    #             return keyword