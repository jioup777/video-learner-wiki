"""
抖音下载处理器
使用 f2 库下载抖音视频（替代 yt-dlp，因为 yt-dlp 对抖音支持不稳定）
"""

import os
import re
import subprocess
import sys
import http.cookiejar
import tempfile
import glob
import shutil
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DownloadResult:
    title: str
    audio_file: str | None = None
    subtitle_file: str | None = None
    subtitle_text: str | None = None
    needs_transcription: bool = True


class DouyinDownloader:
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.cookies_file = os.getenv(
            'DOUYIN_COOKIES_PATH',
            str(Path(__file__).parent.parent.parent / 'cookies' / 'douyin_cookies.txt')
        )
    
    def _load_cookie_string(self) -> str:
        """将 Netscape cookie 文件转为 f2 需要的纯文本 cookie 字符串"""
        cookies_path = Path(self.cookies_file).expanduser().resolve()
        if not cookies_path.exists():
            raise RuntimeError(
                f"抖音 Cookies 文件不存在: {cookies_path}\n"
                f"请从浏览器导出 Netscape 格式的 cookies 文件"
            )
        self.cookies_file = str(cookies_path)
        
        cj = http.cookiejar.MozillaCookieJar()
        cj.load(self.cookies_file)
        return '; '.join(f'{c.name}={c.value}' for c in cj)
    
    def process(self, url: str) -> DownloadResult:
        """
        处理抖音视频
        
        Args:
            url: 抖音分享链接或完整链接
        
        Returns:
            DownloadResult对象
        """
        # 1. 解析短链接为完整 URL
        full_url = self._resolve_url(url)
        print(f"  [抖音] 完整链接: {full_url}")
        
        # 2. 获取视频ID
        video_id = self._extract_video_id(full_url)
        print(f"  [抖音] 视频ID: {video_id}")
        
        # 3. 下载视频
        output_dir = os.path.join(self.temp_dir, f"douyin_{video_id}")
        video_file, title = self._download_video(full_url, output_dir)
        print(f"  [抖音] 视频已下载: {video_file}")
        print(f"  [抖音] 视频标题: {title}")
        
        # 4. 从视频提取音频（用于 ASR 转录）
        audio_file = self._extract_audio(video_file, video_id)
        print(f"  [抖音] 音频已提取: {audio_file}")
        
        return DownloadResult(
            title=title,
            audio_file=audio_file,
            needs_transcription=True
        )
    
    def _resolve_url(self, url: str) -> str:
        """将抖音短链接解析为完整 URL"""
        if 'v.douyin.com' not in url:
            return url
        
        try:
            cmd = ['curl', '-s', '-o', '/dev/null', '-w', '%{url_effective}',
                   '-L', '--max-redirs', '5', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout.strip():
                resolved = result.stdout.strip()
                if 'douyin.com/video/' in resolved:
                    return resolved
        except Exception:
            pass
        
        # fallback: 直接返回原始 URL
        return url
    
    def _extract_video_id(self, url: str) -> str:
        """从链接提取视频ID"""
        # 长链接格式: https://www.douyin.com/video/7619936329945615616
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        
        # 短链接格式: https://v.douyin.com/xxxxx/
        match = re.search(r'v\.douyin\.com/([a-zA-Z0-9_]+)', url)
        if match:
            return match.group(1)
        
        # 兜底
        import time
        return f"douyin_{int(time.time())}"
    
    def _download_video(self, url: str, output_dir: str) -> tuple:
        """
        使用 f2 下载视频
        
        Returns:
            (video_file_path, title)
        """
        cookie_str = self._load_cookie_string()
        
        # f2 下载命令
        # 注意：必须从 /tmp 目录运行，避免 workspace 中的 secrets/ 目录
        # 与 Python 标准库 secrets 模块冲突导致 ImportError
        cmd = [
            sys.executable, '-m', 'f2', 'dy',
            '-u', url,
            '-k', cookie_str,
            '-p', output_dir,
            '-M', 'one',
            '--languages', 'zh_CN',
        ]
        
        print(f"  [抖音] 使用 f2 下载视频...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd='/tmp'  # 避开 secrets/ 目录冲突
        )
        
        if result.returncode != 0:
            # f2 的 Bark 通知错误可忽略
            stderr_lines = [l for l in result.stderr.split('\n') 
                          if l.strip() and 'Bark' not in l and 'api.day.app' not in l]
            real_errors = [l for l in stderr_lines 
                         if 'ERROR' in l or 'Traceback' in l or 'Exception' in l]
            
            if real_errors:
                error_detail = '\n'.join(real_errors[-5:])
                raise RuntimeError(f"f2 下载失败:\n{error_detail}")
        
        # 查找下载的视频文件
        # f2 输出路径: output_dir/douyin/one/<作者名>/<日期_标题_video.mp4>
        video_files = []
        for pattern in [
            os.path.join(output_dir, '**', '*_video.mp4'),
            os.path.join(output_dir, '**', '*.mp4'),
        ]:
            video_files = glob.glob(pattern, recursive=True)
            if video_files:
                break
        
        if not video_files:
            # 检查 stdout 中是否有文件路径
            for line in result.stdout.split('\n'):
                if '.mp4' in line:
                    # 提取文件路径
                    parts = line.strip().split()
                    for p in parts:
                        if p.endswith('.mp4') and os.path.exists(p):
                            video_files = [p]
                            break
                    if video_files:
                        break
        
        if not video_files:
            raise RuntimeError(
                f"视频文件未找到，下载可能失败\n"
                f"输出目录: {output_dir}\n"
                f"请检查 cookies 是否过期"
            )
        
        video_file = video_files[0]
        
        # 从文件名提取标题
        filename = os.path.basename(video_file)
        # 格式: 2026-03-22 12-44-50_10__女频的爽点模型_唯一性_#女频_video.mp4
        title = filename.replace('_video.mp4', '')
        # 去掉开头的日期时间前缀
        title_match = re.match(r'\d{4}-\d{2}-\d{2}\s+\d{2}-\d{2}-\d{2}_(.*)', title)
        if title_match:
            title = title_match.group(1).replace('_', ' ')
        else:
            title = title.replace('_', ' ')
        
        return video_file, title
    
    def _extract_audio(self, video_file: str, video_id: str) -> str:
        """使用 ffmpeg 从视频提取音频"""
        audio_file = os.path.join(self.temp_dir, f"douyin_{video_id}.m4a")
        
        cmd = [
            'ffmpeg', '-y', '-i', video_file,
            '-vn', '-acodec', 'copy',
            audio_file
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"音频提取失败: {result.stderr[:200]}")
        
        if not os.path.exists(audio_file):
            raise RuntimeError("音频文件未生成")
        
        return audio_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python douyin.py <抖音分享链接>")
        print("\n示例:")
        print("  python douyin.py 'https://v.douyin.com/xxxxx/'")
        print("  python douyin.py 'https://www.douyin.com/video/7619936329945615616'")
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
