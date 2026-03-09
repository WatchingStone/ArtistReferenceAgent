import os
# os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE" # 必须放在所有 import 的最前面，解决 PyTorch/ChromaDB 与 PyQt5 的底层的 OpenMP DLL 冲突（没用）

# 强制在 PyQt5 之前导入底层 C++ 依赖库！极其重要！
# PyQt5 自带了一个阉割版的 sqlite3.dll。如果 PyQt5 先被 Import，ChromaDB 就会被迫使用 PyQt5 的 SQLite，这会导致 ChromaDB 缺少必要特性而崩溃。
# 所以必须让 chromadb 和 torch 在 PyQt5 之前被 Import。要么在最开始导入 torch 和 chromadb，要么将 lib.xxx 中包含 chromadb 的库提前导入。
# import torch
# import chromadb

from lib.Controller import Controller
from lib.UI import *
from lib import ResourceManager

import json
import sys
from PyQt5.QtWidgets import QApplication



if __name__ == '__main__':
    ResourceManager.load_text_image_model()
    with open('config/Config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    with open('config/feature_tags.json', 'r', encoding='utf-8') as f:
        feature_tags = json.load(f)

    app = QApplication(sys.argv)

    # 创建 Controller
    controller = Controller(config=config, feature_tags=feature_tags)

    # 创建 UI，传入 Controller
    mainwindow = MainWindow(controller=controller, config=config)
    mainwindow.show()

    sys.exit(app.exec_())   # 启动事件循环