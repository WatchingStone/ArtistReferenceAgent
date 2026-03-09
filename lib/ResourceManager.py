# /lib/ResourceManager.py
# 安装各类资源，主要是huggingface 的 clip 模型
import json
from huggingface_hub import snapshot_download
import os
from lib.NetworkProxyDetection import get_proxies


def load_text_image_model():
    '''下载文本与图片编码模型'''
    #
    # # 设置镜像站环境变量（必须在导入 huggingface_hub 之后立即设置）
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

    # 设置代理
    proxies = get_proxies()
    if proxies:
        print(f"正在使用代理：{proxies}")
        os.environ['HTTP_PROXY'] = proxies['http']
        os.environ['HTTPS_PROXY'] = proxies['https']
    else:
        print("未检测到代理，开始直连")

    resource_config = json.load(open('config/Resource_config.json', 'r', encoding='utf-8'))
    model_dir = resource_config['model_dir']

    # 确保 model 目录存在
    os.makedirs(model_dir, exist_ok=True)

    text_model_id = resource_config['text_model_id']
    text_model_dir = os.path.join(model_dir, text_model_id)
    os.makedirs(text_model_dir, exist_ok=True)

    print(f"正在下载中文文本编码模型：【{text_model_id}】")
    print(f"保存路径：{text_model_dir}")
    print(f"使用镜像站：{os.environ.get('HF_ENDPOINT')}")

    try:
        snapshot_download(
            repo_id=text_model_id,
            local_dir=text_model_dir,
            local_files_only=False
        )
        print(f"下载完成")
    except Exception as e:
        print(f"下载失败：{e}")
        print("请检查网络连接，或尝试使用代理")
        raise

    image_model_id = resource_config['image_model_id']
    image_model_dir = os.path.join(model_dir, image_model_id)
    os.makedirs(image_model_dir, exist_ok=True)

    print(f"正在下载图片编码模型：【{image_model_id}】")
    print(f"保存路径：{image_model_dir}")

    try:
        snapshot_download(
            repo_id=image_model_id,
            local_dir=image_model_dir,
            local_files_only=False
        )
        print(f"下载完成")
    except Exception as e:
        print(f"下载失败：{e}")
        print("请检查网络连接，或尝试使用代理")
        raise