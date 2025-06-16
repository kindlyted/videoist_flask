from selenium import webdriver
from time import sleep
from cookielogin import CookieLogin

cookie_number = input('请选择要登录的账号类型：\n1.小红书zhi\n2.小红书share\n3.抖音zhi\n4.抖音share\n5.视频号zhi\n请输入数字：')
 
if cookie_number == '1':
    url = "https://creator.xiaohongshu.com/login"
    cookie_fname = './cookies/cookie_xhs_zhi.json'
elif cookie_number == '2':
    url = "https://creator.xiaohongshu.com/login"
    cookie_fname = './cookies/cookie_xhs_share.json'
elif cookie_number == '3':
    url = "https://creator.douyin.com/"
    cookie_fname = './cookies/cookie_douyin_zhi.json'
elif cookie_number == '4':
    url = "https://creator.douyin.com/"
    cookie_fname = './cookies/cookie_douyin_share.json' 
elif cookie_number == '5':
    url = "https://channels.weixin.qq.com/"
    cookie_fname = './cookies/cookie_sph_zhi.json'
  

prefs = {
    'profile.default_content_setting_values': {
        'notifications': 2  # 隐藏chromedriver的通知
    },
    'credentials_enable_service': False,  # 隐藏chromedriver自带的保存密码功能
    'profile.password_manager_enabled': False  # 隐藏chromedriver自带的保存密码功能
}

# 创建一个配置对象
options = webdriver.ChromeOptions()
options.add_experimental_option('prefs', prefs)
options.add_experimental_option('excludeSwitches', ['enable-automation'])  # 设置为开发者模式,禁用chrome正受到自动化检测的显示
options.add_argument('--disable-gpu')  # 谷歌文档提到需要加上这个属性来规避bug

wd = webdriver.Chrome(options=options)

# 最大化窗口
wd.maximize_window()
wd.implicitly_wait(5)

wd.get(url=url)

# 现主页实现登录,用二维码扫就行
# wd.find_element(By.XPATH, '//*[@id="__sidebar"]/div/div[1]/div[1]/div/button').click()
sleep(60)

# 保存cookie到本地
cookies = wd.get_cookies()

login = CookieLogin(cookie_fname)

login.save_cookies(cookies)

wd.close()
wd.quit()
