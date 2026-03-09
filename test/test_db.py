# 测试本地chromadb是否运行正常
import os
import shutil
import uuid
import numpy as np
import chromadb
from chromadb.config import Settings

# 1. 环境变量修复（针对多重 DLL 冲突）
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def run_test():
    db_path = "./test_db_dir"
    collection_name = "test_collection"

    # 清理旧数据
    if os.path.exists(db_path):
        print(f"清理旧测试目录: {db_path}")
        shutil.rmtree(db_path)

    print("--- 步骤 1: 初始化 PersistentClient ---")
    try:
        # 测试持久化写入，这是最容易崩溃的点
        client = chromadb.PersistentClient(path=db_path)
        print("客户端初始化成功")
    except Exception as e:
        print(f"客户端初始化失败: {e}")
        return

    print("\n--- 步骤 2: 创建 Collection (带索引配置) ---")
    try:
        # 模拟你之前的配置，只保留关键的 hnsw:space
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print("集合创建成功")
    except Exception as e:
        print(f"集合创建失败: {e}")
        return

    print("\n--- 步骤 3: 准备模拟数据 (512维向量) ---")
    # 模拟 CLIP-512 维度的向量
    num_samples = 3
    dim = 512

    # 生成随机归一化向量（模拟特征提取后的结果）
    test_embeddings = np.random.focused_distribution = np.random.randn(num_samples, dim).astype(np.float32)
    test_embeddings = (test_embeddings / np.linalg.norm(test_embeddings, axis=1, keepdims=True)).tolist()

    test_ids = [str(uuid.uuid4()) for _ in range(num_samples)]

    # 模拟你代码中的路径（包含中文字符和反斜杠）
    test_metadatas = [
        {
            "local_path": "E:\\测试\\图片_1.jpg",
            "source": "test_script",
            "url": "http://example.com/1"
        },
        {
            "local_path": "C:/Users/Admin/Desktop/photo.png",
            "source": "unknown",
            "url": ""
        },
        {
            "local_path": "relative/path/test.webp",
            "source": "null_test",
            "url": "none"
        }
    ]
    test_documents = ["doc_1", "doc_2", "doc_3"]

    print(f"准备插入 {num_samples} 条数据...")

    print("\n--- 步骤 4: 执行 Upsert (关键点) ---")
    try:
        # 如果这里崩溃，说明是 chromadb 底层库或 numpy 版本问题
        collection.upsert(
            ids=test_ids,
            embeddings=test_embeddings,
            metadatas=test_metadatas,
            documents=test_documents
        )
        print("Upsert 操作成功！")
    except Exception as e:
        print(f"Upsert 失败: {e}")
        return

    print("\n--- 步骤 5: 测试查询 ---")
    try:
        query_result = collection.query(
            query_embeddings=[test_embeddings[0]],
            n_results=1
        )
        print("查询成功，匹配 ID:", query_result['ids'][0])
    except Exception as e:
        print(f"查询失败: {e}")

    print("\n--- 测试完成 ---")
    print(f"数据库文件已保存至: {os.path.abspath(db_path)}")


if __name__ == "__main__":
    run_test()