# -*- coding: utf-8 -*-
import os
import sys
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import inspect
from pathlib import Path
from extensions import db, login_manager, mail, bootstrap, migrate, csrf
from config import DevelopmentConfig

def create_app(config_name='development'):
    """创建并配置Flask应用"""
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)
    
    # 在导入其他模块前确保项目根目录在Python路径中
    # project_root = str(Path(__file__).parent)
    # if project_root not in sys.path:
    #     sys.path.insert(0, project_root)
    
    # 确保instance目录存在
    Path(app.instance_path).mkdir(exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # 初始化认证模块
    from auth import init_auth
    init_auth(app)
    
    # 确保user_loader被注册
    from auth import utils  # 触发@login_manager.user_loader装饰器

    # 注册蓝图
    from auth.routes import auth_bp
    from main.routes import main_bp
    from note.routes import bp as notes_generator_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(notes_generator_bp)
    
    return app

# 显式创建app实例以支持flask命令
app = create_app()

if __name__ == '__main__':
    print("\n应用启动信息:")
    print(f"模板目录: {app.jinja_loader.searchpath}")
    print(f"服务地址: http://localhost:5009")
    
    app.run(host='0.0.0.0', port=5009, debug=app.config.get('DEBUG'))