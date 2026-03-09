# /lib/CacheManager.py
# 缓存管理器。主要缓存图片数据，那些相似度得分低于阈值的图片不必缓存。设计一个单独的类有助于添加LRU等缓存管理功能
import os
from typing import Optional, Dict, List
from PIL import Image
import requests
from io import BytesIO
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed     # 并发线程池
from collections import OrderedDict                                 # LRU缓存
from lib.dto.ImageInfoDTO import ImageInfoDTO

class CacheManager:
    '''单例模式，缓存各类数据，主要是图片数据'''
    _instance = None                # 类变量，所有实例都指向同一个对象
    _cls_lock = threading.Lock()    # 单例初始化锁，保证单例模式下只有一个实例

    def __new__(cls):                                       # 控制创建对象的唯一入口
        if cls._instance is None:                           # 第一次检查：防止锁竞争
            with cls._cls_lock:
                if cls._instance is None:                   # 第二次检查：防止多个线程同时通过第一次检查
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:                           # 防止重复初始化
            return

        self.max_cache_size = 100
        self.image_dowmload_timeout = 10
        self.max_worker_num = 5                         # 线程池大小（最大并发线程数）
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://huaban.com/',  # 通用的请求头配置，添加 Referer 绕过防盗链
        }

        self.image_cache: OrderedDict[str, Image.Image] = OrderedDict()     # 图片数据缓存字典，自带LRU缓存功能
        self._data_lock = threading.Lock()              # 实例锁，保证self.image_cache读写安全
        self._initialized = True                        # 初始化完成
        self._log('__init__', "缓存管理器初始化完成")

    def _log(self,function_name: str = "None", data: str = "-"):
        '''格式化输出'''
        print(f">> >> [CacheManager]-[{function_name}]: {data}")

    # ================== 锁内：核心原子操作 ==================
    def _get_from_cache(self, url: str) -> Optional[Image.Image]:
        '''原子操作，从缓存中获取图片，自带LRU'''
        with self._data_lock:
            if url in self.image_cache:
                self.image_cache.move_to_end(url)   # 移动到末尾，实现LRU
                return self.image_cache[url]
        return None

    def _add_to_cache(self, url: str, image: Image.Image):
        '''原子操作，将图片添加进缓存'''
        with self._data_lock:
            self.image_cache[url] = image
            self.image_cache.move_to_end(url)       # 移动到末尾，实现LRU

            # 检查缓存容量
            if len(self.image_cache) > self.max_cache_size:
                removed_url, _ = self.image_cache.popitem(last=False)
                self._log('_add_to_cache', f"缓存容量已满，移除图片[{removed_url}]")

    # ================== 锁外：耗时操作 ==================
    def _download_image(self, url: str, headers: Dict[str, str] = None) -> Optional[Image.Image]:
        '''用url下载图片'''
        try:
            request_headers = self.default_headers.copy()   # 设置请求头
            if headers:
                request_headers.update(headers)
            response = requests.get(url, timeout=self.image_dowmload_timeout, headers=request_headers)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            image = image.convert('RGB')    # 深拷贝并转为 RGB 格式
            return image
        except Exception as e:
            self._log('_download_image', f"图片[{url}]下载失败：{str(e)}")
            return None

    # ================== 对外接口 ==================
    def get_by_url(self, url: str) -> Optional[Image.Image]:
        '''从缓存中获取图片'''
        # 检查内存
        self._log('get', f"开始获取图片[{url}]")
        img = self._get_from_cache(url)
        if img:
            return img
        self._log('get', f"图片不在缓存中，开始下载")

        # 若不在缓存中，则下载
        img = self._download_image(url)
        if img:
            self._log('get', f"图片下载成功")
            self._add_to_cache(url, img)
            return img
        self._log('get', f"图片下载失败")

        return None

    def get(self, dto: ImageInfoDTO) -> Optional[Image.Image]:
        '''传入图片dto，从缓存中获取图片'''
        # 先检查dto中的local_path是否有效
        local_path = dto.local_path
        if local_path is not None and os.path.exists(local_path):
            # 检查内存中是否存在该图片
            img = self._get_from_cache(local_path)
            if img:
                return img
            else:
                # 若不在缓存中，则从本地路径加载
                img = Image.open(local_path)
                if img:
                    self._log('get', f"从本地路径加载成功")
                    self._add_to_cache(local_path, img)
                    return img
                self._log('get', f"从本地路径加载失败")
                return None
        else:
            url = dto.url
            # 检查内存
            self._log('get', f"开始获取图片[{url}]")
            img = self._get_from_cache(url)
            if img:
                return img
            self._log('get', f"图片不在缓存中，开始下载")

            # 若不在缓存中，则下载
            img = self._download_image(url)
            if img:
                self._log('get', f"图片下载成功")
                self._add_to_cache(url, img)
                return img
            self._log('get', f"图片下载失败")

            return None


    def add_batch(self, url_list: List[str]) -> List[str]:
        '''批量下载图片进缓存，返回成功下载或已在缓存中的图片url列表'''
        success_urls = []       # 进入缓存的图片url列表
        candidate_urls = []     # 不在缓存中的url

        # 筛选出不在缓存中的url
        for url in url_list:
            if self._get_from_cache(url):
                success_urls.append(url)
            else:
                candidate_urls.append(url)

        # 如果候选url为空，则无需下载，直接返回成功下载的url列表
        if not candidate_urls:
            return success_urls

        # 开始批量处理下载任务
        self._log('add_batch', f"开始批量处理下载任务，候选url数量：{len(candidate_urls)}")

        with ThreadPoolExecutor(max_workers=self.max_worker_num) as executor:                           # 使用线程池并发下载
            url_futures = {executor.submit(self._download_image, url) : url for url in candidate_urls}  # 提交任务
            # as_completed 是 concurrent.futures 模块中的一个迭代器函数，会按照任务实际完成的先后顺序逐个返回 Future 对象
            # 如果已有任务完成：立即返回已完成的 Future
            # 如果没有任何任务完成：阻塞等待，直到至少有一个任务完成并返回
            for future in as_completed(url_futures):                                                    # 等待任务完成
                url = url_futures[future]
                try:
                    image = future.result()                                                             # 获取结果。阻塞，直到任务完成，不过此时已经由as_completed保证任务完成
                    if image:
                        self._add_to_cache(url, image)
                        success_urls.append(url)
                except Exception as e:
                    self._log('add_batch', f"图片[{url}]下载失败：{str(e)}")

        return success_urls