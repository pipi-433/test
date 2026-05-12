# 灵境导游

中国软件杯 A5「景区导览服务 AI 数字人」项目。当前版本已完成游客端 QA、mock 识景、mock 路线推荐、自然语言路线推荐、Route Memory Agent、模拟拥挤度分流、运营事件控制台、知识缺口闭环、评测看板、Kiosk 二维码路线带走、本地交互日志/反馈洞察和数字人语音演示闭环；默认无 API Key 可运行。

## 本轮实现

- 游客手机端 `/`：数字人主区域、景点选择、Query Understanding Gate、自然语言能力矩阵、RAG 问答、拍照识景、路线推荐、逐站讲解入口。
- 景区终端 `/kiosk`：横屏触控欢迎态、大数字人、大按钮、热门问题、路线摘要、二维码占位。
- 管理后台 `/admin`：左侧导航、顶部状态栏、指标卡、mock 图表、热门问题、provider 状态。
- 后端 API：health、provider、景点、知识切片、QA、识景、路线推荐。
- 问题结构门控：所有文本先经 `mock_rule_gate` 判断景区问答、路线规划、澄清或资料外兜底，避免导览通用词误触发 RAG。
- 游客自然语言能力矩阵：把“介绍景区”“我对历史感兴趣”“灵山和拈花湾哪个适合拍照”“现在人多吗”等问题分流到景区总览、兴趣推荐、对比、拥挤/运营状态或 RAG。
- 拥挤度感知路线：mock_simulation 快照、路线评分拆解、决策说明、后台拥挤点预警。
- 自然语言路线推荐：规则 parser 将“老人孩子、3 小时、别太挤、必去景点”等口语输入转为结构化约束，再由受控路线规划器生成路线。
- Route Memory Agent：本地 mock 会话记忆保存偏好、必去点、避开点和上一条路线，支持缩短、少走路、避拥挤、多拍照、多历史等多轮重规划。
- 路线约束规则矩阵：集中 `ROUTE_CONSTRAINT_RULES`，补齐必去/避开冲突、无效景点、短时长、多 session 隔离和取消必去等边界评测。
- 全量景点候选池：经典路线模板只作为 seed，全部 22 个已解析景点都可作为必去、可选、避开或主题补充点参与规划。
- 运营事件控制台：后台可发布拥挤、临时关闭、演出提醒和推荐分流事件，路线规划会读取 active events 并在 `decision_trace` 中解释调整原因。
- 评测看板：后台读取 `evals/reports/*_latest.json`，展示 QA、识景、路线、约束、知识缺口等本地评测通过率、失败数和失败样例摘要。
- 数字人语音演示层：GPT Image 辅助确定 2D 新中式导览员视觉方向，最终以 React/SVG/CSS 可控数字人落地，接入浏览器 SpeechSynthesis TTS、可选 SpeechRecognition 输入和文本降级。
- Kiosk 路线带走：终端生成拥挤度感知路线，展示二维码、短码和手机打开链接，手机访问 `/route/:id/share?code=...` 查看同一条路线。
- 交互日志与反馈：QA、识景、路线、二维码带走和游客反馈写入本地 SQLite，后台 `/admin` 读取 `/api/analytics/overview` 展示运营洞察。
- DX 配置：`.env.example`、README、Task 02 目录预留。

## Mock Provider 模式

默认不需要任何 API Key。`.env.example` 中所有 provider 都是 `mock`，真实模型接入会在后续任务通过后端 provider 抽象完成。前端不会直接调用模型厂商 API。

## 安装前端依赖

```powershell
cd frontend
npm install --cache ..\.npm-cache
```

