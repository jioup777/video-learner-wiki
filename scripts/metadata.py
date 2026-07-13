"""metadata.json 7 层 schema — 双端共享契约"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from models import PostCaption

VALID_TOPICS = ["AI科技", "内容创作", "IP运营", "成功方法论"]
SCHEMA_VERSION = "1.0"


class ContractError(Exception):
    pass


def build_metadata(
    platform: str, video_id: str, url: str, title: str,
    creator: Optional[str] = None, creator_url: Optional[str] = None,
    published_at: Optional[str] = None, duration_sec: Optional[int] = None,
    description: Optional[str] = None, tags: Optional[List[str]] = None,
    view_count: Optional[int] = None, like_count: Optional[int] = None,
    comment_count: Optional[int] = None, language: str = "zh",
    caption: Optional[PostCaption] = None,
    transcript_source: Optional[str] = None, transcript_text: str = "",
    summary: str = "",
    topic: Optional[str] = None, subtopic: Optional[List[str]] = None,
    topic_confidence: float = 0.0, topic_source: str = "ai_suggested",
    scene_tags: Optional[List[str]] = None, custom_tags: Optional[List[str]] = None,
    quality_score: Optional[int] = None,
    note_url: Optional[str] = None, archived_by: str = "openclaw",
    download_status: str = "ok", video_path: str = "", audio_path: str = "",
    ratio: str = "", route: str = "", caveats: str = "",
    asr_backend: str = "", asr_model: str = "", asr_status: str = "ok",
    transcript_path: str = "", raw: Optional[dict] = None,
) -> dict:
    """组装 7 层 metadata.json(archive.note_url/archived_at 上传后回填)"""
    word_count = len(transcript_text) if transcript_text else 0
    return {
        "schema_version": SCHEMA_VERSION,
        "normalized": {
            "platform": platform, "video_id": video_id, "url": url,
            "title": title, "creator": creator, "creator_url": creator_url,
            "published_at": published_at, "duration_sec": duration_sec,
            "description": description, "tags": tags or [],
            "view_count": view_count, "like_count": like_count,
            "comment_count": comment_count, "language": language,
        },
        "post_caption": {
            "raw_text": caption.raw_text if caption else "",
            "hashtags": caption.hashtags if caption else [],
            "mentions": caption.mentions if caption else [],
        },
        "transcript": {
            "source": transcript_source, "language": language,
            "duration_sec": duration_sec, "word_count": word_count,
        },
        "summary": summary,
        "archive": {
            "topic": topic, "subtopic": subtopic or [],
            "topic_confidence": topic_confidence, "topic_source": topic_source,
            "scene_tags": scene_tags or [], "custom_tags": custom_tags or [],
            "quality_score": quality_score,
            "note_url": note_url,
            "archived_at": datetime.now().astimezone().isoformat(),
            "archived_by": archived_by,
        },
        "download": {
            "status": download_status, "video_path": video_path,
            "audio_path": audio_path, "ratio": ratio, "route": route,
            "caveats": caveats,
        },
        "asr": {
            "backend": asr_backend, "model": asr_model, "status": asr_status,
            "transcript_path": transcript_path,
        },
        "raw": raw or {},
    }


def validate_metadata(m: dict) -> None:
    """校验 artifact 契约 — 不符合抛 ContractError"""
    if m.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"schema_version 必须 {SCHEMA_VERSION}")
    archive = m.get("archive", {})
    topic = archive.get("topic")
    if not topic:
        raise ContractError("archive.topic 必填(主领域)")
    if topic not in VALID_TOPICS:
        raise ContractError(f"archive.topic 必须是 {VALID_TOPICS} 之一, 当前: {topic}")
    for layer in ["normalized", "post_caption", "transcript", "summary",
                  "archive", "download", "asr"]:
        if layer not in m:
            raise ContractError(f"缺层: {layer}")
    if archive.get("archived_by") not in ("cc", "openclaw"):
        raise ContractError("archive.archived_by 必须 cc 或 openclaw")
