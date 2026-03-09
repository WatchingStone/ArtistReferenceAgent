# /lib/LocalDB.py
# 本地向量数据库，用于保存本地图片的特征向量，需要由 VisualEvaluator 来控制特征向量的提取

import os
# os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import chromadb
from typing import List, Dict, Optional, Any
from PIL import Image
import uuid             # 将字符串（图片本地保存路径）哈希成唯一标识符
from lib.dto.ImageInfoDTO import ImageInfoDTO


from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

# 自定义一个符合 ChromaDB 规范的空嵌入类
class EmptyEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return []


class LocalDB:
    '''本地图片特征向量数据库，k=图片路径的唯一标识码，v1=图片特征向量，v2=图片本地保存路径'''
    _instance = None        # 单例模式

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, db_path: str = './cache/LocalDB_dir'):
        self.log_prefix = "LocalDB"
        self._log('__init__', f"初始化LocalDB")

        if not hasattr(self, 'initialized'):
            self.initialized = False

        if self.initialized:
            self._log('__init__', f"LocalDB已初始化，无需重复初始化")
            return



        # 显式创建一个不执行任何操作的空嵌入函数
        # 这样 ChromaDB 就不会去调用 onnxruntime 加载默认模型了
        def empty_embedding_function(texts):
            return []

        # 初始化客户端
        self.client = chromadb.PersistentClient(path=db_path)
        # self.client = chromadb.EphemeralClient()
        self._log('__init__', f"已创建数据库客户端，路径：{os.path.abspath(db_path)}")

        # 创建数据库中的表（在chromadb中叫做集合collection）（chromadb中一行数据条目叫做一个document）
        self.collection = self.client.get_or_create_collection(
            name='local_img_feature',
            embedding_function=EmptyEmbeddingFunction(),
            metadata={                          # metadata是collection的配置字典，前身是settings。作用是定义条目的属性，
                                                # 一个条目应该有3部分属性：唯一标识符id、向量表示embedding、结构化条目属性metadata（类似于mysql属性列的集合）
                'hnsw:space': 'cosine',         # 设置向量空间为cosine，用余弦相似度度量
                'local_path': 'cache',
                'source': 'unknown',
                'url': 'unknown'
            }
        )

        self.initialized = True
        self._log('__init__', f"本地数据库初始化完成，当前库中图片数量为 [{self.collection.count()}]")

    def _log(self, function_name: str = "None", data: str = "-"):
        '''格式化输出'''
        print(f">> >> [{self.log_prefix}]-[{function_name}]: {data}")

    def add_image(self, image_dto: ImageInfoDTO, image_feature: List[float]) -> bool:
        '''
        向数据库中添加图片特征向量
        :param image_dto: 图片的dto信息
        :param image_feature: 由 VisualEvaluator 得出的图片特征向量
        :return bool: 是否成功添加
        '''
        self._log('add_image', f"添加图片 [{image_dto.local_path}]")

        if image_dto.local_path == '' or not os.path.exists(image_dto.local_path):
            self._log('add_image', f"图片 [{image_dto.local_path}] 本地存储路径无效，添加失败")
            return False

        if not image_feature:
            self._log('add_image', f"图片 [{image_dto.local_path}] 特征向量为空，添加失败")
            return False

        # 图片的属性字典，以metadata形式存储
        metadata = {
            'local_path': str(image_dto.local_path),
            'source': str(image_dto.source) if image_dto.source else 'unknown',
            'url': str(image_dto.url) if image_dto.url else 'unknown',
        }
        self._log('add_image', f"图片 [{image_dto.local_path}] 属性为 [{metadata}]")
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, image_dto.local_path))   # 将字符串（图片本地保存路径）哈希成唯一标识符
        self._log('add_image', f"图片 [{image_dto.local_path}] 唯一标识符为 [{uid}]")

        # 添加图片进数据库
        try:
            self.collection.upsert(
                ids=[uid],
                embeddings=[image_feature],
                metadatas=[metadata],
                documents=[str(image_dto.local_path)]      # documents参数通常存放原始内容，此处存储图片的元数据，即图片的本地存储路径
            )
            self._log('add_image', f"图片 [{image_dto.local_path}] 添加成功")
            return True
        except Exception as e:
            self._log('add_image', f"图片 [{image_dto.local_path}] 添加失败：{str(e)}")
            return False

    def add_image_by_batch(self, image_dtos: List[ImageInfoDTO], image_embeddings: List[List[float]]):
        '''
        批量添加图片特征向量
        :param image_dtos: 图片信息列表
        :param image_embeddings: 图片特征向量列表
        '''
        self._log('add_image_by_batch', f"批量添加图片，图片数量为 [{len(image_dtos)}]")
        if image_dtos and image_embeddings and len(image_dtos) == len(image_embeddings):
            for i in range(len(image_dtos)):
                self.add_image(
                    image_dto=image_dtos[i],
                    image_feature=image_embeddings[i]
                )
        else:
            self._log('add_image_by_batch', f"图片信息列表和图片特征向量列表长度含空或不一致，添加失败")
        self._log('add_image_by_batch', f"批量添加图片完成")

    def search_by_feature(self, query_feature: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        '''
        向量搜索，对传入的特征向量搜索数据库中前top_k个相近条目
        :param query_feature: 查询文本的特征向量
        :param top_k: 搜索返回条目数
        :return: 搜索结果条目的 metadata 字典
        '''
        self._log('search', "搜索特征向量")

        if not query_feature:
            self._log('search', "特征向量为空，搜索失败")
            return []

        # 查询数据库条目
        results = self.collection.query(
            query_embeddings=[query_feature],           # 查询向量，默认是一个列表形式，表示一系列查询，因此返回值也会是一系列查询的结果
            n_results=top_k
            # , where={'source': 'huabanwang'}
        )

        self._log('search', f"搜索结果条目数： [{len(results['ids'])}]")

        # 获取结果，将搜索相似度得分添加到结果中
        ans: List[Dict[str, Any]] = []
        if results and results['metadatas']:
            res_metadata = results['metadatas'][0]
            res_distance = results['distances'][0]

            for i in range(len(res_metadata)):
                metadata = dict(res_metadata[i])
                metadata['distance'] = res_distance[i]
                ans.append(metadata)

        self._log('search', f"搜索完成")

        return ans