## 启动后端

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/provider/status
```

## 启动前端

```powershell
cd frontend
npm run dev
```

访问：

- 手机游客端：http://127.0.0.1:5173/
- 景区终端：http://127.0.0.1:5173/kiosk
- 管理后台：http://127.0.0.1:5173/admin

## 构建检查

```powershell
cd frontend
npm run build
```

## 资料解析

Task 02 使用标准库解析只读资料包，不需要额外 Python 依赖：

```powershell
python .\scripts\parse_sources.py
python .\scripts\validate_processed_data.py
```

输出文件：

- `data/processed/attractions.json`
- `data/processed/knowledge_chunks.json`
- `data/processed/behavior_summary.json`

## 数据库初始化

Task 03 使用 SQLite 和 Python 标准库导入处理后的 JSON：

```powershell
python .\scripts\init_db.py
python .\scripts\validate_api_data.py
```

默认数据库位置：

- `data/app.db`

基础 API：

- `GET /api/attractions`
- `GET /api/attractions/{id}`
- `GET /api/knowledge/chunks?attraction_id={id}`
- `GET /api/analytics/behavior-summary`

## Mock RAG 问答

Task 04 提供本地 lexical retrieval + mock 生成，不需要 API Key、向量库或真实大模型：

```powershell
python .\scripts\eval_qa.py
```

### Query Understanding Gate

Task 04.7 在 RAG 前增加问题结构门控。游客输入会先进入本地规则版 `mock_rule_gate`，输出结构化理解结果：

- `domain`：`scenic_guide` / `route_planning` / `recommendation` / `operations` / `out_of_scope` / `unclear`
- `intent`：事实问答、景点介绍、景区总览、兴趣推荐、景点/景区对比、拥挤运营状态、路线请求、路线重规划或未知
- `entities`：命中的本地 22 个景点 ID
- `slots`：景区、兴趣、同行人群、时间预算、对比对象等结构化槽位
- `handler`：`qa_rag` / `scenic_area_intro` / `interest_recommendation` / `comparison` / `crowd_status` / `route_planner` / `clarification` / `out_of_scope`
- `should_retrieve` / `should_route`：是否允许进入 RAG 或路线规划
- `needs_clarification`：是否先追问

关键边界：`适合`、`怎么游览`、`介绍`、`看点`、`讲解` 只是意图词，不是景区实体。没有景区实体或明确上下文时，不会进入 RAG；例如“海底两万里”“天上适合怎么游览？”会返回资料外兜底，`sources=[]`，不编造景区内容。未来可替换为 LLM Query Understanding Agent，但 LLM 只允许输出结构化意图 JSON，不能直接生成事实答案或路线。

调试 API：

- `POST /api/query/understand`

```json
{
  "message": "灵山大佛适合怎么游览？",
  "selected_attraction_id": null,
  "current_route_id": null
}
```

评测：

```powershell
python .\scripts\eval_query_understanding.py
python .\scripts\eval_query_capability.py
```

问答 API：

- `POST /api/qa`

请求示例：

```json
{
  "question": "灵山大佛适合怎么游览？",
  "attraction_id": "lingshan-ls-011",
  "visitor_profile": {
    "group_type": "family",
    "time_budget_minutes": 120,
    "interests": ["佛教文化", "拍照打卡"]
  }
}
```

### Natural Language Capability Matrix

Task 04.8 将游客文本入口从“关键词判 RAG/路线”升级为本地规则能力矩阵。`/api/qa` 和调试入口 `/api/guide/query` 会根据 `understanding.handler` 返回不同结构：

- `qa_rag`：景点事实、文化故事、演艺时间等必须进入本地知识切片检索，并返回 `sources`。
- `scenic_area_intro`：介绍灵山胜境、介绍拈花湾，或“介绍景区”先澄清范围。
- `interest_recommendation`：根据 22 个景点的标签、类别、简介和游客兴趣返回 3-5 个推荐景点。
- `comparison`：比较两个景点或景区，例如“灵山和拈花湾哪个适合拍照”。
- `crowd_status`：复用 mock 拥挤度和运营事件，回答“现在人多吗”“有临时关闭吗”等状态问题。
- `route_planner`：路线需求只交给受约束 Route Planner，不用 RAG 自由编排行程。
- `out_of_scope` / `clarification`：资料外问题不编造；缺少实体或范围时先追问。

当前实现仍是 `mock_rule_gate`，不接真实 LLM。后续如接 LLM，只能替换/增强结构化意图解析，不能绕过 RAG sources、Route Planner 约束、Crowd/Operation 策略直接生成事实答案或路线。

## Mock 识景与 Top3 候选确认

Task 04.5 提供文件名 / hint / text_hint 驱动的 mock 识景，Task 04.6 将其升级为 Top3 候选确认流程。不需要真实 VLM 或 API Key：

```powershell
python .\scripts\eval_vision.py
```

识景 API：

- `POST /api/vision/recognize`

表单字段：

- `file`: 上传图片文件或 mock 样例文件
- `hint`: 可选，景点名称、景点 id 或关键词
- `text_hint`: 可选，补充描述

返回会兼容旧字段 `matched_attraction`、`confidence`、`explanation`、`suggested_questions`、`mode`、`latency_ms`，并新增：

- `candidates`：最多 3 个本地景点候选，每个候选包含景点对象、置信度、判断依据和命中信号。
- `needs_confirmation`：低置信或候选分差较小时为 `true`。
- `confirmation_reason`：解释为什么需要确认。
- `selected_attraction_id`：当前确认前为 `null`，前端确认后在本地切换当前讲解景点。

游客端不会把低置信候选直接当事实讲解；确认某个候选后才进入该景点的一键讲解和 suggested questions。无匹配时 `matched_attraction` 为 `null` 且 `candidates=[]`，不会编造识别结果。未来可替换为真实 VLM provider，但 VLM 只负责候选识别，事实讲解仍由 RAG 来源生成。

## Mock 路线推荐

Task 06/06.5 提供亲子、历史、自然、祈福、拍照 5 类路线模板，并在 mock_simulation 拥挤度快照下做可解释分流推荐。不需要真实 GPS、真实客流硬件或真实模型：

```powershell
python .\scripts\eval_routes.py
python .\scripts\eval_crowd_routes.py
python .\scripts\eval_route_share.py
python .\scripts\eval_analytics.py
python .\scripts\eval_route_constraints.py
python .\scripts\eval_operation_events.py
```

路线 API：

- `GET /api/routes/themes`
- `GET /api/crowd/snapshot`
- `POST /api/routes/recommend`
- `GET /api/routes/{id}/share?code={share_code}`

请求示例：

```json
{
  "theme": "family",
  "time_budget_minutes": 240,
  "group_type": "family",
  "intensity": "easy",
  "interests": ["亲子轻松", "佛教文化"],
  "start_attraction_id": "lingshan-ls-011",
  "avoid_crowd": true,
  "crowd_tolerance": "medium",
  "must_visit_attraction_ids": ["nianhuawan-nh-003"],
  "optional_attraction_ids": ["nianhuawan-nh-002"],
  "avoid_attraction_ids": ["lingshan-ls-006"]
}
```

返回会包含路线名称、主题、预计时长、逐站点位、停留时间、讲解重点、适合原因、`recommendation_score`、`score_breakdown`、`decision_trace`、`crowd_policy` 和 30 分钟有效的 mock 分享码。每个 stop 会包含：

- `crowd_level`: `low` / `medium` / `high`
- `crowd_score`: 0-100
- `wait_minutes`
- `crowd_note`
- `operation_events` / `operation_note`：如该站受运营事件影响，会显示事件来源和处理说明。

拥挤度快照示例：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/crowd/snapshot
```

