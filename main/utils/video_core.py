# 新增加了opencv/ff静默输出/判段是否有comfyui
# ===== Python标准库 =====
import os
import io
import asyncio
import re
import base64
import time
import subprocess
import shutil
from typing import Dict, List, Tuple
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from config import Config
# ===== 图像/视频处理 =====
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
# ===== 音频处理 =====
from pydub import AudioSegment
# ===== 字幕处理 =====
import pysrt
# ===== 网络请求 =====
import requests
from .cookielogin import CookieLogin
# ===== 数据解析 =====
import yaml
import markdown
from bs4 import BeautifulSoup
# ===== 模板引擎 =====
from jinja2 import Template
# ===== 语音合成 =====
import edge_tts
# ===== 浏览器自动化 =====
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# ===== AI服务 =====
from openai import OpenAI

async def speaking(OUTPUT_FILE: str, WEBVTT_FILE: str, TEXT: str, VOICE: str) -> None:
    # 确保目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(WEBVTT_FILE), exist_ok=True)
    
    communicate = edge_tts.Communicate(TEXT, VOICE)
    submaker = edge_tts.SubMaker()
    with open(OUTPUT_FILE, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    with open(WEBVTT_FILE, "w", encoding="utf-8") as file:
        file.write(submaker.get_srt())

async def process_dialogue(
    input_file: str,
    output_audio: str,
    output_srt: str,
    voice_mapping: Dict[str, str],
    temp_dir: str = "tmp",
    silence_duration_ms: int = 500
) -> None:
    """
    处理多角色对话文本，生成合并后的音频和字幕（带静音间隔）
    
    Args:
        input_file: 输入文本文件路径
        output_audio: 输出音频文件路径
        output_srt: 输出字幕文件路径
        voice_mapping: 角色到语音的映射字典
        temp_dir: 临时文件存放目录
        silence_duration_ms: 角色间静音间隔时长(毫秒)
    """
    # 确保临时目录存在
    os.makedirs(temp_dir, exist_ok=True)
    
    # 解析对话文本
    dialogues = parse_dialogue_file(input_file, voice_mapping)
    
    # 为每个对话片段生成音频和字幕
    tasks = []
    for i, (speaker, text) in enumerate(dialogues):
        voice = voice_mapping.get(speaker)
        if not voice:
            continue
            
        audio_file = os.path.join(temp_dir, f"part_{i}.mp3")
        srt_file = os.path.join(temp_dir, f"part_{i}.srt")
        
        tasks.append(speaking(audio_file, srt_file, text, voice))
    
    # 并行处理所有对话片段
    await asyncio.gather(*tasks)
    
    # 合并音频和字幕（带静音间隔）
    merge_audio_and_srt_with_silence(
        temp_dir, 
        len(dialogues), 
        output_audio, 
        output_srt,
        silence_duration_ms
    )
    
    # 清理临时文件
    for i in range(len(dialogues)):
        try:
            os.remove(os.path.join(temp_dir, f"part_{i}.mp3"))
            os.remove(os.path.join(temp_dir, f"part_{i}.srt"))
        except:
            pass

def parse_dialogue_file(
    file_path: str, 
    voice_mapping: Dict[str, str]
) -> List[Tuple[str, str]]:
    """
    解析对话文本文件，返回(角色, 文本)列表
    
    输入文件格式示例:
    momo: 你好，今天天气真好
    labubu: 是啊，适合出去玩
    
    Args:
        file_path: 文本文件路径
        voice_mapping: 角色到语音的映射字典
        
    Returns:
        包含(角色, 文本)元组的列表
    """
    dialogues = []
    current_speaker = None
    current_text = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是新的说话者行
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[0] in voice_mapping:
                # 保存前一个说话者的内容
                if current_speaker and current_text:
                    dialogues.append((current_speaker, ' '.join(current_text)))
                    current_text = []
                
                current_speaker = parts[0]
                current_text.append(parts[1].strip())
            else:
                # 继续当前说话者的内容
                current_text.append(line)
    
    # 添加最后一个说话者的内容
    if current_speaker and current_text:
        dialogues.append((current_speaker, ' '.join(current_text)))
    
    return dialogues

def merge_audio_and_srt_with_silence(
    temp_dir: str, 
    part_count: int,
    output_audio: str,
    output_srt: str,
    silence_duration_ms: int = 500
) -> None:
    """
    合并多个音频和字幕文件，在音频间添加静音间隔
    
    Args:
        temp_dir: 临时文件目录
        part_count: 部分文件数量
        output_audio: 输出音频路径
        output_srt: 输出字幕路径
        silence_duration_ms: 静音间隔时长(毫秒)
    """
    # 合并音频（带静音间隔）
    silence = AudioSegment.silent(duration=silence_duration_ms)
    combined_audio = None
    first_audio = True
    
    for i in range(part_count):
        audio_file = os.path.join(temp_dir, f"part_{i}.mp3")
        
        if not os.path.exists(audio_file):
            continue
            
        audio = AudioSegment.from_mp3(audio_file)
        
        if combined_audio is None:
            combined_audio = audio
            first_audio = False
        else:
            combined_audio += silence + audio
    
    if combined_audio is not None:
        combined_audio.export(output_audio, format="mp3")
    
    # 合并字幕并调整时间戳（考虑静音间隔）
    with open(output_srt, 'w', encoding='utf-8') as out_srt:
        total_duration = 0  # 毫秒
        first_audio = True  # 标记是否是第一个音频
        
        for i in range(part_count):
            audio_file = os.path.join(temp_dir, f"part_{i}.mp3")
            srt_file = os.path.join(temp_dir, f"part_{i}.srt")
            
            if not os.path.exists(audio_file) or not os.path.exists(srt_file):
                continue
                
            # 如果不是第一个音频，添加静音间隔时间
            if not first_audio:
                total_duration += silence_duration_ms
            else:
                first_audio = False
                
            # 读取并调整字幕
            with open(srt_file, 'r', encoding='utf-8') as in_srt:
                content = in_srt.read()
                adjusted_content = adjust_srt_timestamps(content, total_duration)
                out_srt.write(adjusted_content)
                out_srt.write('\n')
            
            # 累加当前音频时长
            audio = AudioSegment.from_mp3(audio_file)
            total_duration += len(audio)

def adjust_srt_timestamps(srt_content: str, offset_ms: int) -> str:
    """
    调整SRT字幕的时间戳
    
    Args:
        srt_content: 原始SRT内容
        offset_ms: 时间偏移量(毫秒)
        
    Returns:
        调整后的SRT内容
    """
    if offset_ms == 0:
        return srt_content
        
    lines = srt_content.split('\n')
    adjusted_lines = []
    
    for line in lines:
        if '-->' in line:
            # 这是时间轴行
            parts = line.split('-->')
            start, end = parts[0].strip(), parts[1].strip()
            
            # 调整时间
            start = adjust_time(start, offset_ms)
            end = adjust_time(end, offset_ms)
            
            line = f"{start} --> {end}"
        
        adjusted_lines.append(line)
    
    return '\n'.join(adjusted_lines)

def adjust_time(time_str: str, offset_ms: int) -> str:
    """
    调整单个时间戳
    
    Args:
        time_str: 时间字符串 (HH:MM:SS,mmm)
        offset_ms: 偏移量(毫秒)
        
    Returns:
        调整后的时间字符串
    """
    # 解析时间
    hh_mm_ss, ms = time_str.split(',')
    hh, mm, ss = hh_mm_ss.split(':')
    
    total_ms = (int(hh) * 3600 + int(mm) * 60 + int(ss)) * 1000 + int(ms)
    total_ms += offset_ms
    
    # 转换回时间格式
    new_ms = total_ms % 1000
    total_seconds = total_ms // 1000
    new_ss = total_seconds % 60
    total_minutes = total_seconds // 60
    new_mm = total_minutes % 60
    new_hh = total_minutes // 60
    
    return f"{new_hh:02d}:{new_mm:02d}:{new_ss:02d},{new_ms:03d}"

# 定义将 SubRipTime 对象转换为秒数的函数
def time2sec(subriptime):
    return (
        subriptime.hours * 3600 +
        subriptime.minutes * 60 +
        subriptime.seconds +
        subriptime.milliseconds / 1000.0
    )

# 定义合并字幕条目的函数
def merge_subtitles(srt, max_duration_s) -> None:
    subtitles = pysrt.open(srt)
    merged_subtitles = []
    current_sub = None

    for sub in subtitles:
        if current_sub is None:
            current_sub = sub
        else:
            # 计算当前字幕条目的开始时间和结束时间
            start_time = time2sec(sub.start)
            end_time = time2sec(sub.end)
               
            # 计算上一个字幕条目的结束时间
            current_start_time = time2sec(current_sub.start)
            current_end_time = time2sec(current_sub.end)
        
            # 如果当前字幕条目的开始时间与上一个条目的结束时间相差不超过 0.1 秒，
            # 并且合并后的时间跨度不超过 max_duration_s 秒，
            # 则合并这两个条目。
            if start_time - current_end_time <= 0.1 and (end_time - current_start_time) <= max_duration_s:
                current_sub.end = sub.end
                current_sub.text = current_sub.text.strip() + "" + sub.text.strip()
            else:
                # 否则，将当前合并的字幕条目添加到结果列表中，并开始新的字幕条目。
                merged_subtitles.append(current_sub)
                current_sub = sub
                
    # 添加最后一个字幕条目
    if current_sub:
        merged_subtitles.append(current_sub)
    
    # 将合并后的字幕条目列表转换为 SubRipFile 对象
    merged_subrip_file = pysrt.SubRipFile(merged_subtitles)
    # 保存合并后的字幕到新的 .srt 文件
    merged_subrip_file.save(srt, encoding="utf-8")

def draw_text_on_frame(frame, text, font, color, position, screen_size, stroke_width, stroke_color, use_shadow):
    """（高低配都调用）在视频帧上绘制文本"""
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_pil = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(frame_pil)

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    if isinstance(position[0], str) and position[0].lower() == "center":
        x = (screen_size[0] - text_width) // 2
    else:
        x = position[0]
    
    if isinstance(position[1], str) and position[1].lower() == "middle":
        y = (screen_size[1] - text_height) // 2
        y -= text_bbox[1]
    else:
        y = position[1]

    draw.text(
        (x, y),
        text,
        font=font,
        fill=color[::-1],
        stroke_width=stroke_width if use_shadow else 0,
        stroke_fill=stroke_color[::-1] if use_shadow else None
    )
    return cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

def render_frame(args):
    """修改后支持动态帧率的版本"""
    frame_idx, sub_times, bg_with_title, screen_size, font, text_color, position, stroke_width, stroke_color, use_shadow, fps = args 
    frame_time = frame_idx / fps 
    frame = bg_with_title.copy()
    
    for start, end, text in sub_times:
        if start <= frame_time < end:
            frame = draw_text_on_frame(
                frame=frame,
                text=text,
                font=font,
                color=text_color,
                position=position,
                screen_size=screen_size,
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                use_shadow=use_shadow
            )
    return frame.tobytes()

# 高低配都调用生成拼色背景
def create_gradient_background(width, height): 
    BG_COLOR = (243, 66, 26)  # 蓝色 RGB(80,80,80)灰色
    CANVAS_COLOR = (93, 20, 0)  # 蓝黑 RGB（0,0,0）黑色
    bg = np.zeros((height, width, 3), dtype=np.uint8)
    # 上黑（25%高度）
    bg[:height//4, :] = CANVAS_COLOR
    # 中灰（50%高度）
    bg[height//4:height*3//4, :] = BG_COLOR 
    # 下黑（25%高度）
    bg[height*3//4:, :] = CANVAS_COLOR
    return bg

def create_video_multi(srt_filename, audio_filename, output_filename, screen_size, title_txt):
    """多线程版本"""
    start_time = time.time()
    try:
        # 核心参数配置
        FPS = 24
        TITLE_FONT_SIZE = 85
        TITLE_COLOR = (93, 20, 0) # 蓝黑 BGR(171, 229, 243)金色
        TITLE_STROKE_COLOR = (200, 200, 200) # 灰色
        TITLE_STROKE_WIDTH = 2
        TITLE_Y = int(screen_size[1] * 0.5) #250
        SUB_FONT_SIZE = 100
        SUB_COLOR = (0, 0, 255) # 红色 BGR(171, 229, 243)金色
        SUB_STROKE_COLOR = (0, 0, 0)
        SUB_STROKE_WIDTH = 2
        SUB_POSITION = ("center", "middle")
        SUB_USE_SHADOW = False

        subs = pysrt.open(srt_filename, encoding='utf-8')
        sub_times = [(time2sec(sub.start), time2sec(sub.end), sub.text) for sub in subs]
        audio = AudioSegment.from_file(audio_filename)
        total_duration = max(time2sec(subs[-1].end), len(audio)/1000)

        # 生成拼色背景
        bg_image = create_gradient_background(screen_size[0], screen_size[1])

        try:
            font_path = current_app.config['VIDEO_FONT_DIR'] / 'ceym.ttf'
            font_title = ImageFont.truetype(font_path, TITLE_FONT_SIZE)
            font_sub = ImageFont.truetype(font_path, SUB_FONT_SIZE)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        bg_with_title = draw_text_on_frame(
            frame=bg_image,
            text=title_txt,
            font=font_title,
            color=TITLE_COLOR,
            position=("center", TITLE_Y),
            screen_size=screen_size,
            stroke_width=TITLE_STROKE_WIDTH,
            stroke_color=TITLE_STROKE_COLOR,
            use_shadow=False
        )

        # FFmpeg参数
        cmd = [
        'ffmpeg', '-y',
        '-thread_queue_size', '2048',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{screen_size[0]}x{screen_size[1]}',
        '-pix_fmt', 'bgr24',
        '-r', '24',
        '-i', '-',
        '-i', str(audio_filename),  # 确保路径是字符串
        '-preset', 'fast',
        # '-c:v', 'h264_nvenc',          # 改用 NVIDIA NVENC 编码 
        # '-pix_fmt', 'nv12',            # NVENC 推荐格式（原 yuv420p）
        # '-cq', '23',                   # NVENC 质量参数（原 global_quality）
        # '-rc', 'vbr',                  # NVIDIA新增：码率控制模式（可变码率）
        # '-b:v', '0',                   # NVIDIA新增：自动码率（基于 cq 值）
        '-c:v', 'h264_qsv',           # Intel 加速
        '-pix_fmt', 'yuv420p',        # Intel 默认格式
        '-global_quality', '23',      # Intel 编码质量参数
        '-c:a', 'aac',
        '-metadata', f'title={title_txt}',
        '-metadata', 'encoder=FFmpeg',
        str(output_filename)  # 确保路径是字符串
    ]

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor, \
             subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as process:
            
            # 在 create_video_multi 中构建参数时加入 fps
            frame_args = [
                (i, sub_times, bg_with_title, screen_size, font_sub, 
                SUB_COLOR, SUB_POSITION, SUB_STROKE_WIDTH, SUB_STROKE_COLOR, SUB_USE_SHADOW, FPS)  # 新增 FPS
                for i in range(int(total_duration * FPS))  # 这里也使用 FPS 替代硬编码值
            ]
            
            for frame_data in executor.map(render_frame, frame_args):
                process.stdin.write(frame_data)

        print(f"视频生成完成 | 耗时: {time.time()-start_time:.1f}秒")

    except Exception as e:
        print(f"错误: {str(e)}")
        raise

def create_video_single(srt_filename, audio_filename, output_filename, screen_size, title_txt):
    """单线程版本"""
    start_time = time.time()
    try:
        # 核心参数配置
        SCALE = 640 / 1080  # 直接使用分数关系
        PROCESS_SIZE = (int(screen_size[0] * SCALE), int(screen_size[1] * SCALE)) # PROCESS_SIZE = (640, 1136)
        FPS = 18
        TITLE_FONT_SIZE = 50
        TITLE_COLOR = (93, 20, 0)
        TITLE_STROKE_COLOR = (200, 200, 200)
        TITLE_STROKE_WIDTH = 2
        TITLE_Y = int(PROCESS_SIZE[1] * 0.5) # int(PROCESS_SIZE[1] * 0.13)
        SUB_FONT_SIZE = 59
        SUB_COLOR = (171, 229, 243)
        SUB_STROKE_COLOR = (0, 0, 0)
        SUB_STROKE_WIDTH = 0
        SUB_POSITION = ("center", "middle")
        SUB_USE_SHADOW = False

        subs = pysrt.open(srt_filename, encoding='utf-8')
        sub_times = [(time2sec(sub.start), time2sec(sub.end), sub.text) for sub in subs]

        # 生成拼色背景
        bg = create_gradient_background(PROCESS_SIZE[0], PROCESS_SIZE[1])

        font_path = current_app.config['VIDEO_FONT_DIR'] / 'ceym.ttf'
        if not os.path.exists(font_path):
            raise RuntimeError("必须的字体文件缺失: ceym.ttf")
        
        font_title = ImageFont.truetype(font_path, TITLE_FONT_SIZE)
        font_sub = ImageFont.truetype(font_path, SUB_FONT_SIZE)

        title_layer = draw_text_on_frame(
            frame=bg,
            text=title_txt,
            font=font_title,
            position=("center", TITLE_Y),
            screen_size=PROCESS_SIZE,
            color=TITLE_COLOR,
            stroke_width=TITLE_STROKE_WIDTH,
            stroke_color=TITLE_STROKE_COLOR,
            use_shadow=False
        )

        # 保持原有cmd参数（包括注释）完全不变
        cmd = [
            'ffmpeg', '-y',
            '-thread_queue_size', '2048',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{PROCESS_SIZE[0]}x{PROCESS_SIZE[1]}',
            '-pix_fmt', 'bgr24',
            '-r', str(FPS),
            '-i', '-',
            '-thread_queue_size', '512',
            '-i', audio_filename,
            '-c:v', 'libx264',
            '-profile:v', 'main',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-preset', 'fast',
            '-crf', '23',
            '-x264-params', 'ref=4:bframes=0',
            '-c:a', 'aac',
            '-ar', '44100',
            '-b:a', '128k',
            '-ac', '1',
            '-metadata', f'title={title_txt}',
            '-metadata', 'encoder=FFmpeg',
            output_filename
        ]

        with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as proc:
            for frame_idx in range(int(time2sec(subs[-1].end) * FPS)):
                frame_time = frame_idx / FPS
                frame = title_layer.copy()
                
                for start, end, text in sub_times:
                    if start <= frame_time < end:
                        frame = draw_text_on_frame(
                            frame=frame,
                            text=text,
                            font=font_sub,
                            position=SUB_POSITION, 
                            screen_size=PROCESS_SIZE,
                            color=SUB_COLOR,
                            stroke_width=SUB_STROKE_WIDTH,
                            stroke_color=SUB_STROKE_COLOR,
                            use_shadow=SUB_USE_SHADOW
                        )
                        break
                
                proc.stdin.write(frame.tobytes())
            
            proc.stdin.close()
            proc.wait()

        print(f"视频生成成功 | 耗时: {time.time()-start_time:.1f}秒")
        return True

    except Exception as e:
        print(f"生成失败: {str(e)}")
        return False
     
# 创建封面postist和videoist共用
def creating_cover(text, keywords, cover_filename) -> None:

    # 确保 keywords 是一个列表
    if isinstance(keywords, str):
        keywords = keywords.split(',')

    # 设置路径
    html_template_path = Config.HTML_DIR / 'template-xhscover.html'
    html_file_path = Path('./tmp/working.html').resolve()
    os.makedirs(html_file_path.parent, exist_ok=True)

    # 渲染HTML模板
    with open(html_template_path, 'r', encoding='utf-8') as file:
        template = Template(file.read())

    html_content = template.render(text=text, keywords=keywords)
    
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)

    # 设置Chrome选项
    driver_path = os.getenv('CHROME_DRIVER_PATH')
    if not driver_path:
        raise ValueError("环境变量 CHROME_DRIVER_PATH 未设置，请指定ChromeDriver路径。")
    service = Service(driver_path)
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式，不显示浏览器窗口

    # 启动Chrome浏览器
    driver = webdriver.Chrome(options=chrome_options, service=service)
    driver.set_window_size(1200, 1600) # 设置浏览器窗口大小

    try:
        # 打开HTML文件
        driver.get(f'file://{html_file_path}')
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'text-container'))
        )

        # 获取页面截图
        screenshot = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "png", "fromSurface": True, "captureBeyondViewport": True})
        with open(cover_filename, 'wb') as f:
            img = base64.b64decode(screenshot['data'])
            f.write(img)
    except Exception as e:
        print(f"发生错误：{e}")
    finally:
        # 关闭浏览器
        driver.quit()


