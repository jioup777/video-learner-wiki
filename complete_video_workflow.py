#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书视频学习助手 - 完整流程脚本

功能：下载视频 → ASR 转录 → 笔记生成 → 飞书上传播

使用方法：
  python3 complete_video_workflow.py "视频链接" "视频标题（可选）"

示例：
  python3 complete_video_workflow.py "https://www.bilibili.com/video/BVxxxxx"
  python3 complete_video_workflow.py "https://www.douyin.com/video/xxxxx" "我的视频"
"""

import os
import sys
import subprocess
import requests
import json
import time
from pathlib import Path

# ==================== 配置 ====================
# 飞书知识库配置
MAIN_DOCUMENT_TOKEN = "LrTAdVQEnoKG1nxxKO5c5JjCn6p"  # 主文档 Token
FEISHU_SPACE_ID = "7566441763399581724"              # 知识库空间 ID

# ASR 配置
ASR_PROVIDER = "aliyun"  # 只使用阿里云 ASR
ALIYUN_ASR_API_KEY = os.getenv("ALIYUN_ASR_API_KEY", "")
ASR_MODEL = os.getenv("ASR_MODEL", "qwen3-asr-flash")  # 阿里云模型

# GLM 配置
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
NOTE_ENGINE = os.getenv("NOTE_ENGINE", "glm")  # glm | smart

# 工作目录
WORK_DIR = Path.home() / ".openclaw" / "workspace-video-learner"
SCRIPT_DIR = WORK_DIR / "scripts"
INBOX_DIR = WORK_DIR / "knowledge" / "inbox"
VIDEO_DIR = INBOX_DIR / "video" / "raw"
TRANS_DIR = INBOX_DIR / "video" / "transcripts"

# ==================== 日志函数 ====================
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'

def log_info(msg):
    print(f"{GREEN}[INFO]{NC} {msg}")

def log_step(msg):
    print(f"{BLUE}[STEP]{NC} {msg}")

def log_warn(msg):
    print(f"{YELLOW}[WARN]{NC} {msg}")

def log_error(msg):
    print(f"{RED}[ERROR]{NC} {msg}")

# ==================== 步骤 1: 平台识别与下载 ====================
def detect_platform_and_download(video_url, title=""):
    """
    识别平台并下载音频/字幕
    """
    log_step(f"📥 步骤 1/5: 识别平台并下载")

    yt_dlp_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    # 如果有 B 站 cookies，添加到配置
    cookies_file = os.getenv("BILIBILI_COOKIES_PATH")
    if cookies_file and os.path.exists(cookies_file):
        yt_dlp_opts["cookies"] = cookies_file

    # 如果没有标题，使用 URL 作为默认标题
    if not title:
        title = video_url.split("/")[-1][:50]  # 取 URL 最后一部分作为临时标题

    # 根据 URL 判断平台
    if "bilibili.com" in video_url:
        platform = "bilibili"
        # 下载音频
        output_template = str(VIDEO_DIR / "%(id)s.%(ext)s")
        yt_dlp_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        yt_dlp_opts["output"] = output_template
        yt_dlp_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]

    elif "youtube.com" in video_url or "youtu.be" in video_url:
        platform = "youtube"
        # 下载音频
        output_template = str(VIDEO_DIR / "%(id)s.%(ext)s")
        yt_dlp_opts["format"] = "bestaudio/best"
        yt_dlp_opts["output"] = output_template
        yt_dlp_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]

    elif "douyin.com" in video_url:
        platform = "douyin"
        # 下载音频
        output_template = str(VIDEO_DIR / "%(id)s.%(ext)s")
        yt_dlp_opts["format"] = "bestaudio/best"
        yt_dlp_opts["output"] = output_template
        yt_dlp_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]

    else:
        log_error(f"不支持的平台: {platform}")
        return None, None

    try:
        cmd = ["yt-dlp", video_url]
        if yt_dlp_opts:
            cmd.extend([f"--{k}" if isinstance(k, str) else f"--{k}" for k in yt_dlp_opts.keys()])

        log_info(f"下载命令: {' '.join(cmd[:3])} ...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            log_error(f"下载失败: {result.stderr}")
            return None, None

        # 查找下载的文件
        audio_files = list(VIDEO_DIR.glob("*.mp3")) + list(VIDEO_DIR.glob("*.m4a"))
        if not audio_files:
            log_error("未找到下载的音频文件")
            return None, None

        audio_file = audio_files[0]
        log_info(f"✓ 下载成功: {audio_file.name}")
        log_info(f"  文件大小: {audio_file.stat().st_size / 1024 / 1024:.2f} MB")

        return platform, audio_file.name

    except Exception as e:
        log_error(f"下载失败: {e}")
        return None, None


# ==================== 步骤 2: ASR 转录 ====================
def asr_transcribe(audio_file, platform="unknown"):
    """
    使用阿里云 ASR 转录音频
    """
    log_step(f"🎤 步骤 2/5: ASR 转录 ({platform})")

    # 使用阿里云 ASR
    log_info("使用阿里云 qwen3-asr-flash 模型")
    if not ALIYUN_ASR_API_KEY:
        log_error("未设置 ALIYUN_ASR_API_KEY")
        return None

    try:
        # 读取音频文件
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        # 调用阿里云 API
        url = "https://dashscope.aliyuncs.com/api/v1/services/audio/transcription/tasks"
        headers = {
            "Authorization": f"Bearer {ALIYUN_ASR_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": ASR_MODEL,
            "input": {
                "audio": audio_data
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if response.status_code != 200 or data.get("code") != 0:
            log_error(f"阿里云 ASR 调用失败: {data.get('message', 'Unknown error')}")
            return None

        # 等待任务完成
        task_id = data["data"]["task_id"]
        log_info(f"任务 ID: {task_id}")

        max_wait = 300  # 最大等待 5 分钟
        waited = 0
        while waited < max_wait:
            time.sleep(10)
            waited += 10

            # 查询任务状态
            query_url = f"https://dashscope.aliyuncs.com/api/v1/services/audio/transcription/tasks/{task_id}"
            response = requests.get(query_url, headers={"Authorization": f"Bearer {ALIYUN_ASR_API_KEY}"})
            data = response.json()

            if data.get("code") != 0:
                log_error(f"查询任务失败: {data.get('message')}")
                return None

            status = data["data"]["output"]["status"]
            log_info(f"状态: {status}")

            if status == "SUCCEEDED":
                transcript_text = data["data"]["output"]["result"]["text"]
                # 保存转录结果
                base_name = audio_file.stem
                transcript_file = VIDEO_DIR / f"{base_name}.txt"
                with open(transcript_file, "w", encoding="utf-8") as f:
                    f.write(transcript_text)
                log_info(f"✓ 转录成功: {transcript_file.name}")
                return str(transcript_file)

            elif status == "FAILED":
                log_error(f"转录失败: {data['data']['output'].get('message', 'Unknown error')}")
                return None

        log_error("转录超时")
        return None

    except Exception as e:
        log_error(f"ASR 转录失败: {e}")
        return None


# ==================== 步骤 3: 笔记生成 ====================
def generate_note(transcript_file, title):
    """
    使用 GLM-4-Flash 生成笔记
    """
    log_step(f"📝 步骤 3/5: 生成笔记 ({title})")

    if not GLM_API_KEY:
        log_error("未设置 GLM_API_KEY")
        return None

    try:
        # 读取转录内容
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript = f.read()

        # 调用 GLM-4-Flash API
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Authorization": f"Bearer {GLM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "glm-4-flash",
            "messages": [
                {
                    "role": "system",
                    "content": """你是一个专业的视频学习笔记生成助手。请根据视频转录内容生成结构化笔记，包含以下部分：

