# 配置说明

## 环境变量配置

### 必需配置

```bash
# GLM-4-Flash API Key（用于笔记生成）
export GLM_API_KEY="your_glm_api_key_here"

# 飞书知识库配置（用于上传笔记）
export FEISHU_SPACE_ID="7566441763399581724"
export MAIN_DOCUMENT_TOKEN="LrTAdVQEnoKG1nxxKO5c5JjCn6p"
```

### 可选配置

```bash
# 阿里云 ASR API Key（用于语音转录）
export ALIYUN_ASR_API_KEY="sk-xxxxx"

# ASR 提供商选择（auto | aliyun | whisper）
export ASR_PROVIDER="auto"

# 使用环境变量中的 ASR 模型
export ASR_MODEL="qwen3-asr-flash"
```

## 飞书文档路径

### 主文档信息

- **文档 Token**: `LrTAdVQEnoKG1nxxKO5c5JjCn6p`
- **文档链接**: https://vicyrpffceo.feishu.cn/docx/LrTAdVQEnoKG1nxxKO5c5JjCn6p
- **文档标题**: 视频学习助手
- **知识库空间 ID**: `7566441763399581724`

### 子文档位置

所有视频学习笔记都会在**主文档下创建子文档**，而不是在知识库根目录下。

**示例**:
- 视频标题: "LLM 基础教程"
- 创建路径: 主文档 → "LLM 基础教程"（子文档）
- 文档链接: https://vicyrpffceo.feishu.cn/wiki/[子文档 Token]

## 目录结构

```
~/.openclaw/workspace-video-learner/
├── scripts/
│   ├── complete_video_workflow.py    # 完整流程脚本（推荐）
│   ├── asr_router.py                  # ASR 路由器
│   ├── glm_note_generator.py           # 笔记生成器
│   ├── upload_feishu.sh                # 飞书上传播（已废弃）
│   └── create_video_node.py            # 节点创建工具
├── knowledge/
│   └── inbox/
│       └── video/
│           ├── raw/                    # 原始音频/字幕
│           └── transcripts/            # 转录结果
└── config/
    └── asr_config.json                 # ASR 配置文件
```

## 配置文件示例

### ~/.bashrc

```bash
# ============================================
# 视频学习助手配置
# ============================================

# GLM-4-Flash API Key
export GLM_API_KEY="your_glm_api_key_here"

# 飞书知识库配置
export FEISHU_SPACE_ID="7566441763399581724"
export MAIN_DOCUMENT_TOKEN="LrTAdVQEnoKG1nxxKO5c5JjCn6p"

# 阿里云 ASR（可选）
export ALIYUN_ASR_API_KEY="sk-xxxxx"
export ASR_PROVIDER="auto"

# ============================================
```

### ~/.zshrc

```bash
# ============================================
# 视频学习助手配置
# ============================================

# GLM-4-Flash API Key
export GLM_API_KEY="your_glm_api_key_here"

# 飞书知识库配置
export FEISHU_SPACE_ID="7566441763399581724"
export MAIN_DOCUMENT_TOKEN="LrTAdVQEnoKG1nxxKO5c5JjCn6p"

# 阿里云 ASR（可选）
export ALIYUN_ASR_API_KEY="sk-xxxxx"
export ASR_PROVIDER="auto"

# ============================================
```

## 验证配置

### 检查环境变量

```bash
# 检查 GLM API Key
echo $GLM_API_KEY

# 检查飞书配置
echo $FEISHU_SPACE_ID
echo $MAIN_DOCUMENT_TOKEN
```

### 检查依赖

```bash
# 检查 yt-dlp
yt-dlp --version

# 检查 ffmpeg
ffmpeg -version

# 检查 Python 依赖
python3 -c "import requests; print('✓ requests OK')"
python3 -c "import json; print('✓ json OK')"
```

### 测试飞书连接

```bash
curl -X POST https://open.feishu.cn/open-apis/wiki/v2/nodes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "node": {
      "space_id": "7566441763399581724",
      "parent_node_token": "LrTAdVQEnoKG1nxxKO5c5JjCn6p",
      "title": "测试",
      "obj_type": "docx",
      "page_title": "测试",
      "content": "# 测试\n\n测试内容"
    }
  }'
```

## 常见问题

### Q: 为什么笔记不在知识库根目录下？

A: 所有笔记都在主文档 `LrTAdVQEnoKG1nxxKO5c5JjCn6p` 下创建子文档，便于集中管理。

### Q: 如何查看已上传的笔记？

A: 打开飞书链接: https://vicyrpffceo.feishu.cn/docx/LrTAdVQEnoKG1nxxKO5c5JjCn6p，在主文档下可以看到所有子文档。

### Q: 飞书 API 调用失败怎么办？

A: 检查环境变量配置是否正确，确保 `GLM_API_KEY` 和 `FEISHU_SPACE_ID` 设置正确。

### Q: ASR 转录失败怎么办？

A: 如果阿里云 ASR 失败，脚本会自动降级到本地 Whisper tiny 模型。

## 配置更新记录

- **2026-03-15**: 更新主文档 Token 为 `LrTAdVQEnoKG1nxxKO5c5JjCn6p`
- **2026-03-15**: 创建完整配置说明文档