# gpt part 生成正文，postist_core.py里也有，但后缀不同表示api不同
def generating_byds(content, prompt_path):
    client = OpenAI(
        api_key=os.getenv('API_KEY_DS'),
        base_url=os.getenv('URL_DS'), 
    )
    # 定义提示词
    with open(prompt_path, 'r', encoding='utf-8') as file:
        your_prompt = file.read()
    your_prompt = your_prompt + content
    try:
        completion = client.chat.completions.create(
            model='deepseek-chat',   
            messages = [
                {
                    "role": "user",
                    "content": your_prompt
                }
            ],
            stream=False
        )
        print(completion.choices[0].message.content)
        answer = completion.choices[0].message.content
    except Exception as e:
        print("提示", e)
        answer = "敏感词censored by Deepseek"
    print("DeepSeek大模型工作中，请稍等片刻")
    return answer

# gpt part 生成正文，postist_core.py里也有，但后缀不同表示api不同
def generating_bykm(content, prompt_path):
    client = OpenAI(
        api_key=os.getenv('API_KEY_KIMI'),
        base_url=os.getenv('URL_KIMI'), 
    )
    # 定义提示词
    with open(prompt_path, 'r', encoding='utf-8') as file:
        your_prompt = file.read()
    your_prompt = your_prompt + content
    try:
        completion = client.chat.completions.create(
            model='moonshot-v1-8k',   
            messages = [
                {
                    "role": "user",
                    "content": your_prompt
                }
            ],
            stream=False
        )
        print(completion.choices[0].message.content)
        answer = completion.choices[0].message.content
    except Exception as e:
        print("提示", e)
        answer = "敏感词censored by Moonshot"
    print("Moonshot大模型工作中，请稍等片刻")
    return answer

