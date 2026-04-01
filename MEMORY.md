# MEMORY.md - 视频学习专员记忆

## 职责
- 解析 B站/YouTube/抖音视频链接，生成结构化学习笔记并上传飞书 Wiki
- 工作流程：识别平台 → 下载音频(yt-dlp) → ASR转录(阿里云) → GLM生成笔记 → 上传Wiki

## 关键配置
- Wiki space_id: 环境变量 FEISHU_SPACE_ID
- Wiki parent_token: 环境变量 FEISHU_PARENT_TOKEN
- B站cookies: ~/.openclaw/workspace-video-learner/cookies/bilibili_cookies.txt
- 脚本目录: ~/.openclaw/workspace-video-learner/scripts/
- 输出目录: ~/.openclaw/workspace-video-learner/output/

## 环境依赖
- yt-dlp, ffmpeg, python3
- GLM_API_KEY（笔记生成）
- ALIYUN_ASR_API_KEY（语音转录）

## 笔记结构模板
1. 核心主题 → 2. 核心观点 → 3. 典型案例 → 4. 识别方法 → 5. 实践建议 → 6. 核心金句

## 已处理视频记录
- （待积累）

## 老板要求
- Wiki笔记必须包含完整转录文本 + 原始视频链接（方便后期查阅）

## 经验教训
- 上传Wiki用 OpenClaw 内置飞书工具，不依赖 openclaw_runtime 模块
- WORKSPACE环境变量的`~`需要`.expanduser().resolve()`
- ASR脚本的dashscope.api_key必须显式设置，SDK不会自动读ALIYUN_ASR_API_KEY（2026-03-29修复）
- ASR上传文件改用纯HTTP requests绕过SDK（SDK的Files.upload会卡死）
- ASR上传响应格式可能是`{"data":...}`或`{"output":...}`，需兼容
- 音频格式不要转WAV（无压缩会变大），直接上传原始m4a
- 笔记生成应在ASR后检查转录文本是否为空，避免产出空笔记
- f2下载抖音视频偶尔会卡住无输出，注意cookies有效期(2-4周)
- 飞书Wiki API: 创建节点用`/wiki/v2/spaces/{space_id}/nodes`，不是`/wiki/v2/nodes`
- 飞书Docx API: 写入块用`/docx/v1/documents/{id}/blocks/{id}/children`，必须含block_id
- 飞书block_type: 3=H1,4=H2,5=H3...2=text; bullet/code/quote/divider不支持API创建，降级为text块
- `.env`文件需要`set -a && source .env && set +a`才能export到子进程
- feishu_uploader代码块内容必须分块写入（每块≤5000字符），不能截断，否则完整转录内容丢失
- **SSL修复(2026-04-01)**: Python requests默认SSL与DashScope不兼容，需monkey-patch SECLEVEL=1
- **网盘中转方案(2026-04-01)**: litterbox.catbox.moe中转大文件，绕过服务器上行带宽不足问题
  - ✅ litterbox.catbox.moe 可用（阿里云可访问），❌ catbox.moe 被屏蔽
  - 阿里云ASR支持最长12h/2GB文件，无需分段
  - 上传litterbox后拿公开URL直接提交ASR，阿里云从公网下载（快）
