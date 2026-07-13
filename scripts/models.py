"""共享数据模型 — 双端 artifact 契约的 Python 投影"""
import re
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class PostCaption:
    """发布文案原始结构化(拆运营看 raw_text 真实写法)"""
    raw_text: str = ""
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> "PostCaption":
        """从原始文案文本提取 hashtags(#xxx) 和 mentions(@xxx)"""
        if not text:
            return cls()
        hashtags = re.findall(r'#([^\s#]+)', text)
        hashtags = [f"#{h}" for h in hashtags]
        mentions = re.findall(r'@([^\s@]+)', text)
        return cls(raw_text=text, hashtags=hashtags, mentions=mentions)


@dataclass
class DownloadResult:
    """下载器统一返回结构(所有平台 downloader 共用)"""
    title: str
    audio_file: Optional[str] = None
    video_file: Optional[str] = None
    subtitle_file: Optional[str] = None
    subtitle_text: Optional[str] = None
    needs_transcription: bool = True
    # ⭐ 新增:文案提取字段
    caption: Optional[PostCaption] = None
    description: Optional[str] = None       # 发布描述/正文
    tags: List[str] = field(default_factory=list)  # 平台标签(标准化)
    duration_sec: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    creator: Optional[str] = None
    creator_url: Optional[str] = None
    published_at: Optional[str] = None
    raw: dict = field(default_factory=dict)  # 平台原始 JSON 留底
