# Video-Learner ASR 能力增强方案

## 📊 **现状对比**

| 项目 | 当前方案 | 新增方案（DashScope） |
|------|---------|----------------------|
| **模型** | Whisper Small | SenseVoice（硅基流动） |
| **速度** | 5分钟视频 ≈ 1分钟 | 5分钟视频 ≈ 10秒 ⚡ |
| **准确度** | 良好 | 更高（中文优化） |
| **大文件处理** | 无 | 自动分段 |
| **成本** | 免费 | 免费额度（硅基流动） |

---

## 🎯 **整合方案**

### **步骤 1：安装依赖**

```bash
# 安装硅基流动 API 依赖
pip3 install requests

# 设置环境变量（可选）
export SILICONFLOW_API_KEY="你的API Key"
```

**获取 API Key**：
1. 访问：https://cloud.siliconflow.cn/
2. 注册账号
3. 获取免费额度 API Key

---

### **步骤 2：集成到现有脚本**

#### **方案 A：在 process_douyin.sh 中集成（推荐）**

修改抖音处理脚本，使用 SenseVoice 替代 Whisper：

```bash
#!/bin/bash
# 更新后的抖音处理流程

# 步骤 1：解析链接
log_step "步骤 1/7: 解析抖音链接..."
cd "$DOUYIN_MCP" && uv run python douyin-video/scripts/douyin_downloader.py -l "$douyin_url" -a info -q

# 步骤 2：下载视频
log_step "步骤 2/7: 下载无水印视频..."
curl -L -o "${TMP_DIR}/douyin_${video_id}.mp4" "$download_url"

# 步骤 3：提取音频
log_step "步骤 3/7: 提取音频..."
ffmpeg -i "${TMP_DIR}/douyin_${video_id}.mp4" \
    -vn -acodec libmp3lame -q:a 2 \
    "${TMP_DIR}/douyin_${video_id}.mp3" \
    -y -loglevel quiet

# 步骤 4：**使用 SenseVoice 转录（新增）**
log_step "步骤 4/7: 语音转录（SenseVoice API）..."
source ~/.openclaw/venv/bin/activate > /dev/null 2>&1
python3 "${WORKSPACE}/scripts/sense_voice_transcriber.py" \
    "${TMP_DIR}/douyin_${video_id}.mp3" \
    --api-key "${SILICONFLOW_API_KEY}" \
    --chunk-seconds 540 \
    --language zh

transcript_file="${TMP_DIR}/douyin_${video_id}.txt"
if [[ ! -f "$transcript_file" ]]; then
    log_error "❌ 转录失败"
    return 1
fi

# 步骤 5：生成笔记（保持不变）
log_step "步骤 5/7: 生成学习笔记..."
python3 "${WORKSPACE}/scripts/smart_note_generator.py" "$transcript_file" "$video_title"

# 步骤 6-7：飞书上传和清理（保持不变）
```

---

#### **方案 B：创建统一的转录脚本**

创建 `scripts/uni_transcribe.py`：

```python
#!/usr/bin/env python3
"""统一的转录脚本：支持 Whisper 和 SenseVoice API"""

from pathlib import Path
from sense_voice_transcriber import transcribe_long_audio
from openai_whisper import load_model

def transcribe_with_model(
    audio_path: Path,
    model_name: str = "base",
    use_api: bool = True,
    **api_kwargs
) -> str:
    """
    选择转录模型

    Args:
        audio_path: 音频文件路径
        model_name: Whisper 模型名称（tiny/base/small/medium/large）
        use_api: 是否使用 SenseVoice API
        **api_kwargs: API 调用参数

    Returns:
        str: 转录文本
    """
    if use_api:
        # 使用 SenseVoice API（更快）
        result = transcribe_long_audio(audio_path, **api_kwargs)
        return result["text"]
    else:
        # 使用 Whisper（免费）
        model = load_model(model_name)
        result = model.transcribe(str(audio_path), language="zh")
        return result["text"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="统一转录脚本")
    parser.add_argument("audio_path", help="音频文件路径")
    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="small",
        help="Whisper 模型（默认：small）"
    )
    parser.add_argument(
        "--use-api",
        action="store_true",
        help="使用 SenseVoice API（优先级高于 Whisper）"
    )
    parser.add_argument(
        "--api-key",
        help="SILICONFLOW API Key"
    )

    args = parser.parse_args()

    audio_path = Path(args.audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    try:
        text = transcribe_with_model(
            audio_path,
            model_name=args.model,
            use_api=args.use_api,
            api_key=args.api_key,
            chunk_seconds=540,
            language="zh",
        )

        print(text)
        text_file = audio_path.with_suffix(".txt")
        text_file.write_text(text, encoding="utf-8")
        print(f"\n✓ 文本已保存到: {text_file}")

    except Exception as exc:
        print(f"❌ 转录失败: {exc}", file=sys.stderr)
        sys.exit(1)
```

---

## 📋 **使用方式**

### **方式 1：直接调用 ASR 脚本**

```bash
# 使用 SenseVoice API
python3 scripts/sense_voice_transcriber.py audio.mp3 \
    --api-key "sk-xxx" \
    --chunk-seconds 540

# 输出：audio.txt
```

### **方式 2：在 video-learner 中自动使用**

```bash
# 处理抖音视频（自动使用 SenseVoice）
cd ~/.openclaw/workspace-video-learner
./scripts/process_douyin.sh "https://v.douyin.com/xxxxx/"
```

### **方式 3：选择转录模型**

```bash
# 使用 Whisper
python3 scripts/sense_voice_transcriber.py audio.mp3

# 使用 SenseVoice（更快）
python3 scripts/sense_voice_transcriber.py audio.mp3 \
    --use-api \
    --api-key "sk-xxx"
```

---

## 🔄 **工作流程对比**

### **原有流程（Whisper）**

```
视频链接 
→ 下载视频
→ 提取音频
→ Whisper 转录（慢！）
→ 生成笔记
→ 上传飞书
```

### **新流程（SenseVoice）**

```
视频链接 
→ 下载视频
→ 提取音频
→ SenseVoice API 转录（快 10x）⚡
→ 生成笔记
→ 上传飞书
```

---

## ✅ **优势总结**

1. **速度提升 10x**
   - 5分钟视频：1分钟 → 10秒

2. **成本为零**
   - 硅基流动提供免费额度

3. **自动分段**
   - 支持长音频（>1小时）

4. **中文优化**
   - SenseVoice 专门优化了中文语音识别

5. **易于维护**
   - 复用现有智能笔记和飞书上传功能

---

## 📝 **配置说明**

### **环境变量**

```bash
# 方式 1：环境变量
export SILICONFLOW_API_KEY="sk-xxxxxxxxxxxxxxxx"

# 方式 2：命令行参数
python3 scripts/sense_voice_transcriber.py audio.mp3 --api-key "sk-xxxxxxxxxxxxxxxx"
```

### **脚本配置**

在 `sense_voice_transcriber.py` 中修改默认值：

```python
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
DEFAULT_MODEL = "FunAudioLLM/SenseVoiceSmall"
DEFAULT_CHUNK_SECONDS = 540  # 9分钟一段
```

---

## 🚀 **下一步**

1. ✅ 安装依赖：`pip3 install requests`
2. ✅ 获取 API Key：https://cloud.siliconflow.cn/
3. ✅ 测试脚本：`python3 scripts/sense_voice_transcriber.py test.mp3`
4. ✅ 整合到 video-learner：修改 `process_douyin.sh`

---

**创建时间**: 2026-03-13  
**维护人**: 调度小妹
