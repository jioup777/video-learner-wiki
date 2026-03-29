# 视频学习助手 - 核心配置

> 重要配置信息，防止遗忘

---

## 🎯 飞书文档路径（重要！）

**主文档 Token**: `LrTAdVQEnoKG1nxxKO5c5JjCn6p`  
**文档链接**: https://vicyrpffceo.feishu.cn/docx/LrTAdVQEnoKG1nxxKO5c5JjCn6p  
**知识库空间 ID**: `7566441763399581724`

**上传位置**: 
- ✅ **在主文档下创建子文档**（不是知识库根目录）
- ✅ 自动以视频标题命名
- ✅ 文档链接格式：`https://vicyrpffceo.feishu.cn/wiki/[子文档 Token]`

---

## ⚙️ 环境变量配置

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加

# GLM-4-Flash 配置（笔记生成）
export GLM_API_KEY="your_glm_api_key"

# 飞书知识库配置（重要！）
export FEISHU_SPACE_ID="7566441763399581724"
export MAIN_DOCUMENT_TOKEN="LrTAdVQEnoKG1nxxKO5c5JjCn6p"

# ASR 配置
export ALIYUN_ASR_API_KEY="sk-xxxxx"
export ASR_PROVIDER="auto"
```

---

## 📁 项目路径

**工作目录**: `~/.openclaw/workspace-video-learner/`

**核心脚本**:
- `scripts/complete_video_workflow.py` - 完整流程脚本（推荐）
- `scripts/asr_router.py` - ASR 路由器
- `scripts/glm_note_generator.py` - 笔记生成器
- `scripts/create_video_node.py` - 飞书节点创建工具

**文档**:
- `VIDEO_LEARNER_SKILL.md` - Skill 文档
- `CONFIGURATION.md` - 配置说明
- `QUICKSTART.md` - 快速上手指南
- `UPGRADE_LOG.md` - 升级日志

---

## 🚀 使用方法

### 命令行

```bash
cd ~/.openclaw/workspace-video-learner

# 处理 B 站视频
python3 complete_video_workflow.py "https://www.bilibili.com/video/BVxxxxx"

# 处理抖音视频
python3 complete_video_workflow.py "https://www.douyin.com/video/xxxxx"
```

### 飞书群聊

直接在飞书群聊中发送视频链接，我会自动处理完整流程。

---

## 📊 性能数据

- **3 分钟视频**: ~18 秒
- **12 分钟视频**: ~49 秒
- **ASR 转录**: 2-3 秒（阿里云）vs 15-20 秒（Whisper）

---

## 📝 笔记格式

生成的笔记包含 6 个部分：
1. 核心主题
2. 核心观点（3-5 条）
3. 典型案例（2-3 个）
4. 识别方法
5. 防骗建议
6. 核心金句（5 条）

---

## 🔧 技术栈

- **yt-dlp**: 视频/音频下载
- **阿里云 qwen3-asr-flash**: 语音转录（2-3 秒）
- **Whisper**: 本地转录（降级方案）
- **GLM-4-Flash**: 笔记生成
- **飞书 API**: 文档上传（在主文档下创建子文档）

---

## ⚠️ 注意事项

1. **飞书文档路径**: 所有笔记都在主文档 `LrTAdVQEnoKG1nxxKO5c5JjCn6p` 下创建子文档
2. **环境变量**: 确保 `GLM_API_KEY` 和 `FEISHU_SPACE_ID` 配置正确
3. **ASR 引擎**: 优先使用阿里云，失败时自动降级到 Whisper

---

**最后更新**: 2026 年 3 月 15 日  
**维护者**: 谭明 (Boss)
