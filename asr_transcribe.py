#!/usr/bin/env python3
"""
语音识别脚本：使用 DashScope ASR API 将视频音频转写为文本
"""
import os
import json
from http import HTTPStatus
import dashscope
from dashscope.audio.asr import Transcription
from dashscope import Files

# 配置参数
API_KEY = "sk-601abb31fe354b6daf24067c7a56adc6"
MODEL = "fun-asr-mtl"
AUDIO_FILE = "/home/ubuntu/.openclaw/workspace-video-learner/audio_output.wav"
OUTPUT_FILE = "/home/ubuntu/.openclaw/workspace-video-learner/transcription_result.json"

def transcribe_audio():
    """
    使用 DashScope ASR API 进行语音识别
    """
    # 设置 API KEY
    dashscope.api_key = API_KEY

    print("=" * 60)
    print("🎤 DashScope 语音识别")
    print("=" * 60)
    print(f"音频文件：{AUDIO_FILE}")
    print(f"音频大小：{os.path.getsize(AUDIO_FILE) / (1024*1024):.2f} MB")
    print(f"识别模型：{MODEL}")
    print("=" * 60)

    # 步骤 1: 上传文件到 DashScope
    print("\n📤 步骤 1: 上传音频文件到 DashScope（可能需要几分钟）...")
    print("   文件较大，请耐心等待...")
    try:
        file_response = Files.upload(file_path=AUDIO_FILE, purpose='inference')
        print(f"   上传响应状态码: {file_response.status_code}")
        
        if file_response.status_code != HTTPStatus.OK:
            print(f"❌ 文件上传失败")
            print(f"   响应: {file_response}")
            return False
        
        file_id = file_response.output.file_id
        file_url = file_response.output.url
        print(f"✅ 文件上传成功!")
        print(f"   File ID: {file_id}")
        print(f"   File URL: {file_url}")
    except Exception as e:
        print(f"❌ 文件上传异常：{e}")
        import traceback
        traceback.print_exc()
        return False

    # 步骤 2: 创建转写任务
    print("\n📝 步骤 2: 创建语音识别任务...")
    try:
        task_response = Transcription.async_call(
            model=MODEL,
            file_urls=[file_url]
        )
        
        if task_response.status_code != HTTPStatus.OK:
            print(f"❌ 任务创建失败：{task_response}")
            return False
        
        task_id = task_response.output.task_id
        print(f"✅ 任务创建成功!")
        print(f"   任务 ID: {task_id}")
    except Exception as e:
        print(f"❌ 任务创建异常：{e}")
        return False

    # 步骤 3: 等待任务完成
    print("\n⏳ 步骤 3: 等待处理完成...")
    try:
        transcribe_response = Transcription.wait(task=task_id)
        
        if transcribe_response.status_code != HTTPStatus.OK:
            print(f"❌ 识别失败，状态码：{transcribe_response.status_code}")
            print(f"   错误信息：{transcribe_response.message}")
            return False
        
        output = transcribe_response.output
        task_status = output.get('task_status', 'UNKNOWN')
        
        if task_status == 'SUCCEEDED':
            print(f"✅ 语音识别完成!")
            
            # 提取转写结果
            results = output.get('results', [])
            if results:
                result = results[0]
                if 'transcription_url' in result:
                    # 从 URL 下载转写结果
                    import urllib.request
                    print(f"📥 下载转写结果...")
                    with urllib.request.urlopen(result['transcription_url']) as response:
                        transcription_data = json.loads(response.read().decode('utf-8'))
                    
                    # 保存结果
                    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(transcription_data, f, ensure_ascii=False, indent=2)
                    print(f"✅ 结果已保存到：{OUTPUT_FILE}")
                    
                    # 打印转写文本
                    print("\n" + "=" * 60)
                    print("📄 转写文本:")
                    print("=" * 60)
                    if 'transcripts' in transcription_data:
                        for transcript in transcription_data['transcripts']:
                            if 'text' in transcript:
                                print(transcript['text'])
                    print("=" * 60)
                    return True
                else:
                    print(f"❌ 结果中没有 transcription_url")
                    print(f"   完整结果：{json.dumps(result, indent=2, ensure_ascii=False)}")
                    return False
            else:
                print(f"❌ 没有识别结果")
                return False
        else:
            print(f"❌ 任务状态：{task_status}")
            print(f"   错误代码：{output.get('code', 'UNKNOWN')}")
            print(f"   错误信息：{output.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ 等待任务完成时异常：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 检查音频文件是否存在
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ 音频文件不存在：{AUDIO_FILE}")
        print("请先运行 extract_audio.py 提取音频")
        exit(1)
    
    success = transcribe_audio()
    exit(0 if success else 1)
