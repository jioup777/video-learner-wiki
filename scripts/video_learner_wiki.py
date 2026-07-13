#!/usr/bin/env python3
"""
Video Learner Wiki版本
从视频生成转录文本，笔记生成由Agent大模型完成

核心改进：
- 不再依赖GLM API生成笔记
- Agent直接用当前对话大模型生成笔记
- 脚本只负责：下载音频 + ASR转录
"""

import os
import sys
import re
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')  # 明确从项目根加载 .env(不依赖 cwd)

# 导入原有模块
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace-video-learner/scripts'))
from downloaders.bilibili import BilibiliDownloader
from downloaders.youtube import YouTubeDownloader
from downloaders.douyin import DouyinDownloader
from downloaders.xiaohongshu import XiaoHongShuDownloader
from asr_aliyun import AliyunASR
from metadata import build_metadata
from summarizer import summarize


@dataclass
class ProcessResult:
    title: str
    video_id: str
    platform: str
    video_url: str = ""
    audio_file: Optional[str] = None
    transcript: Optional[str] = None
    transcript_file: Optional[str] = None
    errors: list = field(default_factory=list)


class VideoLearnerWiki:
    """视频转录器（Agent负责笔记生成和Wiki上传）"""
    
    PLATFORM_HANDLERS = {
        'bilibili': BilibiliDownloader,
        'youtube': YouTubeDownloader,
        'douyin': DouyinDownloader,
        'xiaohongshu': XiaoHongShuDownloader,
    }
    
    def __init__(self):
        # ASR: 优先 Groq Whisper（免费），回退阿里云
        asr_provider = os.getenv('ASR_PROVIDER', 'groq').lower()
        if asr_provider == 'groq' and os.getenv('GROQ_API_KEY'):
            from asr_groq import GroqASR
            self.asr = GroqASR()  # 无参→自动读 GROQ_API_KEY+GROQ_API_KEYS 多key轮换
            self.log('INFO', 'ASR引擎: Groq Whisper (免费)')
        else:
            self.asr = AliyunASR(api_key=os.getenv('ALIYUN_ASR_API_KEY') or os.getenv('DASHSCOPE_API_KEY'))
            self.log('INFO', 'ASR引擎: 阿里云')
        
        self.workspace = Path(os.getenv('WORKSPACE', Path.home() / '.openclaw' / 'workspace-video-learner')).expanduser().resolve()
        self.output_dir = self.workspace / 'output'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def detect_platform(self, url: str) -> tuple:
        """识别平台和视频ID"""
        url = url.strip()
        
        if 'bilibili.com' in url or 'b23.tv' in url:
            video_id = self._extract_bvid(url)
            return 'bilibili', video_id
        elif 'youtube.com' in url or 'youtu.be' in url:
            video_id = self._extract_youtube_id(url)
            return 'youtube', video_id
        elif 'douyin.com' in url or 'v.douyin.com' in url:
            video_id = self._extract_douyin_id(url)
            return 'douyin', video_id
        elif 'xiaohongshu.com' in url or 'xhslink.com' in url:
            return 'xiaohongshu', self._extract_xhs_id(url)
        else:
            raise ValueError(f"不支持的平台: {url}")
    
    def _extract_bvid(self, url: str) -> str:
        match = re.search(r'BV([a-zA-Z0-9]+)', url)
        return match.group(0) if match else "unknown"
    
    def _extract_youtube_id(self, url: str) -> str:
        patterns = [
            r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return "unknown"
    
    def _extract_douyin_id(self, url: str) -> str:
        """提取抖音视频ID。

        优先匹配长链 /video/<数字>(注:group(1)取纯数字, 非 group(0) 的 '/video/xxx');
        短链 v.douyin.com 跟随重定向解析后再匹配;
        兜底用短链码(加 dy_ 前缀, 区分于纯数字ID)。失败返回 unknown。
        """
        # 长链: https://www.douyin.com/video/7619936329945615616
        m = re.search(r'/video/(\d+)', url)
        if m:
            return m.group(1)
        # 短链: https://v.douyin.com/ahoP0DhfTac/
        if 'v.douyin.com' in url:
            resolved = self._resolve_douyin_short_url(url)
            m = re.search(r'/video/(\d+)', resolved)
            if m:
                return m.group(1)
            m = re.search(r'v\.douyin\.com/([a-zA-Z0-9]+)', resolved)
            if m:
                return f"dy_{m.group(1)}"
        return "unknown"

    def _resolve_douyin_short_url(self, url: str) -> str:
        """跟随抖音短链重定向拿完整URL(curl -L); 失败/超时返回原url(fail-soft)。

        注: -o 必须用 os.devnull(Windows='nul'); 写 '/dev/null' 会让 curl rc=23
        (Failed writing body), 历史上这就是抖音短链 video_id=unknown 的根因。
        """
        import subprocess
        try:
            cmd = ['curl', '-s', '-L', '--max-redirs', '5', '--max-time', '10',
                   '-o', os.devnull, '-w', '%{url_effective}', url]
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=15)
            if r.stdout.strip() and '://' in r.stdout:
                return r.stdout.strip()
        except Exception:
            pass
        return url

    def _extract_xhs_id(self, url: str) -> str:
        """提取小红书笔记ID(格式多变): explore/note/discovery-item/xhslink。"""
        for pat in [r'/(?:explore|note)/([a-zA-Z0-9]+)',
                    r'/discovery/item/([a-zA-Z0-9]+)',
                    r'xhslink\.com/([a-zA-Z0-9]+)']:
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return "unknown"

    def log(self, level: str, message: str):
        colors = {
            'INFO': '\033[0;32m',
            'WARN': '\033[1;33m',
            'ERROR': '\033[0;31m',
            'STEP': '\033[0;34m',
        }
        nc = '\033[0m'
        print(f"{colors.get(level, '')}[{level}]{nc} {message}", file=sys.stderr)
    
    def process(self, url: str) -> ProcessResult:
        """处理视频：下载 + ASR转录，返回转录文本供Agent生成笔记"""
        start_time = datetime.now()
        result = ProcessResult(title="", video_id="", platform="", video_url=url)
        
        # Step 1: 平台识别
        self.log("STEP", "步骤 1/3: 平台识别...")
        platform, video_id = self.detect_platform(url)
        result.platform = platform
        result.video_id = video_id
        self.log("INFO", f"平台: {platform}, ID: {video_id}")
        
        # Step 2: 下载
        self.log("STEP", "步骤 2/3: 下载视频/获取字幕...")
        handler_class = self.PLATFORM_HANDLERS.get(platform)
        if not handler_class:
            raise ValueError(f"不支持的平台: {platform}")
        
        handler = handler_class()
        download_result = handler.process(url)
        
        result.title = download_result.title
        result.audio_file = download_result.audio_file
        result.subtitle_text = getattr(download_result, 'subtitle_text', None)
        needs_transcription = getattr(download_result, 'needs_transcription', True)
        
        # Step 3: ASR转录
        self.log("STEP", "步骤 3/3: ASR转录...")
        if result.subtitle_text:
            result.transcript = result.subtitle_text
            self.log("INFO", "✓ 使用字幕文本，跳过ASR")
        elif result.audio_file:
            transcript = self.asr.transcribe(result.audio_file)
            result.transcript = transcript
            self.log("INFO", f"✓ 转录完成 ({len(transcript)} 字符)")
        else:
            raise ValueError("无法获取转录文本：没有音频文件也没有字幕")
        
        # ===== 组装标准化 artifact(7层 metadata + 5文件契约) =====
        # topic 待 CC 端归类填, archived_by=openclaw(OpenClaw 产原料)
        artifact_dir = self.workspace / "downloads" / video_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # transcript.txt
        transcript_path = artifact_dir / "transcript.txt"
        transcript_path.write_text(result.transcript or "", encoding="utf-8")
        result.transcript_file = str(transcript_path)

        # post_caption.txt(从 download_result.caption; 抖音需 Task 4b f2 探查后才有)
        caption = getattr(download_result, "caption", None)
        (artifact_dir / "post_caption.txt").write_text(
            caption.raw_text if caption else "", encoding="utf-8")

        # summary(fail-safe, 失败返回空串不阻塞)
        summary = summarize(result.transcript or "", result.title)

        # metadata.json
        import json
        metadata = build_metadata(
            platform=result.platform, video_id=result.video_id, url=url,
            title=result.title, creator=getattr(download_result, "creator", None),
            duration_sec=getattr(download_result, "duration_sec", None),
            description=getattr(download_result, "description", None),
            tags=getattr(download_result, "tags", []) or [],
            view_count=getattr(download_result, "view_count", None),
            like_count=getattr(download_result, "like_count", None),
            comment_count=getattr(download_result, "comment_count", None),
            caption=caption,
            transcript_source=("subtitle" if result.subtitle_text else type(self.asr).__name__.lower()),
            transcript_text=result.transcript or "",
            summary=summary,
            topic=None, subtopic=[], topic_source="pending",  # CC 端归类填
            archived_by="openclaw",
            video_path=getattr(download_result, "video_file", "") or "",
            audio_path=result.audio_file or "",
            route=result.platform,
            asr_backend=type(self.asr).__name__,
            asr_status="ok",
            transcript_path=str(transcript_path),
            raw=getattr(download_result, "raw", {}) or {},
        )
        (artifact_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        # 清理临时音频(artifact 只留 transcript/post_caption/metadata;
        # video/audio 文件路径记录在 metadata.download, 文件本身按需保留)
        if result.audio_file and Path(result.audio_file).exists():
            try:
                Path(result.audio_file).unlink()
            except Exception:
                pass

        elapsed = (datetime.now() - start_time).total_seconds()
        self.log("INFO", f"✅ artifact 产出完成, 耗时 {elapsed:.1f} 秒: {artifact_dir}")

        # 输出 JSON 供 CC 端 fetch_artifact.sh 解析 artifact_dir
        output = {
            "artifact_dir": str(artifact_dir),
            "video_id": result.video_id,
            "platform": result.platform,
            "title": result.title,
        }
        print(json.dumps(output, ensure_ascii=False))

        return result


def main():
    parser = argparse.ArgumentParser(
        description='Video Learner - 视频转录器（笔记由Agent生成）',
        epilog="""
示例:
  python video_learner_wiki.py "https://www.bilibili.com/video/BVxxxxx"
  python video_learner_wiki.py "https://www.youtube.com/watch?v=xxxxx"

环境变量:
  GROQ_API_KEY          - Groq Whisper API密钥 (优先)
  ALIYUN_ASR_API_KEY   - 阿里云ASR API密钥 (备选)
  ASR_PROVIDER          - asr引擎: groq(默认) | aliyun
        """
    )
    parser.add_argument('url', help='视频链接')
    
    args = parser.parse_args()
    
    learner = VideoLearnerWiki()
    learner.process(args.url)


if __name__ == "__main__":
    main()
