# 灵境导游

中国软件杯 A5「景区导览服务 AI 数字人」项目。当前版本已完成游客端 QA、mock 识景、mock 路线推荐、自然语言路线推荐、Route Memory Agent、模拟拥挤度分流、Kiosk 二维码路线带走、本地交互日志/反馈洞察和数字人语音演示闭环；默认无 API Key 可运行。

## 本轮实现

- 游客手机端 `/`：数字人主区域、景点选择、RAG 问答、拍照识景、路线推荐、逐站讲解入口。
- 景区终端 `/kiosk`：横屏触控欢迎态、大数字人、大按钮、热门问题、路线摘要、二维码占位。
- 管理后台 `/admin`：左侧导航、顶部状态栏、指标卡、mock 图表、热门问题、provider 状态。
- 后端 API：health、provider、景点、知识切片、QA、识景、路线推荐。
- 拥挤度感知路线：mock_simulation 快照、路线评分拆解、决策说明、后台拥挤点预警。
- 自然语言路线推荐：规则 parser 将“老人孩子、3 小时、别太挤、必去景点”等口语输入转为结构化约束，再由受控路线规划器生成路线。
- Route Memory Agent：本地 mock 会话记忆保存偏好、必去点、避开点和上一条路线，支持缩短、少走路、避拥挤、多拍照、多历史等多轮重规划。
- 路线约束规则矩阵：集中 `ROUTE_CONSTRAINT_RULES`，补齐必去/避开冲突、无效景点、短时长、多 session 隔离和取消必去等边界评测。
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

## Mock 识景

Task 04.5 提供文件名 / hint / text_hint 驱动的 mock 识景，不需要真实 VLM 或 API Key：

```powershell
python .\scripts\eval_vision.py
```

识景 API：

- `POST /api/vision/recognize`

表单字段：

- `file`: 上传图片文件或 mock 样例文件
- `hint`: 可选，景点名称、景点 id 或关键词
- `text_hint`: 可选，补充描述

返回会包含 `matched_attraction`、`confidence`、`explanation`、`suggested_questions`、`mode`、`latency_ms`。无匹配时 `matched_attraction` 为 `null`，不会编造识别结果。

## Mock 路线推荐

Task 06/06.5 提供亲子、历史、自然、祈福、拍照 5 类路线模板，并在 mock_simulation 拥挤度快照下做可解释分流推荐。不需要真实 GPS、真实客流硬件或真实模型：

```powershell
python .\scripts\eval_routes.py
python .\scripts\eval_crowd_routes.py
python .\scripts\eval_route_share.py
python .\scripts\eval_analytics.py
python .\scripts\eval_route_constraints.py
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
  "crowd_tolerance": "medium"
}
```

返回会包含路线名称、主题、预计时长、逐站点位、停留时间、讲解重点、适合原因、`recommendation_score`、`score_breakdown`、`decision_trace`、`crowd_policy` 和 30 分钟有效的 mock 分享码。每个 stop 会包含：

- `crowd_level`: `low` / `medium` / `high`
- `crowd_score`: 0-100
- `wait_minutes`
- `crowd_note`

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

## 后续任务

后续可继续推进更高拟真度的数字人表现、真实 TTS provider、真实语音识别或更完整的多模态讲解，但这些能力仍应在 mock 模式稳定、无 API Key 可运行的前提下逐步接入。
