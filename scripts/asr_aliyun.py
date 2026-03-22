"""
阿里云ASR语音转录模块
使用DashScope SDK和fun-asr-mtl模型进行语音识别
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
                "未配置阿里云ASR API Key。\n"
                "请设置环境变量: export DASHSCOPE_API_KEY='your_api_key'\n"
                "获取API Key: https://dashscope.console.aliyun.com/"
            )
        
        if not DASHSCOPE_AVAILABLE:
            raise ImportError(
                "dashscope库未安装。\n"
                "请运行: pip install dashscope"
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
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")
        
        file_size = os.path.getsize(audio_file)
        file_size_mb = file_size / 1024 / 1024
        print(f"  [ASR] 音频文件: {os.path.basename(audio_file)} ({file_size_mb:.1f} MB)")
        
        LARGE_FILE_THRESHOLD_MB = 5  # 5MB阈值
        
        if file_size_mb > LARGE_FILE_THRESHOLD_MB:
            print(f"  [ASR] 大文件检测: {file_size_mb:.1f}MB > {LARGE_FILE_THRESHOLD_MB}MB，启用分段处理")
            return self._transcribe_with_segments(audio_file, file_size_mb, language)
        else:
            converted_file = self._convert_audio(audio_file)
            if converted_file != audio_file:
                print(f"  [ASR] 已转换为WAV格式")
            
            try:
                result = self._transcribe_with_upload(converted_file)
            finally:
                if converted_file != audio_file:
                    try:
                        os.unlink(converted_file)
                    except:
                        pass
            
            return result
    
    def _transcribe_with_segments(self, audio_file: str, file_size_mb: float, language: str) -> str:
        """
        分段处理大文件
        
        Args:
            audio_file: 音频文件路径
            file_size_mb: 文件大小(MB)
            language: 语言代码
        
        Returns:
            合并的转录文本
        """
        # 先压缩音频到8kHz，减小体积
        print(f"  [ASR] 压缩音频以加速上传...")
        compressed_file = self._convert_audio(audio_file)
        compressed_size_mb = os.path.getsize(compressed_file) / 1024 / 1024
        
        LARGE_FILE_THRESHOLD_MB = 5
        MAX_SEGMENT_SIZE_MB = 4  # 每段最大 4MB
        MAX_SEGMENT_SIZE_BYTES = MAX_SEGMENT_SIZE_MB * 1024 * 1024
        
        if compressed_size_mb > LARGE_FILE_THRESHOLD_MB:
            
            # 使用ffmpeg分段音频
            segments = self._split_audio_by_size(compressed_file, MAX_SEGMENT_SIZE_BYTES)
            num_segments = len(segments)
            
            print(f"  [ASR] 音频已分段为 {num_segments} 段")
        else:
            segments = [compressed_file]
            num_segments = 1
            print(f"  [ASR] 文件较小，无需分段")
        
        all_texts = []
        for i, segment_file in enumerate(segments):
            print(f"  [ASR] 处理分段 {i+1}/{num_segments}")
            
            try:
                text = self._transcribe_single_file(segment_file)
                all_texts.append(text)
            except Exception as e:
                print(f"  [ASR] 分段{i+1}转录失败: {e}")
                all_texts.append("")  # 保持数组长度
        
        # 合并转录结果
        combined_text = '\n'.join(all_texts)
        print(f"  [ASR] 分段转录完成，总字符数: {len(combined_text)}")
        return combined_text
    
    def _split_audio_by_size(self, audio_file: str, max_size_bytes: int) -> list:
        """
        按文件大小分段音频
        
        Args:
            audio_file: 音频文件路径
            max_size_bytes: 最大字节数
        
        Returns:
            分段文件列表
        """
        # 获取音频总时长
        duration = self._get_audio_duration(audio_file)
        if duration is None:
            print(f"  [ASR] 无法获取音频时长，使用固定分段")
            return [audio_file]  # 无法分段则返回原文件
        
        # 计算分段数量
        file_size = os.path.getsize(audio_file)
        num_segments = int(file_size / max_size_bytes) + 1
        
        segments = []
        for i in range(num_segments):
            start_time = (i * duration) / num_segments
            segment_duration = duration / num_segments
            output_file = f"{audio_file}_part{i}.wav"
            
            self._split_audio_segment(audio_file, start_time, segment_duration, output_file)
            segments.append(output_file)
        
        return segments
    
    def _get_audio_duration(self, audio_file: str) -> Optional[float]:
        """
        获取音频时长
        
        Args:
            audio_file: 音频文件路径
        
        Returns:
            音频时长（秒），失败返回None
        """
        try:
            result = subprocess.run(
                ['ffprobe', '-i', audio_file, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=p=0'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                duration_str = result.stdout.strip()
                if duration_str:
                    return float(duration_str)
        except Exception as e:
            print(f"  [ASR] 获取音频时长失败: {e}")
        
        return None
    
    def _split_audio_segment(self, audio_file: str, start_time: float, duration: float, output_file: str):
        """
        分割音频段
        
        Args:
            audio_file: 源音频文件
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
            output_file: 输出文件路径
        """
        try:
            subprocess.run([
                'ffmpeg', '-y', '-i', audio_file,
                '-ss', str(start_time),
                '-t', str(duration),
                '-acodec', 'copy',
                '-vn', '-sn', '-dn',
                output_file
            ], check=True)
        except Exception as e:
            print(f"  [ASR] ffmpeg分割失败: {e}")
    
    def _transcribe_single_file(self, audio_file: str) -> str:
        """
        转录单个文件
        
        Args:
            audio_file: 音频文件路径
        
        Returns:
            转录文本
        """
        converted_file = self._convert_audio(audio_file)
        if converted_file != audio_file:
            print(f"  [ASR] 已转换为WAV格式")
        
        try:
            result = self._transcribe_with_upload(converted_file)
        finally:
            if converted_file != audio_file:
                try:
                    os.unlink(converted_file)
                except:
                    pass
        
        return result
    
    def _convert_audio(self, audio_file: str) -> str:
        """转换为8kHz单声道WAV，减小文件体积加速上传"""
        compressed_file = audio_file.rsplit('.', 1)[0] + '_8k.wav'
        
        try:
            result = subprocess.run(
                ['ffmpeg', '-y', '-i', audio_file, '-ar', '8000', '-ac', '1', '-sample_fmt', 's16', compressed_file],
                capture_output=True,
                timeout=120
            )
            if result.returncode == 0 and os.path.exists(compressed_file):
                original_size = os.path.getsize(audio_file) / 1024 / 1024
                compressed_size = os.path.getsize(compressed_file) / 1024 / 1024
                print(f"  [ASR] 音频压缩: {original_size:.1f}MB -> {compressed_size:.1f}MB (8kHz mono)")
                return compressed_file
        except Exception as e:
            print(f"  [ASR] ffmpeg压缩失败: {e}")
        
        return audio_file
    
    def _transcribe_with_upload(self, audio_file: str) -> str:
        """使用纯 curl 完成上传+异步ASR+轮询，避免 Python SSL 问题"""
        import subprocess
        import json
        
        start_time = time.time()
        api_key = self.api_key
        base_url = 'https://dashscope.aliyuncs.com/api/v1'
        
        try:
            # 1. 上传文件
            print(f"  [ASR] 上传文件到DashScope...")
            result = subprocess.run([
                'curl', '-s', '-X', 'POST', f'{base_url}/files',
                '-F', f'file=@{audio_file}',
                '-F', 'purpose=file-extract',
                '-H', f'Authorization: Bearer {api_key}'
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                raise RuntimeError(f"curl上传失败: {result.stderr}")
            
            response = json.loads(result.stdout)
            uploaded = response.get('data', {}).get('uploaded_files', [])
            if not uploaded:
                raise RuntimeError(f"文件上传失败: {result.stdout}")
            
            file_id = uploaded[0].get('file_id')
            print(f"  [ASR] 文件上传成功 (file_id: {file_id[:20]}...)")
            
            # 2. 获取文件URL
            file_info_result = subprocess.run([
                'curl', '-s', '-X', 'GET', f'{base_url}/files/{file_id}',
                '-H', f'Authorization: Bearer {api_key}'
            ], capture_output=True, text=True, timeout=30)
            
            file_info = json.loads(file_info_result.stdout)
            file_url = file_info.get('data', {}).get('url')
            if not file_url:
                raise RuntimeError(f"获取文件URL失败: {file_info_result.stdout}")
            
            # 3. 提交异步ASR任务
            print(f"  [ASR] 提交异步ASR任务...")
            task_result = subprocess.run([
                'curl', '-s', '-X', 'POST',
                f'{base_url}/services/audio/asr/transcription',
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-H', 'X-DashScope-Async: enable',
                '-d', json.dumps({
                    "model": self.MODEL,
                    "input": {"file_urls": [file_url]},
                    "parameters": {"language_hints": ["zh"]}
                })
            ], capture_output=True, text=True, timeout=30)
            
            task_data = json.loads(task_result.stdout)
            task_id = task_data.get('output', {}).get('task_id')
            if not task_id:
                raise RuntimeError(f"ASR任务提交失败: {task_result.stdout}")
            
            print(f"  [ASR] 任务ID: {task_id}，等待转录完成...")
            
            # 4. 轮询任务状态
            max_wait = 600  # 最长等10分钟
            poll_interval = 5
            elapsed_poll = 0
            transcription_url = None
            
            while elapsed_poll < max_wait:
                time.sleep(poll_interval)
                elapsed_poll += poll_interval
                
                status_result = subprocess.run([
                    'curl', '-s', '-X', 'GET',
                    f'{base_url}/tasks/{task_id}',
                    '-H', f'Authorization: Bearer {api_key}'
                ], capture_output=True, text=True, timeout=15)
                
                status_data = json.loads(status_result.stdout)
                task_status = status_data.get('output', {}).get('task_status', '')
                
                if task_status in ('SUCCEEDED', 'SUCCESS'):
                    # 获取转录结果URL
                    output = status_data.get('output', {})
                    results = output.get('results', [])
                    if results and isinstance(results, list):
                        transcription_url = results[0].get('transcription_url') if isinstance(results[0], dict) else None
                    break
                elif task_status in ('FAILED', 'ERROR'):
                    raise RuntimeError(f"ASR任务失败: {status_result.stdout}")
                else:
                    if int(elapsed_poll) % 30 == 0:
                        print(f"  [ASR] 转录中... ({int(elapsed_poll)}s)")
            
            if not transcription_url and task_status in ('SUCCEEDED', 'SUCCESS'):
                # 尝试从 output 直接取文本
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
                fetch_result = subprocess.run([
                    'curl', '-s', transcription_url
                ], capture_output=True, text=True, timeout=30)
                
                trans_data = json.loads(fetch_result.stdout)
                texts = []
                if 'transcripts' in trans_data:
                    for item in trans_data['transcripts']:
                        if isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'])
                
                elapsed = time.time() - start_time
                print(f"  [ASR] 转录完成 (耗时 {elapsed:.1f}s)")
                
                # 清理上传的文件
                subprocess.run([
                    'curl', '-s', '-X', 'DELETE', f'{base_url}/files/{file_id}',
                    '-H', f'Authorization: Bearer {api_key}'
                ], capture_output=True, timeout=10)
                
                return '\n'.join(texts) if texts else ''
            
            raise RuntimeError(f"ASR任务超时或未获取到结果: {status_result.stdout}")
                
        except Exception as e:
            raise RuntimeError(f"ASR转录异常: {str(e)}")
    
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
                    elif 'text' in result:
                        texts.append(result['text'])
                elif hasattr(result, 'transcription_url'):
                    text = self._fetch_transcription(result.transcription_url)
                    if text:
                        texts.append(text)
                elif hasattr(result, 'transcription_text'):
                    texts.append(result.transcription_text)
                elif hasattr(result, 'text'):
                    texts.append(result.text)
            if texts:
                return '\n'.join(texts)
        
        output_dict = output if isinstance(output, dict) else (vars(output) if hasattr(output, '__dict__') else {})
        
        if 'results' in output_dict:
            texts = []
            for result in output_dict['results']:
                if isinstance(result, dict):
                    if 'transcription_url' in result:
                        text = self._fetch_transcription(result['transcription_url'])
                        if text:
                            texts.append(text)
                    elif 'transcription_text' in result:
                        texts.append(result['transcription_text'])
                    elif 'text' in result:
                        texts.append(result['text'])
            if texts:
                return '\n'.join(texts)
        
        if 'transcription_text' in output_dict:
            return output_dict['transcription_text']
        
        return str(output)
    
    def _fetch_transcription(self, url: str) -> str:
        import urllib.request
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                texts = []
                if 'transcripts' in data:
                    for item in data['transcripts']:
                        if 'text' in item:
                            texts.append(item['text'])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'])
                elif isinstance(data, dict) and 'text' in data:
                    texts.append(data['text'])
                return '\n'.join(texts) if texts else ''
        except Exception as e:
            print(f"  [ASR] Warning: Failed to fetch transcription: {e}")
            return ''


def transcribe_file(audio_file: str, api_key: str = None) -> str:
    asr = AliyunASR(api_key=api_key)
    return asr.transcribe(audio_file)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python asr_aliyun.py <音频文件> [API_KEY]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        text = transcribe_file(audio_file, api_key)
        print(f"\n[OK] 转录完成:\n{text}")
    except Exception as e:
        print(f"\n[ERROR] 转录失败: {e}")
        sys.exit(1)
