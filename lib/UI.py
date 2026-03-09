# /lib/UI.py
import sys
from PyQt5.QtWidgets import  (QApplication, QMainWindow, QTextEdit, QPushButton,
                              QVBoxLayout, QHBoxLayout, QWidget, QLabel, QScrollArea,
                              QGridLayout, QDialog, QMessageBox, QSizePolicy,
                              QFileDialog, QCheckBox)
# 网络部分
from PyQt5.QtCore import Qt, pyqtSignal, QStandardPaths, QEvent
from PyQt5.QtGui import QPixmap

from lib.Controller import *
from lib.dto.ImageInfoDTO import ImageInfoDTO


def _pil_to_qpixmap(img) -> QPixmap:
    """将PIL的Image转为QPixmap"""
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue())
    return pixmap



class MainWindow(QMainWindow):
    image_load_finish_sgn = pyqtSignal(str, object)    # 类变量（定义在构造函数前，类的本质属性，所有实例共用同一个）

    def __init__(self, controller, config: Dict[str, Any]):
        super().__init__()

        self.log_prefix = "MainWindow"
        self.config = config.get("ui_config")
        self.default_save_path = config.get("default_save_picture_path")
        self.controller = controller
        self.keywords = {}
        self.search_mode = 'internet'
        self._register_controller_callbacks()

        # ui部件
        ### （上半部分）基础输入框
        self.row1_layout = None                     # 第1行布局
        self.row2_layout = None                     # 第2行布局
        self.row3_layout = None                     # 第3行布局，搜索模式选择

        self.input_text_edit = None                 # 需求描述输入框
        self.extractor_keyword_btn = None           # 需求描述输入框对应的提取关键词按钮
        self.keywords_combination_static_label = None           # 静态标签："当前搜索所用关键词组合："QLabel
        self.keywords_label = None                  # 动态文本标签：当前搜索所用关键词组合的变量QLabel。可以直接用\n换行
        self.regeneration_keyword_btn = None        # 重新生成关键词组合按钮
        self.import_local_dir_btn = None            # 导入本地文件夹按钮，将本地图片文件夹中的所有图片导入本地向量数据库中
        self.search_btn = None                      # 搜索按钮
        self.set_mode_internet_btn = None           # 设置搜索模式为：internet
        self.set_mode_local_btn = None              # 设置搜索模式为：local

        ### （下半部分）瀑布流式多行多列图片显示
        self.row4_layout = None                     # 第4行布局（系统信息回显）
        self.system_info_label = None               # 系统信息回显
        self.scroll_area = None                     # 滚动区域
        self.scroll_widget = None                   # 滚动区域的内容
        self.image_grid_layout = None               # 瀑布流式多行多列图片显示
        self.image_grid_column = self.config.get('image_grid_column', 5)
        self.init_ui()

    def _log(self, function_name: str = "None", data: str = "-"):
        """格式化输出"""
        print(f">> >> [{self.log_prefix}]-[{function_name}]: {data}")

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
        self.import_local_dir_btn = QPushButton("导入本地目录")
        self.import_local_dir_btn.setMinimumWidth(80)
        self.import_local_dir_btn.setEnabled(True)
        self.import_local_dir_btn.clicked.connect(self._on_import_local_dir_btn_clicked)

        self.row2_layout.addWidget(self.keywords_combination_static_label, stretch=1)
        self.row2_layout.addWidget(self.keywords_combination_label, stretch=2)
        self.row2_layout.addWidget(self.regeneration_keyword_btn, stretch=1)
        self.row2_layout.addWidget(self.import_local_dir_btn, stretch=1)

        # （上半部分row3）创建第3行布局QHBoxLayout：
        self.row3_layout = QHBoxLayout()
        self.search_btn = QPushButton("搜索")                             # 搜索按钮
        self.search_btn.setMinimumWidth(160)
        self.search_btn.setEnabled(False)
        self.search_btn.clicked.connect(self._on_search_btn_clicked)
        self.set_mode_local_btn = QCheckBox("本地搜索")
        self.set_mode_local_btn.setChecked(False)
        self.set_mode_local_btn.setMinimumWidth(60)
        self.set_mode_local_btn.setMaximumWidth(100)
        self.set_mode_local_btn.clicked.connect(self._on_set_mode_local_btn_clicked)
        self.set_mode_internet_btn = QCheckBox("网络搜索")
        self.set_mode_internet_btn.setChecked(True)
        self.set_mode_internet_btn.setMinimumWidth(60)
        self.set_mode_internet_btn.setMaximumWidth(100)
        self.set_mode_internet_btn.clicked.connect(self._on_set_mode_internet_btn_clicked)

        self.row3_layout.addWidget(self.set_mode_internet_btn, stretch=1)
        self.row3_layout.addWidget(self.set_mode_local_btn, stretch=1)
        self.row3_layout.addWidget(self.search_btn, stretch=1)

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

        # （下半部分row4）创建第4行布局QHBoxLayout：
        self.row4_layout = QHBoxLayout()
        self.system_info_label = QLabel()
        self.system_info_label.setMinimumWidth(200)
        self.row4_layout.addWidget(self.system_info_label, stretch=1)

        # 将3个布局添加到主布局
        main_layout.addLayout(self.row1_layout, stretch=1)
        main_layout.addLayout(self.row2_layout, stretch=1)
        main_layout.addLayout(self.row3_layout, stretch=1)

        main_layout.addWidget(self.scroll_area, stretch=6)
        main_layout.addLayout(self.row4_layout, stretch=1)

    def _register_controller_callbacks(self):
        """将 UI 方法注册为 Controller 的回调函数"""
        self.controller._register_ui_callback('_on_keywords_extracted', self._on_keywords_extracted_DO_update_ui_keywords)
        self.controller._register_ui_callback('_on_query_generated', self._on_query_generated_DO_show_current_query)
        self.controller._register_ui_callback('_on_search_start', self._on_search_start_DO_show_loading)
        self.controller._register_ui_callback('_on_images_load_finish', self._on_images_load_finish_DO_display_image)
        self.controller._register_ui_callback('_on_error', self._on_error_DO_show_error)

    # =================== 按钮事件处理函数（用户点击按钮，调用 Controller 处理，不直接更新ui） ===================
    def _on_extractor_keyword_btn_clicked(self):
        """按钮事件：点击分析关键词按钮"""
        # 获取输入文本
        input_text = self.input_text_edit.toPlainText()
        if not input_text.strip():
            self._log("on_extractor_keyword_btn_clicked", "输入文本为空")
            return
        self.controller.prepare_search_context(input_text)      # 交给Controller处理

    def _on_regeneration_keyword_btn_clicked(self):
        """按钮事件：点击重新生成关键词组合按钮"""
        self.controller.get_next_query()

    def _on_search_btn_clicked(self):
        """按钮事件：点击搜索按钮"""
        self.controller.search_with_current_query(mode=self.search_mode)

    def _on_import_local_dir_btn_clicked(self):
        """按钮事件：点击导入本地目录按钮"""
        file_path = QFileDialog.getExistingDirectory(self, "选择目录", "")
        if file_path:
            self._log('_on_import_local_dir_btn_clicked', f"选中导入本地图片文件夹路径：{file_path}")
            self.import_local_dir_btn.setEnabled(False)     # 禁用按钮，防止重复导入
            self.import_local_dir_btn.setText("导入中...")

            # 创建一个线程，将图片导入到数据库中
            self.import_worker = ImportLocalDirWorker(self.controller, file_path)
            self.import_worker.finished_sgn.connect(self._on_import_finished)
            self.import_worker.start()
        else:
            self._log('_on_import_local_dir_btn_clicked', "导入本地图片文件夹路径无效！！！")

    def _on_set_mode_local_btn_clicked(self):
        """按钮事件：将搜索模式设置为【本地搜索local】"""
        self.search_mode = 'local'
        self.set_mode_local_btn.setChecked(True)
        self.set_mode_internet_btn.setChecked(False)

    def _on_set_mode_internet_btn_clicked(self):
        """按钮事件：将搜索模式设置为【网络搜索internet】"""
        self.search_mode = 'internet'
        self.set_mode_internet_btn.setChecked(True)
        self.set_mode_local_btn.setChecked(False)


    # =================== 回调函数（由 Controller 调用，更新ui） =========================================================
    def _on_keywords_extracted_DO_update_ui_keywords(self, keywords):
        """回调：Controller 关键词已提取。保存关键词到本地变量，准备后续使用"""
        self._log('_on_keywords_extracted', f"收到关键词：{list(keywords.keys())}")
        self.keywords = keywords
        # 注意：这里不更新按钮状态，等查询生成（_on_query_generated）后再更新

    def _on_query_generated_DO_show_current_query(self, query):
        """回调：Controller 生成查询条件。更新关键词组合显示"""
        self._log('_on_query_generated', f"收到查询条件：{query}")
        if query:
            self.display_current_keywords_combination(query)
            self._set_2row_button_enabled(True)
        else:
            self.keywords_combination_label.setText("无有效关键词")
            self._set_2row_button_enabled(False)

    def _on_search_start_DO_show_loading(self, data):
        """后台开始搜索（data参数是作为回调函数传参格式占位用的）"""
        self._log('_on_search_start', "开始搜索")
        self.system_info_label.setText("正在搜索中...")

    def _on_images_load_finish_DO_display_image(self, image_dtos : List[ImageInfoDTO]):
        """后台完成图片加载，开始输出到UI中"""
        self._log('_on_images_load_finish', f"后台完成图片加载，开始输出到UI中，接收到图片dto数量：{len(image_dtos)}")
        self.system_info_label.setText("图片加载完成")
        self.display_image(image_dtos)

    def _on_error_DO_show_error(self, error_msg):
        """发生错误"""
        self._log('_on_error', f"收到错误：{error_msg}")
        self.system_info_label.setText(f"错误：{error_msg}")
        QMessageBox.critical(self, "错误", error_msg)

    # =================== 其他工具函数 ============================================================================
    def _set_2row_button_enabled(self, enabled : bool):
        """设置row2的【重新生成】和【搜索】按钮是否允许点击。当未生成有效关键词组合时不可点击"""
        self.regeneration_keyword_btn.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)

    def display_current_keywords_combination(self, query: List[str]):
        """
        在self.keywords_combination_label中显示当前搜索所用关键词组合
        """
        if not query:
            self.keywords_combination_label.setText("错误：无可用的关键词组合")
            return

        # 获取当前关键词组合并显示
        key_text = ', '.join(query)
        self.keywords_combination_label.setText(key_text)


    def display_image(self, image_dtos : List[ImageInfoDTO]):
        """
        瀑布流显示图片
        调用时机：用户点击搜索按钮后，获取到图片urls时调用
        """
        self._log('display_image', f"开始显示图片，图片数量：{len(image_dtos)}")

        # 清除旧图片的显示
        for i in reversed(range(self.image_grid_layout.count())):
            widget = self.image_grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 添加新图片及对应控件
        for idx, dto in enumerate(image_dtos):
            # 创建标签，显示加载情况（"加载中..."）
            label = QLabel("加载中...")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
            label.setMinimumSize(100, 100)
            label.setMaximumSize(200, 200)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # 设置标签属性，用于后续识别
            label.setProperty('image_url', dto.url)
            label.dto = dto     # 在标签中保存图片dto，方便后续传递给图片信息子窗口

            # # 给标签添加点击事件
            # label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            # 添加到对应网格位置
            row = idx // self.image_grid_column
            col = idx % self.image_grid_column
            self.image_grid_layout.addWidget(label, row, col)

            label.installEventFilter(self)  # 安装事件过滤器，而不是绑定点击事件

            # self._log('display_image', f"添加图片标签-位置：({row}, {col})，图片dto：{dto.to_dict()}")

            # 将图片信息与label绑定
            self._load_image_from_cache(dto, label)

    def _load_image_from_cache(self, dto: ImageInfoDTO, label: QLabel):
        """
        从缓存中加载图片
        """
        image = self.controller.cache_manager.get(dto)
        if image:
            qpixmap = _pil_to_qpixmap(image)
            label.setPixmap(qpixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio))
            # self._log("_load_image_from_cache", f"从缓存中加载图片成功：{dto.to_dict()}")
        else:
            label.setText("图片dto无效")
            self._log("_load_image_from_cache", f"从缓存中加载图片失败！！！：{dto.to_dict()}")

    def eventFilter(self, obj, event):
        """事件过滤器，用于.display_image() 中处理图片点击事件"""
        if event.type() == QEvent.Type.MouseButtonPress:
            self._log('eventFilter', f"点击图片 [{obj.dto.url}]")
            self.show_image_detail(obj.dto)
            return True     # 事件已处理，不再传递给父类
        return super().eventFilter(obj, event)

    def show_image_detail(self, image_dto : ImageInfoDTO):
        """点击图片，弹出详细信息"""
        try:
            self._log('show_image_detail', f"打开图片详情对话框：[{image_dto.url}]")
            image_detail_dialog = ImageDetailDialog(
                self.config,
                self.default_save_path,
                image_dto,
                self.controller.cache_manager
            )
            image_detail_dialog.exec_()
        except Exception as e:
            self._log('show_image_detail', f"图片详细信息弹出失败：{e}")

    def _on_import_finished(self, success, msg):
        """线程结束时，完成导入"""
        self._log('_on_import_finished', "导入完成")
        self.import_local_dir_btn.setEnabled(True)
        self.import_local_dir_btn.setText("导入本地目录")
        if success:
            self.system_info_label.setText(f"导入成功：{msg}")
        else:
            self.system_info_label.setText(f"导入失败：{msg}")
            QMessageBox.critical(self, "错误：导入失败：", msg)

