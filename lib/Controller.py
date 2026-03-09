# /lib/Controller.py
# 用来控制ImageSearcher、KeywordExtractor、QueryGenerator类的交互
# 最终由外界ui来使用该Controller

from lib.ImageSearchClass import *
from lib.QueryGenerator import *
from lib.KeywordExtractor import *
from lib.CacheManager import *
from lib.VisualEvaluator import *
from lib.dto.SearchResultDTO import *
from lib.dto.ImageInfoDTO import *
from lib.LocalDB import *
from lib.LocalImageLoader import *

class Controller:
    def __init__(self, config : Dict[str, Any], feature_tags : Dict[str, Any], proxy = None):
        self.log_prefix = "Controller"
        self.config = config

        # 各个组件实例
        self.query_generator: QueryGenerator = QueryGenerator(config=config, proxy=proxy)
        self.keyword_extractor: KeywordExtractor = KeywordExtractor(config=config, feature_tags=feature_tags, mod='jieba')
        self.image_searcher_factory: ImageSearchFactory = ImageSearchFactory(config=config, proxy=proxy)
        self.image_searchers = [self.image_searcher_factory.get_searcher("huabanwang")]     # 临时调试，固定使用花瓣网
        self.cache_manager: CacheManager = CacheManager()
        self.visual_evaluator: VisualEvaluator = VisualEvaluator(cache_manager=self.cache_manager)
        self.local_db: LocalDB = LocalDB(db_path=config.get("local_db_path", "./cache/LocalDB_dir"))
        self.local_image_loader = LocalImageLoader()

        # 各类当前状态
        self.keywords = {}                                                      # 当用户输入需求描述并点击提取按钮时，记录提取得到的关键词字典
        self.proxy = self.set_proxy()                                           # 设置代理
        self.default_save_path = config.get("default_save_picture_path", "")    # 默认保存图片的路径
        self.current_input_text = ""
        self.current_keywords = None
        self.generated_queries = []  # 存储所有生成的查询
        self.current_query_index = 0  # 当前使用的查询索引
        self.search_results = {}
        self.ui_callbacks = {                   # UI回调函数，由外界ui调用，传入参数为回调函数
            '_on_keywords_extracted': None,     # 关键词提取完成
            '_on_query_generated': None,        # 查询生成完成
            '_on_search_start': None,           # 搜索开始
            '_on_images_load_finish': None,     # 图片加载完成
            '_on_error': None                   # 发生错误
        }

    def _log(self, function_name: str = "None", data: str = "-"):
        '''格式化输出'''
        print(f">> [{self.log_prefix}]-[{function_name}]: {data}")

    def _register_ui_callback(self, event_name, callback):
        '''注册UI回调函数'''
        if event_name in self.ui_callbacks:
            self.ui_callbacks[event_name] = callback
            self._log('register_ui_callback', f"注册UI回调函数：{event_name} : {callback.__name__}")
        else:
            self._log('register_ui_callback', f"无效的UI回调函数：{event_name} : {callback.type()}")

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

    def _notify_ui(self, event_name, data):
        '''通知UI事件发生'''
        callback = self.ui_callbacks.get(event_name)
        if callback:
            try:
                self._log('_notify_ui', f"通知UI事件：{event_name}")
                callback(data)
            except Exception as e:
                self._log('_notify_ui', f"UI回调函数 [{event_name}] 发生异常：{str(e)}")
        else:
            self._log('_notify_ui', f"无效的UI回调函数：{event_name}")

    def prepare_search_context(self, input_text: str):
        """
        准备搜索上下文，包括关键词提取和初始查询生成
        由 UI._on_extractor_keyword_btn_clicked()调用
        """
        try:
            self._log('prepare_search_context', f"准备搜索上下文：{input_text}")
            self.current_input_text = input_text
            self.current_keywords = self.keyword_extractor.extract(input_text)
            self._notify_ui('_on_keywords_extracted', self.current_keywords)

            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0
            self._notify_ui('_on_query_generated', self.generated_queries[0])
        
            self._log('prepare_search_context', f"提取关键词：{self.current_keywords}, 生成查询数量：{len(self.generated_queries)}")
            return self.current_keywords, self.generated_queries

        except Exception as e:
            self._log('prepare_search_context', f"准备搜索上下文失败：{str(e)}")
            self._notify_ui('_on_error', str(e))
            return []

    def get_first_query(self) -> List[str]:
        """
        获取第一组查询关键词
        """
        if not self.generated_queries:
            return []
        self.current_query_index = 0
        return self.generated_queries[self.current_query_index]

    def get_next_query(self) -> List[str]:
        """
        获取下一个查询组合，如果需要则重新生成
        """

        # 如果还有未使用的查询组合，直接返回下一个
        if (self.current_query_index + 1) < len(self.generated_queries):
            self.current_query_index += 1
            self._notify_ui('_on_query_generated', self.generated_queries[self.current_query_index])
            return self.generated_queries[self.current_query_index]

        # 如果没有更多查询组合，重新生成一批
        if self.current_keywords:
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0 if self.generated_queries else -1
            if self.generated_queries:
                self._notify_ui('_on_query_generated', self.generated_queries[self.current_query_index])
                return self.generated_queries[self.current_query_index]
        
        return []

    def reset_query_generation(self):
        """
        重置查询生成状态，重新开始生成查询组合
        """
        if self.current_keywords:
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0

    def search_with_current_query(self, mode: str = 'internet') -> List[ImageInfoDTO]:
        """
        使用当前查询组合进行搜索，可选搜索模式：
            'internet' : 网络搜索，调用图片搜索器进行url解析相关操作
            'local' : 本地搜索，读取本地数据库中记录的图片，不使用网络
            （未启用） 'mix' : 混合搜索，既网络搜索，又本地搜索
        由UI._on_search_btn_clicked()调用
        触发2个回调函数：_on_search_start 和 _on_images_load_finish
        """
        self._log('search_with_current_query', f"【搜索模式】：{mode}，开始搜索：{self.current_input_text}")

        try:
            if not self.generated_queries or self.current_query_index < 0:
                self._log('search_with_current_query', "错误：没有可用的查询组合")
                self._notify_ui('_on_error', "没有可用的查询组合")
                raise ValueError("没有可用的查询组合")

            # 生成查询语句
            current_query = self.generated_queries[self.current_query_index]    # 获取当前的查询语句
            self._log('search_with_current_query', f"使用查询：{current_query}")
            self._notify_ui('_on_search_start', current_query)
            qualited_imageinfo_dtos: List[ImageInfoDTO] = []

            if mode not in ['internet','local']:
                mode = 'internet'

            # 根据搜索模式搜索图片
            if mode == 'internet':
                # 开始搜索图片，获取返回的url列表
                urls = self.image_searchers[0].search(current_query)                # 在图像搜索器中使用查询语句进行搜索，返回图片 url 列表
                valid_urls = self.cache_manager.add_batch(urls)                     # 下载图片到缓存，返回有效的图片 url 列表
                query_text = " ".join(current_query)                                # 构造查询文本
                self._log('search_with_current_query', f"有效 URL 数量：{len(valid_urls)}, 查询文本：{query_text}")

                # 交给 VisualEvaluator 进行视觉评估
                qualited_imageinfo_dtos = self.visual_evaluator.filter_and_rank(query_text, valid_urls, threshold=self.config.get("similarity_threshold", 0.2))
                self._log('search_with_current_query', f"筛选后图片数量：{len(qualited_imageinfo_dtos)}")
                self._notify_ui('_on_images_load_finish', qualited_imageinfo_dtos)

            elif mode == 'local':
                query_text_feature = self.visual_evaluator.get_text_feature(current_query)  # 获取搜索文本的文本特征
                metadatas = self.local_db.search_by_feature(query_feature=query_text_feature, top_k=self.config.get("top_k", 10))
                self._log('search_with_current_query', f"搜索结果数量：{len(metadatas)}")
                for metadata in metadatas:
                    dto: ImageInfoDTO = ImageInfoDTO(
                        local_path=metadata['local_path'],
                        score=metadata['distance']
                    )
                    if metadata['source'] != 'unknown':
                        dto.source = metadata['source']
                    if metadata['url'] != 'unknown':
                        dto.url = metadata['url']

                    qualited_imageinfo_dtos.append(dto)
                self._log('search_with_current_query', f"筛选后图片数量：{len(qualited_imageinfo_dtos)}")
                self._notify_ui('_on_images_load_finish', qualited_imageinfo_dtos)

            self._log('search_with_current_query', f"搜索结束，图片数量：{len(qualited_imageinfo_dtos)}")
            return qualited_imageinfo_dtos

        except Exception as e:
            self._log('search_with_current_query', f"搜索失败：{str(e)}")
            self._notify_ui('_on_error', str(e))
            return []

    def get_current_query(self) -> List[str]:
        """
        获取当前查询组合
        """
        if not self.generated_queries or self.current_query_index < 0:
            return []
        return self.generated_queries[self.current_query_index]

    def regenerate_queries(self) -> List[List[str]]:
        """
        重新生成查询组合
        """
        if self.current_keywords:
            self.generated_queries = self.query_generator.generate_query(self.current_keywords)
            self.current_query_index = 0
            return self.generated_queries
        return []

    def import_local_image_dir(self, local_path: str):
        """
        导入本地图片文件夹，装填本地图片数据库
        由 UI 调用
        """
        local_path = os.path.abspath(local_path)
        self._log('import_local_image_dir', f"导入本地图片文件夹：{local_path}")
        image_dtos = self.local_image_loader.scan_folder(local_path)                    # 扫描文件夹，返回图片路径列表
        image_features = self.local_image_loader.save_image_features(image_dtos, self.visual_evaluator)
        self._log('import_local_image_dir', f"提取有效图片特征数量：{len(image_features)}")
        self.local_db.add_image_by_batch(image_dtos, image_features)                    # 添加图片特征向量到数据库