重要边界：当前所有拥挤度均为 `mock_simulation` 演示数据，不代表真实景区客流，也没有接入闸机、摄像头、Wi-Fi 探针、GPS 或 IoT 硬件。

## 自然语言路线推荐与 Route Memory Agent

Task 06.8 增加本地规则版自然语言路线推荐。工程边界仍是“规则/mock parser + 受约束 Route Planner”，不接真实 LLM，不允许模型自由决定路线点位；后续 LLM/RAG 只能增强意图解析或表达，不得绕过 `ROUTE_CONSTRAINT_RULES`。

新增 API：
- `POST /api/routes/intent`
- `POST /api/routes/conversation`

意图解析示例：
```json
{
  "message": "我带老人孩子，3 小时，别太挤，灵山大佛一定要去",
  "selected_attraction_id": "lingshan-ls-011"
}
```

对话式路线示例：
```json
{
  "session_id": "mock-session-001",
  "message": "太累了，缩短一点",
  "current_route_id": "route-xxx",
  "selected_attraction_id": "lingshan-ls-011"
}
```

支持的结构化约束：
- `must_visit_attraction_ids`：必去景点，不能因为模拟拥挤被直接删除，只能保留、延后或提示错峰。
- `optional_attraction_ids`：可选兴趣点，时间允许时优先补充。
- `avoid_attraction_ids`：用户明确不想去或已去过的点，除非与必去冲突。
- `crowd_tolerance`：`low` / `medium` / `high`。

