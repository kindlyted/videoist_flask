import os
from pathlib import Path
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import inspect
from config import config
from extensions import db, login_manager, mail, bootstrap, migrate

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 初始化扩展
    db.init_app(app)
    migrate = Migrate(app, db)  # 必须添加这行
    login_manager.init_app(app)  # 先初始化login_manager基础
    
    # 初始化认证模块（会配置login_manager）
    from auth import init_auth
    init_auth(app)
    
    # 确保user_loader被注册（导入auth.utils）
    from auth import utils  # 触发@login_manager.user_loader装饰器

    # 注册蓝图
    from auth.routes import auth_bp
    from main.routes import main_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)  # 不添加url_prefix，使其成为根路由
    return app

def init_database(app):
    """初始化数据库和默认数据"""
    # 开发环境下：删除旧表重建（谨慎操作！）
    if app.config['DEBUG']:
        db.drop_all()
    
    db.create_all()
    
    # 创建默认管理员账户
    from models import User
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True,
            is_active=True  # 确保激活状态
        )
        admin.set_password('123456')
        db.session.add(admin)
        db.session.commit()
        print("✅ 已创建默认管理员账户: admin/123456")
    
    # 调试信息
    inspector = inspect(db.engine)
    print("📊 数据库表清单:", inspector.get_table_names())
    print("🛠️ 数据库文件位置:", app.config['SQLALCHEMY_DATABASE_URI'])

# 显式创建app实例以支持flask命令
app = create_app()

if __name__ == '__main__':
    print("\n🚀 应用启动信息:")
    print(f"📁 模板目录: {app.jinja_loader.searchpath}")
    print(f"🌐 服务地址: http://localhost:5008")
    
    # 生产环境下不应自动初始化数据库
    # if app.config.get('DEBUG'):
    #     with app.app_context():
    #         init_database(app)
    
    app.run(host='0.0.0.0', port=5009, debug=app.config.get('DEBUG'))