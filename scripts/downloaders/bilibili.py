"""
Bilibili下载处理器
使用 yt-dlp + cookies 下载B站视频音频
"""

import os
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

YT_DLP_CMD = ['yt-dlp']
PROXY = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('VIDEO_LEARNER_PROXY')  # 可选代理


@dataclass
class DownloadResult:
    title: str
    audio_file: str | None = None
    subtitle_file: str | None = None
    subtitle_text: str | None = None
    needs_transcription: bool = True


class BilibiliDownloader:
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def __init__(self):
        self.cookies_file = os.getenv(
            'BILIBILI_COOKIES',
            str(Path(__file__).parent.parent.parent / 'cookies' / 'bilibili_cookies.txt')
        )
        self.cookies_valid = self._validate_cookies()
    
    def process(self, url: str) -> DownloadResult:
        """处理B站视频：先尝试获取字幕，有字幕则跳过ASR"""
        video_id = self._extract_bvid(url)
        
        title = self._get_title(url)
        
        # 尝试获取字幕（CC/AI字幕）
        subtitle_text = self._try_get_subtitle(url, video_id)
        
        if subtitle_text:
            # 有字幕，不需要下载音频和ASR
            return DownloadResult(
                title=title,
                subtitle_text=subtitle_text,
                needs_transcription=False
            )
        
        # 无字幕，下载音频走ASR流程
        audio_file = self._download_audio(url, video_id)
        
        return DownloadResult(
            title=title,
            audio_file=audio_file,
            needs_transcription=True
        )
    
    def _try_get_subtitle(self, url: str, video_id: str) -> str | None:
        """尝试获取B站视频字幕（CC字幕 > AI字幕）"""
        temp_dir = tempfile.gettempdir()
        sub_template = str(Path(temp_dir) / f"bilibili_{video_id}.%(ext)s")
        
        # 按优先级尝试：zh-Hans(简中AI) > zh-CN > ai_zh > zh
        lang_list = ['ai-zh', 'zh-Hans', 'zh-CN', 'ai_zh', 'zh']
        
        for lang in lang_list:
            cmd = YT_DLP_CMD + [
                '--write-subs', '--sub-lang', lang,
                '--sub-format', 'vtt',
                '--skip-download',
                '-o', sub_template,
                '--no-playlist',
            ]
            
            if Path(self.cookies_file).exists():
                cmd.extend(['--cookies', str(self.cookies_file)])
            if PROXY:
                cmd.extend(['--proxy', PROXY])
            cmd.append(url)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # 查找下载的字幕文件
            for ext in ['.vtt', '.srt', '.ass']:
                # yt-dlp可能用 lang 作为后缀，如 bilibili_xxx.ai-zh.srt
                candidates = [
                    Path(temp_dir) / f"bilibili_{video_id}.{lang}{ext}",
                    Path(temp_dir) / f"bilibili_{video_id}{ext}",
                ]
                # 也glob匹配
                candidates.extend(Path(temp_dir).glob(f"bilibili_{video_id}*{ext}"))
                for sub_file in candidates:
                    if sub_file.exists():
                        try:
                            text = self._parse_subtitle(sub_file)
                            if text and len(text) > 20:  # 太短的字幕不可用
                                print(f"[INFO] ✓ 获取到B站字幕 ({lang}, {len(text)}字符)", file=sys.stderr)
                                sub_file.unlink(missing_ok=True)
                                return text
                        except Exception:
                            pass
                        sub_file.unlink(missing_ok=True)
        
        return None
    
    def _parse_subtitle(self, file_path: Path) -> str:
        """解析字幕文件，返回纯文本"""
        content = file_path.read_text(encoding='utf-8')
        ext = file_path.suffix.lower()
        
        if ext == '.vtt':
            # VTT格式：去掉WEBVTT头和时间戳行
            lines = content.split('\n')
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith('WEBVTT') or line.startswith('NOTE') or '-->' in line:
                    continue
                # 去掉序号
                if re.match(r'^\d+$', line):
                    continue
                # 去掉HTML标签
                line = re.sub(r'<[^>]+>', '', line)
                if line:
                    text_lines.append(line)
            return '\n'.join(text_lines)
        
        elif ext == '.srt':
            lines = content.split('\n')
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line or re.match(r'^\d+$', line) or '-->' in line:
                    continue
                line = re.sub(r'<[^>]+>', '', line)
                if line:
                    text_lines.append(line)
            return '\n'.join(text_lines)
        
        elif ext == '.ass':
            # ASS格式：提取Dialogue行的文本
            text_lines = []
            for line in content.split('\n'):
                if line.startswith('Dialogue:'):
                    # ASS格式: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        text = parts[9]
                        # 去掉ASS标签
                        text = re.sub(r'\{[^}]*\}', '', text)
                        text = re.sub(r'\\[nN]', '', text)
                        text = text.strip()
                        if text:
                            text_lines.append(text)
            return '\n'.join(text_lines)
        
        return ""
    
    def _extract_bvid(self, url: str) -> str:
        """提取BV号，支持短链(b23.tv)"""
        match = re.search(r'BV[a-zA-Z0-9]+', url)
        if match:
            return match.group(0)
        # 短链无法直接提取BV号，用yt-dlp解析
        try:
            cmd = YT_DLP_CMD + ['--get-id']
            if Path(self.cookies_file).exists():
                cmd.extend(['--cookies', str(self.cookies_file)])
            if PROXY:
                cmd.extend(['--proxy', PROXY])
            cmd.append(url)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                extracted = result.stdout.strip()
                match = re.search(r'BV[a-zA-Z0-9]+', extracted)
                if match:
                    return match.group(0)
                return extracted
        except Exception:
            pass
        return "unknown"
    
    def _validate_cookies(self) -> bool:
        """验证cookies文件是否存在且有效"""
        if not Path(self.cookies_file).exists():
            return False
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return False
                
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('#') or not line.strip():
                        continue
                    
                    if '.bilibili.com' in line or 'bilibili.com' in line:
                        parts = line.strip().split('\t')
                        if len(parts) >= 7:
                            return True
        except Exception:
            pass
        
        return False
    
    def _get_title(self, url: str) -> str:
        try:
            cmd = YT_DLP_CMD + ['--get-title']
            
            # 添加Cookies（优先级：cookies文件 > 浏览器cookies）
            if Path(self.cookies_file).exists():
                cmd.extend(['--cookies', str(self.cookies_file)])
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
            
            if PROXY:
                cmd.extend(['--proxy', PROXY])
            cmd.append(url)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        
        return "B站视频"
    
    def _download_audio(self, url: str, video_id: str) -> str:
        temp_dir = tempfile.gettempdir()
        output_template = str(Path(temp_dir) / f"bilibili_{video_id}.%(ext)s")
        
        cmd = YT_DLP_CMD + [
            '-f', 'bestaudio/best',
            '-x', '--audio-format', 'm4a',
            '-o', output_template,
            '--no-playlist',
        ]
        
        # 添加Cookies（优先级：cookies文件 > 浏览器cookies）
        if Path(self.cookies_file).exists():
            cmd.extend(['--cookies', str(self.cookies_file)])
        
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        
        cmd.append(url)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            
            # 412错误 - Cookies问题（详细提示）
            if "412" in error_msg or "Precondition Failed" in error_msg:
                raise RuntimeError(
                    "B站下载失败(412): Cookies无效或过期\n\n"
                    f"解决方案:\n"
                    f"1. 更新Cookies文件: {self.cookies_file}\n"
                    f"   格式: Netscape HTTP Cookie File\n"
                    f"   必须包含: .bilibili.com 域名的 SESSDATA, DedeUserID, bili_jct\n\n"
                    f"获取方式:\n"
                    f"  - 浏览器扩展导出（推荐: EditThisCookie、Get cookies.txt）\n"
                    f"  - 浏览器F12 → Network → 复制cookies\n\n"
                    f"2. 或尝试浏览器Cookies: yt-dlp --cookies-from-browser chrome\n\n"
                    f"3. 注意事项:\n"
                    f"   - SESSDATA有效期通常为1个月，需要定期更新\n"
                    f"   - 确保登录状态（登录B站后再导出cookies）\n"
                    f"   - Cookies文件路径可通过环境变量 BILIBILI_COOKIES 指定\n"
                )
            
            raise RuntimeError(f"B站下载失败: {error_msg}")
        
        for ext in ['.m4a', '.webm', '.opus', '.mp3']:
            audio_file = Path(temp_dir) / f"bilibili_{video_id}{ext}"
            if audio_file.exists():
                return str(audio_file)
        
        raise RuntimeError("音频文件未找到，下载可能失败")
