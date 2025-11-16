# 测试网络链接与代理
import winreg
import requests

def detect_system_proxy():
    """检测 Windows 系统代理设置"""
    print("=== 系统代理设置检测 ===\n")

    try:
        # 读取 Windows 注册表中的代理设置
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            try:
                proxy_enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
                proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
                print(f"系统代理启用: {proxy_enable == 1}")
                if proxy_enable == 1:
                    print(f"代理服务器: {proxy_server}")
                    return proxy_server
                else:
                    print("系统代理未启用")
                    return None
            except FileNotFoundError:
                print("未找到代理设置")
                return None
    except Exception as e:
        print(f"读取注册表失败: {e}")
        return None

def get_proxies():
    proxy_server = detect_system_proxy()
    if proxy_server:
        proxies = {
            "http": f"http://{proxy_server}",
            "https": f"http://{proxy_server}"
        }
        return proxies
    return {}

def test_with_system_proxy():
    """使用系统代理设置进行测试"""
    proxy_server = detect_system_proxy()

    if proxy_server:
        print(f"\n使用系统代理进行测试: {proxy_server}")
        proxies = {
            "http": f"http://{proxy_server}",
            "https": f"http://{proxy_server}"
        }

        test_urls = [
            "https://pixabay.com/api/?key=53008434-7888aef04c3d173a19c8831e8&q=yellow+flowers&image_type=photo&pretty=true",
            "https://www.google.com"
        ]

        for url in test_urls:
            try:
                response = requests.get(url, proxies=proxies, timeout=10)
                print(f"✓ {url}: 成功 (状态码: {response.status_code})")
            except Exception as e:
                print(f"✗ {url}: 失败 - {e}")
    else:
        print("\n未检测到系统代理设置")