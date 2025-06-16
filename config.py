import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # ==================== 基础配置 ====================
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ==================== 项目目录结构 ====================
    BASE_DIR = Path(__file__).parent  # 项目根目录
    INSTANCE_DIR = BASE_DIR / 'instance'     # 实例目录
    
    # ==================== 静态资源路径 ====================
    STATIC_FOLDER = BASE_DIR / 'static'               # 全局静态资源
    MAIN_STATIC_FOLDER = BASE_DIR / 'main' / 'static' # 主业务静态资源
    
    # ==================== 视频处理路径 ====================
    ARTICLE_DIR = MAIN_STATIC_FOLDER / 'output' / 'articles'  # 文章工作区
    OUTPUT_DIR = MAIN_STATIC_FOLDER / 'output' / 'outputs'   # 视频输出
    INPUT_DIR = MAIN_STATIC_FOLDER / 'output' / 'txt'            # 文本输入目录
    VIDEO_FONT_DIR = MAIN_STATIC_FOLDER / 'fonts'           # 字体目录
    PROMPT_DIR = MAIN_STATIC_FOLDER / 'prompts'        # AI提示词目录
    HTML_DIR = MAIN_STATIC_FOLDER / 'html'          # HTML模板目录
    SCREEN_SIZE = (1080, 2060)              # 视频分辨率
    
    # ==================== 语音合成配置 ====================
    VOICE_NAMES = [
        "zh-CN-XiaoxiaoNeural",    # 普通话女声-晓晓
        "zh-CN-XiaoyiNeural",      # 普通话女声-晓伊
        "zh-CN-YunjianNeural",     # 普通话男声-云健
        "zh-CN-YunxiNeural",      # 普通话男声-云溪
        "zh-CN-YunxiaNeural",     # 普通话男声-云霞
        "zh-CN-YunyangNeural",    # 普通话男声-云扬
        "zh-CN-liaoning-XiaobeiNeural",  # 东北女声
        "zh-CN-shaanxi-XiaoniNeural",    # 陕西女声
        "zh-HK-HiuGaaiNeural",    # 粤语女声-晓佳
        "zh-HK-HiuMaanNeural",    # 粤语女声-晓敏
        "zh-HK-WanLungNeural",   # 粤语男声-云龙
        "zh-TW-HsiaoChenNeural",  # 台湾女声-晓晨
        "zh-TW-HsiaoYuNeural",    # 台湾女声-晓雨
        "zh-TW-YunJheNeural"     # 台湾男声-云哲
    ]
    DEFAULT_VOICE = "zh-CN-YunxiaNeural"
    
    # ==================== 数据库配置 ====================
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f"sqlite:///{Path(__file__).parent / 'instance' / 'app.db'}")
    
    # ==================== 初始化方法 ====================
    @classmethod
    def ensure_dirs(cls):
        """创建所有必需的目录"""
        required_dirs = [
            # 静态资源
            cls.STATIC_FOLDER,
            cls.MAIN_STATIC_FOLDER,
            
            # 视频处理相关目录
            cls.ARTICLE_DIR,
            cls.OUTPUT_DIR,
            cls.VIDEO_FONT_DIR,
            cls.PROMPT_DIR,
            cls.HTML_DIR,
            
            # 输入输出目录
            cls.INPUT_DIR,
            
            # 系统目录
            cls.INSTANCE_DIR
        ]
        
        for dir_path in required_dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"创建目录失败 {dir_path}: {str(e)}")

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    EXPLAIN_TEMPLATE_LOADING = True  # 显示模板加载信息
    
    # 开发环境特殊路径
    VIDEO_DEBUG_OUTPUT = Path('/tmp/video_debug')  # 调试输出目录已弃用
    
    # 直接赋值数据库URI
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{Config.INSTANCE_DIR / 'dev.db'}"

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 安全增强
    PROPAGATE_EXCEPTIONS = True   # 传播异常到WSGI层
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    
    # 生产环境路径覆盖
    OUTPUT_DIR = Path('/var/www/videos/output')        # 生产输出目录
    
    # 直接赋值数据库URI
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/prod_db')
    
    @staticmethod
    def get_allowed_paths():
        """生产环境路径访问白名单"""
        return [
            str(Config.STATIC_FOLDER),
            str(Config.ARTICLE_DIR),
            '/tmp',
            '/var/www/videos'
        ]

# ==================== 配置字典 ====================
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# 应用启动时初始化目录
if __name__ == '__main__':
    print("初始化项目目录结构...")
    Config.ensure_dirs()
    print("当前配置:")
    print(f"静态文件目录: {Config.STATIC_FOLDER}")
    print(f"视频输出目录: {Config.ARTICLE_DIR}")
    print(f"字体目录: {Config.VIDEO_FONT_DIR}")
else:
    # 作为模块导入时自动初始化
    Config.ensure_dirs()