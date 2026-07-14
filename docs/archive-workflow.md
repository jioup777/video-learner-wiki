# 视频归档上传标准化工作流（方案 B）

> **目的**：任何端（OpenClaw agent / CC）上传视频笔记到飞书时，都必须走完整归档 5 步，
> 杜绝"视频裸挂根节点 / Base 检索不到 / 归类缺失"。
> **适用**：`video_learner_wiki.py` 跑完产 artifact 后，由上传端执行本流程。
> **工具无关**：步骤 + 字段 + token 是契约；CC 用 lark-cli，OpenClaw 用内置 feishu_wiki/feishu_doc 等效执行。

---

## 前置：artifact 就绪

`video_learner_wiki.py` 跑完，`downloads/<video_id>/` 含：
- `metadata.json`（7 层：normalized/post_caption/transcript/summary/archive/download/asr）
- `transcript.txt`（口播稿全文）
- `post_caption.txt`（发布文案 raw_text）

读 `metadata.json` 拿 `normalized`（标题/博主/统计）+ `summary` + `archive`（待填 topic/note_url）。

---

## 步骤 1：判 topic（归类，最关键，禁止跳过）

读 `normalized.title/description/tags` + `summary`，按下表判 **1 个主 topic** + **0~N 个 subtopic**。

### 5 主题 + 杂项

| topic | 定义 | 典型关键词 | subtopic 候选 |
|---|---|---|---|
| **AI科技** | AI 工具/Agent/Skill/编程/生图/LLM/视频制作技术 | claude/openclaw/skill/agent/mcp/gemini/gpt/编程/生图/蒸馏/提示词/模型/yt-dlp | AI绘画/AI编程/AI视频/Agent/LLM/提示词工程 |
| **内容创作** | 写作/编故事/网文/小说/剧本/短剧/文案 | 网文/小说/写作/剧本/短剧/邪修/起点/金手指/爽点/拆书/大纲/编剧/码字 | 小说/短剧/剧本/网文 |
| **IP运营** | 做账号/搞流量/做人设/选题/自媒体运营 | IP/人设/流量/钩子/选题/自媒体/抖音运营/小红书运营/涨粉/网感/注意力/播放 | 短视频制作/账号运营/涨粉/变现/选题 |
| **成功方法论** | 认知/思维/效率/习惯/决策/人生/读书 | 认知/效率/习惯/决策/方法论/人生系统/纳瓦尔/反脆弱/心法/焦虑/复盘 | 认知/效率/习惯/决策 |
| **搞钱收集** | 赚钱/副业/投资/金融/网赚/防骗避坑 | 赚钱/搞钱/副业/量化/期权/韭菜/灰产/炒币/金融/经济/房产/投毒/防骗 | 防骗/副业/投资/灰产识别 |
| **杂项** | 非 5 主题（生活/健身/旅游/测试/政治/无法分类） | 健身/蛋白粉/旅游/钓鱼/美食/测试/政治/纪录片 | — |

### 判断优先级（避免误判，从上到下）

1. **写作/编故事类**（即使含"AI 写小说"）→ 内容创作（AI 只是手段）
2. **赚钱/金融类**（即使含"AI 赚钱/OpenClaw 炒币"）→ 搞钱收集
3. **做 IP/流量/账号类** → IP运营
4. **AI 工具/技术类** → AI科技
5. **认知/思维/人生类** → 成功方法论
6. **都不沾** → 杂项

### 边界例

| 标题 | 正确归类 | 易错点 |
|---|---|---|
| AI 写小说没风格 | 内容创作 | 不是 AI科技 |
| OpenClaw 自动炒币赚钱 | 搞钱收集 | 不是 AI科技 |
| 纳瓦尔做 IP | IP运营 | 含"IP" |
| 纳瓦尔建立系统 | 成功方法论 | 无"IP"，是认知 |
| 中年失业倒卖赚钱 | 搞钱收集 | 副业搞钱 |
| 30 万粉知识付费变现 | IP运营 | 流量变现非纯金融 |

> CC 端可跑 `scripts/topic_suggest.py`（关键词版，仅 4 领域，需手工补"搞钱收集/杂项"）；OpenClaw agent 直接按本表语义判断。

### 主题节点 token（素材卡挂这里，**不是根节点！**）

| topic | parent_node_token |
|---|---|
| AI科技 | `VB3EwujEwiXlpJkptLgcRJWvn4b` |
| 内容创作 | `Zg8cwEP2hiFz45kCXVpcduZrnNe` |
| IP运营 | `GzkuwDk7finlyUkl3rCcSOzMn9d` |
| 成功方法论 | `AdEpwiqfhiM5uQk7PaDcI3ngn6d` |
| 搞钱收集 | `LUy4wZiCZiJgV9kKY6VcT1XUnNy` |
| 杂项 | `OxQ0wdmbaidFaEkYFmPcRDDBnKb` |

- space_id：`7566441763399581724`
- 根节点（**禁止直接挂素材卡**）：`I1GtwmgL4iok6WkfOghcR1uwnld`

---

## 步骤 2：建素材卡节点（挂在步骤 1 的主题节点下）

在**主题节点**下建 docx 子节点。命名：`[MMDD][博主] 标题`（标题截断到 ~30 字）。

