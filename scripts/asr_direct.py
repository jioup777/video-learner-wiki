#!/usr/bin/env python3
"""
直接用 requests 调用 DashScope ASR API，绕过 dashscope SDK 的 SSL 问题
"""
import os
import sys
import json
import time
import requests

API_KEY = os.getenv('DASHSCOPE_API_KEY') or os.getenv('ALIYUN_ASR_API_KEY')
BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
MODEL = "fun-asr-mtl"


def upload_file(file_path: str) -> dict:
    """上传文件到 DashScope"""
    url = f"{BASE_URL}/files"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    file_size_mb = os.path.getsize(file_path) / 1024 / 1024
    print(f"  [ASR] 上传文件: {os.path.basename(file_path)} ({file_size_mb:.1f} MB)")
    
    with open(file_path, 'rb') as f:
        resp = requests.post(url, headers=headers,
                           files={'file': (os.path.basename(file_path), f)},
                           data={'purpose': 'inference'},
                           timeout=300)
    
    if resp.status_code != 200:
        raise RuntimeError(f"上传失败: {resp.status_code} {resp.text}")
    
    result = resp.json()
    file_id = result['data']['uploaded_files'][0]['file_id']
    print(f"  [ASR] 上传成功, file_id: {file_id}")
    return file_id


def get_file_url(file_id: str) -> str:
    """获取文件URL"""
    url = f"{BASE_URL}/files/{file_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"获取文件URL失败: {resp.status_code} {resp.text}")
    return resp.json()['data']['url']


def transcribe(file_urls: list) -> dict:
    """提交转录任务"""
    url = f"{BASE_URL}/services/audio/asr/transcription"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "input": {"file_urls": file_urls},
        "parameters": {}
    }
    resp = requests.post(url, headers=headers, json=data, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"提交转录失败: {resp.status_code} {resp.text}")
    result = resp.json()
    return result['output']['task_id']


def wait_task(task_id: str, interval: int = 5, max_wait: int = 300) -> dict:
    """等待任务完成"""
    url = f"{BASE_URL}/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    start = time.time()
    while time.time() - start < max_wait:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"查询任务失败: {resp.status_code} {resp.text}")
        
        result = resp.json()['output']
        status = result.get('task_status', '')
        
        if status == 'SUCCEEDED':
            return result
        elif status == 'FAILED':
            raise RuntimeError(f"转录失败: {result.get('message', 'unknown')}")
        
        print(f"  [ASR] 等待中... 状态: {status}")
        time.sleep(interval)
    
    raise RuntimeError(f"超时 ({max_wait}s)")


def fetch_transcription(url: str) -> str:
    """获取转录文本"""
    resp = requests.get(url, timeout=30)
    data = resp.json()
    texts = []
    if 'transcripts' in data:
        for t in data['transcripts']:
            if 'text' in t:
                texts.append(t['text'])
    return '\n'.join(texts)


def process_audio(file_path: str) -> str:
    """处理单个音频文件"""
    # 上传
    file_id = upload_file(file_path)
    
    # 获取URL
    file_url = get_file_url(file_id)
    
    # 提交转录
    task_id = transcribe([file_url])
    print(f"  [ASR] 任务ID: {task_id}")
    
    # 等待完成
    result = wait_task(task_id)
    
    # 获取结果
    results = result.get('results', [])
    if not results:
        raise RuntimeError("没有转录结果")
    
    transcription_url = results[0].get('transcription_url')
    if not transcription_url:
        raise RuntimeError("没有转录URL")
    
    text = fetch_transcription(transcription_url)
    
    # 清理文件
    try:
        requests.delete(f"{BASE_URL}/files/{file_id}", 
                       headers={"Authorization": f"Bearer {API_KEY}"}, timeout=10)
    except:
        pass
    
    return text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python asr_direct.py <音频文件> [--output 输出文件]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    output_file = None
    if '--output' in sys.argv:
        output_file = sys.argv[sys.argv.index('--output') + 1]
    
    if not os.path.exists(audio_file):
        print(f"文件不存在: {audio_file}")
        sys.exit(1)
    
    try:
        text = process_audio(audio_file)
        print(f"\n[OK] 转录完成 ({len(text)} 字符)")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"[OK] 已保存: {output_file}")
        else:
            print(text)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