每个路线站点会补充：
- `constraint_type`: `must_visit` / `optional` / `recommended` / `alternative`
- `constraint_reason`
- `decision_reason`
- `crowd_action`: `keep` / `delay` / `replace` / `skip` / `keep_with_warning`

评测：
```powershell
python .\scripts\eval_route_conversation.py
python .\scripts\eval_route_constraints.py
python .\scripts\eval_route_full_pool.py
```

当前 parser、memory 和 session 都是本地 mock 演示机制，不接真实账号系统，不记录个人敏感身份，不接真实 GPS、真实客流硬件或真实 LLM。

### 路线约束规则矩阵

Task 06.9 将路线约束集中到 `backend/app/services/route_service.py` 的 `ROUTE_CONSTRAINT_RULES`。约束优先级固定为：

1. 数据不可用 / 景点不存在。
2. 用户明确避开 `avoid_attraction_ids`。
3. 用户明确必去 `must_visit_attraction_ids`。
4. 时间预算。
5. 拥挤舒适度。
6. 主题偏好。
7. 系统推荐 / 模板默认。

关键边界：

- 同一景点同时出现在必去和避开中时，`/api/routes/conversation` 不生成路线，返回澄清选项。
- 必去点遇到 high 模拟拥挤时不能删除，只能 `delay` 或 `keep_with_warning`，并写入 `decision_trace`。
- 多个必去点导致时间不足时，优先删低优先级推荐点，保留必去点，并在 `constraint_summary.warning` 中说明。
- 不存在的景点 id 不进入路线，会写入 `constraint_summary.invalid_attraction_ids`。
- 起点如果被避开，只作为上下文，不作为停留点，除非同时被明确设为必去。
- 新 session 不继承旧 session 的 must/avoid 约束；同 session 中“算了，不去 X”会移除必去约束。

后续接入真实 LLM/RAG 时，只能增强意图解析和讲解表达，不得绕过 `ROUTE_CONSTRAINT_RULES` 直接生成路线点位。

### 全量景点路线候选池

Task 06.10 将路线规划从“核心五点 demo”扩展为“全部已解析景点可约束规划”。`ROUTE_TEMPLATES` 仍保留为经典路线 seed，但最终候选池来自 `GET /api/attractions` 的 22 个景点；游客可把任意景点设为必去、可选或避开，规划器再结合主题画像、时间预算、拥挤度和约束规则生成路线。

关键点：
- `must_visit_attraction_ids`、`optional_attraction_ids`、`avoid_attraction_ids` 支持灵山胜境和拈花湾全部景点 id。
- 每个景点会派生路线画像：`family_score`、`history_score`、`nature_score`、`blessing_score`、`photo_score`、`route_priority`、`default_stay_minutes`、`is_core_landmark`。
- 每个 stop 增加 `selection_source`、`profile_match_reason`、`theme_score`，用于解释它来自必去约束、经典 seed、可选加权还是全量候选池补充。
- 自然语言解析基于全部景点名和别名，例如“香月花街一定要去，九龙灌浴避开”“我想去拈花湾的五灯湖和梵天花海”。
- 游客端路线面板提供全量景点搜索选择器，可添加“必去 / 可选 / 避开” chips，不再硬编码少数核心点。

评测：
```powershell
python .\scripts\eval_route_full_pool.py
```

当前仍是规则评分 + mock parser，不接真实 LLM、真实 GPS 或真实客流硬件。经典模板只是 seed，不是候选上限。

### 运营事件控制台

Task 06.12 将“mock 拥挤度分流”升级为“运营人员可配置事件 + 路线即时响应”。后台 `/admin` 提供运营事件控制台，可以快速创建并启停 4 类事件：

