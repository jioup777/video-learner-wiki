"""
GLM笔记生成模块
使用GLM编码套餐专属Coding端点生成结构化学习笔记
"""

import os
import json
import time
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.error


class GLMNoteGenerator:
    API_URL = "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions"
    MODEL = "glm-4-flash"  # GLM编码套餐专属模型
    
    SYSTEM_PROMPT = """你是一位专业的学习笔记整理专家。请根据视频转录文本，整理成结构化的学习笔记。

输出格式要求（Markdown）：
1. 核心主题（一句话概括）
2. 核心观点（3-5条，每条简洁明了）
3. 典型案例（如有，提取具体例子）
4. 识别方法（如有，提取方法论）
5. 防骗建议（如适用）
6. 核心金句（3-5句，简短有力）

注意事项：
- 加粗关键内容
- 保持逻辑清晰
- 提取精华，去除废话
- 如内容不适用某部分，可省略该部分"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GLM_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "未配置GLM API Key。\n"
                "请设置环境变量: export GLM_API_KEY='your_api_key'\n"
                "获取API Key: https://open.bigmodel.cn/"
            )
    
    def generate(self, transcript: str, video_title: str = "视频笔记") -> str:
        """
        生成学习笔记
        
        Args:
            transcript: 转录文本
            video_title: 视频标题
        
        Returns:
            笔记内容（Markdown格式）
        """
        print(f"  [GLM] Transcription: {len(transcript)} chars")
        
        generated_content = self._call_api(transcript, video_title)
        
        note = self._format_note(generated_content, video_title, transcript)
        
        return note
    
    def _call_api(self, transcript: str, video_title: str) -> str:
        """调用GLM API"""
        user_prompt = f"""视频标题：{video_title}

转录文本：
{transcript}

请根据以上内容生成结构化学习笔记。"""
        
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 4000
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        try:
            req = urllib.request.Request(
                self.API_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'choices' not in result or len(result['choices']) == 0:
                    raise ValueError(f"API返回格式异常: {result}")
                
                content = result['choices'][0]['message']['content']
                elapsed = time.time() - start_time
                
                usage = result.get('usage', {})
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                
                print(f"  [OK] GLM call success (elapsed {elapsed:.1f}s)")
                print(f"     输入: {input_tokens} tokens, 输出: {output_tokens} tokens")
                
                return content
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"GLM API错误 ({e.code}): {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"GLM API网络错误: {e.reason}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"GLM API响应解析失败: {e}")
    
    def _format_note(self, generated_content: str, video_title: str, transcript: str) -> str:
        """格式化最终笔记"""
        now = datetime.now()
        
        note = f"""# {video_title}

## 📹 视频信息
- **视频标题**: {video_title}
- **处理时间**: {now.strftime('%Y-%m-%d %H:%M')}
- **生成引擎**: GLM-4-Flash

---

{generated_content}

---

## 📝 完整转录内容

<details>
<summary>点击展开完整转录</summary>

```
{transcript}
```

</details>

---

*🤖 此笔记由 Video Learner 使用 GLM-4-Flash 智能生成*
*📅 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return note


def generate_note(transcript: str, video_title: str, api_key: str = None) -> str:
    """便捷函数：生成笔记"""
    generator = GLMNoteGenerator(api_key=api_key)
    return generator.generate(transcript, video_title)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python note_generator.py <转录文件> [视频标题] [API_KEY]")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    video_title = sys.argv[2] if len(sys.argv) > 2 else "视频笔记"
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(transcript_file):
        print(f"❌ 文件不存在: {transcript_file}")
        sys.exit(1)
    
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()
    
    try:
        note = generate_note(transcript, video_title, api_key)
        
        output_file = transcript_file.replace('.txt', '_note.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(note)
        
        print(f"\n✅ 笔记已生成: {output_file}")
        
    except Exception as e:
        print(f"\n❌ 笔记生成失败: {e}")
        sys.exit(1)
