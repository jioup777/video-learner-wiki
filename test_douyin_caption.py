"""parse_f2_metadata 测试 — 基于 f2 常见输出字段(mock),真实字段待 Task 4b 环境校准"""
from scripts.downloaders.douyin import parse_f2_metadata

# 模拟 f2 dy 模式输出的视频 metadata(实际字段以 f2 实测为准)
MOCK_F2_JSON = {
    "desc": "3个动作让开头留人 #短视频运营 #开头留人",
    "create_time": 1719600000,
    "duration": 183000,
    "author": {"nickname": "爆款研究所", "sec_uid": "xxx"},
    "statistics": {"digg_count": 8900, "comment_count": 423, "play_count": 152000},
    "text_extra": [{"hashtag_name": "短视频运营"}, {"hashtag_name": "开头留人"}],
}


def test_parse_extracts_caption_and_stats():
    r = parse_f2_metadata(MOCK_F2_JSON)
    assert r.description == "3个动作让开头留人 #短视频运营 #开头留人"
    assert "#短视频运营" in r.caption.hashtags
    assert r.duration_sec == 183  # f2 duration 是毫秒
    assert r.view_count == 152000
    assert r.creator == "爆款研究所"


def test_parse_handles_missing_fields():
    r = parse_f2_metadata({})
    assert r.caption is not None
    assert r.description == ""  # raw.get("desc") or "" → ""
