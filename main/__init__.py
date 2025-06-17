# main/__init__.py
from flask import Blueprint

# 确保只创建一次蓝图实例
main_bp = Blueprint('main', __name__, 
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/main/static')

from . import routes