class ImageDetailDialog(QDialog):
    """图片详情对话框"""

    def __init__(self, ui_config, default_save_path, image_dto: ImageInfoDTO, cache_manager: CacheManager):
        super().__init__()
        self.log_prefix = "ImageDetailDialog"
        self.config = ui_config                             # 保存默认 ui 配置
        self.default_save_path = default_save_path          # 保存图片默认路径
        self.image_dto: ImageInfoDTO = image_dto            # 图片信息数据传输对象
        self.cache_manager: CacheManager = cache_manager    # 图片缓存管理器
        layout = QHBoxLayout()                              # 主体水平布局
        self.setWindowTitle("图片详情")

        # 显示图片
        cached_image = self.cache_manager.get(self.image_dto)       # 获取缓存中的图片 PIL.Image
        if cached_image:
            self._log('__init__', "cached_image 已加载")
            cached_image = _pil_to_qpixmap(cached_image)
        else:
            self._log('__init__', "cached_image 未命中")
        self.original_image: Optional[QPixmap] = cached_image       # 原始图片 QPixmap
        self._log('__init__', "self.original_image 加载完成")
        self.img = QLabel()
        self.img.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img.setMinimumSize(500, 400)
        self._log('__init__', "self.img 已创建，开始将图片存入 self.img")
        if self.original_image and not self.original_image.isNull():
            self.img.setPixmap(self.original_image)
            self._log('__init__', "self.original_image 已加载进入 self.img，准备显示")
            self.update_image_display()
        else:
            download_image = self.cache_manager.get(self.image_dto)
            if download_image:
                self._log('__init__', "self.original_image 已重新下载")
                download_image = _pil_to_qpixmap(download_image)
                self.img.setPixmap(download_image)
                self.update_image_display()
            else:
                self._log('__init__', f"self.original_image 错误！无法下载 url：[{self.image_dto.url}]")

        layout.addWidget(self.img, stretch=4)

        # 右侧图片信息
        right_layout = QVBoxLayout()
        self.info_label = QLabel(self.image_dto.url)
        self._log('__init__', f"正在查看图片详细信息，url: {self.info_label.text()}")
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

    def _log(self, function_name: str = "None", data: str = "-"):
        """格式化输出"""
        print(f">> >> >> [{self.log_prefix}]-[{function_name}]: {data}")

    def get_filename_from_url(self):
        """从图片url中获取文件名"""
        url = self.image_dto.url
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
        file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)")
        file_dialog.setWindowTitle("保存图片")

        # 设置默认保存路径
        if self.default_save_path and self.default_save_path != '':                              # 根据Config.json的路径配置保存图片
            file_dialog.setDirectory(self.default_save_path)
        else:                                                   # 否则默认打开本地根目录
            file_dialog.setDirectory(QStandardPaths.writableLocation(QStandardPaths.HomeLocation))

        # 获取url中的文件名
        filename = self.get_filename_from_url()
        file_dialog.selectFile(filename)

        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]          # 获取文件路径
            file_ext = os.path.splitext(file_path)[1].lower()   # 获取文件扩展名
            self._log('save_image', f"开始保存图片：file_ext = [{file_ext}], file_path = [{file_path}]")
            if self.original_image and not self.original_image.isNull():
                if file_ext == ".jpg" or file_ext == ".jpeg":
                    self.original_image.save(file_path, "JPEG")
                elif file_ext == ".bmp":
                    self.original_image.save(file_path, "BMP")
                elif file_ext == ".png":
                    self.original_image.save(file_path, "PNG")
                elif file_ext == ".webp":
                    self.original_image.save(file_path, "WEBP")
                else:
                    self._log('save_image', "不支持的图片格式")
            else:
                self._log('save_image', "图片为空")

    def update_image_display(self):
        """随窗口大小更新图片显示"""
        # self._log('update_image_display', f"开始更新图片显示 [{self.image_dto.url}]")
        if self.original_image and not self.original_image.isNull():
            # self._log('update_image_display', "图片有效，开始缩放")
            scaled_pixmap = self.original_image.scaled(
                self.img.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.img.setPixmap(scaled_pixmap)
        else:
            self._log('update_image_display', "图片无效!!!")

    def resizeEvent(self, event):
        """窗口大小改变时，更新图片显示"""
        super().resizeEvent(event)
        self.update_image_display()


from PyQt5.QtCore import QThread, pyqtSignal

class ImportLocalDirWorker(QThread):
    finished_sgn = pyqtSignal(bool, str)    # 线程结束信号, 参数为成功与否，以及错误信息

    def __init__(self, controller: Controller, local_dir: str):
        super().__init__()
        self.controller = controller
        self.local_dir = local_dir

    def run(self):
        print("【子线程】：开始导入本地图片目录")
        try:
            self.controller.import_local_image_dir(self.local_dir)
            self.finished_sgn.emit(True, "")
        except Exception as e:
            self.finished_sgn.emit(False, str(e))

if __name__ == '__main__':
    with open('config/Config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    with open('config/feature_tags.json', 'r', encoding='utf-8') as f:
        feature_tags = json.load(f)

    app = QApplication(sys.argv)

    controller = Controller(config=config, feature_tags=feature_tags)
    mainwindow = MainWindow(controller=controller, config=config)
    mainwindow.show()

    sys.exit(app.exec_())   # 启动事件循环