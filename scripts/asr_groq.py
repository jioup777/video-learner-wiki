#!/usr/bin/env python3
"""
Groq Whisper ASR - 免费语音转录
使用 Groq API 的 Whisper Large V3 Turbo 模型进行语音转录。
免费tier: 25MB文件上限，$0.04/hour（whisper-large-v3-turbo）
"""

import os
import sys
import argparse
import requests
import json

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
# 免费tier最大25MB，超过需分片
MAX_FILE_SIZE = 25 * 1024 * 1024


def _get_all_keys():
    """获取所有可用的 Groq API keys，支持轮换"""
    keys = []
    # 主key
    primary = os.getenv("GROQ_API_KEY", "")
    if primary:
        keys.append(primary)
    # 备用keys（逗号分隔）
    extras = os.getenv("GROQ_API_KEYS", "")
    if extras:
        for k in extras.split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys


class GroqASR:
    """Groq Whisper ASR，兼容 AliyunASR 接口，支持多key轮换"""

    def __init__(self, api_key: str = None):
        if api_key:
            self.api_keys = [api_key]
        else:
            self.api_keys = _get_all_keys()
        self.model = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")

    def transcribe(self, audio_file: str, language: str = None) -> str:
        """转录音频文件，返回文本，自动轮换key"""
        if not self.api_keys:
            raise ValueError("需要设置 GROQ_API_KEY 或 GROQ_API_KEYS")
        last_err = None
        for key in self.api_keys:
            try:
                return _transcribe_impl(audio_file, language, key, self.model)
            except RuntimeError as e:
                err_str = str(e)
                if "rate_limit" in err_str.lower() or "429" in err_str:
                    print(f"[Groq Whisper] Key ...{key[-6:]} 配额用完，切换下一个", file=sys.stderr)
                    last_err = e
                    continue
                raise
        raise RuntimeError(f"所有 Groq API keys 配额用完: {last_err}")


def _transcribe_impl(audio_file: str, language: str, api_key: str, model: str) -> str:
    """内部转录实现"""
    file_size = os.path.getsize(audio_file)
    print(f"[Groq Whisper] 文件大小: {file_size / 1024 / 1024:.1f}MB, 模型: {model}", file=sys.stderr)

    # 超过25MB需要压缩或分片
    if file_size > MAX_FILE_SIZE:
        print(f"[Groq Whisper] 文件超过25MB，尝试用ffmpeg压缩...", file=sys.stderr)
        compressed = _compress_audio(audio_file)
        if compressed:
            audio_file = compressed
            file_size = os.path.getsize(audio_file)
            print(f"[Groq Whisper] 压缩后: {file_size / 1024 / 1024:.1f}MB", file=sys.stderr)
        if file_size > MAX_FILE_SIZE:
            return _transcribe_chunked(audio_file, language, api_key, model)

    return _transcribe_single(audio_file, language, api_key, model)


def _transcribe_single(audio_file: str, language: str, api_key: str, model: str) -> str:
    """单次转录"""
    headers = {"Authorization": f"Bearer {api_key}"}

    data = {"model": model, "response_format": "verbose_json", "timestamp_granularities[]": "segment"}
    if language:
        data["language"] = language

    with open(audio_file, "rb") as f:
        files = {"file": (os.path.basename(audio_file), f)}
        resp = requests.post(GROQ_API_URL, headers=headers, data=data, files=files, timeout=300)

    if resp.status_code != 200:
        raise RuntimeError(f"Groq API 错误: {resp.status_code} - {resp.text}")

    result = resp.json()

    # 提取文本
    if "text" in result:
        text = result["text"]
    else:
        raise RuntimeError(f"Groq API 返回格式异常: {result}")

    # 如果有 segments，拼接更干净的文本
    if "segments" in result:
        segments = result["segments"]
        lines = []
        for seg in segments:
            seg_text = seg.get("text", "").strip()
            if seg_text:
                lines.append(seg_text)
        if lines:
            text = "".join(lines)

    # 去重连续重复行
    seen = set()
    unique = []
    for line in text.split("\n"):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            unique.append(line)
    text = "\n".join(unique)

    return text


def _compress_audio(audio_file: str) -> str:
    """用ffmpeg压缩音频到16kHz mono flac"""
    import subprocess, tempfile
    output = tempfile.mktemp(suffix=".flac")
    cmd = ["ffmpeg", "-y", "-i", audio_file, "-ar", "16000", "-ac", "1", "-map", "0:a", "-c:a", "flac", output]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode == 0 and os.path.exists(output):
            return output
    except Exception as e:
        print(f"[Groq Whisper] 压缩失败: {e}", file=sys.stderr)
    if os.path.exists(output):
        os.unlink(output)
    return None


def _transcribe_chunked(audio_file: str, language: str, api_key: str, model: str) -> str:
    """分片转录大文件（每片不超过24MB）"""
    import subprocess, tempfile

    print(f"[Groq Whisper] 启动分片转录模式...", file=sys.stderr)

    # 先获取音频时长
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_file]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    duration = float(r.stdout.strip()) if r.returncode == 0 else 600

    # 分片：每片约20分钟
    chunk_duration = 1200  # 20 min
    overlap = 5  # 5秒重叠
    chunks = []
    tmp_dir = tempfile.mkdtemp()

    t = 0
    idx = 0
    while t < duration:
        out_file = os.path.join(tmp_dir, f"chunk_{idx:04d}.flac")
        cmd = [
            "ffmpeg", "-y", "-i", audio_file,
            "-ss", str(t), "-t", str(chunk_duration),
            "-ar", "16000", "-ac", "1", "-map", "0:a", "-c:a", "flac", out_file
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode == 0 and os.path.exists(out_file):
            chunks.append(out_file)
        t += chunk_duration - overlap
        idx += 1

    print(f"[Groq Whisper] 分成 {len(chunks)} 片", file=sys.stderr)

    # 逐片转录
    texts = []
    for i, chunk in enumerate(chunks):
        print(f"[Groq Whisper] 转录片段 {i+1}/{len(chunks)}...", file=sys.stderr)
        try:
            text = _transcribe_single(chunk, language, api_key, model)
            texts.append(text)
        except Exception as e:
            print(f"[Groq Whisper] 片段 {i+1} 失败: {e}", file=sys.stderr)

    # 清理
    for chunk in chunks:
        os.unlink(chunk)
    os.rmdir(tmp_dir)

    return "\n".join(texts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Groq Whisper ASR")
    parser.add_argument("audio_file", help="音频文件路径")
    parser.add_argument("--language", "-l", help="语言代码（如 zh, en）")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--api-key", help="Groq API Key")
    args = parser.parse_args()

    text = _transcribe_impl(args.audio_file, language=args.language, api_key=args.api_key or os.getenv('GROQ_API_KEY'), model=MODEL)
    print(f"[Groq Whisper] 转录完成: {len(text)} 字符", file=sys.stderr)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[Groq Whisper] 已保存到: {args.output}", file=sys.stderr)
    else:
        print(text)
