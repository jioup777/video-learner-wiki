# 升级日志

> 记录所有重要更新和改进

---

## 2026-03-15 - v2.0 稳定版

### ✨ 新功能

1. **完整流程脚本** (`complete_video_workflow.py`)
   - 集成所有步骤：下载 → 转录 → 笔记 → 上传
   - 智能平台识别（B站/抖音/YouTube）
   - 智能 ASR 路由（阿里云优先，Whisper 降级）
   - 完整的错误处理和日志输出

2. **飞书节点创建工具** (`create_video_node.py`)
   - 直接在主文档下创建子文档
   - 支持 Markdown 内容写入
   - 返回文档链接

3. **Skill 文档** (`VIDEO_LEARNER_SKILL.md`)
   - 完整功能说明和文档
   - 性能数据和使用指南
   - 技术栈和配置说明

4. **配置文档** (`CONFIGURATION.md`)
   - 环境变量配置说明
   - 飞书文档路径信息
   - 常见问题解答

5. **快速上手指南** (`QUICKSTART.md`)
   - 3步完成视频处理
   - 使用场景说明
   - 性能数据展示

### 🔧 配置更新

- **主文档 Token**: `LrTAdVQEnoKG1nxxKO5c5JjCn6p`
- **文档链接**: https://vicyrpffceo.feishu.cn/docx/LrTAdVQEnoKG1nxxKO5c5JjCn6p
- **知识库空间 ID**: `7566441763399581724`

**重要变更**: 所有视频学习笔记现在都在**主文档下创建子文档**，而不是在知识库根目录下。

### 📝 更新文件列表

```
scripts/
├── complete_video_workflow.py    # 新增：完整流程脚本
├── create_video_node.py           # 新增：飞书节点创建工具
├── asr_router.py                  # 保留：ASR 路由器
├── glm_note_generator.py           # 保留：笔记生成器
├── video_with_feishu.sh            # 保留：B站流程
└── process_douyin.sh              # 保留：抖音流程

root/
├── VIDEO_LEARNER_SKILL.md         # 新增：Skill 文档
├── CONFIGURATION.md               # 新增：配置说明
├── QUICKSTART.md                  # 新增：快速上手指南
└── UPGRADE_LOG.md                 # 本文档
```

### 🐛 修复

1. 修复 `upload_feishu.sh` 使用飞书 API 创建子文档节点
2. 确保所有脚本都使用正确的父节点 Token
3. 添加完整的环境变量配置说明

### 📊 性能提升

- **完整流程时间**: 25-50秒（取决于视频长度）
- **ASR 转录速度**: 2-3秒（阿里云 qwen3-asr-flash）
- **笔记生成速度**: 10-30秒（GLM-4-Flash）

---

## 2026-03-14 - v1.2 性能优化版

### ✨ 新功能

1. **ASR 路由器** (`asr_router.py`)
   - 智能选择 ASR 引擎
   - 阿里云优先（2-3秒）
   - Whisper 降级方案（15-20秒）

2. **GLM 笔记生成器** (`glm_note_generator.py`)
   - 结构化笔记生成
   - 6个部分：主题、观点、案例、识别方法、防骗建议、金句

### 📈 性能提升

- **ASR 转录速度**: 提升 4-5倍（从 30-40秒 到 9-15秒）
- **完整流程时间**: 提升 30%

### 🔧 优化

1. 优化笔记格式，增加6个结构化部分
2. 添加性能数据展示
3. 改进错误处理和日志输出

---

## 2026-03-13 - v1.1 功能完善版

### ✨ 新功能

1. **B站视频流程** (`video_with_feishu.sh`)
   - yt-dlp 下载音频
   - GLM 笔记生成
   - 飞书上传播

2. **抖音视频流程** (`process_douyin.sh`)
   - yt-dlp 下载音频
   - GLM 笔记生成
   - 飞书上传播

3. **笔记生成器** (`glm_note_generator.py`)
   - 基于 GLM-4-Flash
   - 结构化笔记格式

### 📝 新增文件

```
scripts/
├── video_with_feishu.sh           # B站流程
├── process_douyin.sh              # 抖音流程
└── glm_note_generator.py           # 笔记生成器
```

---

## 2026-03-12 - v1.0 初始版本

### ✨ 新功能

1. **基础架构**
   - 项目目录结构
   - 基础脚本框架

2. **ASR 工具**
   - 阿里云 ASR 集成
   - 本地 Whisper 支持

3. **飞书集成**
   - 文档创建工具
   - 内容上传功能

---

## 📊 版本演进

```
v1.0 (2026-03-12) - 初始版本
  ↓
v1.1 (2026-03-13) - 功能完善（B站/抖音/笔记生成）
  ↓
v1.2 (2026-03-14) - 性能优化（ASR 路由）
  ↓
v2.0 (2026-03-15) - 稳定版（完整流程脚本 + 完整文档）
```

---

## 🎯 未来计划

- [ ] 支持 YouTube 字幕直接提取
- [ ] 添加字幕时间戳同步
- [ ] 支持批量处理
- [ ] GPU 加速（Whisper）
- [ ] 更多笔记模板
- [ ] PDF 导出功能

---

**最后更新**: 2026年3月15日
**维护者**: 谭明 (Boss)
