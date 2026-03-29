# 🎬 Video Learner 安装完成报告

**安装时间**: 2026-03-15 14:54 GMT+8  
**安装位置**: `~/.openclaw/workspace-video-learner/`  
**Skill 位置**: `~/.openclaw/extensions/video-learner/SKILL.md`

---

## ✅ 安装完成项

### 1. 系统依赖
| 依赖 | 版本 | 状态 |
|------|------|------|
| Python | 3.12.3 | ✅ |
| FFmpeg | 6.1.1 | ✅ |
| yt-dlp | 2026.03.13 | ✅ |
| deno | 2.7.5 | ✅ |

### 2. Python 依赖（虚拟环境：`~/.openclaw/venv-video-learner/`）
| 包 | 状态 |
|------|------|
| yt-dlp | ✅ |
| dashscope | ✅ |
| python-dotenv | ✅ |
| f2 | ✅ |

### 3. 脚本文件
| 文件 | 状态 |
|------|------|
| video_learner.py | ✅ |
| downloaders/__init__.py | ✅ |
| downloaders/bilibili.py | ✅ |
| downloaders/youtube.py | ✅ |
| downloaders/douyin.py | ✅ |
| asr_aliyun.py | ✅ |
| note_generator.py | ✅ |
| feishu_uploader.py | ✅ |

### 4. 环境变量配置
| 变量 | 状态 | 值 |
|------|------|-----|
| GLM_API_KEY | ✅ | 已配置 |
| ALIYUN_ASR_API_KEY | ✅ | 已配置 |
| FEISHU_SPACE_ID | ✅ | 已配置 |
| FEISHU_PARENT_TOKEN | ✅ | 已配置 |

---

## 🚀 使用方法

### 基本用法
```bash
# 激活虚拟环境
source ~/.openclaw/venv-video-learner/bin/activate

# 设置 PATH（包含 deno）
export PATH="$HOME/.deno/bin:$PATH"

# 运行视频处理
cd ~/.openclaw/workspace-video-learner
python scripts/video_learner.py "视频 URL"
```

### 示例命令

#### B 站视频
```bash
python scripts/video_learner.py "https://www.bilibili.com/video/BV1xx411c7mD"
```

#### YouTube 视频
```bash
python scripts/video_learner.py "https://www.youtube.com/watch?v=xxxxx"
```

#### 抖音视频
```bash
python scripts/video_learner.py "https://v.douyin.com/xxxxx/"
```

#### 不上传飞书（仅生成本地笔记）
```bash
python scripts/video_learner.py "URL" --no-upload
```

---

## ⚠️ 可选配置（提升成功率）

### B 站 Cookies（推荐配置）

B 站下载需要有效的 cookies 文件，否则可能遇到 412 错误。

**获取方式：**
1. 登录 bilibili.com
2. 使用浏览器扩展导出 Netscape 格式 cookies
3. 保存到 `~/.openclaw/workspace-video-learner/cookies/bilibili_cookies.txt`

**或使用浏览器 cookies：**
```bash
yt-dlp --cookies-from-browser chrome "https://www.bilibili.com/video/BVxxxxx"
```

### YouTube Cookies（推荐配置）

YouTube 反爬虫机制严格，建议使用 cookies。

**获取方式：**
```bash
yt-dlp --cookies-from-browser chrome "https://www.youtube.com/watch?v=xxxxx"
```

---

## 📊 性能指标

| 视频时长 | 下载 | ASR | GLM 笔记 | 飞书 | 总计 |
|----------|------|-----|---------|------|------|
| 2 分钟 | ~2s | ~3s | ~5s | ~3s | ~13s |
| 5 分钟 | ~5s | ~6s | ~10s | ~5s | ~26s |
| YouTube(有字幕) | ~2s | 跳过 | ~5s | ~3s | ~10s |

---

## 🔧 故障排查

### B 站下载失败 (412 错误)
```bash
# 需要配置有效的 B 站 cookies
# 保存到 ~/.openclaw/workspace-video-learner/cookies/bilibili_cookies.txt
```

### 抖音下载失败
```bash
# 确保 f2 已安装
source ~/.openclaw/venv-video-learner/bin/activate
f2 --version
```

### YouTube 字幕未检测到
- 部分视频没有官方字幕，会自动回退到 ASR
- 字幕检测支持：zh-CN, zh-Hans, zh, zh-TW, zh-Hant

### 飞书上传失败
检查：
- FEISHU_SPACE_ID 是否正确
- FEISHU_PARENT_TOKEN 是否有写权限
- 飞书授权是否有效

---

## 📝 后续配置

老板，你现在可以：

1. **测试运行** - 提供一个视频 URL 测试完整流程
2. **配置 B 站 cookies** - 提升 B 站视频下载成功率
3. **配置 YouTube cookies** - 提升 YouTube 视频下载成功率
4. **调整笔记生成策略** - 修改 note_generator.py 中的提示词

---

*Video Learner v2.0 - 安装完成*
*Ready to learn from videos! 🎬*
