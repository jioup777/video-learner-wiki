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

# Fix SSL issue with DashScope (SECLEVEL compatibility)
import requests as _requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class _TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

_monkey_session = _requests.Session()
_monkey_session.mount('https://', _TLSAdapter())
# Monkey-patch requests to use TLS adapter for DashScope
_orig_post = _requests.post
_orig_get = _requests.get
_orig_request = _requests.Session.request

def _patched_post(url, *args, **kwargs):
    if 'dashscope.aliyuncs.com' in str(url):
        return _monkey_session.post(url, *args, **kwargs)
    return _orig_post(url, *args, **kwargs)

def _patched_get(url, *args, **kwargs):
    if 'dashscope.aliyuncs.com' in str(url):
        return _monkey_session.get(url, *args, **kwargs)
    return _orig_get(url, *args, **kwargs)

_requests.post = _patched_post
_requests.get = _patched_get


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
            print(f"  [ASR] 大文件检测：{file_size_mb:.1f}MB > {LARGE_FILE_THRESHOLD_MB}MB，启用网盘中转")
            return self._transcribe_via_relay(audio_file, file_size_mb, language)
        
        # 小文件直接上传到 DashScope
        return self._transcribe_with_upload(audio_file)
    
    def _upload_to_litterbox(self, audio_file: str, validity: str = "72h") -> str:
        """上传文件到 litterbox.catbox.moe 并返回公开 URL
        
        Args:
            audio_file: 文件路径
            validity: 有效期 (1h/12h/24h/72h)
            
        Returns:
            公开访问 URL
        """
        import subprocess
        import tempfile
        
        print(f"  [中转] 上传到 litterbox.catbox.moe (有效期: {validity})...")
        print(f"  [中转] 文件大小: {os.path.getsize(audio_file)/1024/1024:.1f} MB")
        print(f"  [中转] 预计上传时间: {os.path.getsize(audio_file)/1024/60:.0f} 分钟（上行带宽较低）")
        
        # 用临时文件存储上传结果
        result_file = tempfile.mktemp(suffix='.litterbox')
        
        # 后台运行 curl 上传
        proc = subprocess.Popen(
            ['curl', '-s', '-F', 'reqtype=fileupload', '-F', f'time={validity}',
             '-F', f'fileToUpload=@{audio_file}',
             'https://litterbox.catbox.moe/resources/internals/api.php'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        
        # 定期检查进度（每30分钟报告一次）
        check_interval = 30 * 60  # 30 分钟
        start_time = time.time()
        report_count = 0
        
        while proc.poll() is None:
            try:
                proc.wait(timeout=check_interval)
            except subprocess.TimeoutExpired:
                report_count += 1
                elapsed_min = (time.time() - start_time) / 60
                print(f"  [中转] 仍在上传中... (已等待 {elapsed_min:.0f} 分钟)")
        
        if proc.returncode != 0:
            raise RuntimeError(f"litterbox 上传失败: {proc.stderr.read()[:200]}")
        
        url = proc.stdout.read().strip()
        if not url.startswith('http'):
            raise RuntimeError(f"litterbox 返回异常: {url[:200]}")
        
        elapsed_min = (time.time() - start_time) / 60
        print(f"  [中转] 上传完成！耗时 {elapsed_min:.1f} 分钟")
        print(f"  [中转] 公开链接: {url}")
        return url
    
    def _transcribe_via_relay(self, audio_file: str, file_size_mb: float, language: str = "zh") -> str:
        """大文件通过网盘中转 + 阿里云 ASR（不分段）
        
        流程: 上传 litterbox → 拿到 URL → 提交阿里云 ASR → 轮询结果
        """
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        api_key = self.api_key
        base_url = 'https://dashscope.aliyuncs.com/api/v1'
        start_time = time.time()
        
        # 1. 上传到 litterbox
        file_url = self._upload_to_litterbox(audio_file, validity="72h")
        
        # 2. 提交阿里云 ASR 任务
        print(f"  [ASR] 提交异步 ASR 任务...")
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable'
        }
        payload = {
            "model": self.MODEL,
            "input": {"file_urls": [file_url]},
            "parameters": {"language_hints": [language]}
        }
        
        task_resp = requests.post(
            f'{base_url}/services/audio/asr/transcription',
            headers=headers, json=payload, timeout=30
        )
        task_data = task_resp.json()
        task_id = task_data.get('output', {}).get('task_id')
        if not task_id:
            raise RuntimeError(f"ASR 任务提交失败：{task_data}")
        
        print(f"  [ASR] 任务 ID: {task_id}，等待转录完成...")
        
        # 3. 轮询任务状态（每30分钟报告一次，阿里云处理大文件可能需要较长时间）
        max_wait = 3600  # 最长等 1 小时
        poll_interval = 30  # 每 30 秒检查一次
        report_every = 60  # 每 30 分钟报告一次
        elapsed_poll = 0
        transcription_url = None
        task_status = ''
        
        while elapsed_poll < max_wait:
            time.sleep(poll_interval)
            elapsed_poll += poll_interval
            
            status_resp = requests.get(
                f'{base_url}/tasks/{task_id}',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=15
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
                # 定期报告
                if int(elapsed_poll) % report_every == 0:
                    print(f"  [ASR] 阿里云转录中... ({int(elapsed_poll)}s)")
        
        if transcription_url:
            # 4. 下载转录结果
            print(f"  [ASR] 获取转录结果...")
            fetch_resp = requests.get(transcription_url, timeout=60)
            trans_data = fetch_resp.json()
            
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
            ext = os.path.splitext(audio_file)[1]
            output = f"{os.path.splitext(audio_file)[0]}_part{i}{ext}"
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
                    timeout=30
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
                headers=headers, json=payload, timeout=30
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
                    timeout=15
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
                fetch_resp = requests.get(transcription_url, timeout=60)
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
