# /lib/ImageSearchClass.py
import abc
import requests
from typing import List, Dict, Any
from lib.NetworkProxyDetection import *
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import json

class BaseImageSearch(abc.ABC):
    '''图片搜索类基类，定义抽象接口'''
    def __init__(self, config : Dict[str, Any], proxy=None, timeout=None):
        self.config = config
        self.api_key = config.get('api_key', '')         # 从配置获取API密钥
        self.enabled = config.get('enabled', False)
        self.max_results = config.get('max_results', 5)

        if config.get("timeout", None):
            self.timeout = config.get("timeout", 10)
        else:
            self.timeout = timeout

        self.proxy = proxy

    @abc.abstractmethod
    def search(self, query : List[str]) -> List[str]:
        '''执行图片搜索，返回图片url列表'''
        pass

    def _make_request(self, url : str, params : Dict[str, Any], headers=None) -> Dict:
        '''通用请求方法，处理api调用'''
        if not self.enabled:
            raise ValueError(f"搜索网址 【{self.__class__.__name__}】 当前不可用")

        print(f"尝试访问url：{url}")
        start_time = time.time()

        try:
            if headers:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    proxies=self.proxy
                )
            else:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    proxies=self.proxy
                )

            response.raise_for_status()     # 检查HTTP状态码（非200则抛出异常
            print(f"页面加载完成，用时：{time.time() - start_time}")
            return response.json()
        except Exception as e:
            raise RuntimeError(f"API 请求错误：{str(e)}") from e

    def _get_url_response(self, url : str, referer=None, headers=None):
        """对于哪些没有api的网页，只能直接手动构造url去访问，响应可能是json或html。那么不能使用_make_request，而是使用该方法，返回webdriver.Chrome对象"""
        if not self.enabled:
            raise ValueError(f"搜索网址 【{self.__class__.__name__}】 当前不可用")

        chrome_options = Options()
        chrome_options.add_argument("--headless")                   # 启用无头模式，浏览器在后台运行不显示GUI界面
        chrome_options.add_argument('--no-sandbox')                 # 禁用沙盒模式，避免在某些环境下出现权限问题
        chrome_options.add_argument('--disable-dev-shm-usage')      # 禁用/dev/shm的使用，避免在内存受限环境中出现问题
        chrome_options.add_argument('--disable-logging')            # 禁用日志输出，减少控制台信息
        chrome_options.add_argument('--log-level=3')                # 设置日志级别为3（ERROR级别），只显示错误信息
        chrome_options.add_argument('--silent')                     # 静默模式，进一步减少输出信息
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
        chrome_options.add_argument(f'--referer={referer}')     # 设置Referer头，形如'--referer=https://huaban.com/'

        driver = None

        print(f"尝试访问url：{url}")
        start_time = time.time()

        try:
            # 创建ChromeDriver
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(self.timeout or 10)

            # 发送请求获取网页内容
            driver.get(url)


            wait = WebDriverWait(driver, self.timeout or 10)                            # 等待网页加载完成
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'hb-image')))     # 等待图片加载完成

            # # 滚动页面以触发懒加载
            # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # time.sleep(2)

            print(f"页面加载完成，用时：{time.time() - start_time}")
            return driver
        except TimeoutException:
            print(f"页面加载超时：{url}")
            return None
        except Exception as e:
            raise RuntimeError(f"网页请求错误：{str(e)}")

    def _query_convert(self, query : List[str]) -> str:
        '''将查询语句转换为搜索API所需的参数'''
        return ' '.join(query)

    def _debug_response(self, response):
        """调试输出响应信息并保存"""
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {response.headers}")
        print(f"响应内容长度: {len(response.text)}")
        # 保存完整响应内容到文件
        import urllib.parse
        # filename = f"response_{urllib.parse.quote(url, safe='')}.html"
        filename = f"response_{self.__class__.__name__}_{time.time()}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"响应内容已保存到文件: {filename}")



class PixabaySearch(BaseImageSearch):
    '''Pixabay中的图片搜索'''
    def search(self, query : List[str]) -> List[str]:
        url = url = self.config.get("url", "https://pixabay.com/api/")
        params = {
            'key' : self.api_key,
            'q' : self._query_convert(query),
            'image_type' : 'photo',
            'per_page' : self.max_results,
            'safesearch' : 'true',
            'pretty' : 'true'
        }
        data = self._make_request(url, params)
        return [item['webformatURL'] for item in data.get('hits', [])]      # 提取缩略图url

    def _query_convert(self, query : List[str]) -> str:
        '''将查询语句转换为搜索API所需的参数'''
        return '+'.join(query)


