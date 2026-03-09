import os
import sys

# 1. 解决路径问题，确保能导入 lib
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(project_root)

# 2. 关键：尝试在导入 torch 之前或之后设置环境变量
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import uuid
import chromadb
from lib.VisualEvaluator import VisualEvaluator
from lib.dto.ImageInfoDTO import ImageInfoDTO


def run_combined_test():
    print("--- 步骤 1: 初始化 VisualEvaluator (加载模型) ---")
    try:
        # 这里的 config_path 需要根据你 test 脚本的位置调整
        config_path = os.path.join(project_root, 'config', 'Resource_config.json')
        evaluator = VisualEvaluator(
            config_path=config_path,
            text_model_dir="D:/python/pythonProject/ArtistReferenceAgent/model/IDEA-CCNL/Taiyi-CLIP-Roberta-102M-Chinese",
            image_model_dir="D:/python/pythonProject/ArtistReferenceAgent/model/openai/clip-vit-base-patch32"
        )
        print("VisualEvaluator 初始化成功")
    except Exception as e:
        print(f"VisualEvaluator 初始化失败: {e}")
        return

    print("\n--- 步骤 2: 初始化 ChromaDB (PersistentClient) ---")
    db_path = os.path.join(project_root, "cache", "test_combined_db")
    if os.path.exists(db_path):
        import shutil
        shutil.rmtree(db_path)

    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(
        name="test_combined",
        metadata={"hnsw:space": "cosine"}
    )
    print("ChromaDB 初始化成功")

    print("\n--- 步骤 3: 提取真实特征向量 ---")
    # 创建一个空的 DTO 或指向一张真实存在的测试图
    test_dto = ImageInfoDTO(
        local_path=os.path.join(project_root, "test_image.jpg"),  # 确保这有一张图，或者随便找一张
        source="test"
    )

    # 如果没有真实图，我们手动模拟一个从 torch 出来的向量
    import torch
    print("模拟从 Torch 生成 Tensor 并转换...")
    mock_tensor = torch.randn(1, 512).to('cuda' if torch.cuda.is_available() else 'cpu')

    # 关键点：检查是否是因为直接操作了 Torch 转换后的对象导致的崩溃
    # 强制转换为标准的 Python 浮点数列表
    real_feature = mock_tensor.detach().cpu().numpy().flatten().tolist()
    print(f"向量提取/模拟成功，维度: {len(real_feature)}")

    print("\n--- 步骤 4: 执行 Upsert (压力测试点) ---")
    try:
        uid = str(uuid.uuid4())
        # 传入 metadata 必须严格为基础类型
        metadata = {
            "local_path": str(test_dto.local_path),
            "source": "unknown"
        }

        print("开始调用 collection.upsert...")
        collection.upsert(
            ids=[uid],
            embeddings=[real_feature],
            metadatas=[metadata],
            documents=["test_doc"]
        )
        print("Upsert 成功！未发生崩溃。")

    except Exception as e:
        print(f"Upsert 过程中捕获到异常: {e}")
    except BaseException as e:
        print(f"捕获到严重系统错误: {e}")

    print("\n--- 步骤 5: 验证数据 ---")
    count = collection.count()
    print(f"当前数据库条目数: {count}")


if __name__ == "__main__":
    run_combined_test()