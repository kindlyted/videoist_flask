from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp  # 从当前包导入
from models import db, User, WordPressSite, WechatAccount
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
    wordpress_sites = current_user.wordpress_sites.filter_by(is_active=True).all()
    wechat_accounts = current_user.wechat_accounts.filter_by(is_active=True).all()
    return render_template('auth/dashboard.html', 
                         title='个人中心',
                         wordpress_sites=wordpress_sites,
                         wechat_accounts=wechat_accounts)

# 账户信息页面
@auth_bp.route('/account')
@login_required
def account_info():
    """用户账户信息页面"""
    return render_template('auth/account_info.html', 
                         title='账户信息')

# WordPress管理页面
@auth_bp.route('/wordpress')
@login_required
def wordpress():
    """WordPress管理页面"""
    wordpress_sites = current_user.wordpress_sites.filter_by(is_active=True).all()
    return render_template('auth/wordpress.html', 
                         title='WordPress管理',
                         wordpress_sites=wordpress_sites)

# 微信公众号管理页面
@auth_bp.route('/wechat')
@login_required
def wechat():
    """微信公众号管理页面"""
    wechat_accounts = current_user.wechat_accounts.filter_by(is_active=True).all()
    return render_template('auth/wechat.html', 
                         title='微信公众号管理',
                         wechat_accounts=wechat_accounts)

# WordPress站点管理API
@auth_bp.route('/api/wordpress', methods=['GET', 'POST'])
@login_required
def manage_wordpress():
    if request.method == 'GET':
        sites = current_user.wordpress_sites.filter_by(is_active=True).all()
        return jsonify([{
            'id': site.id,
            'site_name': site.site_name,
            'site_url': site.site_url,
            'username': site.username
        } for site in sites])
    
    # POST请求处理添加/更新
    data = request.form
    if not data or 'site_name' not in data or 'site_url' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    try:
        if 'id' in data:
            # 更新现有站点
            site = WordPressSite.query.filter_by(id=data['id'], user_id=current_user.id).first()
            if not site:
                return jsonify({'success': False, 'message': '站点不存在或无权访问'}), 404
            site.site_name = data['site_name']
            site.site_url = data['site_url']
            site.username = data['username']
            site.api_key = data['api_key']
        else:
            # 添加新站点
            site = WordPressSite(
                user_id=current_user.id,
                site_name=data['site_name'],
                site_url=data['site_url'],
                username=data['username'],
                api_key=data['api_key']
            )
            db.session.add(site)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '操作成功',
            'id': site.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500
    
    db.session.commit()
    return jsonify({'success': True})

# 微信公众号管理API
@auth_bp.route('/api/wechat', methods=['GET', 'POST'])
@login_required
def manage_wechat():
    if request.method == 'GET':
        accounts = current_user.wechat_accounts.filter_by(is_active=True).all()
        return jsonify([{
            'id': account.id,
            'account_name': account.account_name,
            'account_id': account.account_id,
            'app_id': account.app_id
        } for account in accounts])
    
    # POST请求处理添加/更新
    data = request.form
    if not data or 'account_name' not in data or 'account_id' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    try:
        if 'id' in data:
            # 更新现有公众号
            account = WechatAccount.query.filter_by(id=data['id'], user_id=current_user.id).first()
            if not account:
                return jsonify({'success': False, 'message': '公众号不存在或无权访问'}), 404
            account.account_name = data['account_name']
            account.account_id = data['account_id']
            account.app_id = data['app_id']
            account.app_secret = data['app_secret']
        else:
            # 添加新公众号
            account = WechatAccount(
                user_id=current_user.id,
                account_name=data['account_name'],
                account_id=data['account_id'],
                app_id=data['app_id'],
                app_secret=data['app_secret']
            )
            db.session.add(account)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '操作成功',
            'id': account.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500

# 删除WordPress站点
@auth_bp.route('/api/wordpress/<int:id>', methods=['DELETE'])
@login_required
def delete_wordpress(id):
    site = WordPressSite.query.filter_by(id=id, user_id=current_user.id).first()
    if not site:
        return jsonify({'error': '站点不存在或无权访问'}), 404
    site.is_active = False
    db.session.commit()
    return jsonify({'success': True})

# 删除微信公众号
@auth_bp.route('/api/wechat/<int:id>', methods=['DELETE'])
@login_required
def delete_wechat(id):
    account = WechatAccount.query.filter_by(id=id, user_id=current_user.id).first()
    if not account:
        return jsonify({'error': '公众号不存在或无权访问'}), 404
    account.is_active = False
    db.session.commit()
    return jsonify({'success': True})