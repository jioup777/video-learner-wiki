"""summarizer 测试 — mock GLM,不依赖真实 API"""
from unittest.mock import patch
from scripts.summarizer import summarize


@patch("scripts.summarizer.call_glm")
def test_summarize_returns_concise_text(mock_glm):
    mock_glm.return_value = "这是一段摘要。"
    s = summarize("很长的口播内容..." * 100, title="测试")
    assert "摘要" in s
    assert len(s) < 1000


@patch("scripts.summarizer.call_glm")
def test_summarize_handles_glm_failure(mock_glm):
    mock_glm.side_effect = Exception("API 挂了")
    # 文本需 >20 字才会触发 call_glm
    s = summarize("这是一段足够长的口播内容用于触发GLM调用", title="测试")
    assert s == ""  # 失败返回空串,不阻塞流程


def test_summarize_short_text_returns_empty():
    # 短文本直接返回空串,不调 GLM
    s = summarize("短", title="测试")
    assert s == ""
