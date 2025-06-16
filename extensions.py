from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate

# 初始化扩展实例（不包含具体配置）
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
bootstrap = Bootstrap()
migrate = Migrate()