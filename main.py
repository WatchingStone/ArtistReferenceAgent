import json
import sys
import os
from PyQt5.QtWidgets import QApplication
from lib.UI import *



if __name__ == '__main__':
    with open('config/Config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    with open('config/feature_tags.json', 'r', encoding='utf-8') as f:
        feature_tags = json.load(f)

    app = QApplication(sys.argv)

    mainwindow = MainWindow(config=config, feature_tags=feature_tags)
    mainwindow.show()

    sys.exit(app.exec_())   # 启动事件循环