class UnsplashSearch(BaseImageSearch):
    '''Unsplash中的图片搜索'''
    def search(self, query : str) -> List[str]:
        url = self.config.get("url", "https://api.unsplash.com/search/photos")
        params = {
            'client_id' : self.api_key,
            'query' : query,
            'per_page' : self.max_results,
        }
        data = self._make_request(url, params)
        return [item['urls']['regular'] for item in data.get('results', [])]      # 提取缩略图url


class PexelsSearch(BaseImageSearch):
    '''Pexels中的图片搜索'''
    def search(self, query : str) -> List[str]:
        url = self.config.get("url", "https://api.pexels.com/v1/search")
        params = {
            'query' : query,
            'per_page' : self.max_results,
        }
        headers = {
            'Authorization' : self.api_key
        }
        data = self._make_request(url, params, headers)
        return [item['url'] for item in data.get('photos', [])]


class HuabanwangSearch(BaseImageSearch):
    '''花瓣网中的图片搜索，由于花瓣网禁止爬虫抓取所有子网页，所以原则上不能用花瓣网搜索。本方法使用网页url直接模拟访问的方式实现，不使用self.api_key'''
    def search(self, query) -> List[str]:
        # 使用手动构造url的方式直接访问搜索页面，获取url模版，其中“filter_ids”项后面的两个参数分别表示“屏蔽ai结果”和“不看素材（只看原图）”
        # url中的“q={}”项是需要替换的搜索关键词项，用query替换"{}"
        url = self.config.get("url", "https://huaban.com/search?q={}&sort=all&type=pin&filter_ids=is_ai-5342747.6124374.6124380%7Eis_material-5342747.6124373.6124375")
        query_str = self._query_convert(query)
        url = url.format(query_str)     # 替换url中的"{}"项为query

        print("正在搜索【花瓣网】")
        print(json.dumps({
            "本次使用搜索器": str(self.__class__.__name__),
            "搜索关键词": query_str,
            "搜索url": url,
        }, indent=4, ensure_ascii=False))

        try:
            # 访问url，获取网页内容
            driver = self._get_url_response(url=url)
            if driver is None:
                print(f"访问花瓣网url出错：{url}")
                return []

            image_urls = []
            img_elements = driver.find_elements(By.CSS_SELECTOR, 'img.transparent-img-bg.hb-image')  # 找到所有img元素，类别为“transparent-img-bg hb-image”
            print(f"找到的图片数量: {len(img_elements)}")

            for img in img_elements:             # 遍历img元素的前self.max_results个元素
                print(f'img src: {img.get_attribute("src")}')

                if len(image_urls) >= self.max_results:
                    break
                if img.get_attribute('srcset'):
                    srcset = img.get_attribute('srcset')
                    if srcset and srcset.startswith('https://gd-hbimg.huaban.com/'):
                        img_url = srcset.split(' ')[0]
                        image_urls.append(img_url)
            return image_urls
        except Exception as e:
            print(f"访问花瓣网url出现错误：{url}")
            print(str(e))
            return []

    def _query_convert(self, query : List[str]) -> str:
        t = '+'.join(query)
        return '+'.join(query)

class ImageSearchFactory:
    '''图片搜索器管理类，配置管理搜索器'''
    def __init__(self, config : Dict[str, Any], proxy=None):
        self.config = config
        self.available_sites = {
            'huabanwang' : HuabanwangSearch,
            'pixabay' : PixabaySearch,
            'pexels' : PexelsSearch,
            'unsplash' : UnsplashSearch,
            # 'pixiv': PixivSearch
        }
        self.proxy = proxy  # 获取系统代理，用于构造request

    def get_searcher(self, site : str) -> BaseImageSearch:
        '''获取指定网站的搜索器'''
        if site not in self.available_sites:
            raise ValueError(f"不支持的网站：【{site}】，当前可用搜索网站：【{list(self.available_sites)}】")

        site_config = self.config["search_sites"].get(site, {})
        if not site_config.get('enabled', False):
            raise ValueError(f"网站【{site}】在配置文件中未启用")

        return self.available_sites[site](site_config, proxy=self.proxy, timeout=self.config.get("timeout", 5))

    def _get_available_sites(self) -> List[str]:
        return [site for site, config in self.config["search_sites"].items() if config.get('enabled', False)]

    def get_all_avaliable_sites(self) -> List[BaseImageSearch]:
        """获取所有可用的搜索网站的搜索器"""
        avaliable_sites = []
        for s in self._get_available_sites():
            avaliable_sites.append(self.get_searcher(s))

        return avaliable_sites

