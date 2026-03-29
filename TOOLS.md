# TOOLS.md - 视频学习专员工具箱

## 核心技能

### 视频学习助手（推荐）
- **技能名称:** `video-learner`
- **位置:** `~/.npm-global/lib/node_modules/openclaw/skills/video-learner/`
- **用途:** 视频链接处理、语音转录、智能笔记生成、飞书上传
- **特点:** 使用阿里云ASR + GLM-4-Flash，速度快、质量高、结构化笔记

### 视频帧提取和剪辑（辅助）
- **技能名称:** `video-frames`
- **位置:** `~/.npm-global/lib/node_modules/openclaw/skills/video-frames/`
- **用途:** 提取视频帧、生成短片段
- **特点:** 基于 ffmpeg，本地处理无需 API

## 工作目录

| 位置 | 说明 |
|------|------|
| 输出目录 | `~/.openclaw/workspace-video-learner/output/` |
| 临时文件 | `~/.openclaw/workspace-video-learner/tmp/` |
| B站Cookies | `~/.openclaw/workspace-video-learner/cookies/bilibili_cookies.txt` |

## 常用命令

### 创建输出目录
```bash
mkdir -p ~/.openclaw/workspace-video-learner/output
mkdir -p ~/.openclaw/workspace-video-learner/tmp
mkdir -p ~/.openclaw/workspace-video-learner/cookies
```

### 处理B站视频
```bash
cd ~/.openclaw/workspace-video-learner
./scripts/video_with_feishu.sh "https://www.bilibili.com/video/BVxxxxx"
```

### 处理YouTube视频
```bash
cd ~/.openclaw/workspace-video-learner
./scripts/video_processor.sh "https://www.youtube.com/watch?v=xxxxx"
```

### 处理抖音视频
```bash
cd ~/.openclaw/workspace-video-learner
./scripts/process_douyin.sh "https://v.douyin.com/xxxxx/"
```

### 查看已处理视频
```bash
ls -lh ~/.openclaw/workspace-video-learner/output/
```

---

工具在手，视频处理不愁。
