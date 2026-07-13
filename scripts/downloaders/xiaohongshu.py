"""小红书下载处理器
使用 yt-dlp XiaoHongShu extractor + cookies 下载视频笔记
"""

import os
import re
import json
import subprocess
import sys
import tempfile
from pathlib import Path

YT_DLP_CMD = [sys.executable, '-m', 'yt_dlp']  # 用当前python跑yt_dlp模块(不依赖PATH/venv未激活)
PROXY = os.getenv('VIDEO_LEARNER_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')  # VIDEO_LEARNER_PROXY优先


# 统一数据模型(Task1 已抽到 models.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import DownloadResult, PostCaption


class XiaoHongShuDownloader:

    def __init__(self):
        self.cookies_file = os.getenv(
            'XHS_COOKIES_PATH',
            str(Path(__file__).parent.parent.parent / 'cookies' / 'xhs_cookies.txt')
        )

    def process(self, url: str) -> DownloadResult:
        """处理小红书视频笔记: 文案提取 + 音频下载(走ASR, 小红书通常无字幕)"""
        video_id = self._extract_note_id(url)

        title = self._get_title(url)
        info = self._get_info_json(url, video_id)  # 文案+统计(7层契约)

        description = info.get('description') or ''
        tags = info.get('tags') or []
        caption = PostCaption.from_text(description) if description else None
        duration_sec = int(info.get('duration')) if info.get('duration') else None
        published = info.get('upload_date') or ''
        if len(published) == 8:
            published = f"{published[:4]}-{published[4:6]}-{published[6:8]}"

        common = dict(
            description=description, tags=tags, caption=caption,
            duration_sec=duration_sec,
            view_count=info.get('view_count'),
            like_count=info.get('like_count'),
            comment_count=info.get('comment_count'),
            creator=info.get('uploader') or info.get('channel'),
            creator_url=info.get('uploader_url') or info.get('channel_url'),
            published_at=published,
        )

        # 小红书视频笔记通常无字幕, 直接下载音频走ASR
        audio_file = self._download_audio(url, video_id)
        return DownloadResult(
            title=title, audio_file=audio_file,
            needs_transcription=True, **common
        )

    def _extract_note_id(self, url: str) -> str:
        """提取笔记ID: xiaohongshu.com/explore/<id> | /discovery/item/<id> | /note/<id> | xhslink"""
        for pat in [r'/(?:explore|note)/([a-zA-Z0-9]+)',
                    r'/discovery/item/([a-zA-Z0-9]+)',
                    r'xhslink\.com/([a-zA-Z0-9]+)']:
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return "unknown"

    def _get_title(self, url: str) -> str:
        cmd = YT_DLP_CMD + ['--get-title']
        if Path(self.cookies_file).exists():
            cmd.extend(['--cookies', self.cookies_file])
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        cmd.append(url)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            pass
        return "小红书笔记"

    def _get_info_json(self, url: str, video_id: str) -> dict:
        """用 yt-dlp --write-info-json 获取笔记元数据(文案/统计), 失败返回空dict"""
        output_path = Path(tempfile.gettempdir()) / f"xhs_{video_id}"
        cmd = YT_DLP_CMD + ['--write-info-json', '--skip-download', '-o', str(output_path)]
        if Path(self.cookies_file).exists():
            cmd.extend(['--cookies', self.cookies_file])
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        cmd.append(url)
        try:
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        except Exception:
            pass
        info_file = Path(tempfile.gettempdir()) / f"xhs_{video_id}.info.json"
        if info_file.exists():
            try:
                return json.loads(info_file.read_text(encoding='utf-8'))
            except Exception:
                return {}
        return {}

    def _download_audio(self, url: str, video_id: str) -> str:
        output_template = str(Path(tempfile.gettempdir()) / f"xhs_{video_id}.%(ext)s")
        cmd = YT_DLP_CMD + [
            '-f', 'bestaudio/best',
            '-x', '--audio-format', 'm4a',
            '-o', output_template,
            '--no-playlist',
        ]
        if Path(self.cookies_file).exists():
            cmd.extend(['--cookies', self.cookies_file])
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            raise RuntimeError(f"小红书下载失败: {error_msg[:300]}")

        for ext in ['.m4a', '.webm', '.opus', '.mp3']:
            f = Path(tempfile.gettempdir()) / f"xhs_{video_id}{ext}"
            if f.exists():
                return str(f)
        raise RuntimeError("小红书音频文件未找到, 下载可能失败")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python xiaohongshu.py <小红书链接>")
        sys.exit(1)
    url = sys.argv[1]
    print(f"[小红书] 处理链接: {url}")
    try:
        result = XiaoHongShuDownloader().process(url)
        print(f"\n✅ 下载成功:")
        print(f"  标题: {result.title}")
        print(f"  音频: {result.audio_file}")
        print(f"  博主: {result.creator}")
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        sys.exit(1)
