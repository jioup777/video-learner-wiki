# MEMORY.md - 视频学习专员记忆

## 职责
- 解析 B站/YouTube/抖音视频链接，生成结构化学习笔记并上传飞书 Wiki
- 工作流程：识别平台 → 下载音频(yt-dlp) → ASR转录(阿里云) → GLM生成笔记 → 上传Wiki

## 关键配置
- Wiki space_id: 环境变量 FEISHU_SPACE_ID
- Wiki parent_token: 环境变量 FEISHU_PARENT_TOKEN（视频笔记统一放这个节点下）
- B站cookies: ~/.openclaw/workspace-video-learner/cookies/bilibili_cookies.txt
- 脚本目录: ~/.openclaw/workspace-video-learner/scripts/
- 输出目录: ~/.openclaw/workspace-video-learner/output/

## 环境依赖
- yt-dlp, ffmpeg, python3
- GROQ_API_KEY（默认ASR引擎，Groq Whisper）
- ALIYUN_ASR_API_KEY（备用ASR，设ASR_PROVIDER=aliyun启用）
- 笔记生成：**由Agent大模型直接生成，不需要外部API**
- FEISHU_SPACE_ID / FEISHU_PARENT_TOKEN（Wiki上传）

## 笔记结构模板
1. 核心主题 → 2. 核心观点 → 3. 典型案例 → 4. 识别方法 → 5. 实践建议 → 6. 核心金句

## 已处理视频记录
- （待积累）

## 老板要求
- Wiki笔记必须包含完整转录文本 + 原始视频链接（方便后期查阅）
- **上传Wiki时必须包含转录全文，不能只写笔记摘要！**（2026-05-10再次强调）

## ASR引擎
- **默认使用 Groq Whisper**（免费、秒级），ASR_PROVIDER=groq
- 备用阿里云 ASR（付费），设 ASR_PROVIDER=aliyun
- 子agent任务必须明确指定用 GroqASR，不要用 AliyunASR
- Groq Whisper 免费tier限制25MB/文件，大文件自动分片

## 经验教训
- **Wiki上传必须包含完整转录全文！**（2026-05-10 六爷明确要求，不要只写笔记摘要就结束）
- 上传流程：先写笔记摘要 → 再append完整转录文本 → 返回链接。两步缺一不可。
- 脚本生成的.md文件里已有转录内容，上传时不要跳过"📝 完整转录内容"部分。

## 老板反馈记录
- 2026-05-10：六爷指出Wiki笔记缺少完整转录内容，要求修复且不再重复出现。已补录并更新流程。

---

## 经验教训(旧)
- 上传Wiki用 OpenClaw 内置飞书工具，不依赖 openclaw_runtime 模块
- WORKSPACE环境变量的`~`需要`.expanduser().resolve()`
- ASR脚本的dashscope.api_key必须显式设置，SDK不会自动读ALIYUN_ASR_API_KEY（2026-03-29修复）
- ASR上传文件改用纯HTTP requests绕过SDK（SDK的Files.upload会卡死）
- ASR上传响应格式可能是`{"data":...}`或`{"output":...}`，需兼容
- 音频格式不要转WAV（无压缩会变大），直接上传原始m4a
- 笔记生成应在ASR后检查转录文本是否为空，避免产出空笔记
- f2下载抖音视频偶尔会卡住无输出，注意cookies有效期(2-4周)
- **抖音下载必须用f2库，不要用yt-dlp**(2026-04-08确认)：yt-dlp对抖音反爬无解(报Fresh cookies needed)，f2库+cookies可正常下载
- 抖音视频处理应走video-learner-wiki skill流程：`python3 scripts/video_learner_wiki.py "URL"`，脚本内部自动识别平台、调用f2下载、ASR转录、GLM笔记
- 飞书Wiki API: 创建节点用`/wiki/v2/spaces/{space_id}/nodes`，不是`/wiki/v2/nodes`
- 飞书Docx API: 写入块用`/docx/v1/documents/{id}/blocks/{id}/children`，必须含block_id
- 飞书block_type: 3=H1,4=H2,5=H3...2=text; bullet/code/quote/divider不支持API创建，降级为text块
- `.env`文件需要`set -a && source .env && set +a`才能export到子进程
- feishu_uploader代码块内容必须分块写入（每块≤5000字符），不能截断，否则完整转录内容丢失
- **SSL修复(2026-04-01)**: Python requests默认SSL与DashScope不兼容，需monkey-patch SECLEVEL=1
- **网盘中转方案(2026-04-01, 2026-04-21验证)**: litterbox.catbox.moe中转大文件
  - ✅ litterbox.catbox.moe 可用（阿里云可访问），❌ catbox.moe 被屏蔽
  - 阿里云ASR支持最长12h/2GB文件，无需分段
  - 上传litterbox后拿公开URL直接提交ASR，阿里云从公网下载（快）
  - **关键！必须用 api.php 端点**：`https://litterbox.catbox.moe/resources/internals/api.php`
  - ❌ `upload.php` 端点返回404，不要用！
  - 已封装为 skill: `~/.openclaw/skills/file-relay/`
  - 飞书Bot无法用tenant_access_token上传文件到用户云空间（drive/v1/files/upload_all报1061002）
  - 大文件传输统一走 litterbox 中转方案
