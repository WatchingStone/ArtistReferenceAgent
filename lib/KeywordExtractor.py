# \lib\KeywordExtractor.py
# 对自然语言的图片描述提取关键词，使用jieba或llm等。
# 不直接构造图片查询请求
import json
import requests
import jieba
from typing import Dict, List, Any
from llama_cpp import Llama
from time import time
import os

class KeywordExtractor:
    def __init__(self, config : Dict[str, Any], feature_tags : Dict[str, List[str]], mod="jieba"):
        self.mod = mod
        self.config = config
        self.llm_config = config.get("llm_sites", {})
        self.feature_tags = feature_tags
        self.model = None       # 本地模型
        self.llm_name = ""
        self.local_llm_name = ""
        self.api_key = ""
        self.api_url = ""

        if mod == "llm":
            self.llm_name = config.get("llm_name", "unsupported llm")
            if self.llm_name == "local_model":
                self.local_llm_name = config.get("local_llm_name", "no avaliable local llm")
                self.load_local_model()
            else:
                self.api_key = self.llm_config.get(self.llm_name, {}).get("api_key", "")
                self.api_url = self.llm_config.get(self.llm_name, {}).get("api_url",  "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation")
        elif mod == "jieba":
            pass
            # jieba_cache_path = config.get('jieba_cache_path', "./cache/jieba.txt")
            # os.makedirs(os.path.dirname(jieba_cache_path), exist_ok=True)
            # if not os.path.exists(jieba_cache_path):
            #     with open(jieba_cache_path, 'w', encoding='utf-8') as f:
            #         f.write("")
            # jieba.set_dictionary(jieba_cache_path)  # 如果需要自定义词典，设置jieba字典缓存
            # jieba.default_cache_file = config.get("jieba_running_cache_path", "./cache/jieba.cache")
            # jieba.initialize()  # 初始化

    def load_local_model(self):
        """加载本地模型"""
        if self._llm_in_ollama():   # 如果用的是ollama的模型如deepseek，则加载模型url
            try:
                self.api_url = self.llm_config.get("local_model").get(self.local_llm_name, {}).get("api_url", "")
                if self.api_url == "":
                    raise ValueError("请配置本地模型url")
            except Exception as e:
                print(f"LLM配置错误：{e}")
                raise
            return

        model_name = self.llm_config.get("local_model", {}).get(self.local_llm_name, "")
        model_path = self.llm_config.get("local_model", {}).get(self.local_llm_name, "")
        if model_path == "":
            raise ValueError("请配置本地模型路径")
        try:
            self.model = Llama(
                model_path=model_path,
                n_ctx=2048,           # 上下文长度（足够处理提示词）
                n_threads=4,          # 使用4个CPU线程（根据您的CPU核心数调整）
                n_batch=512,          # 批处理大小
                verbose=False,        # 关闭详细日志
                temperature=0.7,      # 低温度确保输出稳定
                top_p=0.7,            # 提高多样性
            )
            print(f"模型加载成功：{model_name}")
        except Exception as e:
            print(f"模型加载失败：{model_name} - {e}")
            raise

    def extract(self, input_text) -> Dict[str, Any]:
        """从输入文本中提取关键词"""
        result = {}
        if self.mod == "jieba":
            result = self.extract_jieba(input_text)
        elif self.mod == "llm":
            result = self.extract_llm(input_text)
        else:
            raise ValueError(f"不支持的搜索模式：【{self.mod}】")

        print(f"关键词提取结果：{result}")
        return result


    def extract_jieba(self, input_text) -> Dict[str, Any]:
        """使用jieba分词模型进行关键词提取"""
        words = jieba.lcut(input_text)
        filter_chars = {' ', '\t', '\n', '\r', '"', "'", ',', '.', '!', '?', ';', ':',
                        '(', ')', '[', ']', '{', '}', '<', '>', '/', '\\', '|', '-', '_',
                        '=', '+', '*', '&', '^', '%', '$', '#', '@', '~', '`'}

        # 过滤掉完全由空白字符和特殊符号组成的词语
        filtered_words = []
        for word in words:
            # 检查词语是否包含有效字符
            if word and not all(char in filter_chars for char in word):
                filtered_words.append(word)
        word_set = set(filtered_words)

        result = {}
        for category, keywords in self.feature_tags.items():
            sorted_keywords = sorted(keywords, key=len, reverse=True)
            matched = [kw for kw in sorted_keywords if kw in word_set]
            if matched:
                result[category] = matched
        if not result:
            return {"其他": filtered_words}
        return result

    def extract_llm(self, input_text) -> Dict[str, Any]:
        """使用LLM进行关键词提取"""
        result = {}
        if self.llm_name == "local_model":
            result = self.llm_extract_local_llm(input_text)
        elif self.llm_name == "qwen":
            result = self.llm_extract_qwen(input_text)
        else:
            raise ValueError(f"不支持的模型：【{self.llm_name}】")

        return result

    def llm_extract_local_llm(self, input_text : str) -> Dict[str, Any]:
        """使用本地的LLM进行关键词提取"""

        template = {
            "人体结构": ["头部特写", "上半身", "丰满"],
            "发型": [],
            "表情": [],
            "服装": [],
            "场景环境": [],
            "动作姿态": [],
            "其他": []
        }

        prompt = f"""请从以下文本中提取关键词并按照“大类-小类”的形式分类。严格按照指定JSON格式输出，不要添加任何解释性文字。

        文本内容：{input_text}

        输出要求：
        - 仅返回一个JSON对象，不要使用```json等代码块标记
        - 不要添加编号、说明或其他文字
        - 只包含文本中存在的关键词
        - 没有匹配关键词的大类请忽略，不要输出为空数组
        
        JSON格式的分类模板：
        {json.dumps(template, ensure_ascii=False, indent=2)}

        请开始提取："""

        try:
            print("========================")
            print(f"LLM输入：")
            print(prompt)
            print("========================")
            print("LLM正在生成提示词...")
            start_time = time()

            # 访问所用本地模型，构造提示词输入给模型
            if self._llm_in_ollama():
                payload = {
                    "model": self.local_llm_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                }
                response = requests.post(
                    url=self.api_url,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                output = result.get("response", "")
            else:
                response = self.model(
                    prompt,
                    max_tokens=512,         # 最大生成token数
                    temperature=0.3,        # 低温度确保稳定输出
                    top_p=0.9,              # 核采样
                    echo=False,             # 不返回输入
                    stop=["</s>"]             # 停止标记
                )
                output = response['choices'][0]['text'].strip()

            # 从模型输出响应中提取json结果
            print(f"LLM响应结果：{output}")
            print(f"LLM响应时间：{time() - start_time:.2f}秒")
            # 解析响应结果
            import re
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                json_str = json.loads(json_str)
                json_str = self.filter_json(json_str)
                print("========================")
                print(f"LLM响应结果提取为json：{json_str}")
                return json_str
            else:
                print("无法解析LLM响应结果为json")
                return {}
        except Exception as e:
            print(f"LLM调用失败：{e}")
            return {}

    def llm_extract_qwen(self, input_text : str) -> Dict[str, Any]:
        """（禁用！当前未配置合适的qwen的api）使用QWEN进行关键词提取"""
        if not self.api_key:
            raise ValueError("请配置api_key")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        template = {
            "人体结构": [
                "头部特写", "上半身", "丰满",...
            ],
            "发型": [],
            "表情": [],
            "服装": [],
            "场景环境": [],
            "动作姿态": [],
            "其他": []
        }

        # 提示词构造
        prompt = f"""请从文本【{input_text}】中提取关键词，请按照以下分类提取关键词，并返回严格的JSON格式：
                    {json.dumps(template, ensure_ascii=False, indent=2)}
                    要求：
                    1.优先使用上述分类中的大类进行分析
                    2.每个大类下可以有多个匹配的小类
                    3.如果某大类没有匹配的关键词，忽略该大类
                    4.只返回json，不要其他任何内容
                """

        # 构造完整的请求数据
        data = {
            "model": "qwen-turbo",
            "input": {
                "prompt": prompt,
            },
            "parameters":{
                "stream": False,
                "max_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.7        # 核采样（nucleus sampling）的阈值。它与temperature配合使用，用于控制生成文本的质量和多样性。0.9表示只考虑累积概率达到90%的词汇进行采样
            }
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(data)
            )
            response.raise_for_status()
            result = response.json()

            output_text = result.get("output", {}).get("text", "")
            import re
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return {}
        except Exception as e:
            print(f"qwen关键词提取失败：{e}")
            return {}

    def _llm_in_ollama(self) -> bool:
        """检查配置的模型是否是本地ollama的模型"""
        avaliable_models = ["deepseek-r1:1.5b","deepseek-r1:7b"]
        return self.local_llm_name in avaliable_models

    def filter_json(self, json_dict : Dict[str, Any]) -> Dict[str, Any]:
        """过滤json结果，将内容为空的大类过滤，或进行其他处理"""
        return {k: v for k, v in json_dict.items() if v}



        # prompt = f"""请从文本【{input_text}】中提取关键词，请按照以下分类提取关键词，并返回严格的JSON格式：
        #             {json.dumps(template, ensure_ascii=False, indent=2)}
        #             要求：
        #             1.优先使用上述分类中的大类进行分析
        #             2.每个大类下可以有多个匹配的小类
        #             3.如果某大类没有匹配的关键词，忽略该大类
        #             4.只返回json，不要其他任何内容"""

        # prompt = f"""目标文本：{input_text}，请从文本中提取关键词。
        #             1. 请只返回JSON，不要其他文字
        #             2. 请只提取文本中存在的关键词
        #             3. 请没有匹配的分类可以省略
        #             4. 请按以下JSON格式返回结果：
        #             {json.dumps(template, ensure_ascii=False, indent=2)}
        #             """

        # prompt = f"""请从以下文本中提取关键词并按照“大类-小类”的形式分类。严格按照指定JSON格式输出，不要添加任何解释性文字。
        #
        # 文本内容：{input_text}
        #
        # 输出要求：
        # - 仅返回一个JSON对象
        # - 不要添加编号、说明或其他文字
        # - 只包含文本中存在的关键词
        # - 没有匹配关键词的大类请忽略，不要输出为空数组
        #
        # JSON格式的分类模板：
        # {json.dumps(template, ensure_ascii=False, indent=2)}
        #
        # 请开始提取："""

        # prompt = f"""请从以下文本中提取关键词并按照“大类-小类”的形式分类。严格按照指定JSON格式输出，不要添加任何解释性文字。
        #
        # 文本内容：{input_text}
        #
        # 输出要求：
        # - 仅返回一个JSON对象，不要使用```json等代码块标记
        # - 不要添加编号、说明或其他文字
        # - 只包含文本中存在的关键词
        # - 没有匹配关键词的大类请忽略，不要输出为空数组
        #
        # JSON格式的分类模板：
        # {json.dumps(template, ensure_ascii=False, indent=2)}
        #
        # 请开始提取："""
