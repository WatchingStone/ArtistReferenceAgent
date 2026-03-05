# 视觉评估模块，调用clip模型，检查后台搜索的图片结果是否匹配用户输入的原始关键词，以得分的形式过滤低分结果
# 如果优质结果过少，则通知模型上一步搜索结果质量差，需要调整搜索关键词组合
import json
import os.path
from typing import List
from lib.dto.ImageInfoDTO import ImageInfoDTO
import numpy as np

from PIL import Image
import torch
from transformers import BertForSequenceClassification, BertTokenizer, CLIPProcessor, CLIPModel

class VisualEvaluator:
    '''视觉评估类，评估得到的图片信息是否足够匹配原始字符组合'''
    _instance = None
    def __new__(cls, *args, **kwargs):
        '''单例模式，避免模型重复加载'''
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, cache_manager):
        if self.initialized:    # 避免重复加载
            return

        self.log_prefix = "VisualEvaluator"
        self.cache_manager = cache_manager      # 图片缓存管理器
        self.batch_size = 8                     # 批处理图片数量

        resource_config = json.load(open('config/Resource_config.json', 'r', encoding='utf-8'))
        model_dir = resource_config['model_dir']
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        # self.model = CLIPModel.from_pretrained(model_dir).to(self.device)

        try:
            # 读取 Taiyi 中文 text encoder
            text_model_dir = os.path.join(model_dir, resource_config['text_model_id'])
            self.text_tokenizer = BertTokenizer.from_pretrained(text_model_dir, local_files_only=True)
            # self.text_encoder = BertForSequenceClassification.from_pretrained(text_model_dir, local_files_only=True).eval()
            self._log('__init__', "加载文本处理模型成功")

            # 读取 clip 的 image encoder
            image_model_dir = os.path.join(model_dir, resource_config['image_model_id'])
            self.processor = CLIPProcessor.from_pretrained(image_model_dir, local_files_only=True)
            self.model = CLIPModel.from_pretrained(image_model_dir, local_files_only=True).to(self.device).eval()
            self._log('__init__', "加载图片处理模型成功")

            self.initialized = True
        except Exception as e:
            self._log('__init__', str(e))
            self._log('__init__', "加载图片与文本处理模型失败，请检查模型文件是否正确")

    def _log(self, function_name: str = "None", data: str = "-"):
        '''格式化输出'''
        print(f">> >> [{self.log_prefix}]-[{function_name}]: {data}")

    def filter_and_rank(self, text : str, image_url_list: List[str], threshold: float = 0.1) -> List[ImageInfoDTO]:
        '''
        以当前搜索的原始文本为基础，检查搜索到的所有图片与文本的匹配相似度，返回相似度超过阈值的图片列表，以DTO形式返回
        :param text: 原始文本
        :param image_url_list: 图片url列表
        :param threshold: 相似度过滤阈值
        :return: 超过阈值的图片List[DTO]
        '''

        # 从缓存类中下载并提取图片
        valid_images = []
        valid_image_dtos = []
        for url in image_url_list:
            try:
                image = self.cache_manager.get(url)
                if image:
                    valid_images.append(image)
                    valid_image_dtos.append(ImageInfoDTO(url=url))
            except Exception as e:
                self._log('filter_and_rank', f"图片[{url}]处理失败：{str(e)}")
                continue

        if not valid_images:
            self._log('filter_and_rank', "无有效图片")
            return []

        self._log('filter_and_rank', f"输入文本text = {text}")

        # 批处理图片，计算图片特征与相似度得分
        result = []
        try:
            with torch.no_grad():
                # 将文本转为token
                text_token = self.text_tokenizer(text, return_tensors='pt', padding=True).to(self.device)
                # text_token = {k: v.to(self.device) for k, v in text_token.items()}
                # 计算文本特征
                # text_features = self.text_encoder(**text_token).logits  # 解包**text_inputs 等价于将字典的键值对作为关键字参数传入。得到的.logits是原始输出，未经过softmax归一化

                text_token = {k: v for k, v in text_token.items() if k != 'token_type_ids'}    # 过滤掉 token_type_ids，Taiyi模型特有的token_type_ids参数，而CLIP 模型不需要这个参数
                text_features = self.model.get_text_features(**text_token)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)  # 用L2范数归一化，保持向量方向，仅对向量大小进行缩放。适合相似度计算

                # 分batch处理图片
                all_image_num = len(valid_images)
                for i in range(0, all_image_num, self.batch_size):
                    batch_images = valid_images[i : min(i + self.batch_size, all_image_num)]
                    self._log('filter_and_rank', f"处理图片 [{i} ~ {min(i + self.batch_size, all_image_num)}]")
                    image_tokens = self.processor(images=batch_images, return_tensors='pt', padding=True).to(self.device)
                    image_features = self.model.get_image_features(**image_tokens)
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)

                    # 计算相似度
                    similarity_scores = (image_features @ text_features.T).cpu().numpy().flatten()

                    # 结果过滤
                    if np.ndim(similarity_scores) == 0:  # similarity_scores 可能是单个float (如果只有1张图) 或 array
                        similarity_scores = [similarity_scores]
                    for j, score in enumerate(similarity_scores):
                        score = float(score)
                        self._log('filter_and_rank', f"id = {i + j} 相似度得分：{score} from 图片[{valid_image_dtos[i + j].url}]")
                        if score > threshold:
                            dto = valid_image_dtos[i + j]
                            dto.score = score
                            dto.description = text
                            result.append(dto)

                    # （如果可用）释放GPU批缓存
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

        except Exception as e:
            self._log('filter_and_rank', f"图片特征计算失败：{str(e)}")
            import traceback
            traceback.print_exc()
            return []

        # 将结果按相似度得分降序排序
        result.sort(key = lambda x: x.score, reverse=True)
        return result


