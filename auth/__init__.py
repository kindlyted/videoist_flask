# auth/__init__.py
from flask import Blueprint
from extensions import login_manager  # 改为绝对导入（不再使用..）

auth_bp = Blueprint('auth', __name__, template_folder='templates')

def init_auth(app):
    """认证模块初始化"""
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请登录以访问此页面'
    login_manager.login_message_category = 'warning'

# 必须在蓝图创建后导入路由
from . import routes