---
name: video-learner
description: "Video learning assistant: download, transcribe, generate smart notes, and upload to Feishu Wiki. Use when: (1) processing Bilibili/YouTube/Douyin videos, (2) generating structured notes from transcripts, (3) uploading notes to Feishu Wiki knowledge base."
metadata:
  openclaw:
    emoji: "🎬"
  requires:
    bins: ["yt-dlp", "python3", "ffmpeg"]
    files: ["~/.openclaw/workspace-video-learner/cookies/bilibili_cookies.txt"]
    env: ["GLM_API_KEY", "ALIYUN_ASR_API_KEY", "FEISHU_SPACE_ID", "FEISHU_PARENT_TOKEN"]
---

# Video Learner 🎬 (Wiki版)

从B站/YouTube/抖音视频自动生成学习笔记，上传到飞书Wiki知识库。

## ⚠️ 重要：必须使用 Wiki 版流程

**上传方式**：使用 OpenClaw 飞书工具（`feishu_wiki_space_node` + `feishu_update_doc`），**不要用 REST API 直传**。

**所有笔记统一上传到指定 Wiki 父节点下**，返回 Wiki 链接。

## 标准工作流程

收到视频链接后，按以下步骤执行：

### 步骤 1：下载音频

```bash
cd ~/.openclaw/workspace-video-learner

# B站
yt-dlp -x --audio-format wav --audio-quality 0 \
  --cookies cookies/bilibili_cookies.txt \
  -o "output/audio_%(id)s.%(ext)s" "VIDEO_URL"

# YouTube
yt-dlp -x --audio-format wav --audio-quality 0 \
  -o "output/audio_%(id)s.%(ext)s" "VIDEO_URL"

# 抖音
yt-dlp -x --audio-format wav --audio-quality 0 \
  -o "output/audio_%(id)s.%(ext)s" "VIDEO_URL"
```

### 步骤 2：ASR 转录

```bash
cd ~/.openclaw/workspace-video-learner
python3 scripts/asr_aliyun.py "output/audio_xxx.wav" --output "output/transcript_xxx.txt"
```

### 步骤 3：GLM 生成笔记

```bash
cd ~/.openclaw/workspace-video-learner
python3 scripts/note_generator.py "output/transcript_xxx.txt" --title "视频标题" --output "output/note_xxx.md"
```

### 步骤 4：上传飞书 Wiki（使用 OpenClaw 工具）

这是最关键的一步，**必须用 OpenClaw 飞书工具**，不要用 REST API。

1. 调用 `feishu_wiki_space_node` 创建 Wiki 子节点：
   - `action`: "create"
   - `space_id`: `$FEISHU_SPACE_ID`
   - `parent_node_token`: `$FEISHU_PARENT_TOKEN`
   - `obj_type`: "docx"
   - `title`: "【视频笔记】视频标题"

2. 从返回结果获取 `obj_token`，调用 `feishu_update_doc` 写入笔记 Markdown 内容：
   - `doc_id`: obj_token
   - `mode`: "overwrite"
   - `markdown`: 笔记内容

3. 返回 Wiki 链接：`https://www.feishu.cn/wiki/{node_token}`

### 也可一键运行

```bash
cd ~/.openclaw/workspace-video-learner
python3 scripts/video_learner_wiki.py "VIDEO_URL"
```

## 必需环境变量

| 变量 | 用途 |
|------|------|
| `GLM_API_KEY` | 笔记生成 |
| `ALIYUN_ASR_API_KEY` | 语音转录 |
| `FEISHU_SPACE_ID` | Wiki 空间 ID |
| `FEISHU_PARENT_TOKEN` | Wiki 父节点 Token |

## 笔记结构

生成的笔记包含：核心主题、核心观点(3-5个)、典型案例、识别方法、实践建议、核心金句。

## 常见问题

### ASR SSL 错误
大文件会自动分段（9MB阈值），如果仍然报 SSL 错误，尝试先压缩音频：
```bash
ffmpeg -i input.wav -ar 16000 -ac 1 output.wav
```

### B站 412 错误
更新 cookies 文件，或用浏览器 cookies：`yt-dlp --cookies-from-browser chrome "URL"`

### Wiki 上传失败
- 检查 FEISHU_SPACE_ID 和 FEISHU_PARENT_TOKEN
- 确认有知识库写入权限
- **不要用 feishu_uploader.py 的 REST API 方式**，用 OpenClaw 工具

---

*Video Learner Wiki版 v2.1*
*Last Updated: 2026-03-17*
