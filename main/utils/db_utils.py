from models import db, WordPressSite, WechatAccount  # 导入数据库模型

def get_db_credentials(service_name):
    """从数据库获取指定服务的凭据
    
    Args:
        service_name (str): 服务名称('wordpress'或'wechat')
    
    Returns:
        dict: 包含凭据的字典，格式根据服务类型不同
    """
    try:
        if service_name == 'wordpress':
            site = WordPressSite.query.filter_by(is_active=True).first()
            if not site:
                return {}
            return {
                'url': site.site_url,
                'username': site.username,
                'password': site.api_key
            }
        elif service_name == 'wechat':
            account = WechatAccount.query.filter_by(is_active=True).first()
            if not account:
                return {}
            return {
                'app_id': account.app_id,
                'app_secret': account.app_secret
            }
        return {}
    except Exception as e:
        print(f"Error fetching {service_name} credentials: {str(e)}")
        return {}