# gpt part 生成正文
def generating_jskb(content, prompt_path):
    client = OpenAI(
        api_key=os.getenv('API_KEY_DS'),
        base_url=os.getenv('URL_DS'), 
    )
    # 定义提示词
    with open(prompt_path, 'r', encoding='utf-8') as file:
        your_prompt = file.read()
    # your_prompt = your_prompt + content
    try:
        completion = client.chat.completions.create(
            model='deepseek-chat',   
            messages = [{"role": "system", "content": your_prompt}, {"role": "user", "content": content}],
            stream=False,
            temperature=0.4,          # 降低随机性
            # max_tokens=4096,          # 防止过长
            top_p=0.9,                # 平衡多样性
            frequency_penalty=0.5,    # 减少重复
            presence_penalty=0.3,     # 适度控制主题跳跃
            response_format={'type': 'json_object'}
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        print("提示", e)
        answer = "敏感词censored by Deepseek"
    print("DeepSeek大模型工作中，请稍等片刻")
    return answer

# 从网页中提取文本
def extractting(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # 解析网页内容
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取所有文本内容
        text = soup.get_text(separator='\n', strip=True)
        return text

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
        return ""
    except requests.exceptions.RequestException as err:
        print(f"请求错误: {err}")
        return ""

# 生成 Basic Auth Token
def basic_auth_token(username, password):
    credentials = f"{username}:{password}"
    token = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return f"Basic {token}"

# 发布文章并关联图片
def posting(wp_url, token, data):
    url = f"{wp_url}/wp-json/wp/v2/posts"
    
    headers = {
        "Authorization": token,  # 添加 Basic Auth
    }
    response = requests.post(
        url,
        headers=headers,
        json=data,
    )
    if response.status_code == 201:
        return response.json()  # 返回文章信息
    else:
        raise Exception(f"Failed to create post: {response.status_code} - {response.text}")

def getting_picture(query, dir, filename, aspect_ratio):
    """
    Get an image from Unsplash with specified aspect ratio
    
    Args:
        query (str): Search query for the image
        dir (str): Directory to save the image
        filename (str): Base filename (without extension)
        aspect_ratio (int): 
            1 for landscape (horizontal),
            2 for portrait (vertical),
            3 for square (default: 1)
    
    Returns:
        str: Path to saved image or None if failed
    """
    ACCESS_KEY = os.environ.get("UNP_AKEY")
    if not query:
        query = "global map"

    if not ACCESS_KEY:
        raise ValueError("Unsplash API access key not found in environment variables.")

    # Validate aspect ratio
    if aspect_ratio not in (1, 2, 3):
        raise ValueError("aspect_ratio must be 1 (landscape), 2 (portrait), or 3 (square)")

    # Map aspect ratio to Unsplash orientation parameter
    orientation_map = {
        1: "landscape",
        2: "portrait",
        3: "squarish"
    }
    orientation = orientation_map[aspect_ratio]
    per_page = 5

    # Construct API request URL
    url = (
        f"https://api.unsplash.com/search/photos"
        f"?client_id={ACCESS_KEY}"
        f"&query={query}"
        f"&orientation={orientation}"
        f"&per_page={per_page}"
    )

    # Send request
    response = requests.get(url)
    response.raise_for_status()

    # Parse JSON response
    data = response.json()
    if not data['results']:
        print("No matching images found")
        return None

    # Process image results
    for photo in data['results']:
        photo_url = photo['urls']['full']
        photo_description = photo.get('description', "No description")

        # Download image
        try:
            response = requests.get(photo_url)
            response.raise_for_status()
            image_data = response.content
            
            # Always use WebP extension
            file_extension = '.webp'
            # Create directory if not exists
            save_dir = Config.ARTICLE_DIR / dir
            os.makedirs(save_dir, exist_ok=True)
            # Construct full path with directory and filename
            filename = f"{filename}{file_extension}"
            filepath = save_dir / filename

            try:
                # Open the image with PIL
                img = Image.open(io.BytesIO(image_data))
                
                # Convert to RGB if needed (WebP doesn't support alpha channel)
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
                
                # Verify aspect ratio matches request
                width, height = img.size
                ratio = width / height
                
                # Define acceptable ratio ranges for each type
                if aspect_ratio == 1 and ratio < 1.2:  # Landscape (w > h)
                    print(f"Skipping image - requested landscape but got portrait/square")
                    continue
                elif aspect_ratio == 2 and ratio > 0.8:  # Portrait (h > w)
                    print(f"Skipping image - requested portrait but got landscape/square")
                    continue
                elif aspect_ratio == 3 and not (0.9 < ratio < 1.1):  # Square (~1:1)
                    print(f"Skipping image - requested square but got landscape/portrait")
                    continue
                
                # Resize if too large
                max_dimension = 1920
                if max(img.size) > max_dimension:
                    ratio = max_dimension / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Compression parameters for WebP
                quality = 85
                method = 6  # Default compression method (0-6)
                
                # Save directly as WebP
                buffer = io.BytesIO()
                img.save(buffer, format='WEBP', quality=quality, method=method)
                
                # If under 1MB, save directly
                if buffer.getbuffer().nbytes <= 1024 * 1024:
                    with open(filepath, "wb") as f:
                        f.write(buffer.getvalue())
                    print(f"WebP image saved: {filepath} (Size: {buffer.getbuffer().nbytes/1024:.1f}KB)")
                    print(f"Description: {photo_description}")
                    return str(filepath)

                # If still too large, try reducing quality
                print(f"Initial WebP size: {buffer.getbuffer().nbytes/1024:.1f}KB, compressing further...")
                
                while quality >= 30:  # Don't go below 30% quality
                    buffer = io.BytesIO()
                    img.save(buffer, format='WEBP', quality=quality, method=method)
                    
                    if buffer.getbuffer().nbytes <= 1024 * 1024:
                        with open(filename, "wb") as f:
                            f.write(buffer.getvalue())
                        print(f"Compressed WebP saved: {filename} (Size: {buffer.getbuffer().nbytes/1024:.1f}KB, Quality: {quality}%)")
                        print(f"Description: {photo_description}")
                        return filename
                    
                    # Reduce quality for next attempt
                    quality -= 10
                
                # If we get here, all attempts failed
                print("Failed to compress WebP below 1MB")
                continue
                
            except Exception as img_error:
                print(f"Image processing failed: {str(img_error)}")
                continue
                
        except Exception as download_error:
            print(f"Download failed: {str(download_error)}")
            continue

    print("No suitable images found")
    return None

def comfyui_picture(prompt, dir, filename, aspect_ratio):
    """生成图片并保存到指定目录（使用bypy_前缀+序号检测最新文件）
    
    参数:
        prompt (str): 图片生成提示词
        dir (str): 最终保存目录（自动创建）
        filename (str): 主文件名（不带扩展名）
        aspect_ratio (int): 图片尺寸比例 
            1: 768 * 512 (横版)
            2: 512 * 768 (竖版)
            3: 512 * 512 (方形)
    """
    # ---------- 配置区 ----------
    COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"  # ComfyUI API地址
    COMFYUI_OUTPUT_DIR = "C:\\pyproj\\ComfyUI-aki-v1.4\\output"  # ComfyUI输出目录
    TIMEOUT = 600  # 超时时间（秒）
    FILE_PREFIX = "bypy_"  # 固定文件名前缀
    # ---------------------------

    # 根据比例设置宽高
    if aspect_ratio == 1:
        width, height = 384, 256
    elif aspect_ratio == 2:
        width, height = 512, 768
    elif aspect_ratio == 3:
        width, height = 512, 512
    else:
        print(f"⚠️ 未知比例参数 {aspect_ratio}，使用默认 768x512")
        width, height = 768, 512

    # 确保目录存在
    os.makedirs(dir, exist_ok=True)

    # 1. 定义工作流
    workflow = {
        "3": {
            "inputs": {
                "seed": int(datetime.now().timestamp()),
                "steps": 20,
                "cfg": 1,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1,
                "model": ["10", 0],
                "positive": ["15", 0],
                "negative": ["16", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "5": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["11", 0]
            },
            "class_type": "VAEDecode"
        },
        "10": {
            "inputs": {
                "unet_name": "flux1-dev-Q3_K_S.gguf"
            },
            "class_type": "UnetLoaderGGUF"
        },
        "11": {
            "inputs": {
                "vae_name": "FLUX.1-ae.safetensors"
            },
            "class_type": "VAELoader"
        },
        "12": {
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
                "type": "flux",
                "device": "default"
            },
            "class_type": "DualCLIPLoader"
        },
        "15": {
            "inputs": {
                "clip_l": prompt,
                "t5xxl": "",
                "guidance": 3.5,
                "speak_and_recognation": {"__value__": [False, True]},
                "clip": ["12", 0]
            },
            "class_type": "CLIPTextEncodeFlux"
        },
        "16": {
            "inputs": {
                "conditioning": ["15", 0]
            },
            "class_type": "ConditioningZeroOut"
        },
        "18": {
            "inputs": {
                "filename_prefix": FILE_PREFIX,  # 使用固定前缀
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

    # 2. 提交生成请求
    try:
        print("🔄 正在提交生成请求...")
        response = requests.post(COMFYUI_API_URL, json={"prompt": workflow})
        response.raise_for_status()
        prompt_id = response.json()["prompt_id"]
        print(f"✅ 任务已提交 (ID: {prompt_id})")
    except Exception as e:
        print(f"❌ 提交失败: {str(e)}")
        return None

    # 3. 智能轮询（检测bypy_前缀文件中序号最大的）
    print("⏳ 正在监听生成状态...")
    start_time = time.time()
    final_path = None

    while True:
        try:
            # 获取所有bypy_前缀的PNG文件
            prefix_files = [
                f for f in os.listdir(COMFYUI_OUTPUT_DIR)
                if f.startswith(FILE_PREFIX) and f.endswith(".png")
            ]

            if prefix_files:
                # 提取序号并找到最大值（例如 bypy_00003.png -> 3）
                max_num = -1
                latest_file = None
                for f in prefix_files:
                    try:
                        # 提取文件名中的数字部分
                        num_str = f[len(FILE_PREFIX):].split('.')[0]  # "00003"
                        num = int(num_str)  # 转换为整数
                        if num > max_num:
                            max_num = num
                            latest_file = f
                    except (IndexError, ValueError):
                        continue

                if latest_file:
                    src = os.path.join(COMFYUI_OUTPUT_DIR, latest_file)
                    temp_png_path = os.path.join(dir, f"{filename}.png")  # 临时PNG文件
                    final_webp_path = os.path.join(dir, f"{filename}.webp")  # 最终WebP文件
                    
                    # 复制原始PNG文件
                    shutil.copy2(src, temp_png_path)
                    print(f"✅ 已找到原始文件: {latest_file}")
                    
                    try:
                        # 使用Pillow转换为WebP
                        from PIL import Image
                        with Image.open(temp_png_path) as img:
                            # 转换为RGB模式（WebP不支持alpha通道）
                            if img.mode in ('RGBA', 'P', 'LA'):
                                img = img.convert('RGB')
                            
                            # WebP压缩参数
                            quality = 85
                            method = 6  # 默认压缩方法
                            
                            # 保存为WebP
                            img.save(final_webp_path, format='WEBP', quality=quality, method=method)
                            final_path = final_webp_path
                            
                            # 删除临时PNG文件
                            os.remove(temp_png_path)
                            
                            print(f"✅ 已转换为WebP: {final_webp_path}")
                            print(f"文件大小: {os.path.getsize(final_webp_path)/1024:.1f}KB")
                            return final_path
                    except Exception as img_error:
                        print(f"⚠️ WebP转换失败，保留PNG格式: {str(img_error)}")
                        final_path = temp_png_path
                        return final_path

            # 检查任务状态
            history_url = f"{COMFYUI_API_URL.rstrip('prompt')}history/{prompt_id}"
            history_data = requests.get(history_url).json()
            
            if prompt_id in history_data:
                status = history_data[prompt_id]
                if status["status"]["completed"]:
                    print("✅ 任务已完成")
                    # 最终检查一次文件
                    prefix_files = [f for f in os.listdir(COMFYUI_OUTPUT_DIR)
                                  if f.startswith(FILE_PREFIX) and f.endswith(".png")]
                    if prefix_files:
                        # 直接按字符串排序取最大值（bypy_00003 > bypy_00002）
                        latest_file = max(prefix_files)
                        src = os.path.join(COMFYUI_OUTPUT_DIR, latest_file)
                        temp_png_path = os.path.join(dir, f"{filename}.png")
                        final_webp_path = os.path.join(dir, f"{filename}.webp")
                        
                        shutil.copy2(src, temp_png_path)
                        print(f"🔄 找到最终文件: {latest_file}")
                        
                        try:
                            from PIL import Image
                            with Image.open(temp_png_path) as img:
                                if img.mode in ('RGBA', 'P', 'LA'):
                                    img = img.convert('RGB')
                                
                                quality = 85
                                method = 6
                                
                                img.save(final_webp_path, format='WEBP', quality=quality, method=method)
                                final_path = final_webp_path
                                os.remove(temp_png_path)
                                
                                print(f"🔄 最终转换为WebP: {final_webp_path}")
                                return final_path
                        except Exception as img_error:
                            print(f"⚠️ 最终WebP转换失败，保留PNG: {str(img_error)}")
                            final_path = temp_png_path
                            return final_path
                    return final_path
                elif status["status"]["failed"]:
                    print("❌ 任务执行失败")
                    return None

            # 超时处理
            elapsed = time.time() - start_time
            if elapsed > TIMEOUT:
                print(f"⏰ 超过{TIMEOUT}秒未完成，终止等待")
                return None

            time.sleep(1)  # 降低CPU占用

        except Exception as e:
            print(f"⚠️ 轮询出错: {str(e)}")
            time.sleep(5)

# 处理图片上传
def upload_image(wp_url, token, image_path):
    url = f"{wp_url}/wp-json/wp/v2/media"
    headers = {
        "Content-Disposition": f'attachment; filename={os.path.basename(image_path)}',
        "Content-Type": f"image/{os.path.splitext(image_path)[1][1:]}",  # 动态设置 Content-Type
        "Authorization": token,  # 添加 Basic Auth
    }

    # 尝试上传图片
    with open(image_path, "rb") as file:
        response = requests.post(url, headers=headers, data=file)

    # 如果上传成功，返回 media_id 和 image_url
    if response.status_code == 201:
        return response.json()["id"], response.json()["source_url"]

    # 如果返回 502，尝试根据文件名查找媒体库中的图片
    elif response.status_code == 502:
        print("502 error, trying to find image by filename...")
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        # 添加 "-scaled" 到文件名
        filename = name + "-scaled" + ext
        search_url = f"{wp_url}/wp-json/wp/v2/media"
        params = {
            "search": filename  # 根据文件名搜索
        }
        search_response = requests.get(search_url, headers={"Authorization": token}, params=params)

        # 如果找到匹配的图片，返回第一个匹配项的 id 和 url
        if search_response.status_code == 200 and search_response.json():
            media_item = search_response.json()[0]
            return media_item["id"], media_item["source_url"]

        # 如果未找到，重新尝试上传
        else:
            with open(image_path, "rb") as file:
                retry_response = requests.post(url, headers=headers, data=file)
            if retry_response.status_code == 201:
                return retry_response.json()["id"], retry_response.json()["source_url"]
            else:
                raise Exception(f"Failed to upload image after retry: {retry_response.status_code} - {retry_response.text}")

    # 其他错误直接抛出异常
    else:
        raise Exception(f"Failed to upload image: {response.status_code} - {response.text}")
    
def process_markdown_images(markdown_content, wp_url, token, dir):
    """
    处理Markdown中的所有图片，下载并上传到WordPress，然后替换URL
    
    参数:
        markdown_content: Markdown文本内容
        wp_url: WordPress站点URL
        token: WordPress API认证token
        dir: 下载目录名称
    
    返回:
        处理后的Markdown内容
        图片信息字典 {原始引用: {url: str, id: int}}
    """
    # 创建按时间的目录
    download_dir = Config.ARTICLE_DIR / dir
    os.makedirs(download_dir, exist_ok=True)
    
    # 改进的正则表达式，同时匹配alt_text和url
    pattern = r'!\[(.*?)\]\((.*?)\)'  # 正确的模式
    matches = re.findall(pattern, markdown_content)
    image_refs = list(set(matches))  # 去重并转换为列表
    
    print(f"发现 {len(image_refs)} 个图片引用: {image_refs}")
    if not image_refs:
        return markdown_content, {}
    
    image_info = {}
    counter = 1
    COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"  # ComfyUI API地址
    # 直接检查服务是否可用
    try:
        response = requests.get(COMFYUI_API_URL, timeout=5)
        use_comfyui = response.status_code < 400  # 200-399状态码表示服务可用
    except (requests.ConnectionError, requests.Timeout):
        use_comfyui = False

    for alt_text, original_url in image_refs:
        try:
            # 下载图片
            keyword = alt_text if alt_text else "Global Map" # 默认关键词
            filename = f"{counter:02d}"
            # 根据服务是否运行选择不同的方法
            image_path = comfyui_picture(keyword, download_dir, filename, 1) if use_comfyui else getting_picture(keyword, download_dir, filename, 1)
        
            if not image_path:
                continue
                
            # 上传图片
            media_id, image_url = upload_image(wp_url, token, image_path)
            
            # 保存图片信息（使用完整原始引用作为键）
            original_ref = f"![{alt_text}]({original_url})"
            image_info[original_ref] = {
                "url": image_url,
                "id": media_id
            }
            
            counter += 1
            
        except Exception as e:
            print(f"处理图片 {original_url} 失败: {str(e)}")
            continue
    
    # 替换Markdown中的图片引用
    for original_ref, info in image_info.items():
        # 从原始引用中提取alt_text
        alt_match = re.match(r'!$$(.*?)$$', original_ref)
        alt_text = alt_match.group(1) if alt_match else ""
        
        markdown_content = markdown_content.replace(
            original_ref,
            f"![{alt_text}]({info['url']})"
        )
    
    return markdown_content, image_info

def markdown_to_html(md_text):
    """
    增强版 Markdown 转 HTML：
    1. 自动提取 YAML front matter（如标题、作者等）
    2. 统一注入样式（适配微信/WordPress）
    返回：
        - html_content (str): 处理后的HTML
        - metadata (dict): 从YAML解析的元数据（若无YAML则返回空字典）
    """
    # 分离 YAML front matter 和 Markdown 正文
    metadata = {}
    content = md_text
    
    if md_text.startswith('---'):
        parts = md_text.split('---', 2)
        if len(parts) > 2:
            try:
                metadata = yaml.safe_load(parts[1]) or {}  # 解析YAML
                content = parts[2].strip()                 # 剩余部分是正文
            except yaml.YAMLError as e:
                print(f"⚠️ YAML解析失败: {e}")

    # 转换Markdown为HTML
    html = markdown.markdown(content, extensions=['extra'])
    soup = BeautifulSoup(html, 'html.parser')

    # 统一样式表（兼顾微信和WordPress）
    unified_styles = {
        "h2": "color: #1a73e8; border-left: 4px solid #1a73e8; padding: 10px 15px; margin: 20px 0; font-size: 18px !important;",
        "p": "line-height: 1.6; margin: 10px 0;",
        "img": "max-width: 100%; height: auto; display: block; margin: 15px auto;",
        "ul": "padding-left: 20px;",
        "li": "margin: 5px 0;",
        "blockquote": "border-left: 3px solid #ddd; padding-left: 15px; color: #666;"
    }

    # 注入样式
    for tag, style in unified_styles.items():
        for element in soup.find_all(tag):
            element['style'] = style

    return str(soup), metadata  # 返回HTML和元数据

def convert_webp_to_jpg(directory):
    # 遍历指定目录
    for filename in os.listdir(directory):
        # 检查文件是否是.webp文件
        if filename.endswith(".webp"):
            # 构建完整的文件路径
            file_path = os.path.join(directory, filename)
            # 打开.webp文件
            with Image.open(file_path) as img:
                # 构建新的文件名和路径
                new_filename = filename[:-5] + ".jpg"
                new_file_path = os.path.join(directory, new_filename)
                # 将图像转换为RGB模式（因为JPG不支持透明通道）
                img_rgb = img.convert('RGB')
                # 保存为.jpg文件
                img_rgb.save(new_file_path)

            print(f"Converted {filename} to {new_filename}")

def init_chrome_and_login(creator_url, cookie_path, domain):
    """
    初始化 Chrome 并登录创作者平台（完整注释版）
    :param creator_url: 创作者中心首页 URL（如小红书或抖音）
    :param cookie_path: Cookie 文件路径
    :param domain: Cookie 的 domain（如 ".xiaohongshu.com" 或 "creator.douyin.com"）
    :return: 已登录的 driver 对象
    """
    # 定义chrome属性（保留原始注释）
    prefs = {
        'profile.default_content_setting_values': {
            'notifications': 2  # 隐藏chromedriver的通知
        },
        'credentials_enable_service': False,  # 禁用凭据管理服务
        'profile.password_manager_enabled': False  # 隐藏chromedriver自带的保存密码功能
    }

    # 创建一个配置对象（保留原始注释）
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])  # 设置为开发者模式
    options.add_argument('--disable-gpu')  # 谷歌文档提到需要加上这个属性来规避bug

    # 打开窗口（保留原始注释）
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    driver.implicitly_wait(5)

    # 访问创作者中心（保留原始注释）
    driver.get(url=creator_url)
    time.sleep(4)
    driver.delete_all_cookies()

    # 持久化登录（保留原始注释和异常处理）
    login = CookieLogin(cookie_path)
    cookies = login.load_cookies()
    try:
        for cookie in cookies:
            cookie_dict = {
                'domain': domain,
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                "expires": '',
                'path': '/',
                'httpOnly': False,
                'HostOnly': False,
                'Secure': False
            }
            print(cookie_dict)  # 保留原始调试输出
            driver.add_cookie(cookie_dict)
    except Exception as e:
        print(e)  # 保留原始异常打印

    time.sleep(5)
    driver.refresh()  # 保留原始刷新逻辑
    time.sleep(5)
    return driver

def xhs_video_upload(video_path, cover_path, your_title, your_desc, cookie_path):
    # 初始化 Chrome 并登录（带完整注释）
    driver = init_chrome_and_login(
        creator_url="https://creator.xiaohongshu.com",
        cookie_path=cookie_path,
        domain=".xiaohongshu.com"  # 小红书需要子域名
    )

    time.sleep(5)
    url = "https://creator.xiaohongshu.com/publish/publish"
    driver.get(url)

    time.sleep(2)
    
    # 视频上传
    video_upload = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
    video_upload.send_keys(video_path)
    # 等待视频上传完成
    print("视频上传完成！")
    time.sleep(2)

    # 点击设置封面
    set_cover = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//div[contains(@class, "text") and contains(text(), "设置封面")]'))
    )
    set_cover.click()
    time.sleep(5)
    
    # 封面上传
    cover_uplaod = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"][accept*="image"]'))
    )
    driver.execute_script("arguments[0].style.display = 'block';", cover_uplaod)
    cover_uplaod.send_keys(cover_path)
    print("封面上传完成！")
    time.sleep(5)

    confirm_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="mojito-btn-container"]/button[2]'))
    )
    confirm_btn.click()
    print("封面设置完成！")
    time.sleep(2)
    
    # 输入标题和描述
    title_input = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input.d-text[placeholder='填写标题会有更多赞哦～']"))
    )
    driver.execute_script("arguments[0].focus();", title_input)  # 强制聚焦
    title_input.clear()
    title_input.send_keys(your_title)
    print("标题已填写！")

    desc_input = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ql-editor.ql-blank[contenteditable='true']"))
    )
    desc_input.clear()
    desc_input.send_keys(your_desc)
    print("描述已填写！")
    time.sleep(2)
    
    # 点击发布
    driver.find_element(By.XPATH, '//*[@id="publish-container"]/div[2]/div[2]/div/button[1]/div/span').click()
    print("视频发布成功！")
    time.sleep(10)
    driver.close()
    driver.quit()