- `crowd`：拥挤提醒，会覆盖或提高该景点等待时间、拥挤评分和站点提示。
- `closed`：临时关闭。非必去点会被避开；如果是游客明确必去点，路线不会静默删除，而是在 stop 与 `decision_trace` 中提示确认。
- `show`：演出提醒，会进入站点 `operation_note` 或决策说明。
- `recommendation`：推荐分流，对相关景点做温和加权，但不会压过用户 `avoid_attraction_ids`。

运营事件表为 SQLite 本地表 `operation_events`，字段包含 `attraction_id`、`event_type`、`severity`、`message`、`start_at`、`end_at`、`source`、`created_by` 和 `active`。`scripts/init_db.py` 会幂等 seed 若干 `mock_simulation` 演示事件；后台创建的事件来源为 `manual_admin`。

API：

- `GET /api/operations/events?attraction_id=...`
- `GET /api/admin/operations/events?active_only=false`
- `POST /api/admin/operations/events`
- `PATCH /api/admin/operations/events/{id}`

创建示例：

```json
{
  "attraction_id": "lingshan-ls-013",
  "event_type": "closed",
  "severity": "critical",
  "message": "灵山梵宫临时维护，非必去路线建议避开。",
  "source": "manual_admin",
  "created_by": "admin-console",
  "active": true
}
```

路线响应新增：

- `operation_policy` / `operation_events_summary`
- 每个 stop 的 `operation_events`、`operation_note`
- `decision_trace` 中会写明 `manual_admin` 或 `mock_simulation` 来源。

评测：

```powershell
python .\scripts\eval_operation_events.py
```

重要边界：运营事件是本地演示配置，不代表真实闸机、摄像头、Wi-Fi 探针、GPS 或 IoT 数据；后续若接真实硬件，也不能绕过用户明确必去/避开约束规则。

### 数字人语音、TTS 与状态机

Task 07 增加第一版可演示的 2D 数字人语音层，Task 07.5 用 GPT Image 生成视觉参考并重设计为更扁平的新中式数字导览员。当前仍然保持 mock provider 模式，无需真实 TTS Key：

- GPT Image 仅用于确定“湖绿色导览服、铜金胸牌、温和可信、文化感”的视觉方向；最终前端不是静态 PNG，而是 React + SVG/CSS 可控组件。
- 数字人使用扁平 2D 半身导览员插画实现，不引入 Live2D、PixiJS 或生产级 3D 资产。
- 状态机覆盖 `welcome`、`listening`、`thinking`、`speaking`、`comforting`、`error` 和 `happy`。
- speaking 状态包含多段嘴型切换、低调声波和字幕高亮；停止播报后恢复自然微笑。
- 游客端 QA、识景、路线推荐、澄清追问、反馈成功和错误兜底会驱动数字人状态变化。
- TTS 使用浏览器 `window.speechSynthesis`，优先选择 `zh-CN` 声音；新播报会先停止上一段，长文本会截断为演示摘要。
- 语音输入使用浏览器 `SpeechRecognition` / `webkitSpeechRecognition`（如可用），识别结果只填入文本框，由游客确认后发送。
- 浏览器不支持语音能力时，页面会提示“文本提问仍可用”，不影响 QA、路线、识景和反馈主流程。

兼容边界：浏览器可能因系统语音包、权限、无头环境或自动播放策略限制 TTS/语音识别；本项目不接真实语音服务、不写真实 API Key，评审演示时优先使用文本主入口，语音作为附属能力。

### Kiosk 二维码带走

Kiosk 页面 `/kiosk` 可点击“生成推荐路线”，后端会在当前进程内缓存完整路线，并返回 `share.share_code`、`share.share_url`、`qr_payload` 和过期时间。终端展示二维码、短码和手机打开链接。

手机打开：

```text
/route/{route_id}/share?code={share_code}
```

分享页会校验短码并展示同一条路线，包括综合评分、模拟拥挤度说明、站点时间线、等待时间和逐站讲解问题复制按钮。错误码会使用统一结构：

- `ROUTE_SHARE_NOT_FOUND`
- `ROUTE_SHARE_CODE_INVALID`
- `ROUTE_SHARE_EXPIRED`

当前二维码和分享码都是 mock 演示机制，只在当前后端进程内稳定复取，默认 30 分钟有效；不接真实扫码硬件、账号系统或 GPS 导航。

