#!/usr/bin/env python3
"""
Video Learner - 统一视频学习笔记生成器
支持平台: Bilibili, YouTube, Douyin

流程:
1. 平台识别
2. 下载/字幕获取
3. ASR转录(如需要)
4. GLM笔记生成
5. 飞书上传
"""

import os
import sys
import re
import argparse
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from downloaders.bilibili import BilibiliDownloader
from downloaders.youtube import YouTubeDownloader
from downloaders.douyin import DouyinDownloader
from asr_aliyun import AliyunASR
from note_generator import GLMNoteGenerator
from feishu_uploader import FeishuUploader


@dataclass
class ProcessResult:
    title: str
    video_id: str
    platform: str
    audio_file: Optional[str] = None
    subtitle_file: Optional[str] = None
    subtitle_text: Optional[str] = None
    transcript: Optional[str] = None
    note_file: Optional[str] = None
    feishu_link: Optional[str] = None
    needs_transcription: bool = True
    errors: list = field(default_factory=list)


class VideoLearner:
    PLATFORM_HANDLERS = {
        'bilibili': BilibiliDownloader,
        'youtube': YouTubeDownloader,
        'douyin': DouyinDownloader,
    }
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.asr = AliyunASR(api_key=os.getenv('ALIYUN_ASR_API_KEY') or os.getenv('DASHSCOPE_API_KEY'))
        self.note_gen = GLMNoteGenerator(api_key=os.getenv('GLM_API_KEY'))
        self._uploader = None
        self.workspace = Path(os.getenv('WORKSPACE', Path.home() / '.openclaw' / 'workspace-video-learner'))
        self.output_dir = self.workspace / 'output'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def uploader(self):
        """获取飞书上传器（Wiki 版本）"""
        if self._uploader is None:
            self._uploader = FeishuUploader(
                space_id=os.getenv('FEISHU_SPACE_ID'),
                parent_token=os.getenv('FEISHU_PARENT_TOKEN')
            )
        return self._uploader
    
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
            return 'douyin', url
        
        else:
            raise ValueError(f"不支持的平台: {url}")
    
    def _extract_bvid(self, url: str) -> str:
        """提取B站BV号"""
        match = re.search(r'BV[a-zA-Z0-9]+', url)
        if match:
            return match.group(0)
        match = re.search(r'/video/(BV[a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        return "unknown"
    
    def _extract_youtube_id(self, url: str) -> str:
        """提取YouTube视频ID"""
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
    
    def log(self, level: str, message: str):
        """统一日志输出"""
        colors = {
            'INFO': '\033[0;32m',
            'WARN': '\033[1;33m',
            'ERROR': '\033[0;31m',
            'STEP': '\033[0;34m',
        }
        nc = '\033[0m'
        print(f"{colors.get(level, '')}[{level}]{nc} {message}", file=sys.stderr)
    
    def process(self, url: str, skip_upload: bool = False) -> ProcessResult:
        """主处理流程"""
        start_time = datetime.now()
        result = ProcessResult(title="", video_id="", platform="")
        
        try:
            # Step 1: 平台识别
            self.log("STEP", "步骤 1/5: 平台识别...")
            platform, video_id = self.detect_platform(url)
            result.platform = platform
            result.video_id = video_id
            self.log("INFO", f"平台: {platform}, ID: {video_id}")
            
            # Step 2: 下载/获取字幕
            self.log("STEP", "步骤 2/5: 下载视频/获取字幕...")
            handler_class = self.PLATFORM_HANDLERS.get(platform)
            if not handler_class:
                raise ValueError(f"不支持的平台: {platform}")
            
            handler = handler_class()
            download_result = handler.process(url)
            
            result.title = download_result.title
            result.audio_file = download_result.audio_file
            result.subtitle_file = download_result.subtitle_file
            result.subtitle_text = download_result.subtitle_text
            result.needs_transcription = download_result.needs_transcription
            
            if download_result.subtitle_text:
                self.log("INFO", f"✓ 获取到字幕文本 ({len(download_result.subtitle_text)} 字符)")
            elif download_result.audio_file:
                self.log("INFO", f"✓ 音频已下载: {download_result.audio_file}")
            
            # Step 3: ASR转录(如需要)
            if result.needs_transcription and result.audio_file:
                self.log("STEP", "步骤 3/5: ASR转录...")
                transcript = self.asr.transcribe(result.audio_file)
                result.transcript = transcript
                self.log("INFO", f"✓ 转录完成 ({len(transcript)} 字符)")
            elif result.subtitle_text:
                result.transcript = result.subtitle_text
                self.log("INFO", "✓ 使用字幕文本，跳过ASR")
            else:
                raise ValueError("无法获取转录文本：没有音频文件也没有字幕")
            
            # Step 4: 生成笔记
            self.log("STEP", "步骤 4/5: 生成学习笔记...")
            note_content = self.note_gen.generate(result.transcript, result.title)
            
            note_file = self.output_dir / f"{platform}_{video_id}_note.md"
            with open(note_file, 'w', encoding='utf-8') as f:
                f.write(note_content)
            result.note_file = str(note_file)
            self.log("INFO", f"✓ 笔记已生成: {note_file.name}")
            
            # Step 5: 上传飞书（在 wiki 节点下创建子文档）
            if not skip_upload:
                self.log("STEP", "步骤 5/5: 上传飞书 Wiki...")
                
                # 使用 OpenClaw 飞书工具创建 wiki 节点
                import subprocess
                import json
                import tempfile
                
                space_id = os.getenv('FEISHU_SPACE_ID')
                parent_token = os.getenv('FEISHU_PARENT_TOKEN')
                
                if not space_id or not parent_token:
                    raise ValueError("未配置飞书空间ID或父节点Token")
                
                # 创建临时文件保存内容
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                    f.write(note_content)
                    temp_file = f.name
                
                try:
                    # 使用 OpenClaw 工具创建 wiki 节点并写入内容
                    # 注意：这需要在 OpenClaw 运行时环境中执行
                    # 实际使用时，video_learner 应该作为 OpenClaw agent 运行
                    
                    # 备选方案：直接使用 FeishuUploader
                    from feishu_uploader import FeishuUploader
                    uploader = FeishuUploader(space_id=space_id, parent_token=parent_token)
                    feishu_link = uploader.upload(note_content, result.title)
                    result.feishu_link = feishu_link
                    self.log("INFO", f"✓ 飞书 Wiki: {feishu_link}")
                    
                finally:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
            else:
                self.log("INFO", "跳过飞书上传")
            
            # 清理临时文件
            self._cleanup(result)
            
            # 完成
            elapsed = (datetime.now() - start_time).total_seconds()
            self.log("INFO", f"✅ 处理完成，耗时 {elapsed:.1f} 秒")
            
        except Exception as e:
            self.log("ERROR", str(e))
            result.errors.append(str(e))
            raise
        
        return result
    
    def _cleanup(self, result: ProcessResult):
        """清理临时文件"""
        if result.audio_file and Path(result.audio_file).exists():
            try:
                Path(result.audio_file).unlink()
            except:
                pass
        
        if result.subtitle_file and Path(result.subtitle_file).exists():
            try:
                Path(result.subtitle_file).unlink()
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description='Video Learner - 视频学习笔记生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python video_learner.py "https://www.bilibili.com/video/BVxxxxx"
  python video_learner.py "https://www.youtube.com/watch?v=xxxxx"
  python video_learner.py "https://v.douyin.com/xxxxx/"
  python video_learner.py "url" --no-upload  # 不上传飞书

环境变量:
  GLM_API_KEY          - GLM API密钥 (必需)
  ALIYUN_ASR_API_KEY   - 阿里云ASR API密钥 (必需)
  FEISHU_SPACE_ID      - 飞书空间ID (必需)
  FEISHU_PARENT_TOKEN  - 飞书父节点Token (必需)
  BILIBILI_COOKIES     - B站cookies文件路径 (可选)
  WORKSPACE            - 工作目录 (可选)
        """
    )
    parser.add_argument('url', help='视频链接')
    parser.add_argument('--no-upload', action='store_true', help='不上传飞书')
    parser.add_argument('--version', action='version', version='Video Learner 2.0')
    
    args = parser.parse_args()
    
    learner = VideoLearner()
    
    try:
        result = learner.process(args.url, skip_upload=args.no_upload)
        
        print("\n" + "="*50)
        print("[OK] Video processing completed")
        print("="*50)
        print(f"  Platform: {result.platform}")
        print(f"  Title: {result.title}")
        print(f"  Note: {result.note_file}")
        if result.feishu_link:
            print(f"  Feishu: {result.feishu_link}")
        print("="*50)
        
    except Exception as e:
        print(f"\n[ERROR] Processing failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
