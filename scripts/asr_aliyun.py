"""
阿里云 ASR 语音转录模块
使用 DashScope SDK 和 fun-asr-mtl 模型进行语音识别
"""

import os
import json
import time
import subprocess
from typing import Optional
from http import HTTPStatus

try:
    import dashscope
    from dashscope.audio.asr import Transcription
    from dashscope import Files
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False


class AliyunASR:
    MODEL = "fun-asr-mtl"
    
    def __init__(self, api_key: str = None):
        # 优先级：传入参数 > 环境变量 > .env 文件
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('ALIYUN_ASR_API_KEY')
        if not self.api_key:
            env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for ln in f:
                        ln = ln.strip()
                        if ln and not ln.startswith('#') and '=' in ln:
                            k, v = ln.split('=', 1)
                            if k.strip() in ('ALIYUN_ASR_API_KEY', 'DASHSCOPE_API_KEY'):
                                self.api_key = v.strip().strip('"').strip("'")
                                break

        
        if not self.api_key:
            raise ValueError(
                "未配置阿里云 ASR API Key。\n"
                "请设置环境变量：export DASHSCOPE_API_KEY='your_api_key'\n"
                "获取 API Key: https://dashscope.console.aliyun.com/"
            )
        
        if not DASHSCOPE_AVAILABLE:
            raise ImportError(
                "dashscope 库未安装。\n"
                "请运行：pip install dashscope"
            )
        
        dashscope.api_key = self.api_key
    
    def transcribe(self, audio_file: str, language: str = "zh") -> str:
        """
        转录音频文件
        
        Args:
            audio_file: 音频文件路径
            language: 语言代码 (zh/en)
        
        Returns:
            转录文本
        """
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"音频文件不存在：{audio_file}")
        
        file_size = os.path.getsize(audio_file)
        file_size_mb = file_size / 1024 / 1024
        print(f"  [ASR] 音频文件：{os.path.basename(audio_file)} ({file_size_mb:.1f} MB)")
        
        LARGE_FILE_THRESHOLD_MB = 5  # 5MB 阈值
        
        if file_size_mb > LARGE_FILE_THRESHOLD_MB:
            print(f"  [ASR] 大文件检测：{file_size_mb:.1f}MB > {LARGE_FILE_THRESHOLD_MB}MB，启用分段处理")
            return self._transcribe_with_segments(audio_file, file_size_mb, language)
        
        # 小文件也先压缩到 8kHz mono 再处理，减小体积
        converted_file = self._ensure_wav_format(audio_file)
        return self._transcribe_with_upload(converted_file)
    
    def _transcribe_with_segments(self, audio_file: str, file_size_mb: float, language: str = "zh") -> str:
        """大文件分段处理"""
        import subprocess
        import tempfile
        
        print(f"  [ASR] 压缩音频以加速上传...")
        compressed = self._compress_audio(audio_file)
        print(f"  [ASR] 音频压缩：{file_size_mb:.1f}MB -> {os.path.getsize(compressed)/1024/1024:.1f}MB (8kHz mono)")
        
        # 分段（每段 9 分钟，留余量）
        segment_duration = 540  # 9 分钟
        segments = self._split_audio(compressed, segment_duration)
        print(f"  [ASR] 音频已分段为 {len(segments)} 段")
        
        all_texts = []
        for i, seg in enumerate(segments, 1):
            print(f"  [ASR] 处理分段 {i}/{len(segments)}")
            text = self._transcribe_segment(seg)
            if text:
                all_texts.append(text)
            # 清理临时文件
            try:
                os.remove(seg)
            except:
                pass
        
        # 清理压缩文件
        try:
            os.remove(compressed)
        except:
            pass
        
        return '\n'.join(all_texts)
    
    def _compress_audio(self, audio_file: str) -> str:
        """压缩音频为 8kHz 单声道 mono，减小上传体积"""
        import subprocess
        import tempfile
        
        base = os.path.splitext(audio_file)[0]
        output = f"{base}_8k.wav"
        
        if os.path.exists(output):
            return output
        
        cmd = [
            'ffmpeg', '-y', '-i', audio_file,
            '-ar', '8000', '-ac', '1',
            output
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output
    
    def _split_audio(self, audio_file: str, duration: int) -> list:
        """按 duration 秒分割音频"""
        import subprocess
        
        segments = []
        # 获取总时长
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_file],
            capture_output=True, text=True, check=True
        )
        total_duration = float(result.stdout.strip())
        
        # 分割
        n_segments = int(total_duration // duration) + 1
        for i in range(n_segments):
            output = f"{os.path.splitext(audio_file)[0]}_part{i}.wav"
            cmd = [
                'ffmpeg', '-y', '-i', audio_file,
                '-ss', str(i * duration),
                '-t', str(duration),
                '-c', 'copy',
                output
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            if os.path.exists(output):
                segments.append(output)
        
        return segments
    
    def _ensure_wav_format(self, audio_file: str) -> str:
        """保持原格式，不做转换（阿里云 ASR 支持 wav/mp3/m4a/aac）"""
        # 阿里云 ASR 支持多种格式，直接返回原文件
        # 如果需要压缩，可以在这里用 ffmpeg 降采样到 8kHz mono
        return audio_file
    
    def _transcribe_segment(self, audio_file: str) -> str:
        """转录单个分段"""
        converted = self._ensure_wav_format(audio_file)
        if converted != audio_file:
            print(f"  [ASR] 已转换为 WAV 格式")
        return self._transcribe_with_upload(converted)
    
    def _transcribe_with_upload(self, audio_file: str) -> str:
        """使用纯 HTTP requests 上传文件 + 异步 ASR + 轮询 (绕过 SDK)"""
        import requests
        import urllib3
        import mimetypes
        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        start_time = time.time()
        api_key = self.api_key
        base_url = 'https://dashscope.aliyuncs.com/api/v1'
        
        try:
            # 1. 用 requests 直接上传文件 (绕过 dashscope SDK)
            print(f"  [ASR] 上传文件到 DashScope...")
            upload_url = f'{base_url}/files'
            
            # 获取文件 MIME 类型
            mime_type, _ = mimetypes.guess_type(audio_file)
            if not mime_type:
                mime_type = 'audio/wav'
            
            # multipart/form-data 上传
            with open(audio_file, 'rb') as f:
                files = {'file': (os.path.basename(audio_file), f, mime_type)}
                data = {'purpose': 'file-extract'}
                headers = {'Authorization': f'Bearer {api_key}'}
                
                upload_resp = requests.post(upload_url, headers=headers, data=data, files=files, timeout=300)
            
            if upload_resp.status_code != 200:
                raise RuntimeError(f"文件上传失败：{upload_resp.status_code} - {upload_resp.text[:200]}")
            
            upload_data = upload_resp.json()
            # 响应格式可能是 {'data': {...}} 或 {'output': {...}}
            result = upload_data.get('data') or upload_data.get('output', {})
            file_id = result.get('uploaded_files', [{}])[0].get('file_id')
            if not file_id:
                raise RuntimeError(f"上传响应无 file_id: {upload_data}")
            
            file_url = result.get('uploaded_files', [{}])[0].get('url')
            print(f"  [ASR] 文件上传成功 (file_id: {file_id[:20]}...)")
            
            # 2. 如果响应中没有 URL，需要单独获取
            if not file_url:
                print(f"  [ASR] 获取文件 URL...")
                file_info_resp = requests.get(
                    f'{base_url}/files/{file_id}',
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=30, verify=False
                )
                if file_info_resp.status_code != 200:
                    print(f"  [ASR] 获取 URL 失败: {file_info_resp.status_code} - {file_info_resp.text[:100]}")
                    raise RuntimeError(f"获取文件 URL 失败: {file_info_resp.status_code}")
                
                file_info_data = file_info_resp.json()
                file_url = (file_info_data.get('data') or file_info_data.get('output', {})).get('url')
                if not file_url:
                    raise RuntimeError(f"获取文件 URL 响应无 url: {file_info_data}")
            
            if not file_url:
                raise RuntimeError(f"获取文件 URL 失败")
            print(f"  [ASR] 文件 URL 获取成功")
            
            # 3. 提交异步 ASR 任务
            print(f"  [ASR] 提交异步 ASR 任务...")
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'X-DashScope-Async': 'enable'
            }
            payload = {
                "model": self.MODEL,
                "input": {"file_urls": [file_url]},
                "parameters": {"language_hints": ["zh"]}
            }
            
            task_resp = requests.post(
                f'{base_url}/services/audio/asr/transcription',
                headers=headers, json=payload, timeout=30, verify=False
            )
            task_data = task_resp.json()
            task_id = task_data.get('output', {}).get('task_id')
            if not task_id:
                raise RuntimeError(f"ASR 任务提交失败：{task_data}")
            
            print(f"  [ASR] 任务 ID: {task_id}，等待转录完成...")
            
            # 4. 轮询任务状态
            max_wait = 600
            poll_interval = 5
            elapsed_poll = 0
            transcription_url = None
            task_status = ''
            
            while elapsed_poll < max_wait:
                time.sleep(poll_interval)
                elapsed_poll += poll_interval
                
                status_resp = requests.get(
                    f'{base_url}/tasks/{task_id}',
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=15, verify=False
                )
                status_data = status_resp.json()
                task_status = status_data.get('output', {}).get('task_status', '')
                
                if task_status in ('SUCCEEDED', 'SUCCESS'):
                    output = status_data.get('output', {})
                    results = output.get('results', [])
                    if results and isinstance(results, list):
                        transcription_url = results[0].get('transcription_url') if isinstance(results[0], dict) else None
                    break
                elif task_status in ('FAILED', 'ERROR'):
                    raise RuntimeError(f"ASR 任务失败：{status_data}")
                else:
                    if int(elapsed_poll) % 30 == 0:
                        print(f"  [ASR] 转录中... ({int(elapsed_poll)}s)")
            
            if not transcription_url and task_status in ('SUCCEEDED', 'SUCCESS'):
                output = status_data.get('output', {})
                results = output.get('results', [])
                if results:
                    texts = []
                    for r in results:
                        if isinstance(r, dict):
                            t = r.get('transcription_text') or r.get('text', '')
                            if t:
                                texts.append(t)
                    if texts:
                        return '\n'.join(texts)
            
            if transcription_url:
                # 5. 下载转录结果
                print(f"  [ASR] 获取转录结果...")
                fetch_resp = requests.get(transcription_url, timeout=60, verify=False)
                trans_data = fetch_resp.json()
                
                # 新格式：transcripts[0].text
                texts = []
                if 'transcripts' in trans_data:
                    for item in trans_data['transcripts']:
                        if isinstance(item, dict):
                            text = item.get('text', '')
                            if text:
                                texts.append(text)
                
                elapsed = time.time() - start_time
                print(f"  [ASR] 转录完成 (耗时 {elapsed:.1f}s)，字符数: {sum(len(t) for t in texts)}")
                
                return '\n'.join(texts) if texts else ''
            
            raise RuntimeError(f"ASR 任务超时或未获取到结果：{status_data}")
                
        except Exception as e:
            raise RuntimeError(f"ASR 转录异常：{str(e)}")
    
    def _extract_text(self, output) -> str:
        if hasattr(output, 'results'):
            results = output.results
            texts = []
            for result in results:
                if isinstance(result, dict):
                    if 'transcription_url' in result:
                        text = self._fetch_transcription(result['transcription_url'])
                        if text:
                            texts.append(text)
                    elif 'transcription_text' in result:
                        texts.append(result['transcription_text'])
            
            return '\n'.join(texts) if texts else ''
        return ''
    
    def _fetch_transcription(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            texts = []
            if 'transcripts' in data:
                for item in data['transcripts']:
                    if isinstance(item, dict) and 'text' in item:
                        texts.append(item['text'])
            return '\n'.join(texts) if texts else ''
        except Exception as e:
            print(f"  [ASR] 获取转录结果失败：{e}")
            return ''


def main():
    import argparse
    parser = argparse.ArgumentParser(description='阿里云 ASR 语音转录')
    parser.add_argument('audio_file', help='音频文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--language', '-l', default='zh', help='语言代码')
    args = parser.parse_args()
    
    asr = AliyunASR()
    text = asr.transcribe(args.audio_file, args.language)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\n[OK] 转录完成：{args.output}")
        print(f"     字符数：{len(text)}")
    else:
        print(f"\n[OK] 转录完成:")
        print(text[:500] + "..." if len(text) > 500 else text)


if __name__ == '__main__':
    main()