**lark-cli（CC 端参考）**：
```bash
lark-cli wiki +node-create \
  --space-id 7566441763399581724 \
  --parent-node-token <主题节点token> \
  --title "[0714][博主] 标题" \
  --obj-type docx --as user \
  --jq '.data | {node_token, obj_token}'
```
记下返回的 `node_token`（=note_url 的 token）和 `obj_token`（写内容用）。

**OpenClaw**：用内置 feishu_wiki 在对应主题节点下建 docx 子节点，取 node_token + obj_token。

---

## 步骤 3：写基础卡内容

按基础卡 5 区模板生成 markdown，写入素材卡 docx。

**5 区**：①元数据 ②发布文案(post_caption.raw_text) ③口播稿(transcript.txt) ④摘要(summary) ⑤链接(原视频 url + 素材卡 note_url)。

**lark-cli**：
```bash
cd <基础卡.md 所在目录>   # @file 须相对路径
lark-cli docs +update --doc <obj_token> --command overwrite \
  --doc-format markdown --content @基础卡.md --as user
```

**OpenClaw**：用内置 feishu_doc 写入等效内容。

---

## 步骤 4：登记 Base 总索引（全库检索入口，禁止漏）

在 Base 总索引表 append 一行。22 字段从 metadata 映射。

- base_token：`IEG8bOPwNaPIxjsMTl4cvlS0ngc`
- table_id：`tblHp4iDLWJHI0Zt`

### 字段映射（metadata → Base 列）

| Base 列 | 来源 | 类型 |
|---|---|---|
| video_id | normalized.video_id | text |
| url | normalized.url | text |
| platform | normalized.platform（抖音/YouTube/B站/小红书） | select |
| title | normalized.title | text |
| creator | normalized.creator | text |
| creator_url | normalized.creator_url | text(url) |
| published_at | normalized.published_at | datetime |
| duration_sec | normalized.duration_sec | number |
| view_count | normalized.view_count | number |
| like_count | normalized.like_count | number |
| comment_count | normalized.comment_count | number |
| topic | 步骤 1 判定的 topic | select |
| subtopic | 步骤 1 判定的 subtopic | multi-select |
| scene_tags | archive.scene_tags（学知识/拆运营/攒素材/摸底） | multi-select |
| custom_tags | archive.custom_tags | multi-select |
| quality_score | archive.quality_score（1-5） | rating |
| summary | summary | text |
| transcript_source | transcript.source（groq/aliyun/subtitle） | select |
| note_url | 步骤 2 素材卡链接 `https://vicyrpffceo.feishu.cn/wiki/<node_token>` | text(url) |
| archived_at | 当前时间 | datetime |
| archived_by | `openclaw` 或 `cc` | select |
| analysis_cards | 本步留空，产分析卡后回填 | text |

**lark-cli**：
```bash
lark-cli base +record-batch-create \
  --base-token IEG8bOPwNaPIxjsMTl4cvlS0ngc --table-id tblHp4iDLWJHI0Zt \
  --json '{"records":[{"fields":{"video_id":"...","title":"...","topic":"搞钱收集","note_url":"...","archived_by":"openclaw",...}}]}' \
  --as user
```

> select/multi-select 字段写新值前，若该选项不存在需先 `base +field-update` 加选项（全量 options 含已有+新增）。

---

## 步骤 5：回填 artifact metadata.json

更新本地 artifact 的 `metadata.json`，让契约完整（`contract_check` 通过）：

```json
"archive": {
  "topic": "<步骤1判定的topic>",
  "subtopic": ["<步骤1判定的subtopic>"],
  "topic_source": "ai_suggested",          // 或 user_confirmed
  "topic_confidence": 0.9,
  "note_url": "https://vicyrpffceo.feishu.cn/wiki/<node_token>",
  "archived_at": "2026-07-14T...+08:00",
  "archived_by": "openclaw",
  "analysis_cards": []                      // 产分析卡后填 [{type,title,doc_token,url}]
}
```

---

## 上传完必查清单

- [ ] 素材卡挂在**主题节点**下（`node-get` 的 `parent_node_token` ≠ 根节点 `I1GtwmgL4iok6WkfOghcR1uwnld`）
- [ ] Base 总索引有这行（`record-search` 按 title 能搜到，`count ≥ 1`）
- [ ] `metadata.json` 的 `archive.note_url` 已填、`archived_by=openclaw`
- [ ] topic 不是 `pending`（已正式判定）

---

## 常见错误（OpenClaw 首跑就踩过）

| 错误 | 后果 | 正确 |
|---|---|---|
| 素材卡挂根节点 | 裸笔记，未分类，根节点堆积 | 挂步骤 1 的主题节点 |
| 漏 Base 登记 | 全库检索不到，成孤儿 | 步骤 4 必做 |
| topic 判错（AI写小说→AI科技） | 归错类，检索混乱 | 按优先级表判 |
| note_url 不回填 | artifact 契约不完整 | 步骤 5 必做 |

---

## 参考（CC skill references，repo 外）

- 7 层 metadata schema：`~/.claude/skills/video-learner-wiki/references/metadata-schema.md`
- 飞书结构 + 全 token：`references/feishu-structure.md`
- 基础卡/分析卡模板：`references/card-templates.md`
- topic 关键词工具（CC）：`scripts/topic_suggest.py`（关键词版，4 领域，需手工补搞钱/杂项）
