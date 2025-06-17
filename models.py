# models.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db  # 从统一的extensions导入db

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    # 密码处理方法
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        """专门用于设置密码的方法（兼容旧代码）"""
        self.password_hash = generate_password_hash(password)

    def __repr__(self):
        return f'<User {self.username}>'

class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('User', backref='articles')

    def __repr__(self):
        return f'<Article {self.title}>'

class Video(db.Model):
    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('User', backref='videos')

    def __repr__(self):
        return f'<Video {self.title}>'

class PlatformConfig(db.Model):
    __tablename__ = 'platform_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    config_name = db.Column(db.String(100), nullable=False)
    platform_name = db.Column(db.String(50), nullable=False)  # 'wordpress' or 'wechat'
    config_key = db.Column(db.String(100), nullable=False)
    config_value = db.Column(db.Text, nullable=False)
    environment = db.Column(db.String(20), default='production')  # 'development' or 'production'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='platform_configs')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'platform_name', 'config_key', 'environment', 
                          name='_user_platform_key_env_uc'),
    )

    def __repr__(self):
        return f'<PlatformConfig {self.config_name} for {self.platform_name}>'

class TagMapping(db.Model):
    __tablename__ = 'tag_mappings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform_name = db.Column(db.String(50), nullable=False)  # 'wordpress' or 'wechat'
    mapping_name = db.Column(db.String(100), nullable=False)
    tag_name = db.Column(db.String(100), nullable=False)
    tag_id = db.Column(db.Integer, nullable=False)
    environment = db.Column(db.String(20), default='production')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='tag_mappings')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'platform_name', 'tag_name', 'environment',
                          name='_user_platform_tag_env_uc'),
    )

    def __repr__(self):
        return f'<TagMapping {self.tag_name}->{self.tag_id} for {self.platform_name}>'

class WordPressSite(db.Model):
    __tablename__ = 'wordpress_sites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    site_name = db.Column(db.String(100), nullable=False)
    site_url = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('wordpress_sites', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'site_url', name='_user_site_url_uc'),
    )

    def __repr__(self):
        return f'<WordPressSite {self.site_name} ({self.site_url})>'

class WechatAccount(db.Model):
    __tablename__ = 'wechat_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.String(100), nullable=False)
    app_id = db.Column(db.String(100), nullable=False)
    app_secret = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('wechat_accounts', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'account_id', name='_user_account_id_uc'),
    )

    def __repr__(self):
        return f'<WechatAccount {self.account_name} ({self.account_id})>'