def dy_video_upload(video_path, cover_path, your_title, your_desc, cookie_path):
    # 初始化 Chrome 并登录（带完整注释）
    driver = init_chrome_and_login(
        creator_url="https://creator.douyin.com",
        cookie_path=cookie_path,
        domain="creator.douyin.com"  # 抖音只需主域名
    )
    time.sleep(5)
    url = "https://creator.douyin.com/creator-micro/content/upload"
    driver.get(url)

    time.sleep(2)
    print("刷新成功")

    # 视频上传
    video_upload = driver.find_element(By.XPATH, '//input[@type="file" and contains(@accept, "video/") and @style="display: none;"]')
    video_upload.send_keys(video_path)
    # 等待视频上传完成
    print("视频上传完成！")
    time.sleep(10)

    # 点击设置封面
    set_cover = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, '//div[contains(@class, "filter-")]//div[text()="选择封面"]'))
    )
    set_cover.click()
    time.sleep(5)

    # 封面上传
    cover_uplaod = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR,  'input.semi-upload-hidden-input[type="file"]'))
    )
    driver.execute_script("arguments[0].style.display = 'block';", cover_uplaod)
    cover_uplaod.send_keys(cover_path)
    print("封面上传完成！")
    time.sleep(5)

    confirm_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "semi-button-primary")]/span[text()="完成"]/..'))
    )
    confirm_btn.click()
    print("封面设置完成！")
    time.sleep(2)
    
    # 输入标题和描述
    title_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//input[contains(@class, "semi-input") and @placeholder="填写作品标题，为作品获得更多流量"]'))
    )
    driver.execute_script("arguments[0].focus();", title_input)  # 强制聚焦
    title_input.clear()
    title_input.send_keys(your_title)
    print("标题已填写！")

    desc_input = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.editor-kit-container[data-placeholder="添加作品简介"]'))
    )
    desc_input.clear()
    desc_input.send_keys(your_desc)
    print("描述已填写！")
    time.sleep(2)
    
    # 点击发布
    driver.find_element(By.XPATH, '//button[contains(@class, "primary-") and text()="发布"]').click()

    print("视频发布成功！")
    time.sleep(10)
    driver.close()
    driver.quit()

