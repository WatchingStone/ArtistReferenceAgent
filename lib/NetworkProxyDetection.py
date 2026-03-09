# 测试网络链接与代理
import winreg

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
