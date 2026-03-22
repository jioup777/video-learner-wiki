# Video Learner Wiki Skill

🎬 从视频自动生成学习笔记并上传到飞书 Wiki 知识库

## 功能特性

- ✅ 自动下载视频音频（B 站/YouTube/抖音）
- ✅ 阿里云 ASR 转录（fun-asr-mtl，异步模式）
- ✅ GLM-4-Flash 智能笔记生成
- ✅ **Wiki 节点上传**（在指定 wiki 节点下创建子文档）
- ✅ 低带宽优化（8kHz 音频压缩 + curl 上传 + 异步轮询）

## 快速开始

### 1. 安装依赖

```bash
cd ~/.openclaw/skills/video-learner-wiki
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写实际的 API Key 和配置
```

### 3. 运行

```bash
# 在 OpenClaw 环境中运行（推荐）
# 由 OpenClaw Agent 自动调用

# 或手动运行
python scripts/video_learner_wiki.py "https://www.bilibili.com/video/BVxxxxx"
```

## 技术架构

```
视频链接 → yt-dlp下载音频 → ffmpeg压缩(8kHz) → curl上传DashScope 
  → 异步ASR转录 → GLM-4-Flash生成笔记 → feishu_update_doc上传Wiki
```

### ASR 优化

| 优化项 | 说明 |
|--------|------|
| 音频压缩 | 16kHz → 8kHz mono，体积减半，识别率影响 <1% |
| curl 上传 | 替代 dashscope Python SDK，绕过 httpx SSL 问题 |
| 异步模式 | X-DashScope-Async 头 + 轮询，支持长音频 |
| 超时配置 | 上传 600s，轮询 600s，适应低带宽环境 |

### 为什么不用 Whisper？

在阿里云轻量云服务器环境下，Whisper 本地推理对内存和计算资源要求较高。阿里云 ASR（fun-asr-mtl）作为云端服务，转录质量优秀且资源消耗极低，更适合生产环境。

## 配置说明

| 变量 | 必需 | 说明 |
|------|------|------|
| `GLM_API_KEY` | ✅ | 智谱 GLM API（笔记生成） |
| `ALIYUN_ASR_API_KEY` | ✅ | 阿里云 DashScope API（ASR 转录） |
| `FEISHU_SPACE_ID` | ✅ | 飞书知识库空间 ID |
| `FEISHU_PARENT_TOKEN` | ✅ | Wiki 父节点 Token |

### 获取方式

- **GLM API Key**: https://open.bigmodel.cn/
- **阿里云 ASR Key**: https://dashscope.console.aliyun.com/
- **FEISHU_SPACE_ID**: 知识库空间设置
- **FEISHU_PARENT_TOKEN**: 右键 Wiki 文件夹 → 复制 Node Token

## 使用示例

```bash
# B 站视频
python scripts/video_learner_wiki.py "https://www.bilibili.com/video/BVxx411c7mD"

# YouTube 视频
python scripts/video_learner_wiki.py "https://www.youtube.com/watch?v=xxxxx"

# 抖音视频
python scripts/video_learner_wiki.py "https://v.douyin.com/xxxxx/"

# 不上传飞书（仅生成本地笔记）
python scripts/video_learner_wiki.py "url" --no-upload
```

## 文件结构

```
video-learner-wiki/
├── SKILL.md                    # 技能说明（OpenClaw 读取）
├── README.md                   # 本文件
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
└── scripts/
    ├── video_learner_wiki.py   # 主入口脚本
    ├── asr_aliyun.py           # 阿里云 ASR 模块（curl + 异步）
    ├── note_generator.py       # GLM 笔记生成模块
    ├── utils.py                # 工具函数（重试、格式化）
    ├── exceptions.py           # 统一异常定义
    ├── feishu_uploader.py      # 飞书上传模块（备用）
    ├── video_learner.py        # 基础版视频处理脚本
    └── downloaders/
        ├── __init__.py
        ├── bilibili.py         # B站下载器
        ├── youtube.py          # YouTube下载器
        └── douyin.py           # 抖音下载器
```

## 常见问题

**Q: 为什么文档在 wiki 节点下而不是根目录？**

A: 所有笔记都在指定的 wiki 节点下创建子文档，便于集中管理和查看。

**Q: 如何更改 wiki 父节点？**

A: 修改环境变量 `FEISHU_PARENT_TOKEN` 为新的节点 token。

**Q: ASR 转录很慢怎么办？**

A: 受服务器上传带宽影响。已通过音频压缩（8kHz）和 curl 异步上传优化，通常 2-3 分钟完成。

**Q: 为什么不用 Whisper？**

A: 阿里云 ASR 云端服务资源消耗更低，转录质量优秀，更适合轻量云服务器环境。

---

**版本**: 2.0  
**更新时间**: 2026-03-22  
**维护者**: 谭明