1. 核心主题：视频的核心内容概括（1-2句）
2. 核心观点：3-5 条关键观点，每条观点独立成行
3. 典型案例：2-3 个具体案例
4. 识别方法：如何识别相关概念或问题
5. 防骗建议：如果涉及防骗内容，列出识别骗局的方法
6. 核心金句：5 条金句总结

格式要求：
- 使用 Markdown 格式
- 每个部分用 ## 标题
- 每条观点用 - 开头
- 保持简洁清晰
"""
                },
                {
                    "role": "user",
                    "content": f"视频标题：{title}\n\n视频内容：\n{transcript}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if response.status_code != 200 or data.get("choices") is None:
            log_error(f"GLM API 调用失败: {data.get('message', 'Unknown error')}")
            return None

        # 提取笔记内容
        note_content = data["choices"][0]["message"]["content"]

        # 保存笔记
        base_name = Path(transcript_file).stem
        note_file = VIDEO_DIR / f"{base_name}_note.md"
        with open(note_file, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{note_content}")

        log_info(f"✓ 笔记生成成功: {note_file.name}")
        return str(note_file), note_content

    except Exception as e:
        log_error(f"笔记生成失败: {e}")
        return None


# ==================== 步骤 4: 飞书上传播 ====================
def upload_to_feishu(note_file, title, note_content):
    """
    将笔记上传到飞书主文档下的子文档
    """
    log_step(f"📤 步骤 4/5: 飞书上传播")

    if not GLM_API_KEY:
        log_error("未设置 GLM_API_KEY")
        return False

    try:
        # 调用飞书 API 创建节点
        api_url = "https://open.feishu.cn/open-apis/wiki/v2/nodes"

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "node": {
                "space_id": FEISHU_SPACE_ID,
                "parent_node_token": MAIN_DOCUMENT_TOKEN,  # 在主文档下创建子文档
                "title": title,
                "obj_type": "docx",
                "page_title": title,
                "content": note_content
            }
        }

        response = requests.post(api_url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                node = data["data"]["node"]
                node_token = node["node_token"]
                doc_token = node["obj_token"]
                link = f"https://vicyrpffceo.feishu.cn/wiki/{doc_token}"

                log_info(f"✓ 上传成功!")
                log_info(f"  节点 Token: {node_token}")
                log_info(f"  文档 Token: {doc_token}")
                log_info(f"  文档链接: {link}")

                return True, link
            else:
                log_error(f"飞书 API 错误: {data.get('msg')}")
                return False, None
        else:
            log_error(f"HTTP 错误: {response.status_code}")
            log_error(f"响应内容: {response.text}")
            return False, None

    except Exception as e:
        log_error(f"上传失败: {e}")
        return False, None


# ==================== 步骤 5: 清理与总结 ====================
def cleanup(transcript_file):
    """
    清理临时文件
    """
    log_step(f"🧹 步骤 5/5: 清理临时文件")

    try:
        # 删除转录文件
        if transcript_file and os.path.exists(transcript_file):
            os.remove(transcript_file)
            log_info(f"✓ 已删除转录文件: {transcript_file}")

        # 保留音频和笔记文件，供后续查看
        log_info(f"✓ 保留音频和笔记文件供查看")
        log_info(f"  音频: {Path(transcript_file).parent / Path(transcript_file).stem + '.mp3'}" if transcript_file else "  音频: (未下载)")
        log_info(f"  笔记: {transcript_file}")

    except Exception as e:
        log_warn(f"清理失败: {e}")


# ==================== 主函数 ====================
def main():
    if len(sys.argv) < 2:
        print("用法: python3 complete_video_workflow.py <视频链接> [视频标题]")
        print("\n示例:")
        print("  python3 complete_video_workflow.py \"https://www.bilibili.com/video/BVxxxxx\"")
        print("  python3 complete_video_workflow.py \"https://www.douyin.com/video/xxxxx\" \"我的视频\"")
        sys.exit(1)

    video_url = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else ""

    # 检查依赖
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except:
        log_error("未安装 yt-dlp，请先安装: pip install yt-dlp")
        sys.exit(1)

    # 创建必要目录
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    TRANS_DIR.mkdir(parents=True, exist_ok=True)

    # 执行完整流程
    try:
        # 步骤 1: 下载
        platform, audio_file = detect_platform_and_download(video_url, title)

        if not audio_file:
            log_error("下载失败，流程终止")
            sys.exit(1)

        # 步骤 2: ASR 转录
        transcript_file = asr_transcribe(audio_file, platform)
        if not transcript_file:
            log_error("转录失败，流程终止")
            sys.exit(1)

        # 步骤 3: 生成笔记
        note_result = generate_note(transcript_file, title)
        if not note_result:
            log_error("笔记生成失败，流程终止")
            sys.exit(1)

        note_file, note_content = note_result

        # 步骤 4: 飞书上传播
        success, link = upload_to_feishu(note_file, title, note_content)
        if not success:
            log_error("飞书上传播失败，流程终止")
            sys.exit(1)

        # 步骤 5: 清理
        cleanup(transcript_file)

        # 输出总结
        print(f"\n{'='*60}")
        log_info(f"✓ 完整流程完成!")
        log_info(f"  视频标题: {title}")
        log_info(f"  视频链接: {video_url}")
        log_info(f"  文档链接: {link}")
        log_info(f"{'='*60}")

    except KeyboardInterrupt:
        log_warn("\n流程被用户中断")
        sys.exit(1)
    except Exception as e:
        log_error(f"流程异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
s, link = upload_to_feishu(note_file, title, note_content)
        if not success:
            log_error("飞书上传播失败，流程终止")
            sys.exit(1)

        # 步骤 5: 清理
        cleanup(transcript_file)

        # 输出总结
        print(f"\n{'='*60}")
        log_info(f"✓ 完整流程完成!")
        log_info(f"  视频标题: {title}")
        log_info(f"  视频链接: {video_url}")
        log_info(f"  文档链接: {link}")
        log_info(f"{'='*60}")

    except KeyboardInterrupt:
        log_warn("\n流程被用户中断")
        sys.exit(1)
    except Exception as e:
        log_error(f"流程异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
