---
name: video-learner-wiki
description: |
  视频学习笔记生成器 - 从B站/YouTube/抖音视频自动生成学习笔记并上传到飞书Wiki。
  
  **触发条件**（满足任一）：
  - 用户发B站/YouTube/抖音视频链接
  - 用户说"学习整理"、"视频笔记"、"视频学习"

metadata:
  openclaw:
    emoji: "🎬"
  requires:
    bins: ["yt-dlp", "python3", "ffmpeg"]
    env: ["GLM_API_KEY", "ALIYUN_ASR_API_KEY"]
---

# Video Learner Wiki 🎬

从视频自动生成学习笔记并上传到飞书Wiki。

## ⚠️ 前置检查（INVERSION模式：先验证再执行）

**在开始处理之前，必须逐项验证以下条件。任一失败则告知用户并停止：**

| # | 检查项 | 验证方法 | 失败处理 |
|---|--------|----------|----------|
| 1 | 脚本存在 | `ls ~/.openclaw/workspace-video-learner/scripts/video_learner_wiki.py` | 告知用户skill未安装 |
| 2 | 依赖可用 | `which yt-dlp ffmpeg python3` | 提示安装缺失依赖 |
| 3 | API密钥 | `grep GLM_API_KEY ~/.openclaw/workspace-video-learner/.env` | 告知用户配置API密钥 |
| 4 | URL有效 | 识别为 bilibili/youtube/douyin 链接 | 告知用户仅支持这3个平台 |
| 5 | Wiki配置 | `grep FEISHU_SPACE_ID ~/.openclaw/workspace-video-learner/.env` | 笔记仅本地生成，不上传 |

## 工作流程（PIPELINE模式：步骤+门控）

```
GATE 1: 前置检查 ✅
  ↓
STEP 1: 运行脚本 → exec执行（timeout 300s，ASR异步轮询可能较慢）
  ↓
GATE 2: 检查脚本退出码 == 0 且笔记文件存在 ❌则报错停止
  ↓
STEP 2: 读取笔记文件内容
  ↓
STEP 3: Agent调用 feishu_wiki_space_node 创建wiki节点
  ↓
GATE 3: 检查返回值包含 node.node_token 和 node.obj_token ❌则报错停止
  ↓
STEP 4: Agent调用 feishu_update_doc 写入内容
  ↓
GATE 4: 检查返回值 success == true ❌则报错停止
  ↓
✅ 返回Wiki链接给用户
```

### STEP 1: 运行脚本

```bash
cd ~/.openclaw/workspace-video-learner && python3 scripts/video_learner_wiki.py "URL" 2>&1
```

- 使用 `exec` 工具执行，设置 `timeout=300`（5分钟，含ASR异步轮询）
- 脚本负责：下载音频 → ASR转录 → GLM生成笔记 → 保存到 output/

### GATE 2: 验证笔记生成

```bash
# 找到最新笔记文件
ls -t ~/.openclaw/workspace-video-learner/output/*_note.md | head -1
```

- 读取笔记内容（`read` 工具）
- **如果文件不存在或脚本报错**：向用户报告错误，停止流程

### STEP 3-4: 上传Wiki

**从 `.env` 文件获取配置：**
```bash
grep -E 'FEISHU_SPACE_ID|FEISHU_PARENT_TOKEN' ~/.openclaw/workspace-video-learner/.env
```

**创建Wiki节点：**
- `feishu_wiki_space_node(action="create", space_id=..., parent_node_token=..., obj_type="docx", node_type="origin", title="【视频笔记】视频标题")`
- 从返回值提取 `node_token` 和 `obj_token`

**写入内容：**
- `feishu_update_doc(doc_id=obj_token, mode="overwrite", markdown=笔记内容)`

**⚠️ 原视频链接（必须包含）：**
- 在笔记的 `## 📹 视频信息` 部分必须添加一行 `- **原视频链接**: URL`
- Agent 在调用 `feishu_update_doc` 前，必须确保笔记 markdown 中包含原始视频 URL

**返回给用户：**
- `https://www.feishu.cn/wiki/{node_token}`

### 错误处理（REVIEWER模式：分类输出）

| 错误类型 | 日志关键词 | 处理 |
|----------|-----------|------|
| 🔴 **阻断** | `[ERROR]`、exit code ≠ 0 | 停止，报告错误详情 |
| 🟡 **降级** | cookies过期、下载失败 | 笔记仅本地生成，不上传 |
| 🟢 **继续** | `[WARN]` | 记录警告，继续执行 |

## 平台支持

| 平台 | 识别规则 | 特殊要求 |
|------|----------|----------|
| **B站** | `bilibili.com/video/` | cookies文件 |
| **YouTube** | `youtube.com/watch` | cookies + deno(推荐) |
| **抖音** | `v.douyin.com` | cookies 文件（f2 库） |

## ASR 技术细节

**阿里云 DashScope fun-asr-mtl**，通过以下优化确保低带宽环境稳定运行：

1. **音频压缩**：16kHz → 8kHz mono（文件体积减半，识别准确率影响 <1%）
2. **curl 替代 SDK**：绕过 dashscope Python SDK 的 httpx SSL 问题
3. **异步调用**：`X-DashScope-Async: enable` 头 + 轮询等待结果
4. **超时配置**：上传超时 600s，轮询最长 600s

## 配置说明

所有配置在 `~/.openclaw/workspace-video-learner/.env`：

```env
GLM_API_KEY=xxx              # 智谱GLM（笔记生成）
ALIYUN_ASR_API_KEY=xxx       # 阿里云ASR（转录）
FEISHU_SPACE_ID=xxx          # 飞书空间ID
FEISHU_PARENT_TOKEN=xxx      # Wiki父节点Token
DOUYIN_COOKIES_PATH=xxx      # 抖音cookies文件路径
```

## 抖音下载方案（f2 库）

yt-dlp 对抖音支持不稳定，改用 **f2** 库（TikTokDownload 的核心引擎）：

- **仓库**：https://github.com/Johnserf-Seed/TikTokDownload
- **安装**：`pip install f2`（已安装在系统 Python）
- **已克隆到**：`~/.openclaw/workspace-video-learner/tools/TikTokDownload/`

### 下载命令

```bash
# 1. 将 Netscape cookies 转为纯文本格式
python3 -c "
import http.cookiejar, os
cj = http.cookiejar.MozillaCookieJar()
cj.load(os.environ.get('DOUYIN_COOKIES_PATH', '~/.openclaw/workspace-video-learner/cookies/douyin_cookies.txt'))
cookie_str = '; '.join(f'{c.name}={c.value}' for c in cj)
print(cookie_str)
" > /tmp/douyin_cookie.txt

# 2. 使用 f2 下载单个视频
DOUYIN_COOKIE=$(cat /tmp/douyin_cookie.txt)
python3 -m f2 dy -u "https://www.douyin.com/video/VIDEO_ID" \
  -k "$DOUYIN_COOKIE" \
  -p /tmp/douyin_output \
  -M one --languages zh_CN

# 3. 输出文件路径
# /tmp/douyin_output/douyin/one/<作者名>/<日期_标题_video.mp4>
```

### 注意事项

- ⚠️ Cookies 有效期约 2-4 周，过期后需要重新从浏览器导出
- ⚠️ Bark 通知报错可忽略（未配置通知 key）
- ⚠️ f2 依赖 pydantic 2.9.2，可能与 mcp 的 pydantic 版本冲突（不影响运行）
- ✅ 支持：单个作品、主页作品、点赞、收藏、合集、直播
