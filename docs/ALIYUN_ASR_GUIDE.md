# 阿里百炼 SenseVoice API 使用说明

## ✅ 已完成

### 1. **脚本位置**
```
~/.openclaw/workspace-video-learner/scripts/aliyun_asr.py
```

### 2. **配置信息**
- **API Key**: 已内置（你的 Key：sk-8a8d68007214401faf8641745e022430）
- **模型**: qwen3-asr-flash-filetrans（你推荐的模型）
- **API Base**: https://dashscope.aliyuncs.com/api/v1

---

## 🚀 使用方式

### **步骤 1：安装依赖**

```bash
pip3 install dashscope
```

### **步骤 2：处理本地音频文件**

```bash
cd ~/.openclaw/workspace-video-learner

# 处理单个音频文件
python3 scripts/aliyun_asr.py /path/to/your/audio.mp3

# 处理长音频（自动分段）
python3 scripts/aliyun_asr.py /path/to/long/audio.mp3 --chunk-seconds 540
```

### **步骤 3：输出结果**

脚本会：
1. ⏱️ 显示处理进度
2. 📝 显示转录结果
3. 💾 保存到 `.txt` 文件

示例输出：
```
音频时长 300 秒，将分割为 1 段...
开始转录...
  [第 1/1] 转录片段...
  ✓ 片段 1 转录完成 (1234 字符)

✓ 所有片段转录完成，共 1 段

==================================================
转录结果：
==================================================
这里是转录的文本内容...

==================================================
Request ID: merged_300s
状态码: 200

✓ 文本已保存到: /path/to/your/audio.mp3.txt
```

---

## 📋 功能说明

### **支持的音频格式**
- ✅ MP3
- ✅ WAV
- ✅ M4A
- ✅ MP4（音频轨道）

### **长音频处理**
- 自动检测音频时长
- 默认 9 分钟分段（可调整）
- 自动合并结果

### **语言支持**
- 默认：中文（zh）
- 可指定其他语言

---

## 🧪 测试方式

如果你有测试音频文件，可以直接运行：

```bash
cd ~/.openclaw/workspace-video-learner

# 测试短音频（< 9 分钟）
python3 scripts/aliyun_asr.py /path/to/test.mp3

# 测试长音频（> 9 分钟）
python3 scripts/aliyun_asr.py /path/to/long_test.mp3 --chunk-seconds 300
```

---

## 🔧 高级选项

### **自定义 API Key**
```bash
python3 scripts/aliyun_asr.py audio.mp3 --api-key "sk-你的key"
```

### **自定义模型**
```bash
python3 scripts/aliyun_asr.py audio.mp3 --model "qwen3-asr-flash"
```

### **自定义分段时长**
```bash
python3 scripts/aliyun_asr.py audio.mp3 --chunk-seconds 600  # 10 分钟一段
```

---

## 📝 与 video-learner 的集成

### **方案：修改 process_douyin.sh**

```bash
#!/bin/bash
# 使用阿里百炼 ASR 替代 Whisper

# 步骤 4：使用阿里百炼 ASR 转录
log_step "步骤 4/7: 语音转录（SenseVoice API）..."
python3 "${WORKSPACE}/scripts/aliyun_asr.py" \
    "${TMP_DIR}/douyin_${video_id}.mp3" \
    --chunk-seconds 540 \
    --language zh

transcript_file="${TMP_DIR}/douyin_${video_id}.txt"
if [[ ! -f "$transcript_file" ]]; then
    log_error "❌ 转录失败"
    return 1
fi
```

---

## ✅ 预期效果

**性能提升**：
- ⚡ 速度：Whisper（5分钟=1分钟）→ SenseVoice（5分钟=10秒）
- 💰 成本：免费额度
- 🎯 准确度：中文优化

---

**现在可以测试了！** 🎯

有什么问题吗？
