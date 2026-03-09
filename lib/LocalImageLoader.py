# /lib/LocalImageLoader.py
# 本地图片加载器类，内部包含 LocalDB 和 VisualEvaluator

from typing import List, Dict, Any
import os
from lib.dto.ImageInfoDTO import *

class LocalImageLoader:
    '''本地图片加载器类，内部包含 LocalDB 和 VisualEvaluator'''
    log_prefix = "LocalImageLoader"
    img_exts: List[str] = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']

    @staticmethod
    def _log(function_name: str = "None", data: str = "-"):
        '''格式化输出'''
        print(f">> [{LocalImageLoader.log_prefix}]-[{function_name}]: {data}")

    @staticmethod
    def scan_folder(folder_path: str) -> List[ImageInfoDTO]:
        '''
        递归扫描文件夹，返回文件夹中所有图片的dto信息（虽然在本方法中只能读取到图片的本地保存路径信息
        :param folder_path: 文件夹路径
        :return: 图片信息列表
        '''
        LocalImageLoader._log('scan_folder', f"开始扫描文件夹 [{folder_path}]")
        if not os.path.exists(folder_path):
            LocalImageLoader._log('scan_folder', f"文件夹 [{folder_path}] 不存在")
            return []

        image_dtos: List[ImageInfoDTO] = []
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in LocalImageLoader.img_exts:
                        dto = ImageInfoDTO.from_dict({
                            "local_path": os.path.join(root, file)
                        })
                        image_dtos.append(dto)
            LocalImageLoader._log('scan_folder', f"扫描完成，文件夹 [{folder_path}] 下共找到 [{len(image_dtos)}] 张有效图片")
            return image_dtos
        except Exception as e:
            LocalImageLoader._log('scan_folder', f"扫描文件夹 [{folder_path}] 时发生错误: {e}")
            if image_dtos:
                return image_dtos
            else:
                return []

    @staticmethod
    def save_image_features(image_dtos: List[ImageInfoDTO], visual_evaluator, local_db = None) -> List[List[float]]:
        '''
        保存图片特征向量
        :param image_dtos: 图片信息dto列表
        :param visual_evaluator: 传入的VisualEvaluator
        :param local_db: 传入的LocalDB（允许为None）
        :return:
        '''
        LocalImageLoader._log('save_image_features', f"开始保存图片特征向量")
        features = visual_evaluator.get_image_feature_by_batch(
            image_dtos=image_dtos,
            batch_size=8,
            local_db=local_db
        )
        if features is None:
            return []
        return features


