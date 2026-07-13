"""GLM 300 字摘要 — 失败不阻塞,返回空串"""
import os
import requests

GLM_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

SUMMARY_PROMPT = """请把以下视频口播内容压缩成 300 字以内的中文摘要,突出核心观点和可操作结论,不要复述原文:

标题: {title}

口播内容:
{transcript}

摘要:"""


def call_glm(prompt: str) -> str:
    key = os.getenv("GLM_API_KEY")
    if not key:
        raise RuntimeError("GLM_API_KEY 未配置")
    resp = requests.post(GLM_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.3, "max_tokens": 500},
        timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def summarize(transcript: str, title: str = "") -> str:
    """返回摘要;失败返回空串(不阻塞主流程)"""
    if not transcript or len(transcript) < 20:
        return ""
    try:
        return call_glm(SUMMARY_PROMPT.format(title=title, transcript=transcript[:4000]))
    except Exception as e:
        print(f"[summarizer] 摘要失败(忽略): {e}")
        return ""
