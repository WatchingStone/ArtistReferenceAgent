import json
import sys
import os
from typing import List, Dict, Any
from PyQt5.QtWidgets import  (QApplication, QMainWindow, QTextEdit, QPushButton,
                              QVBoxLayout, QHBoxLayout, QWidget, QLabel, QScrollArea,
                              QGridLayout, QFrame, QDialog, QMessageBox, QSizePolicy,
                              QFileDialog)
# 网络部分
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QStandardPaths
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtGui import QPixmap

from lib.Controller import *
from lib.NetworkProxyDetection import *

class MainWindow(QMainWindow):
    image_load_finish_sgn = pyqtSignal(str, object)    # 类变量（定义在构造函数前，类的本质属性，所有实例共用同一个）

    def __init__(self,  config : Dict[str, Any], feature_tags : Dict[str, Any]):
        super().__init__()
        # 逻辑部分
        self.keywords = {}                          # 当用户输入需求描述并点击提取按钮时，记录提取得到的关键词字典
        self.network_manager = QNetworkAccessManager()
        self.proxy = self.set_proxy()
        self.image_load_finish_sgn.connect(self._on_image_load_finish)  # 绑定图片加载完成信号，
        self.image_cache = {}                       # 图片缓存
        self.config = config.get("ui_config")
        self.default_save_path = config.get("default_save_picture_path", "")
        self.controller = Controller(config=config, feature_tags=feature_tags, proxy=self.proxy)

        # ui部件
        ### （上半部分）基础输入框
        self.row1_layout = None                     # 第1行布局
        self.row2_layout = None                     # 第2行布局
        self.row3_layout = None                     # 第3行布局（系统信息回显）
        self.input_text_edit = None                 # 需求描述输入框
        self.extractor_keyword_btn = None           # 需求描述输入框对应的提取关键词按钮
        self.keywords_combination_static_label = None           # 静态标签："当前搜索所用关键词组合："QLabel
        self.keywords_label = None                  # 动态文本标签：当前搜索所用关键词组合的变量QLabel。可以直接用\n换行
        self.regeneration_keyword_btn = None        # 重新生成关键词组合按钮
        self.search_btn = None                      # 搜索按钮
        self.system_info_label = None               # 系统信息回显
        ### （下半部分）瀑布流式多行多列图片显示
        self.scroll_area = None                     # 滚动区域
        self.scroll_widget = None                   # 滚动区域的内容
        self.image_grid_layout = None               # 瀑布流式多行多列图片显示
        self.image_grid_column = self.config.get('image_grid_column', 5)
        self.init_ui()



    def init_ui(self):
        """初始化ui界面"""
        self.setWindowTitle("ArtistReferenceAgent")
        self.setGeometry(
            self.config.get('windowstart_x', 100),
            self.config.get('windowstart_y', 100),
            self.config.get('windowsize_width', 800),
            self.config.get('windowsize_height', 600)
        )

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # （上半部分row1）创建第1行布局QHBoxLayout：
        ### 包含：需求描述输入框QTextEdit、分析关键词按钮QPushButton
        self.row1_layout = QHBoxLayout()
        self.input_text_edit = QTextEdit()                              # 需求描述输入框
        self.input_text_edit.setMaximumHeight(100)
        self.input_text_edit.setPlaceholderText("请输入参考需求描述")
        self.input_text_edit.setPlainText("请给我查找一个穿着短裙演出服的日式偶像少女在舞台上一只手握话筒、另一只手比剪刀手的图片")
        self.input_text_edit.setMinimumWidth(200)
        self.extractor_keyword_btn = QPushButton("分析关键词")        # 需求描述输入框对应的搜索按钮
        self.extractor_keyword_btn.setMinimumWidth(80)
        self.extractor_keyword_btn.clicked.connect(self._on_extractor_keyword_btn_clicked)
        self.row1_layout.addWidget(self.input_text_edit, stretch=4)
        self.row1_layout.addWidget(self.extractor_keyword_btn, stretch=1)

        # （上半部分row2）创建第2行布局QHBoxLayout：
        ### 包含："当前搜索所用关键词组合："QLabel、当前搜索所用关键词组合的变量QLabel、"重新生成关键词组合"QPushButton
        self.row2_layout = QHBoxLayout()
        self.keywords_combination_static_label = QLabel("当前搜索所用关键词组合：")     # 静态标签："当前搜索所用关键词组合："QLabel
        self.keywords_combination_static_label.setMinimumWidth(100)
        self.keywords_combination_label = QLabel()                                  # 动态文本标签：当前搜索所用关键词组合的变量QLabel。可以直接用\n换行
        self.keywords_combination_label.setMinimumWidth(200)
        self.regeneration_keyword_btn = QPushButton("重新生成关键词组合")
        self.regeneration_keyword_btn.clicked.connect(self._on_regeneration_keyword_btn_clicked)
        self.regeneration_keyword_btn.setEnabled(False)                 # 先设置禁用
        self.search_btn = QPushButton("搜索")                             # 搜索按钮
        self.search_btn.setMinimumWidth(80)
        self.search_btn.setEnabled(False)
        self.search_btn.clicked.connect(self._on_search_btn_clicked)
        self.row2_layout.addWidget(self.keywords_combination_static_label, stretch=1)
        self.row2_layout.addWidget(self.keywords_combination_label, stretch=2)
        self.row2_layout.addWidget(self.regeneration_keyword_btn, stretch=1)
        self.row2_layout.addWidget(self.search_btn, stretch=1)

        # （上半部分row3）创建第3行布局QHBoxLayout：
        self.row3_layout = QHBoxLayout()
        self.system_info_label = QLabel()
        self.system_info_label.setMinimumWidth(200)
        self.row3_layout.addWidget(self.system_info_label, stretch=1)

        #  （下半部分）瀑布流式多行多列图片显示
        self.scroll_area = QScrollArea()                            # 创建滚动区域
        self.scroll_area.setWidgetResizable(True)                   # 设置滚动区域可自适应
        self.scroll_widget = QWidget()                              # 创建一个QWidget作为滚动区域的内容
        self.scroll_area.setWidget(self.scroll_widget)
        self.image_grid_layout = QGridLayout()                      # 创建一个grid布局
        self.image_grid_layout.setSpacing(10)                       # 设置图片之间的网格间距
        self.image_grid_layout.setContentsMargins(10, 10, 10, 10)   # 设置边距
        self.scroll_widget.setLayout(self.image_grid_layout)
        main_layout.addWidget(self.scroll_area)

        # 将3个布局添加到主布局
        main_layout.addLayout(self.row1_layout, stretch=1)
        main_layout.addLayout(self.row2_layout, stretch=1)
        main_layout.addLayout(self.row3_layout, stretch=1)
        main_layout.addWidget(self.scroll_area, stretch=6)

    def set_proxy(self):
        """设置代理"""
        proxy = get_proxies()
        if proxy and 'http' in proxy:
            proxy_url = proxy['http']
            # 将代理url解析并设置给QNetworkAccessManager
            from PyQt5.QtNetwork import QNetworkProxy
            proxy_parts = proxy_url.replace('http://', '').split(':')
            if len(proxy_parts) == 2:
                p = QNetworkProxy()
                p.setType(QNetworkProxy.HttpProxy)
                p.setHostName(proxy_parts[0])
                p.setPort(int(proxy_parts[1]))
                QNetworkProxy.setApplicationProxy(p)
        return proxy

    def display_image(self, image_urls : List[str]):
        """
        瀑布流显示图片
        调用时机：用户点击搜索按钮后，获取到图片urls时调用
        """
        # 清除旧图片的显示
        for i in reversed(range(self.image_grid_layout.count())):
            widget = self.image_grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 添加新图片及对应控件
        for idx, url in enumerate(image_urls):
            # 创建标签，显示加载情况（"加载中..."）
            label = QLabel("加载中...")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")

            # 设置标签属性，用于后续识别
            label.setProperty('image_url', url)

            # 给标签添加点击事件
            label.setCursor(Qt.PointingHandCursor)

            # 添加到对应网格位置
            row = idx // self.image_grid_column
            col = idx % self.image_grid_column
            self.image_grid_layout.addWidget(label, row, col)

            # 启动图片加载流程
            self._load_image_from_url(url, label)

    def test_show_message(self, image_info : Dict[str, Any]):
        """测试显示消息框"""
        dialog = ImageDetailDialog(image_info)
        dialog.exec_()

        # message_box = QMessageBox()
        # message_box.setWindowTitle("提示")
        # message_box.setText("这是一个测试消息框")
        # message_box.exec_()

    def show_image_detail(self, image_info: Dict[str, Any]):
        """点击加载的图片，弹出详细信息"""
        image_detail_dialog = ImageDetailDialog(self.config, self.default_save_path, image_info)
        image_detail_dialog.exec_()

    def display_current_keywords_combination(self, query: List[str]):
        """
        显示当前搜索所用关键词组合在self.keywords_combination_label中
        """
        if not query:
            self.keywords_combination_label.setText("错误：无可用的关键词组合")
            return

        # 获取当前关键词组合并显示
        key_text = ', '.join(query)
        self.keywords_combination_label.setText(key_text)

    def _load_image_from_url(self, url : str, label : QLabel):
        """
        从单个url加载图片，告诉图片需要传递给label
        调用时机：由display_image()调用
        """
        # 若缓存中存在该图片，则直接显示
        if url in self.image_cache:
            label.setPixmap(self.image_cache[url])
            return

        # 创建网络请求
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self._on_download_finished(url, reply, label))

    def _on_download_finished(self, url : str, reply : QNetworkReply, label : QLabel):
        """
        图片下载完成的回调函数，从网络请求的响应中提取图片信息
        调用时机：在_load_image_from_url()完成图片网络请求、获得响应时调用
        """
        if reply.error():
            print(f"图片下载失败：{reply.error()}")
            label.setText("加载失败")
            return

        # 读取图片数据
        data = reply.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        # scaled_pixmap = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)    # 缩放

        # 发射信号通知图片加载完成
        self.image_load_finish_sgn.emit(url, pixmap)
        reply.deleteLater()

    def _on_image_load_finish(self, url : str, pixmap : QPixmap):
        """
        当接收到由_on_download_finished()发出的image_load_finish_sgn时，处理并显示加载好的图片pixmap
        """
        self.image_cache[url] = pixmap

        # 遍历网格布局中的所有控件，找到对应url的label并设置图片
        for i in reversed(range(self.image_grid_layout.count())):
            widget = self.image_grid_layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel):
                # 获取控件关联的url
                label_url = widget.property('image_url')
                if label_url == url:
                    scaled_pixmap = pixmap.scaled(widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    widget.setPixmap(scaled_pixmap)
                    image_info = {"url": url, "pixmap": pixmap}
                    widget.mousePressEvent = lambda event, info=image_info: self.show_image_detail(info)
                    break

    def _set_2row_button_enabled(self, enabled : bool):
        """设置row2的【重新生成】和【搜索】按钮是否允许点击。当未生成有效关键词组合时不可点击"""
        self.regeneration_keyword_btn.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)

    def _on_extractor_keyword_btn_clicked(self):
        """按钮事件：点击分析关键词按钮"""
        # 获取输入文本
        input_text = self.input_text_edit.toPlainText()
        if not input_text.strip():
            return

        try:
            # 使用Controller准备搜索上下文
            keywords, queries = self.controller.prepare_search_context(input_text)
            self.keywords = keywords

            # 获取第一组查询关键词
            first_query = self.controller.get_first_query()
            if first_query:
                self.display_current_keywords_combination(first_query)
                self._set_2row_button_enabled(True)
            else:
                self.keywords_combination_label.setText("无有效关键词")
                self._set_2row_button_enabled(False)
        except Exception as e:
            self.keywords_combination_label.setText(f"提取关键词出错：{str(e)}")

    def _on_regeneration_keyword_btn_clicked(self):
        """按钮事件：点击重新生成关键词组合按钮"""
        try:
            # 获取下一组查询关键词
            next_query = self.controller.get_next_query()
            if next_query:
                self.display_current_keywords_combination(next_query)
                self._set_2row_button_enabled(True)
            else:
                self.keywords_combination_label.setText("无法生成新的关键词组合")
                self._set_2row_button_enabled(False)
        except Exception as e:
            self.keywords_combination_label.setText(f"重新生成关键词组合失败：{str(e)}")
            return

    def _on_search_btn_clicked(self):
        """按钮事件：点击搜索按钮"""
        try:
            image_urls = self.controller.search_with_current_query()
            if not image_urls:
                self.system_info_label.setText("无图片结果")
                return
            self.display_image(image_urls)
        except Exception as e:
            self.system_info_label.setText(f"图片搜索失败：{str(e)}")


