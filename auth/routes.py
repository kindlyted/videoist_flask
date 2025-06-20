# auth/routes.py
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
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

# WordPress管理页面1
@auth_bp.route('/wordpress', methods=['GET', 'POST'])
@login_required
def wordpress():
    """WordPress管理页面"""
    if request.method == 'POST':
        # 处理表单提交
        site_id = request.form.get('id')
        site_name = request.form.get('site_name')
        site_url = request.form.get('site_url')
        username = request.form.get('username')
        api_key = request.form.get('api_key')

        # 验证表单数据
        if not all([site_name, site_url, username, api_key]):
            flash('请填写所有必填字段', 'danger')
            return redirect(url_for('auth.wordpress'))

        # 添加或更新WordPress站点
        if site_id:
            # 更新现有站点
            site = WordPressSite.query.get(site_id)
            if site and site.user_id == current_user.id:
                site.site_name = site_name
                site.site_url = site_url
                site.username = username
                site.api_key = api_key
                db.session.commit()
                flash('站点更新成功', 'success')
        else:
            # 检查是否存在相同URL的站点（包括inactive的）
            existing_site = WordPressSite.query.filter_by(
                user_id=current_user.id,
                site_url=site_url
            ).first()
            
            if existing_site:
                if existing_site.is_active:
                    flash('该站点URL已存在', 'danger')
                    return redirect(url_for('auth.wordpress'))
                else:
                    # 恢复软删除的站点
                    existing_site.is_active = True
                    existing_site.site_name = site_name
                    existing_site.username = username
                    existing_site.api_key = api_key
                    flash('站点已恢复', 'success')
            else:
                # 添加新站点
                new_site = WordPressSite(
                    site_name=site_name,
                    site_url=site_url,
                    username=username,
                    api_key=api_key,
                    user_id=current_user.id
                )
                db.session.add(new_site)
                flash('站点添加成功', 'success')
            
            db.session.commit()

        return redirect(url_for('auth.wordpress'))

    # GET请求处理
    wordpress_sites = current_user.wordpress_sites.filter_by(is_active=True).all()
    return render_template('auth/wordpress.html', 
                         title='WordPress管理',
                         wordpress_sites=wordpress_sites)

# 删除WordPress站点2
@auth_bp.route('/delete-wordpress-site', methods=['POST'])
@login_required
def delete_wordpress_site():
    """删除WordPress站点"""
    site_id = request.form.get('site_id')
    if not site_id:
        flash('无效的站点ID', 'danger')
        return redirect(url_for('auth.wordpress'))

    site = WordPressSite.query.get(site_id)
    if not site or site.user_id != current_user.id:
        flash('无权删除该站点', 'danger')
        return redirect(url_for('auth.wordpress'))

    # 软删除，设置is_active为False
    site.is_active = False
    db.session.commit()
    flash('站点已删除', 'success')
    return redirect(url_for('auth.wordpress'))

