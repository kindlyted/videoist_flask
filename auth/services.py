from werkzeug.security import generate_password_hash
from ..models import db, User
from .utils import send_confirmation_email

def register_user(username, email, password):
    """注册新用户"""
    hashed_password = generate_password_hash(password)
    user = User(username=username, email=email, password_hash=hashed_password)
    db.session.add(user)
    db.session.commit()
    
    # 发送确认邮件
    send_confirmation_email(user)
    return user

def authenticate_user(username, password):
    """验证用户登录"""
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None