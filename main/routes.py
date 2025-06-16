# main/routes.py
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required
from config import Config
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from .utils.publisher_core import WeChatPublisher
from .utils.video_core import (
    speaking, 
    process_dialogue,
    merge_subtitles, 
    create_video_multi,
    # create_video_single, # Linux
    creating_cover,
    generating_byds,
    extractting, 
    basic_auth_token, 
    generating_jskb,  
    process_markdown_images, 
    posting,
    markdown_to_html,
    convert_webp_to_jpg,
    dy_video_upload,
    sph_video_upload,
    xhs_video_upload
)

from . import main_bp  # 从__init__.py导入蓝图实例

# --------------------------
# 基础视图路由
# --------------------------
@main_bp.route('/')
def index():
    """主入口页面"""
    return render_template('main/index.html', voice_names=Config.VOICE_NAMES, default_voice=Config.DEFAULT_VOICE)

@main_bp.route('/video_creator')
@login_required
def video_creator():
    """视频创作页面 - 需要登录"""
    return render_template('main/video_creator.html', voice_names=Config.VOICE_NAMES, default_voice=Config.DEFAULT_VOICE)

# --------------------------
# 视频创作子系统
# --------------------------

@main_bp.route('/count_chars', methods=['POST'])
def count_chars():
    text = request.form.get('text', '')
    return jsonify({'count': len(text)})

@main_bp.route('/generate_titles', methods=['POST'])
def generate_titles():
    input_text = request.form.get('text', '')
    if not input_text:
        return jsonify({'error': '请输入台词'}), 400
    
    try:
        title_txt = generating_byds(input_text, str(Config.PROMPT_DIR / "top_title.prompt"))[:12]
        cover_txt = generating_byds(input_text, str(Config.PROMPT_DIR / "cover_title.prompt"))
        
        return jsonify({
            'title': title_txt,
            'cover': cover_txt
        })
    except Exception as e:
        return jsonify({'error': f'生成标题时出错: {str(e)}'}), 500

@main_bp.route('/process_url', methods=['POST'])
def process_url():
    url = request.form.get('url', '')
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({'error': '无效的URL'}), 400
    
    try:
        # 提取内容
        content_text = extractting(url)
        if not content_text:
            return jsonify({'error': '内容为空'}), 400

        # 生成结构化内容
        material = json.loads(generating_jskb(content_text, str(Config.PROMPT_DIR / "structure.prompt")))
        
        # 生成音频脚本
        mode = request.form.get('mode', '朗诵')  # 默认为朗诵模式
        prompt_file = "broadcastscript.prompt" if mode == "对话" else "audioscript.prompt"
        audioscript = generating_byds(material["content"], str(Config.PROMPT_DIR / prompt_file)) #material["content"]和process_markdown_images中的content不同
        
        # 检查WordPress和公众号开关状态
        wordpress_switch = request.form.get('wordpress_switch', 'on')
        wechat_switch = request.form.get('wechat_switch', 'on')
        if wordpress_switch != 'on' and wechat_switch != 'on':
        
            return jsonify({
                'website_url': 'WordPress发布已跳过',
                'article_text': audioscript,
                'working_dir': '图片处理已跳过',
                'wx_result': '公众号发布已跳过'
            })

        # 生成基准文件名（当前日期时间）
        working_dir = datetime.now().strftime("%Y%m%d%H%M%S")
        # 使用配置的工作目录路径
        working_path = Config.ARTICLE_DIR / working_dir
        working_path.mkdir(parents=True, exist_ok=True)  # 自动创建目录
        
        # WordPress配置
        WORDPRESS_URL = os.getenv('WP_URL')  
        USERNAME = os.getenv('WP_USERNAME')  
        APPLICATION_PASSWORD = os.getenv('WP_PASSWORD')  
        token = basic_auth_token(USERNAME, APPLICATION_PASSWORD)
        # 标签映射
        tag_index = {
            "国际教育": 7,
            "定居指南": 49,
            "移民资讯": 8,
            "楼市新闻": 2,
            "房产": 46,
            "教育": 47,
            "海外": 45,
            "留学": 64,
            "移民": 48
        }
        
        # 初始化文章数据
        wp_payload = {
            "title": "",
            "content": "",
            "status": "publish",
            "featured_media": "",
            "categories": [],
            "tags": []
        }
        
        # 读取HTML文件
        with open(Config.HTML_DIR / "seo_footer_wx.html", "r", encoding="utf-8") as f:
            SEO_FOOTER = f.read()
        
        # 保存material到JSON文件
        with open(Config.ARTICLE_DIR / f"{working_dir}/{working_dir}.json", "w", encoding="utf-8") as f:
            json.dump(material, f, ensure_ascii=False, indent=2)
        
        # 处理Markdown中的所有图片
        processed_content, image_info = process_markdown_images(
            material["content"], 
            WORDPRESS_URL, 
            token, 
            working_dir
        )  
        
        # 设置特色图片(第一张图片或默认)
        if image_info:
            first_image = next(iter(image_info.values()))
            wp_payload["featured_media"] = first_image["id"]
        
        # 设置文章内容
        wp_payload["title"] = material["prefix"] + "|" + material["title"]
        html_content, metadata = markdown_to_html(processed_content)
        wp_payload["content"] = html_content + SEO_FOOTER
        
        # 设置分类和标签
        wp_payload["categories"] = tag_index.get(material["categories"], 2)
        wp_payload["tags"] = [tag_index[item] for item in material["tags"] if item in tag_index]
        
        # 发布文章到WordPress
        post = None
        if request.form.get('wordpress_switch', 'on') == 'on':
            post = posting(WORDPRESS_URL, token, wp_payload)
        
        
        # 自动上传到微信公众号
        wx_result = None
        if request.form.get('wechat_switch', 'on') == 'on':
            convert_webp_to_jpg(Config.ARTICLE_DIR / f"{working_dir}")
            material["content"] = material["content"].replace(".webp)", ".jpg)")
            
            with open(Config.ARTICLE_DIR / f"{working_dir}/{working_dir}.md", "w", encoding="utf-8") as f:
                f.write(material["content"])
            
            publisher = WeChatPublisher(
                app_id=os.getenv("WECHAT_APPID"),
                app_secret=os.getenv("WECHAT_APPSECRET"),
                article_name=working_dir,
                source_url=post["link"] if post else ""
            )
            
            wx_result = publisher.publish()
        
        return jsonify({
            'website_url': post["link"] if post else "WordPress发布已跳过",
            'article_text': audioscript,
            'working_dir': working_dir,
            'wx_result': "公众号发布成功" if wx_result else ("公众号发布已跳过" if wx_result is None else "公众号发布失败")
        })
    except Exception as e:
        return jsonify({'error': f'处理URL时出错: {str(e)}'}), 500

