#!/usr/bin/env python3
"""
测试阿里云 ASR API
"""
import os
from http import HTTPStatus
import dashscope
from dashscope.audio.asr import Transcription

# 配置
API_KEY = "sk-601abb31fe354b6daf24067c7a56adc6"
MODEL = "fun-asr-mtl"

dashscope.api_key = API_KEY

print("🧪 测试阿里云 ASR API")
print("=" * 60)

# 先用示例 URL 测试（确保 API 配置正确）
print("\n1️⃣ 测试 API 连通性（使用官方示例音频）...")
try:
    task_response = Transcription.async_call(
        model=MODEL,
        file_urls=['https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav']
    )
    
    print(f"状态码: {task_response.status_code}")
    if task_response.status_code == HTTPStatus.OK:
        task_id = task_response.output.task_id
        print(f"✅ 任务创建成功，任务 ID: {task_id}")
        
        # 等待完成
        print("\n⏳ 等待处理...")
        transcribe_response = Transcription.wait(task=task_id)
        
        if transcribe_response.status_code == HTTPStatus.OK:
            print("✅ API 配置正确！")
            print(f"结果: {transcribe_response.output}")
        else:
            print(f"❌ 处理失败: {transcribe_response.message}")
    else:
        print(f"❌ 任务创建失败: {task_response}")
        print(f"   错误: {task_response.message if hasattr(task_response, 'message') else 'Unknown'}")
        
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
