from flask import url_for, current_app
from flask_mail import Message
from extensions import mail, login_manager
from models import User

# ==================== Flask-Login 用户加载器 ====================
@login_manager.user_loader
def load_user(user_id):
    """核心用户加载回调"""
    return User.query.get(int(user_id))

# ==================== 邮件功能 ====================
def send_confirmation_email(user):
    """发送确认邮件（保持原功能不变）"""
    token = user.generate_confirmation_token()
    msg = Message(
        '确认您的账户',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email]
    )
    msg.body = f"""请点击以下链接确认您的账户:
{url_for('auth.confirm', token=token, _external=True)}

如果您没有请求账户确认，请忽略此邮件。
"""
    mail.send(msg)

# ... 其他邮件功能保持不变 ...
def send_password_reset_email(user):
    """发送密码重置邮件"""
    token = user.generate_reset_token()
    msg = Message(
        '重置您的密码',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email]
    )
    msg.body = f"""要重置密码，请访问以下链接:
{url_for('auth.reset_password', token=token, _external=True)}

如果您没有请求重置密码，请忽略此邮件。
"""
    mail.send(msg)

# ==================== 登录管理器配置 ====================
def configure_login_manager(login_manager):
    """集中配置登录管理器"""
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请登录以访问此页面'
    login_manager.login_message_category = 'warning'