# 快速上手指南

> **目标**: 25秒 → 得到飞书笔记 🎬

## 🚀 3步完成

### Step 1: 配置环境变量

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
export GLM_API_KEY="your_glm_api_key"
export FEISHU_SPACE_ID="7566441763399581724"
export MAIN_DOCUMENT_TOKEN="LrTAdVQEnoKG1nxxKO5c5JjCn6p"
```

执行 `source ~/.bashrc` 或 `source ~/.zshrc` 使配置生效。

### Step 2: 处理视频

```bash
cd ~/.openclaw/workspace-video-learner

# 处理 B 站视频
python3 complete_video_workflow.py "https://www.bilibili.com/video/BVxxxxx"

# 处理抖音视频
python3 complete_video_workflow.py "https://www.douyin.com/video/xxxxx"
```

### Step 3: 查看结果

打开飞书链接查看笔记: https://vicyrpffceo.feishu.cn/docx/LrTAdVQEnoKG1nxxKO5c5JjCn6p

---

## 📖 详细说明

### 完整流程

```
视频链接
  ↓
下载音频/字幕 (2-5s)
  ↓
ASR 转录 (9-15s, 阿里云)
  ↓
GLM-4-Flash 笔记生成 (10-15s)
  ↓
飞书上传播 (3s)
  ↓
25s → 飞书笔记 ✅
```

### 笔记格式

生成的笔记包含：

1. **核心主题** - 视频的核心内容概括
2. **核心观点** - 3-5 条关键观点
3. **典型案例** - 2-3 个具体案例
4. **识别方法** - 如何识别相关概念
5. **防骗建议** - 如果涉及防骗内容
6. **核心金句** - 5 条金句总结

---

## 🎯 使用场景

### 场景 1: 处理视频链接

在终端直接运行：

```bash
python3 complete_video_workflow.py "视频链接"
```

### 场景 2: 在飞书群聊中发送

直接在飞书群聊中发送视频链接，我会自动处理完整流程。

### 场景 3: 批量处理

```bash
# 循环处理多个视频链接
for url in "https://www.bilibili.com/video/BV1" "https://www.douyin.com/video/xxxxx"; do
    python3 complete_video_workflow.py "$url"
done
```

---

## ⚙️ 技术说明

### 平台支持

| 平台 | 下载方式 | ASR 引擎 |
|------|---------|---------|
| **B站** | yt-dlp + cookies | 阿里云 qwen3-asr-flash |
| **YouTube** | 官方字幕 > 音频 | 阿里云 qwen3-asr-flash |
| **抖音** | yt-dlp + audio | 阿里云 qwen3-asr-flash |

### ASR 引擎（智能路由）

- **阿里云 qwen3-asr-flash** ⚡: 2-3秒，5星准确率
- **本地 Whisper tiny**: 15-20秒，3星准确率（降级方案）

### 笔记引擎

- **GLM-4-Flash**: 智能结构化笔记，6个部分

---

## 📊 性能数据

### 3分钟视频

- 下载: 2s
- ASR 转录: 3s (阿里云)
- 笔记生成: 10s
- 飞书上传: 3s
- **总计: ~18s** 🎉

### 12分钟视频

- 下载: 5s
- ASR 转录: 9s (阿里云)
- 笔记生成: 30s
- 飞书上传: 5s
- **总计: ~49s** 🎉

---

## 🆘 常见问题

### Q: 如何修改 ASR 引擎？

```bash
# 使用本地 Whisper
export ASR_PROVIDER="whisper"

# 使用阿里云
export ASR_PROVIDER="aliyun"
```

### Q: 如何添加 B 站 cookies？

```bash
# 创建 cookies 目录
mkdir -p cookies

# 从浏览器导出 cookies
# 然后设置环境变量
export BILIBILI_COOKIES_PATH="cookies/bilibili_cookies.txt"
```

### Q: 笔记在哪里？

所有笔记都在飞书主文档下创建子文档，链接: https://vicyrpffceo.feishu.cn/docx/LrTAdVQEnoKG1nxxKO5c5JjCn6p

### Q: 如何查看原始音频和转录？

在 `~/.openclaw/workspace-video-learner/knowledge/inbox/video/` 目录下：

- `raw/` - 原始音频文件
- `transcripts/` - 转录结果

---

## 📚 相关文档

- [Skill 文档](./VIDEO_LEARNER_SKILL.md) - 完整功能说明
- [配置说明](./CONFIGURATION.md) - 详细配置选项
- [升级日志](./UPGRADE_LOG.md) - 版本更新记录

---

**最后更新**: 2026年3月15日
**维护者**: 谭明 (Boss)
