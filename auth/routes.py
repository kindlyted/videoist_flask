from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp  # 从当前包导入
from models import db, User
from .forms import LoginForm, RegistrationForm, ResetPasswordRequestForm  # 确保导入表单类

# 登录路由
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember_me.data)  # 使用remember_me值
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('用户名或密码错误', 'danger')
    return render_template('auth/login.html', title='登录', form=form)

# 其他路由...
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form, title='注册')

# 注销路由
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# 密码重置请求路由
@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetPasswordRequestForm()  # 实例化表单
    if form.validate_on_submit():
        # 处理密码重置逻辑（如发送邮件）
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', form=form, title='重置密码')

# 用户仪表盘
@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """用户个人信息中心"""
    return render_template('auth/dashboard.html', title='个人中心')