@main_bp.route('/generate_video', methods=['POST'])
@login_required
def generate_video():
    input_text = request.form.get('text', '')
    title_txt = request.form.get('title', '')
    cover_txt = request.form.get('cover', '')
    voice = request.form.get('voice', Config.VOICE_NAMES[4])
    VOICE_MAPPING = {
    "demomo": "zh-CN-YunxiNeural",
    "lasisi": "zh-CN-XiaoxiaoNeural"
    }
    if not cover_txt:
        return jsonify({'error': '请补充封面描述'}), 400
    
    try:
        # 获取当前日期
        base_filename = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 文件路径
        txt_file = str(Config.INPUT_DIR / f"{base_filename}.txt")
        srt_file = str(Config.OUTPUT_DIR / f"{base_filename}.srt") 
        audio_filename = str(Config.OUTPUT_DIR / f"{base_filename}.mp3")
        output_filename = str(Config.OUTPUT_DIR / f"{base_filename}.mp4")
        cover_filename = str(Config.OUTPUT_DIR / f"{base_filename}.png")

        # 将输入文本写入文件
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(input_text)
        
        if not os.path.exists(audio_filename) or not os.path.exists(srt_file):
            # 判断是否为对话文本（包含角色前缀）
            is_dialogue = any(
                line.strip().split(':', 1)[0].strip() in VOICE_MAPPING  # 直接检查是否在VOICE_MAPPING的键中
                for line in input_text.split('\n')
                if ':' in line
            )
            
            if is_dialogue:
                asyncio.run(process_dialogue(txt_file, audio_filename, srt_file, VOICE_MAPPING, temp_dir="tmp", silence_duration_ms=500))
            else:
                # 普通单文本处理模式（原基础函数）
                asyncio.run(speaking(audio_filename, srt_file, input_text, voice))
        merge_subtitles(srt_file, 2)
            
        # 生成封面图片
        cover_keywords = generating_byds(cover_txt, str(Path(Config.PROMPT_DIR) / 'cover_keywords.prompt'))
        creating_cover(cover_txt, cover_keywords, cover_filename)
        
        # 生成视频文件
        create_video_multi(srt_file, audio_filename, output_filename, Config.SCREEN_SIZE, title_txt)
        # create_video_single(srt_file, audio_filename, output_filename, Config.SCREEN_SIZE, title_txt) #Liunx
        
        return jsonify({
            'cover_path': f'/main/static/output/outputs/{base_filename}.png',
            'video_path': f'/main/static/output/outputs/{base_filename}.mp4'
        })
    except Exception as e:
        return jsonify({'error': f'生成视频时出错: {str(e)}'}), 500

@main_bp.route('/upload_video', methods=['POST'])
def upload_video():
    video_path = request.form.get('video_path', '')
    cover_path = request.form.get('cover_path', '')
    title = request.form.get('title', '')
    desc = request.form.get('desc', '')
    
    if not all([video_path, cover_path, title]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 上传小红书 
        acct_info = "./cookies/cookie_xhs_zhi.json"
        xhs_result = xhs_video_upload(video_path, cover_path, title, desc, acct_info)
        
        # 上传抖音
        acct_info = "./cookies/cookie_douyin_zhi.json"
        dy_result = dy_video_upload(video_path, cover_path, title, desc, acct_info)
        
        # 上传视频号
        # acct_info = "./cookies/cookie_sph_zhi.json"
        # sph_result = sph_video_upload(video_path, cover_path, title, desc, acct_info)
        
        if xhs_result and dy_result:  # 可根据实际需求调整判断逻辑
            return jsonify({'message': '视频已成功上传到各平台'})
        else:
            return jsonify({'error': '部分平台上传失败'}), 500
    except Exception as e:
        return jsonify({'error': f'上传视频时出错: {str(e)}'}), 500

@main_bp.route('/download_video')
def download_video():
    filename = request.args.get('filename', '')
    if not filename:
        return jsonify({'error': '文件名不能为空'}), 400
    
    file_path = str(Config.OUTPUT_DIR / filename)
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"video_{datetime.now().strftime('%Y%m%d')}.mp4"
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500