def sph_video_upload(video_path, cover_path, your_title, your_desc, cookie_path):
    # 初始化 Chrome 并登录微信视频号平台（保留全部原始注释）
    driver = init_chrome_and_login(
        creator_url="https://channels.weixin.qq.com",
        cookie_path=cookie_path,
        domain="channels.weixin.qq.com"  # 微信视频号专用domain
    )

    time.sleep(5)
    url = "https://channels.weixin.qq.com/platform"
    # url = "https://channels.weixin.qq.com/platform/post/create"
    driver.get(url)

    time.sleep(2)
    print("刷新成功")

    # 视频上传
    # video_upload = driver.find_element(By.XPATH, '//input[@type="file" and @accept="video/mp4,video/x-m4v,video/*"]')
    video_upload = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
    video_upload.send_keys(video_path)
    # 等待视频上传完成
    print("视频上传完成！")
    time.sleep(10)

    # 点击设置封面
    set_cover = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, '//div[contains(@class, "filter-")]//div[text()="选择封面"]'))
    )
    set_cover.click()
    time.sleep(5)

    # 封面上传
    cover_uplaod = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR,  'input.semi-upload-hidden-input[type="file"]'))
    )
    driver.execute_script("arguments[0].style.display = 'block';", cover_uplaod)
    cover_uplaod.send_keys(cover_path)
    print("封面上传完成！")
    time.sleep(5)

    confirm_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "semi-button-primary")]/span[text()="完成"]/..'))
    )
    confirm_btn.click()
    print("封面设置完成！")
    time.sleep(2)
    
    # 输入标题和描述
    title_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//input[contains(@class, "semi-input") and @placeholder="填写作品标题，为作品获得更多流量"]'))
    )
    driver.execute_script("arguments[0].focus();", title_input)  # 强制聚焦
    title_input.clear()
    title_input.send_keys(your_title)
    print("标题已填写！")

    desc_input = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.editor-kit-container[data-placeholder="添加作品简介"]'))
    )
    desc_input.clear()
    desc_input.send_keys(your_desc)
    print("描述已填写！")
    time.sleep(2)
    
    # 点击发布
    driver.find_element(By.XPATH, '//button[contains(@class, "primary-") and text()="发布"]').click()

    print("视频发布成功！")
    time.sleep(10)
    driver.close()
    driver.quit()

def main():
    # 输出目录
    pass

if __name__ == "__main__":
    main()