## 交互日志、反馈与后台洞察

Task 06.7 增加本地 analytics 闭环。后端会自动记录：

- `qa`：问题、答案预览、来源数量、低置信兜底标记。
- `vision`：识别结果、置信度、文件名/提示词等模拟信息；不保存图片原始内容。
- `route_recommend` / `crowd_avoidance`：路线主题、评分、避拥挤策略和 high 拥挤点。
- `route_share_open`：手机打开 Kiosk 分享路线。
- `feedback`：评分、标签、可选评论。

反馈 API：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/feedback `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"channel":"mobile","route_id":"route-demo","rating":5,"tags":["路线合理","避开拥挤"],"comment":"演示反馈"}'
```

后台洞察 API：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/analytics/overview
```

返回包含 `service_count`、`qa_count`、`vision_count`、`route_count`、`share_open_count`、`feedback_count`、`average_rating`、`popular_questions`、`low_confidence_questions`、`route_theme_distribution`、`crowd_avoidance_count`、`high_crowd_attractions`、`feedback_tags` 和 `recent_events`。

重要边界：当前 analytics 是本地演示日志 + mock/公开样例数据，不代表真实景区全量运营数据；不接真实埋点平台，不记录账号、手机号、身份证等个人身份信息。

## 知识缺口闭环

Task 06.13 增加本地知识缺口工作流。游客问答出现无来源、低置信，或反馈标签包含“信息不准”时，后端会把问题沉淀到 SQLite 表 `knowledge_gaps`，后台 `/admin` 可查看并处理这些缺口。

后端能力：
- `GET /api/admin/knowledge/gaps?status=open`：查看知识缺口列表。
- `POST /api/admin/knowledge/gaps`：手动创建演示缺口。
- `POST /api/admin/knowledge/gaps/{id}/draft-faq`：基于 query、触发类型和命中来源生成规则化 FAQ 草稿。
- `PATCH /api/admin/knowledge/gaps/{id}`：更新 `open` / `drafted` / `resolved` / `ignored` 状态。
- `POST /api/admin/knowledge/gaps/{id}/add-eval`：幂等写入 `evals/knowledge_gaps.jsonl`，为后续评测看板准备样例。

FAQ 草稿当前为 mock/规则生成：如果没有可靠来源，会明确写“需管理员补充资料后发布”，不会编造资料包外事实。当前不会修改原始资料包，也不会重建向量索引。

评测命令：
```powershell
python .\scripts\eval_knowledge_gaps.py
```

Analytics overview 轻量增加 `knowledge_gap_count`、`open_knowledge_gap_count`、`drafted_knowledge_gap_count`。这些数据来自本地演示日志和 SQLite，不代表真实景区全量运营数据。

## 评测看板

Task 06.14 增加后台评测看板。`/admin` 会调用 `GET /api/admin/evals/overview`，读取 `evals/reports/*_latest.json` 的最新结果，并聚合为比赛演示用的可信度证明。该接口只读取本地 report，不会重新运行 eval，也不接外部评测平台。

看板覆盖：
- QA 准确率、识景成功率、路线推荐通过率、拥挤分流通过率、路线分享通过率。
- Query Capability、Analytics、Route Conversation、Route Constraints、Full Pool、Operation Events、Multipart Parser、Knowledge Gaps 等 report 状态。
- 必去景点保留率、拥挤点错峰解释率、低置信澄清准确率、知识缺口闭环通过率等衍生指标；无法精确推断时返回 `null` 和 reason，不伪造数值。
- 每个 report 的状态、样本数、失败数、平均延迟、更新时间和前 3 条失败样例摘要。

评测看板 API：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/admin/evals/overview
```

验证命令：

```powershell
python .\scripts\eval_multipart_parser.py
python .\scripts\eval_eval_reports.py
```

重要边界：评测看板读取的是本地 eval reports，用于比赛演示可信度证明；mock 模式和本地样例不代表生产 SLA，也不代表真实景区全量监控。

## 后续任务

后续可继续推进更高拟真度的数字人表现、真实 TTS provider、真实语音识别或更完整的多模态讲解，但这些能力仍应在 mock 模式稳定、无 API Key 可运行的前提下逐步接入。
