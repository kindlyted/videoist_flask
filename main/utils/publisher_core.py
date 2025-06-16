# freepublish接口不是群发接口，不能直接使用
import os
import re
import json
import time
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote
from .video_core import markdown_to_html
from config import Config

class WeChatPublisher:
    def __init__(self, app_id: str, app_secret: str, article_name: str = "demo", source_url: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret
        self.source_url = source_url  # 存储主程序传入的链接
        self.access_token = None
        self.token_expire_time = 0
        # 使用配置中的文章目录
        self.article_dir = os.path.join(Config.ARTICLE_DIR, article_name)
        self.md_filename = f"{article_name}.md"  # 配套的markdown文件名
        
        # 确保目录存在
        os.makedirs(self.article_dir, exist_ok=True)
        
        # 图片扩展名白名单
        self.ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

    def get_access_token(self) -> str:
        """获取微信access_token（带缓存机制）"""
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token

        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        response = requests.get(url)
        data = response.json()

        if 'access_token' in data:
            self.access_token = data['access_token']
            self.token_expire_time = time.time() + data['expires_in'] - 300
            return self.access_token
        raise Exception(f"获取access_token失败: {data}")

    def _validate_image(self, image_path: str):
        """验证图片是否符合要求"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")
            
        # 检查文件大小（≤10MB）
        MAX_SIZE = 10 * 1024 * 1024
        if os.path.getsize(image_path) > MAX_SIZE:
            raise ValueError(f"图片大小超过10MB限制: {image_path}")
            
        # 检查文件格式
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的图片格式 {ext}")

    def upload_image(self, image_name: str) -> Tuple[str, str]:
        """
        上传图片到微信永久素材库
        返回：(media_id, image_url)
        注：image_url 直接从微信API返回的json中获取，确保有效性
        """
        image_path = os.path.join(self.article_dir, image_name)
        self._validate_image(image_path)
        
        token = self.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"

        for attempt in range(3):
            try:
                with open(image_path, 'rb') as f:
                    response = requests.post(url, files={'media': f}, timeout=10)
                    data = response.json()

                if 'media_id' in data and 'url' in data:  # 关键修改：直接使用API返回的url
                    print(f"✅ 图片上传成功: {image_name} -> {data['media_id']}")
                    return data['media_id'], data['url']  # 不再手动拼接URL
                raise Exception(f"微信API返回数据不完整: {data}")
            except Exception as e:
                if attempt == 2:
                    raise Exception(f"图片上传失败（重试{attempt+1}次）: {str(e)}")
                time.sleep(1)

    def process_images(self, md_content: str) -> Tuple[str, Dict[str, Tuple[str, str]]]:
        """
        处理所有图片并返回：
        - 处理后的markdown内容
        - 图片映射表 {原文件名: (media_id, url)}
        """
        img_map = {}
        
        # 基础版正则匹配
        pattern = r'\((.*?)\)'  # 正则表达式
        matches = re.findall(pattern, md_content)  # 使用 findall 而不是 search
        image_refs = list(set(matches))  # 去重并转换为列表
        print(f"发现 {len(image_refs)} 个图片引用: {list(image_refs)}")

        # 上传所有图片
        for img_ref in image_refs:
            # 直接使用文件名（不含路径）
            img_name = os.path.basename(unquote(img_ref.strip()))
            try:
                media_id, image_url = self.upload_image(img_name)
                img_map[img_ref] = (media_id, image_url)
            except Exception as e:
                raise Exception(f"图片处理失败: {img_name}\n{str(e)}")

        # 替换内容中的图片链接
        for img_ref, (_, image_url) in img_map.items():
            md_content = md_content.replace(f'({img_ref})', f'({image_url})')
            print(f'({image_url})')

        return md_content, img_map

    def parse_markdown(self) -> Dict:
        """解析Markdown文件（集成YAML元数据、图片处理和HTML转换）"""
        md_file_path = os.path.join(self.article_dir, self.md_filename)
        if not os.path.exists(md_file_path):
            raise FileNotFoundError(f"Markdown文件不存在: {md_file_path}")

        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # 处理图片（强制所有图片必须先上传）
        processed_content, img_map = self.process_images(md_content)  # 注意：此处用原始 md_content 确保图片解析正确

        # 调用 markdown_to_html 统一处理 YAML 和 HTML 转换
        html_content, metadata = markdown_to_html(processed_content)

        # 自动选择封面图（优先选择文件名含 cover/封面的图片）
        thumb_media_id = None
        for img_ref, (media_id, _) in img_map.items():
            if re.search(r'cover|封面|thumb', img_ref, re.IGNORECASE):
                thumb_media_id = media_id
                break
        # 如果没有明确封面，使用第一张图片
        if not thumb_media_id and img_map:
            thumb_media_id = next(iter(img_map.values()))[0]

        # 提取标题（优先使用 YAML 中的 title，否则从 Markdown 的 # 标题提取）
        title = metadata.get('title')  # 先尝试从 YAML 获取
        if not title:
            title_match = re.search(r'^#+\s+(.+)$', md_content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else "未命名文章"

        # 提取摘要（优先使用 YAML 中的 digest，否则自动生成）
        digest = metadata.get('digest')
        if not digest:
            plain_text = re.sub(r'[#*`\-!$$$$]', '', md_content)  # 移除Markdown标记
            digest = ' '.join(plain_text.split())[:140]  # 截取前140字符

        print(f"✅ 解析完成: {title}")
        print(f"摘要: {digest}")
        print(f"封面图Media ID: {thumb_media_id}")
        print(f"图片数量: {len(img_map)}")

        return {
            'title': title,
            'content': html_content,
            'digest': digest,
            'thumb_media_id': thumb_media_id,
            'image_map': img_map,
            'metadata': metadata  # 返回完整的YAML元数据（可选）
        }
    def publish(self) -> bool:
        """发布文章到微信公众号（直接发布，非草稿）"""
        print("\n" + "="*50)
        print("📝 开始发布流程")
        
        try:
            # 1. 解析Markdown（包含图片上传）
            article = self.parse_markdown()
            
            # 2. 验证关键数据
            if not article["content"]:
                raise ValueError("错误：文章内容为空")
            if not article["thumb_media_id"]:
                raise ValueError("错误：未设置封面图")
            # 读取HTML文件,并添加到文章内容末尾
            footer_path = os.path.join("main", "static", "html", "seo_footer_wx.html")
            with open(footer_path, "r", encoding="utf-8") as f:
                SEO_FOOTER = f.read()
            article['content'] = article['content'] + SEO_FOOTER

            # 3. 准备发布数据
            payload = {
                "articles": [
                    {
                        "title": article['title'],
                        "thumb_media_id": article['thumb_media_id'],
                        "author": "观海",
                        "digest": article['digest'],
                        "show_cover_pic": 1,
                        "content": article['content'],
                        "content_source_url": self.source_url,
                        "open_comment": 1,
                        "only_fans_can_comment": 0
                    }
                ]
            }

            # 4. 先添加到草稿箱（获取media_id）
            token = self.get_access_token()
            draft_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
            
            draft_response = requests.post(
                draft_url,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json'} 
            )
            
            draft_result = draft_response.json()
            
            
            media_id = draft_result.get('media_id')
            print(f"✅ 草稿创建成功，获取到media_id: {media_id}")

            # 5. 直接发布文章
            publish_url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
            publish_payload = {
                "media_id": media_id
            }
            
            publish_response = requests.post(
                publish_url,
                data=json.dumps(publish_payload, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json'} 
            )
            
            publish_result = publish_response.json()
            
            # 打印完整的响应结果用于调试
            print("\n微信API发布响应结果:")
            print(json.dumps(publish_result, indent=2, ensure_ascii=False))
            
            if publish_result.get('errcode') == 0:
                print(f"\n✅ 发布成功！文章已发布")
                print(f"发布任务ID: {publish_result.get('publish_id')}")
                print(f"文章media_id: {media_id}")
                print(f"封面图Media ID: {article['thumb_media_id']}")
                print("所有图片上传结果:")
                for img_ref, (media_id, url) in article['image_map'].items():
                    print(f"- {img_ref}: {media_id}")
                return True
            print(publish_result)
            # 错误处理（保持不变）
            error_code = publish_result.get('errcode', '未知')
            error_msg = publish_result.get('errmsg', '未知错误')
            
            error_explanations = {
                40001: "无效的access_token，请检查appid和appsecret是否正确",
                40002: "不合法的凭证类型",
                40007: "不合法的media_id，可能是图片上传失败",
                41001: "缺少必要参数",
                45009: "接口调用超过限制",
                48001: "API功能未授权，请检查公众号权限设置",
                88000: "没有留言权限",
                88001: "该图文不存在",
                88002: "文章状态错误",
            }
            
            explanation = error_explanations.get(error_code, 
                "请参考微信公众平台开发文档查看错误代码含义")
            
            error_details = (
                f"发布失败！\n"
                f"错误代码: {error_code}\n"
                f"错误信息: {error_msg}\n"
                f"可能原因: {explanation}\n"
                f"请求数据: {json.dumps(payload, indent=2, ensure_ascii=False)}"
            )
            
            raise Exception(error_details)

        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"解析微信API响应失败: {str(e)}")
        except Exception as e:
            raise Exception(f"发布过程中发生错误: {str(e)}")