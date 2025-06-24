import asyncio
from playwright.async_api import async_playwright
import json
import os
from pathlib import Path

async def get_cookies_with_playwright(url: str, cookie_path: str):
    """获取并保存网站Cookies"""
    async with async_playwright() as p:
        # 启动浏览器（保留原有UI模式方便扫码）
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        )
        
        # 创建上下文（隔离环境）
        context = await browser.new_context(
            viewport=None,  # 最大化窗口
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        )
        
        page = await context.new_page()
        
        try:
            # 导航到目标URL
            await page.goto(url, timeout=120000)
            print(f"请扫码登录（等待60秒）...")
            
            # 获取初始URL
            initial_url = page.url
            
            # 等待URL变化（表示登录成功跳转）
            await page.wait_for_function(
                """initialUrl => {
                    return location.href !== initialUrl;
                }""",
                arg=initial_url,
                timeout=60000
            )
            
            print("检测到页面跳转，登录成功")
            
            # 获取Cookies（包含所有安全属性）
            cookies = await context.cookies()
            
            # 标准化Cookie格式
            processed_cookies = []
            for cookie in cookies:
                processed_cookies.append({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie["path"],
                    "expires": cookie.get("expires"),
                    "httpOnly": cookie["httpOnly"],
                    "secure": cookie["secure"],
                    "sameSite": cookie.get("sameSite", "Lax")
                })
            
            # 直接保存Cookies到文件
            os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
            with open(cookie_path, 'w', encoding='utf-8') as f:
                json.dump(processed_cookies, f, indent=2)
            print(f"Cookies已保存到: {cookie_path}")
            
        except Exception as e:
            print(f"获取Cookie失败: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    try:
        COOKIE_DIR = Path('./main/static/cookies')
        # 账号选择交互
        print('请选择要登录的账号类型：')
        options = {
            '1': ('小红书zhi', 'https://creator.xiaohongshu.com/login', 'cookie_xhs_zhi.json'),
            '2': ('小红书share', 'https://creator.xiaohongshu.com/login', 'cookie_xhs_share.json'),
            '3': ('抖音zhi', 'https://creator.douyin.com/', 'cookie_douyin_zhi.json'),
            '4': ('抖音share', 'https://creator.douyin.com/', 'cookie_douyin_share.json'),
            '5': ('视频号zhi', 'https://channels.weixin.qq.com/', 'cookie_sph_zhi.json')
        }
        
        for num, (name, _, _) in options.items():
            print(f"{num}.{name}")
        
        choice = input('请输入数字：').strip()
        if choice in options:
            url, fname = options[choice][1], options[choice][2]
            cookie_path = str(COOKIE_DIR / fname)
            asyncio.run(get_cookies_with_playwright(url, cookie_path))
        else:
            print("无效的选择")
    except Exception as e:
        print(f"程序异常: {str(e)}")
    input("按任意键退出...")