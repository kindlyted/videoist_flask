import os
import sys
from pathlib import Path
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import inspect
from extensions import db, login_manager, mail, bootstrap, migrate
from config import DevelopmentConfig

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

def create_app(config_name='development'):
    """创建并配置Flask应用"""
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)
    
    # 确保instance目录存在
    Path(app.instance_path).mkdir(exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # 初始化认证模块
    from auth import init_auth
    init_auth(app)
    
    # 确保user_loader被注册
    from auth import utils  # 触发@login_manager.user_loader装饰器

    # 注册蓝图
    from auth.routes import auth_bp
    from main.routes import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    return app

# 显式创建app实例以支持flask命令
app = create_app()

if __name__ == '__main__':
    print("\n🚀 应用启动信息:")
    print(f"📁 模板目录: {app.jinja_loader.searchpath}")
    print(f"🌐 服务地址: http://localhost:5009")
    
    
    app.run(host='0.0.0.0', port=5009, debug=app.config.get('DEBUG'))