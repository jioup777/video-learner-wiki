#!/usr/bin/env python3
"""调试脚本：查看完整的 API 响应"""
import os
import json
from http import HTTPStatus
import dashscope
from dashscope.audio.asr import Transcription

API_KEY = "sk-601abb31fe354b6daf24067c7a56adc6"
MODEL = "fun-asr-mtl"
AUDIO_FILE = "/home/ubuntu/.openclaw/workspace-video-learner/audio_output.wav"

dashscope.api_key = API_KEY

print("创建转写任务...")
task_response = Transcription.async_call(
    model=MODEL,
    file_urls=[f"file://{AUDIO_FILE}"]
)

print(f"任务 ID: {task_response.output.task_id}")
print("\n等待任务完成...")

transcribe_response = Transcription.wait(task=task_response.output.task_id)

print(f"\n状态码：{transcribe_response.status_code}")
print(f"完整响应类型：{type(transcribe_response)}")
print(f"完整响应内容:\n{json.dumps(dict(transcribe_response), indent=2, default=str)}")
