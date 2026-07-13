"""metadata 7层 schema + contract-check 测试"""
import json
from scripts.metadata import build_metadata, validate_metadata, ContractError


def test_build_metadata_seven_layers():
    m = build_metadata(
        platform="douyin", video_id="123", url="https://v.douyin.com/x/",
        title="标题", creator="博主", transcript_source="groq",
        transcript_text="口播内容", summary="摘要",
        topic="内容创作", subtopic=["短剧"], archived_by="openclaw",
    )
    for layer in ["schema_version", "normalized", "post_caption", "transcript",
                  "summary", "archive", "download", "asr", "raw"]:
        assert layer in m, f"缺层: {layer}"


def test_validate_rejects_missing_topic():
    m = {"schema_version": "1.0", "archive": {"topic": None}}
    try:
        validate_metadata(m)
        assert False, "应抛错"
    except ContractError as e:
        assert "topic" in str(e)


def test_validate_passes_full_metadata():
    m = build_metadata(
        platform="douyin", video_id="1", url="u", title="t",
        transcript_source="groq", transcript_text="x", summary="s",
        topic="AI科技", subtopic=[], archived_by="cc",
    )
    validate_metadata(m)  # 不抛错即通过


def test_topic_must_be_one_of_four():
    m = {"schema_version": "1.0", "archive": {"topic": "瞎编领域"}}
    try:
        validate_metadata(m)
        assert False
    except ContractError as e:
        assert "AI科技" in str(e)
