"""
抖音下载处理器
使用 yt-dlp 下载抖音视频（支持抖音分享链接）
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from dataclasses import dataclass

YT_DLP_CMD = [sys.executable, '-m', 'yt_dlp']
PROXY = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('VIDEO_LEARNER_PROXY')


@dataclass
class DownloadResult:
    title: str
    audio_file: str | None = None
    subtitle_file: str | None = None
    subtitle_text: str | None = None
    needs_transcription: bool = True


class DouyinDownloader:
    USER_AGENT = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.cookies_file = os.getenv(
            'DOUYIN_COOKIES',
            str(Path(__file__).parent.parent.parent / 'cookies' / 'douyin_cookies.txt')
        )
    
    def process(self, url: str) -> DownloadResult:
        """
        处理抖音视频
        
        Args:
            url: 抖音分享链接
        
        Returns:
            DownloadResult对象
        """
        # 1. 获取视频ID
        video_id = self._extract_video_id(url)
        print(f"  [抖音] 视频ID: {video_id}")
        
        # 2. 获取视频标题
        title = self._get_title(url)
        print(f"  [抖音] 视频标题: {title}")
        
        # 3. 下载音频
        audio_file = self._download_audio(url, video_id)
        print(f"  [抖音] 音频已下载: {audio_file}")
        
        return DownloadResult(
            title=title,
            audio_file=audio_file,
            needs_transcription=True
        )
    
    def _extract_video_id(self, url: str) -> str:
        """
        从分享链接提取视频ID
        
        Args:
            url: 抖音分享链接
        
        Returns:
            视频ID
        """
        # 抖音分享链接格式: https://v.douyin.com/xxxxx/
        # 先尝试直接从URL提取
        match = re.search(r'v\.douyin\.com/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        
        # 如果是长链接格式
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        
        # 使用时间戳作为后备ID
        import time
        return f"douyin_{int(time.time())}"
    
    def _get_title(self, url: str) -> str:
        """
        获取视频标题
        
        Args:
            url: 视频链接
        
        Returns:
            视频标题
        """
        try:
            cmd = YT_DLP_CMD + ['--get-title', '--no-playlist']
            
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
        except Exception as e:
            print(f"  [抖音] 获取标题失败: {e}")
        
        return "抖音视频"
    
    def _download_audio(self, url: str, video_id: str) -> str:
        """
        下载音频
        
        Args:
            url: 视频链接
            video_id: 视频ID
        
        Returns:
            音频文件路径
        """
        output_template = str(Path(self.temp_dir) / f"douyin_{video_id}.%(ext)s")
        
        cmd = YT_DLP_CMD + [
            '-f', 'bestaudio/best',
            '-o', output_template,
            '--no-playlist',
            '--extract-audio',
            '--audio-format', 'm4a',
            '--audio-quality', '0',
        ]
        
        # 添加Cookies支持
        if Path(self.cookies_file).exists():
            cmd.extend(['--cookies', str(self.cookies_file)])
        
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        
        cmd.append(url)
        
        print(f"  [抖音] 使用yt-dlp下载音频...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            
            # Cookies错误提示
            if 'Fresh cookies' in error_msg or 'cookies' in error_msg.lower():
                raise RuntimeError(
                    f"抖音下载失败: 需要有效的Cookies\n\n"
                    f"解决方案:\n"
                    f"1. 更新Cookies文件: {self.cookies_file}\n"
                    f"   格式: Netscape HTTP Cookie File\n\n"
                    f"获取方式:\n"
                    f"  - 浏览器登录douyin.com\n"
                    f"  - 使用浏览器扩展导出（推荐: EditThisCookie）\n\n"
                    f"2. 注意事项:\n"
                    f"   - 确保登录状态后再导出cookies\n"
                    f"   - Cookies文件路径可通过环境变量 DOUYIN_COOKIES 指定\n"
                )
            
            raise RuntimeError(f"抖音下载失败: {error_msg}")
        
        # 查找下载的文件
        for ext in ['.m4a', '.webm', '.opus', '.mp3', '.mp4']:
            audio_file = Path(self.temp_dir) / f"douyin_{video_id}{ext}"
            if audio_file.exists():
                return str(audio_file)
        
        # 如果没有找到，尝试查找任何匹配的文件
        import glob
        pattern = str(Path(self.temp_dir) / f"douyin_{video_id}*")
        files = glob.glob(pattern)
        if files:
            return files[0]
        
        raise RuntimeError("音频文件未找到，下载可能失败")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python douyin.py <抖音分享链接>")
        print("\n示例:")
        print("  python douyin.py 'https://v.douyin.com/xxxxx/'")
        sys.exit(1)
    
    url = sys.argv[1]
    print(f"[抖音] 处理链接: {url}")
    
    downloader = DouyinDownloader()
    
    try:
        result = downloader.process(url)
        print(f"\n✅ 下载成功:")
        print(f"  标题: {result.title}")
        print(f"  音频: {result.audio_file}")
        print(f"  需要转录: {result.needs_transcription}")
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        sys.exit(1)
