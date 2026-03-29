"""
YouTube下载处理器
优先使用官方字幕，无字幕时使用ASR
"""

import os
import re
import subprocess
import tempfile
import shutil
import requests
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse

YT_DLP_CMD = ['yt-dlp']
PROXY = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('VIDEO_LEARNER_PROXY')  # 可选代理


@dataclass
class DownloadResult:
    title: str
    audio_file: str = None
    subtitle_file: str = None
    subtitle_text: str = None
    needs_transcription: bool = True


class YouTubeDownloader:
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.cookies_file = os.getenv('YOUTUBE_COOKIES_PATH') or str(
            Path(__file__).parent.parent.parent / 'cookies' / 'youtube_cookies.txt'
        )
    
    def process(self, url: str) -> DownloadResult:
        """处理YouTube视频"""
        video_id = self._extract_video_id(url)
        
        title = self._get_title(url, video_id)
        
        has_subtitle, subtitle_lang = self._check_subtitles(url, video_id)
        
        if has_subtitle:
            subtitle_file = self._download_subtitle(url, video_id, subtitle_lang)
            subtitle_text = self._parse_subtitle(subtitle_file)
            
            return DownloadResult(
                title=title,
                subtitle_file=subtitle_file,
                subtitle_text=subtitle_text,
                needs_transcription=False
            )
        else:
            audio_file = self._download_audio(url, video_id)
            
            return DownloadResult(
                title=title,
                audio_file=audio_file,
                needs_transcription=True
            )
    
    def _extract_video_id(self, url: str) -> str:
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
    
    def _get_title(self, url: str, video_id: str = None) -> str:
        try:
            cmd = YT_DLP_CMD + ['--get-title']
            
            # 添加Cookies（优先级：cookies文件 > 浏览器cookies）
            if Path(self.cookies_file).exists():
                cmd.extend(['--cookies', self.cookies_file])
            elif shutil.which('chrome') and not PROXY:
                # 尝试从浏览器读取Cookies
                try:
                    result = subprocess.run(
                        ['yt-dlp', '--cookies-from-browser', 'chrome', '--get-title', url],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
                except:
                    pass
            
            # 添加代理
            if PROXY:
                cmd.extend(['--proxy', PROXY])
            
            cmd.append(url)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return "YouTube视频" if not video_id else "Unknown YouTube Video"
    
    def _check_subtitles(self, url: str, video_id: str = None) -> Tuple[bool, Optional[str]]:
        try:
            cmd = YT_DLP_CMD + ['--list-subs']
            
            # 添加代理
            if PROXY:
                cmd.extend(['--proxy', PROXY])
            
            cmd.append(url)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            
            # 优先检测中文字幕（更全面）
            chinese_lang_patterns = [
                r'zh(?:-CN|-Hans|TW|Hant)',
                r'Chinese',
                r'\u4e2d\u4e2e\u7e2e\u6e80',  # 中文unicode
            ]
            
            for line in output.split('\n'):
                for pattern in chinese_lang_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        if 'zh-CN' in line:
                            return True, 'zh-Hans'
                        elif 'zh-Hant' in line:
                            return True, 'zh-Hant'
                        elif 'zh-TW' in line:
                            return True, 'zh-TW'
                        elif 'zh' in line:
                            return True, 'zh'
                        elif 'Chinese' in line:
                            return True, 'zh'
            
            # 未找到中文字幕，尝试英文字幕（可能需要翻译）
            result = subprocess.run(
                YT_DLP_CMD + ['--list-subs', '--sub-lang', 'en', url],
                capture_output=True,
                text=True,
                timeout=30
            )
            if 'en' in result.stdout.lower():
                print("  [YouTube] 未找到中文字幕，将使用英文字幕（可能需要GLM翻译）")
                return True, 'en'
            
        except Exception as e:
            print(f"  [YouTube] 字幕检测失败: {e}")
            return False, None
    
    def _download_subtitle(self, url: str, video_id: str, lang: str) -> str:
        output_path = Path(self.temp_dir) / f"youtube_{video_id}"
        
        cmd = YT_DLP_CMD + [
            '--write-subs',
            '--sub-langs', lang,
            '--skip-download',
            '-o', str(output_path),
        ]
        
        # 添加代理
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        
        cmd.append(url)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        for ext in ['.zh-Hans.vtt', '.zh-CN.vtt', '.zh.vtt', '.vtt',
                     '.zh-Hans.srt', '.zh-CN.srt', '.zh.srt', '.srt',
                     '.en.vtt', '.en.srt']:
            subtitle_file = Path(self.temp_dir) / f"youtube_{video_id}{ext}"
            if subtitle_file.exists():
                return str(subtitle_file)
        
        possible_files = list(Path(self.temp_dir).glob(f"youtube_{video_id}.*"))
        for f in possible_files:
            if f.suffix in ['.vtt', '.srt']:
                return str(f)
        
        raise RuntimeError("字幕文件下载失败")
    
    def _parse_subtitle(self, subtitle_file: str) -> str:
        """解析字幕文件为纯文本"""
        text_lines = []
        
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            if line.startswith(('WEBVTT', 'NOTE')):
                continue
            
            if '-->' in line:
                continue
            
            if line.isdigit():
                continue
            
            if line.startswith('<'):
                line = re.sub(r'<[^>]+>', '', line)
            
            if line:
                text_lines.append(line)
        
        seen = set()
        unique_lines = []
        for line in text_lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def _download_audio(self, url: str, video_id: str) -> str:
        output_template = str(Path(self.temp_dir) / f"youtube_{video_id}.%(ext)s")
        
        cmd = YT_DLP_CMD + [
            '-f', 'bestaudio',
            '-o', output_template,
            '--no-playlist',
        ]
        
        # 添加代理
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        
        cmd.append(url)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            
            # 412错误 - Cookies问题（详细提示）
            if '412' in error_msg or 'Precondition Failed' in error_msg:
                raise RuntimeError(
                    "YouTube下载失败(412): Cookies无效或过期\n\n"
                    f"解决方案:\n"
                    f"1. 更新Cookies文件: {self.cookies_file}\n"
                    f"   格式: Netscape HTTP Cookie File\n\n"
                    f"获取方式: 浏览器扩展导出（推荐: EditThisCookie）\n"
                    f"2. 或尝试浏览器Cookies: --cookies-from-browser chrome\n\n"
                    f"3. 确认网络环境（海外服务器无需代理）\n"
                )
            
            raise RuntimeError(f"YouTube下载失败: {error_msg}")
        
        for ext in ['.m4a', '.webm', '.opus', '.mp3']:
            audio_file = Path(self.temp_dir) / f"youtube_{video_id}{ext}"
            if audio_file.exists():
                return str(audio_file)
        
        raise RuntimeError("音频文件未找到，下载可能失败")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python youtube.py <YouTube链接>")
        sys.exit(1)
    
    url = sys.argv[1]
    print(f"YouTube链接: {url}")
    
    downloader = YouTubeDownloader()
    
    try:
        result = downloader.process(url)
        print(f"\n[OK] 下载成功:")
        print(f"  标题: {result.title}")
        print(f"  音频: {result.audio_file}")
        print(f"  需要转录: {result.needs_transcription}")
    except Exception as e:
        print(f"\n[ERROR] 下载失败: {e}")
        sys.exit(1)