class ImageDetailDialog(QDialog):
    """图片详情对话框"""

    def __init__(self, ui_config, default_save_path, image_info : Dict[str, Any]):
        super().__init__()
        self.config = ui_config                     # 保存默认ui配置
        self.default_save_path = default_save_path  # 保存图片默认路径
        self.image_info = image_info
        layout = QHBoxLayout()                      # 主体水平布局
        self.setWindowTitle("图片详情")

        # 显示图片
        self.original_pixmap = image_info.get('pixmap', None)
        self.img = QLabel()
        self.img.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.img.setAlignment(Qt.AlignCenter)
        self.img.setMinimumSize(500, 400)
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.img.setPixmap(self.original_pixmap)
            self.update_image_display()
        layout.addWidget(self.img, stretch=4)

        # 右侧图片信息
        right_layout = QVBoxLayout()
        self.info_label = QLabel(image_info.get('url', '无图片url信息'))
        print(f"正在查看图片详细信息，url: {self.info_label.text()}")
        self.info_label.setWordWrap(True)       # 自动换行
        self.info_label.setMaximumSize(300, 200)
        right_layout.addWidget(self.info_label, stretch=1)
        ### 右侧保存按钮
        save_btn = QPushButton("保存图片")
        save_btn.clicked.connect(self.save_image)
        right_layout.addWidget(save_btn, stretch=1)

        layout.addLayout(right_layout, stretch=1)
        self.setLayout(layout)
        self.resize(1000, 600)

    def get_filename_from_url(self):
        """从图片url中获取文件名"""
        url = self.image_info.get('url', '')
        if url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)                      # URL包含协议、域名、路径等多个组成部分，要用urlparse解析
                filename = os.path.basename(parsed_url.path)
                if filename:
                    return filename
            except Exception as e:
                print(f"获取文件名失败：{str(e)}")
        return "unknown_image.png"  # 默认文件名

    def save_image(self):
        """保存图片"""
        file_dialog = QFileDialog()
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setDefaultSuffix("png")
        file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.bmp)")
        file_dialog.setWindowTitle("保存图片")

        # 设置默认保存路径
        if self.default_save_path and self.default_save_path != '':                              # 根据Config.json的路径配置保存图片
            file_dialog.setDirectory(self.default_save_path)
        else:                                                   # 否则默认打开本地根目录
            file_dialog.setDirectory(QStandardPaths.writableLocation(QStandardPaths.HomeLocation))

        # 获取url中的文件名
        filename = self.get_filename_from_url()
        file_dialog.selectFile(filename)

        # 获取文件扩展名（图片格式，默认为png）
        file_ext = os.path.splitext(filename)[1].lower()

        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            if self.original_pixmap and not self.original_pixmap.isNull():
                if file_ext == ".jpg" or file_ext == ".jpeg":
                    self.original_pixmap.save(file_path, "JPEG")
                elif file_ext == ".bmp":
                    self.original_pixmap.save(file_path, "BMP")
                elif file_ext == ".png":
                    self.original_pixmap.save(file_path, "PNG")
                else:
                    print("不支持的图片格式")
            else:
                print("图片为空")

    def update_image_display(self):
        """随窗口大小更新图片显示"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            scaled_pixmap = self.original_pixmap.scaled(
                self.img.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.img.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """窗口大小改变时，更新图片显示"""
        super().resizeEvent(event)
        self.update_image_display()

if __name__ == '__main__':
    with open('config/Config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    with open('config/feature_tags.json', 'r', encoding='utf-8') as f:
        feature_tags = json.load(f)

    app = QApplication(sys.argv)

    mainwindow = MainWindow(config=config, feature_tags=feature_tags)
    mainwindow.show()

    sys.exit(app.exec_())   # 启动事件循环