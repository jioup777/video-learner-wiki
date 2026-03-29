# Video Learner Skill

从 B站/YouTube/抖音 视频自动生成学习笔记并上传飞书。

## 快速开始

```bash
# 设置环境变量
export GLM_API_KEY="your_key"
export DASHSCOPE_API_KEY="your_key"
export FEISHU_SPACE_ID="your_space_id"
export FEISHU_PARENT_TOKEN="your_token"

# 运行 (B站)
python scripts/video_learner.py "https://www.bilibili.com/video/BVxxxxx"

# 运行 (YouTube)
python scripts/video_learner.py "https://www.youtube.com/watch?v=xxxxx"

# 运行 (抖音)
python scripts/video_learner.py "https://v.douyin.com/xxxxx/"

# 不上传飞书
python scripts/video_learner.py "url" --no-upload
```

## 平台要求

| 平台 | 下载方案 | 特殊要求 | 测试状态 |
|------|----------|----------|----------|
| **B站** | yt-dlp + cookies | cookies文件 | ✅ 通过 |
| **YouTube** | yt-dlp + cookies | cookies + deno(推荐) | ✅ 通过 |
| **抖音** | requests API | 无需f2库 | ✅ 通过 |

## 依赖安装

```bash
# 核心依赖
pip install yt-dlp dashscope python-dotenv requests

# JavaScript运行时 (YouTube推荐，非必需)
# macOS: brew install deno
# Linux: curl -fsSL https://deno.land/install.sh | sh
# Windows: https://github.com/denoland/deno/releases

# FFmpeg (音频处理，必需)
# macOS: brew install ffmpeg
# Ubuntu: apt install ffmpeg
# Windows: https://ffmpeg.org/download.html
```

## 配置文件

复制 `.env.example` 为 `.env` 并填写：

| 变量 | 必需 | 说明 |
|------|------|------|
| `GLM_API_KEY` | ✅ | 智谱GLM API |
| `DASHSCOPE_API_KEY` | ✅ | 阿里云ASR API |
| `FEISHU_APP_ID` | ✅ | 飞书应用ID |
| `FEISHU_APP_SECRET` | ✅ | 飞书应用密钥 |
| `FEISHU_SPACE_ID` | ✅ | 飞书知识库空间ID |
| `FEISHU_PARENT_TOKEN` | ✅ | 飞书父节点Token（wiki节点） |
| `BILIBILI_COOKIES` | ❌ | B站cookies路径 |

**重要说明**：
- `FEISHU_PARENT_TOKEN` 是wiki节点token，所有视频笔记都会在该节点下创建子文档
- 例如：`I1GtwmgL4iok6WkfOghcR1uwnld`
- 获取方式：飞书知识库 → 右键目标文件夹 → 复制Node Token

## Cookies 获取

### B站
1. 登录 bilibili.com
2. 使用浏览器扩展导出Netscape格式
3. 保存到 `cookies/bilibili_cookies.txt`

### YouTube
1. 使用 `yt-dlp --cookies-from-browser chrome "URL"`
2. 或手动导出cookies文件

## 常见问题

### 412错误 (B站/YouTube)
cookies过期或无效。解决方法：
1. 更新cookies文件（推荐使用EditThisCookie扩展）
2. 或使用浏览器cookies：`yt-dlp --cookies-from-browser chrome "URL"`
3. 确保登录状态后再导出cookies

### ASR大文件处理失败
音频文件超过10MB会被自动分段（9MB阈值），确保FFmpeg已安装：
```bash
ffmpeg -version
```

### 抖音下载失败
抖音使用requests API，无需安装f2库。确保网络可访问douyin.com。

### 飞书上传失败
检查FEISHU_APP_ID和FEISHU_APP_SECRET是否正确配置，可在飞书开放平台获取。

## 测试结果

| 平台 | 状态 | 备注 |
|------|------|------|
| B站 | ✅ | 需要有效cookies |
| YouTube | ✅ | 需要cookies，建议安装deno |
| 抖音 | ✅ | 使用requests API，无需f2 |

## 文件结构

```
scripts/
├── video_learner.py       # 统一入口
├── downloaders/
│   ├── bilibili.py        # B站下载(cookies验证)
│   ├── youtube.py         # YouTube下载(字幕优先)
│   └── douyin.py          # 抖音下载(requests API)
├── asr_aliyun.py          # 阿里云ASR(自动分段)
├── note_generator.py      # GLM笔记生成
├── feishu_uploader.py     # 飞书上传(直接API)
├── exceptions.py          # 统一异常类
└── utils.py               # 工具函数(重试装饰器)
```

---
详细文档见 [SKILL.md](./SKILL.md)