# WordPress站点管理API3
@auth_bp.route('/api/wordpress', methods=['GET', 'POST'])
@login_required
def manage_wordpress():
    if request.method == 'GET':
        sites = current_user.wordpress_sites.filter_by(is_active=True).all()
        return jsonify([{
            'id': site.id,
            'site_name': site.site_name,
            'site_url': site.site_url
        } for site in sites])
    
    # POST请求处理添加/更新
    data = request.get_json() if request.is_json else request.form
    
    # 验证必填字段
    required_fields = ['site_name', 'site_url', 'username', 'api_key']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': '缺少必要参数',
            'missing_fields': [f for f in required_fields if f not in data]
        }), 400
    
    try:
        if 'id' in data and data['id']:
            # 编辑现有站点
            try:
                site_id = int(data['id'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False, 
                    'message': '无效的站点ID格式',
                    'expected_format': '整数数字',
                    'received_value': str(data.get('id'))
                }), 400
                
            site = WordPressSite.query.filter_by(id=site_id, user_id=current_user.id).first()
            if not site:
                current_app.logger.error(f"WordPress站点不存在或无权访问 - 用户ID: {current_user.id}, 站点ID: {site_id}")
                return jsonify({'success': False, 'message': '站点不存在或无权访问'}), 404
                
            site.site_name = data['site_name']
            site.site_url = data['site_url']
            site.username = data['username']
            site.api_key = data['api_key']
            message = '站点更新成功'
        else:
            # 添加新站点或恢复软删除的站点
            existing_site = WordPressSite.query.filter_by(
                user_id=current_user.id,
                site_url=data['site_url']
            ).first()
            
            if existing_site:
                if existing_site.is_active:
                    return jsonify({
                        'success': False,
                        'message': '该站点URL已存在'
                    }), 400
                else:
                    # 恢复软删除的站点
                    existing_site.is_active = True
                    existing_site.site_name = data['site_name']
                    existing_site.username = data['username']
                    existing_site.api_key = data['api_key']
                    message = '站点已恢复'
                    site = existing_site
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
                message = '站点添加成功'
        
        db.session.commit()
        current_app.logger.info(f"用户 {current_user.id} 成功操作WordPress站点: {data['site_url']}")
        return jsonify({
            'success': True,
            'message': message,
            'id': site.id
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"WordPress站点操作失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500

# 删除WordPress站点API4
@auth_bp.route('/api/wordpress/<int:id>', methods=['DELETE'])
@login_required
def delete_wordpress(id):
    """删除WordPress站点（软删除）"""
    site = WordPressSite.query.filter_by(id=id, user_id=current_user.id).first()
    if not site:
        current_app.logger.warning(f"删除WordPress站点失败 - 记录不存在或无权访问: 用户ID {current_user.id}, 站点ID {id}")
        return jsonify({'error': '站点不存在或无权访问'}), 404
    
    try:
        site.is_active = False
        db.session.commit()
        current_app.logger.info(f"用户 {current_user.id} 成功删除WordPress站点: {site.site_url}")
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除WordPress站点失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

# WeChat管理页面1
@auth_bp.route('/wechat', methods=['GET', 'POST'])
@login_required
def wechat():
    """微信公众号管理页面"""
    if request.method == 'POST':
        # 处理表单提交
        record_id = request.form.get('id')  
        account_id = request.form.get('account_id')  
        account_name = request.form.get('account_name')
        app_id = request.form.get('app_id')
        app_secret = request.form.get('app_secret')

        # 验证表单数据
        if not all([account_name, account_id, app_id, app_secret]):
            flash('请填写所有必填字段', 'danger')
            return redirect(url_for('auth.wechat'))

        # 添加或更新微信公众号
        if record_id:
            # 更新现有公众号
            account = WechatAccount.query.get(record_id)
            if account and account.user_id == current_user.id:
                account.account_name = account_name
                account.account_id = account_id
                account.app_id = app_id
                account.app_secret = app_secret
                db.session.commit()
                flash('公众号更新成功', 'success')                
        else:
            # 检查是否存在相同account_id的公众号（包括inactive的）
            existing_account = WechatAccount.query.filter_by(
                user_id=current_user.id,
                account_id=account_id
            ).first()
            
            if existing_account:
                if existing_account.is_active:
                    flash('该公众号ID已存在', 'danger')
                    return redirect(url_for('auth.wechat'))
                else:
                    # 恢复软删除的公众号
                    existing_account.is_active = True
                    existing_account.account_name = account_name
                    existing_account.app_id = app_id
                    existing_account.app_secret = app_secret
                    flash('公众号已恢复', 'success')
            else:
                # 添加新公众号
                new_account = WechatAccount(
                    account_name=account_name,
                    account_id=account_id,
                    app_id=app_id,
                    app_secret=app_secret,
                    user_id=current_user.id
                )
                db.session.add(new_account)
                flash('公众号添加成功', 'success')

            db.session.commit()
            
        return redirect(url_for('auth.wechat'))

    # GET请求处理
    accounts = current_user.wechat_accounts.filter_by(is_active=True).all()
    return render_template('auth/wechat.html',
                         title='微信公众号管理',
                         wechat_accounts=accounts)

# 删除微信公众号账号2
@auth_bp.route('/delete-wechat-account', methods=['POST'])
@login_required
def delete_wechat_account():
    """删除微信公众号账号"""
    account_id = request.form.get('account_id')
    if not account_id:
        flash('无效的公众号ID', 'danger')
        return redirect(url_for('auth.wechat'))

    account = WechatAccount.query.get(account_id)
    if not account or account.user_id != current_user.id:
        flash('无权删除该公众号', 'danger')
        return redirect(url_for('auth.wechat'))

    # 软删除，设置is_active为False
    account.is_active = False
    db.session.commit()
    flash('公众号已删除', 'success')
    return redirect(url_for('auth.wechat'))

# 微信公众号管理API3
@auth_bp.route('/api/wechat', methods=['GET', 'POST'])
@login_required
def manage_wechat():
    if request.method == 'GET':
        accounts = current_user.wechat_accounts.filter_by(is_active=True).all()
        return jsonify([{
            'id': account.id,
            'account_name': account.account_name,
            'account_id': account.account_id
        } for account in accounts])
    
    # POST请求处理添加/更新
    data = request.get_json() if request.is_json else request.form
    
    # 验证必填字段
    required_fields = ['account_name', 'account_id', 'app_id', 'app_secret']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': '缺少必要参数',
            'missing_fields': [f for f in required_fields if f not in data]
        }), 400
    
    try:
        if 'id' in data and data['id']:
            # 编辑现有公众号
            try:
                account_id = int(data['id'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False, 
                    'message': '无效的公众号ID格式',
                    'expected_format': '整数数字',
                    'received_value': str(data.get('id'))
                }), 400
                
            account = WechatAccount.query.filter_by(id=account_id, user_id=current_user.id).first()
            if not account:
                current_app.logger.error(f"微信公众号不存在或无权访问 - 用户ID: {current_user.id}, 公众号ID: {account_id}")
                return jsonify({'success': False, 'message': '公众号不存在或无权访问'}), 404
                
            account.account_name = data['account_name']
            account.account_id = data['account_id']
            account.app_id = data['app_id']
            account.app_secret = data['app_secret']
            message = '公众号更新成功'
        else:
            # 添加新公众号或恢复软删除的公众号
            existing_account = WechatAccount.query.filter_by(
                user_id=current_user.id,
                account_id=data['account_id']
            ).first()
            
            if existing_account:
                if existing_account.is_active:
                    return jsonify({
                        'success': False,
                        'message': '该公众号ID已存在'
                    }), 400
                else:
                    # 恢复软删除的公众号
                    existing_account.is_active = True
                    existing_account.account_name = data['account_name']
                    existing_account.app_id = data['app_id']
                    existing_account.app_secret = data['app_secret']
                    message = '公众号已恢复'
                    account = existing_account
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
                message = '公众号添加成功'
        
        db.session.commit()
        current_app.logger.info(f"用户 {current_user.id} 成功操作微信公众号: {data['account_id']}")
        return jsonify({
            'success': True,
            'message': message,
            'id': account.id
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"微信公众号操作失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500
    
# 删除微信公众号API4
@auth_bp.route('/api/wechat/<int:id>', methods=['DELETE'])
@login_required
def delete_wechat(id):
    """删除微信公众号账号（软删除）"""
    account = WechatAccount.query.filter_by(id=id, user_id=current_user.id).first()
    if not account:
        current_app.logger.warning(f"删除微信公众号失败 - 记录不存在或无权访问: 用户ID {current_user.id}, 公众号ID {id}")
        return jsonify({'error': '公众号不存在或无权访问'}), 404
    
    try:
        account.is_active = False
        db.session.commit()
        current_app.logger.info(f"用户 {current_user.id} 成功删除微信公众号: {account.account_id}")
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除微信公众号失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500