from lib.LocalImageLoader import LocalImageLoader
from lib.LocalDB import LocalDB
from lib.VisualEvaluator import VisualEvaluator

target_local_image_folder = "your_target_dir"   # 待处理的图片文件夹

# 初始化几个组件
visual_evaluator: VisualEvaluator = VisualEvaluator()
local_db: LocalDB = LocalDB()
local_image_loader = LocalImageLoader()

image_dtos = local_image_loader.scan_folder(target_local_image_folder)                          # 扫描图片文件夹
features = local_image_loader.save_image_features(image_dtos, visual_evaluator, local_db=None)  # 提取图片特征向量
local_db.add_image_by_batch(image_dtos, features)                                               # 添加图片特征向量进数据库

print("【测试完成】：VisualEvaluator 和 LocalDB 成功实现查找文件夹中的图片并保存到数据库的功能")