from scripts.models import DownloadResult, PostCaption

def test_download_result_defaults():
    r = DownloadResult(title="测试")
    assert r.title == "测试"
    assert r.audio_file is None
    assert r.needs_transcription is True
    assert r.caption is None

def test_download_result_with_caption():
    cap = PostCaption(raw_text="标题 #标签 正文", hashtags=["#标签"], mentions=[])
    r = DownloadResult(title="测试", caption=cap, description="正文", tags=["标签"],
                       duration_sec=183, view_count=1000)
    assert r.caption.hashtags == ["#标签"]
    assert r.duration_sec == 183

def test_post_caption_from_text_extracts_hashtags():
    cap = PostCaption.from_text("开头 #标签1 中间 #标签2 结尾 @用户")
    assert "#标签1" in cap.hashtags
    assert "#标签2" in cap.hashtags
    assert "用户" in cap.mentions[0]
