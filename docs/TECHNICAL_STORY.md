# 灵境导游技术叙事

## 一句话

灵境导游不是让大模型自由讲景区，而是用 `Query Understanding Gate + 本地 RAG 来源 + 受约束 Route Planner + 导览图拓扑 + 数字人表现层 + Admin 运营闭环 + 本地 eval reports` 组成可解释、可评测、可演示的景区 AI 数字人系统。

## 三大闭环

### 可信导览闭环

游客输入先进入 Query Understanding Gate。系统判断这是景区事实问答、景区总览、兴趣推荐、景点/景区对比、拥挤运营状态、路线规划、澄清追问，还是资料外问题。

只有属于本地资料范围且允许检索的问题，才进入 RAG。回答必须带 sources；无来源、低置信或资料外问题会明确兜底，并可沉淀为知识缺口。

### 路线分流闭环

路线规划不是 LLM 自由生成路径。系统使用经典路线模板作为 seed，再结合全量 22 景点候选池、必去/可选/避开约束、时间预算、同行人群、拥挤度、运营事件和导览图拓扑做规则评分。

每条路线返回 `recommendation_score`、`score_breakdown`、`decision_trace`、`constraint_summary`、`operation_policy`、`route_topology` 和每站解释。必去点不会因为拥挤被静默删除；遇到临时关闭或高拥挤时，会保留提示、延后或触发澄清。

### 运营改进闭环

QA、识景、路线、二维码带走、反馈会写入本地 SQLite 日志。Admin 展示服务统计、运营事件、知识缺口、游客感受度报告、数据大屏、系统设置和评测看板。

低置信、无来源或“信息不准”反馈会生成 knowledge gap。管理员可以生成 FAQ 草稿、加入评测集、标记状态，为后续资料补充和索引重建提供依据。

## Query Understanding Gate

Gate 是自然语言入口的第一道结构化边界。当前实现是本地 `mock_rule_gate`，后续可替换或增强为 LLM Query Understanding Agent，但输出仍必须是结构化 JSON：

- `domain`
- `intent`
- `entities`
- `slots`
- `handler`
- `should_retrieve`
- `should_route`
- `needs_clarification`
- `reasons`

它解决两个核心问题：

1. “适合、怎么游览、介绍、看点、讲解”只是意图词，不是景区实体。
2. 没有景区实体或明确上下文时，不允许直接进入 RAG 编造答案。

示例：

- `灵山大佛适合怎么游览？` -> `qa_rag`
- `我对历史感兴趣，有什么景点推荐？` -> `interest_recommendation`
- `灵山和拈花湾哪个适合拍照？` -> `comparison`
- `现在人多吗？` -> `crowd_status`
- `介绍景区` -> `clarification`
- `海底两万里` -> `out_of_scope`

## 可信 RAG

资料包只读解析后生成 `data/processed/attractions.json`、`knowledge_chunks.json` 和 `behavior_summary.json`，再初始化到 SQLite。RAG 当前使用本地 lexical retrieval，mock 生成器只基于命中的 chunks 组织中文回答。

关键约束：

- 没有 sources 时不编造。
- sources 展示 `source_file`、`source_section`、`title`。
- 低置信或无来源问题进入 knowledge gap。
- 前端只调用后端 API，不直连模型厂商。

后续可接 embedding、rerank 或 LLM 润色，但事实答案仍必须受 sources 约束。

## 识景确认

当前识景是 mock Top3 候选确认，不接真实 VLM。候选来自文件名、hint、text_hint、景点名、id、标签和景区信息的规则匹配。

流程：

1. 上传图片或 mock 样例。
2. 返回最多 3 个本地景点候选。
3. 前端展示置信度、判断依据和确认按钮。
4. 用户确认后，再进入该景点 RAG 讲解。

未来接真实 VLM 时，VLM 也只负责候选识别；景点事实讲解仍由 RAG sources 生成。

## Route Planner Agent

产品上可以叫 Route Planner Agent / Route Memory Agent，工程上是受约束规则评分器，不允许 LLM 自由决定点位。

### 全量 22 景点候选池

经典路线模板只作为 seed。最终候选池来自 `GET /api/attractions` 的 22 个景点，灵山胜境和拈花湾景点都可作为：

- `must_visit_attraction_ids`
- `optional_attraction_ids`
- `avoid_attraction_ids`
- 主题补充候选

每个景点会派生路线画像，例如亲子、历史、自然、祈福、拍照、默认停留时间和核心地标权重。

### Route Memory

Route Memory 保存 session 级偏好：

- 主题、时间、人群、体力、兴趣
- 必去 / 可选 / 避开景点
- 当前路线、已删除/延后点、高拥挤点
- 最近操作和 turn_count

多轮请求如“太累了，缩短一点”“人太多，换一个”“算了，不去灵山大佛”会先更新 memory，再调用 Route Planner。

### 约束优先级

集中规则表 `ROUTE_CONSTRAINT_RULES` 固定优先级：

1. 数据不可用 / 景点不存在
2. 用户明确避开
3. 用户明确必去
4. 时间预算
5. 拥挤舒适度
6. 主题偏好
7. 系统推荐 / 模板默认

重要边界：

- 同一景点同时必去和避开时，返回澄清，不静默处理。
- 必去点高拥挤时不能删除，只能延后或保留并提示。
- 时间不足时保留必去点，删低优先级推荐点，并写入 warning。
- 新 session 不继承旧 session 约束。

## scenic_graph 拓扑路线解释

`data/processed/scenic_graph.json` 是基于三类资料人工抽象出的半真实游线拓扑：

- 用户提供的线路导览图。
- 手绘观光车图，用于理解观光车站点、观光车线路和出口假日广场关系。
- Bing 地图截图，用于人工参考景点相对位置、道路/步道布局、湖面和停车场边界。

拓扑线路：

- 线路1 中轴线
- 线路2 宝藏东线
- 线路3 愿心西线
- 出口假日广场线
- 拈花湾禅意小镇环线

Route Planner 返回字段：

- `route_topology.route_smoothness_score`
- `route_topology.total_walking_minutes`
- `route_topology.line_names`
- `route_topology.backtrack_count`
- `route_topology.sightseeing_bus_suggestion`
- `route_topology.source_note`
- `stop.topology_line_name`
- `stop.walking_minutes_to_next`
- `stop.transport_hint`
- `stop.backtrack_risk`
- `stop.smoothness_reason`

工程边界：

- 不是 GPS 导航。
- 不是地图导航服务。
- 不接高德 / 百度地图。
- 不代表实时定位。
- 不代表真实客流或硬件采集数据。
- 只用于顺路解释、步行估算、回头路风险、观光车建议和 Route Planner 的轻量评分修正。

## 拥挤度、运营事件与 Crowd Predictor Provider 预留

当前拥挤度来自 `mock_simulation`，每条记录包含 `crowd_level`、`crowd_score`、`wait_minutes`、`source` 和更新时间。运营事件来自后台 `manual_admin` 或 seed 的 `mock_simulation`，可配置拥挤、临时关闭、演出提醒和推荐分流。

路线规划会读取 active events：

- crowd：影响等待时间和拥挤提示。
- closed：非必去点避开；必去点保留并提示确认。
- show：加入演出提醒。
- recommendation：温和加权，不压过用户避开约束。

后续真实部署可增加 Crowd Predictor Provider，但当前演示版没有训练真实模型。候选方案：

- LightGBM / XGBoost：用节假日、时段、天气、预约、历史客流等表格特征预测点位拥挤。
- 时间序列模型：对各景点的分时客流做短时预测。
- 时空图模型：把景点作为节点、游线作为边，预测人流转移。

这些只能作为可替换 provider 接入，且必须继续保留人工运营事件、用户必去/避开约束和“非真实客流”的边界提示。

## OpenAvatarChat + LiteAvatar sidecar

数字人策略分三层：

1. React/SVG/CSS fallback：无 sidecar、无 API Key 时仍有数字人状态和字幕。
2. trusted text：`POST /api/avatar/speak` 接收灵境后端生成的可信短文本，转交 sidecar 播报。
3. preset clip：`POST /api/avatar/play-clip` 只接收白名单 clip_id，播放预存景点讲解 wav。

当前游客端和 Kiosk 的直播画面通过 `POST /api/avatar/webrtc/offer` 走灵境后端 signaling 代理。前端不直连 OpenAvatarChat API，不调用模型厂商，也不让 sidecar 生成景区事实或路线。

关键边界：

- OpenAvatarChat + LiteAvatar 只是表现层。
- 业务大脑仍是 FastAPI 中的 Query Understanding、RAG、Route Planner、Vision、Analytics。
- sidecar 失败时返回 mock accepted 或前端 fallback，不影响主流程。
- 不提交 external 源码、模型、日志、音频缓存或真实 Key。

## Admin Round 1 / Round 2

### Round 1：知识库管理和数字人管理

已完成最小闭环：

- `GET/POST/PATCH /api/admin/knowledge/assets`
- `GET/POST/PATCH /api/admin/knowledge/faqs`
- `POST /api/admin/knowledge/reindex`
- `POST /api/admin/knowledge/publish`
- `GET/PATCH /api/admin/avatar/profile`
- `POST /api/admin/avatar/voice-test`
- `POST /api/admin/avatar/clips/generate`
- `GET /api/admin/avatar/clips/jobs`

边界：后台知识资产和 FAQ 是本地管理闭环，不直接写入现有 RAG chunks；数字人配置只影响管理视图和表现层调用。

### Round 2：游客感受度报告和系统设置

已完成：

- `GET /api/admin/sentiment/report`
- `POST /api/admin/sentiment/report/generate`
- `GET /api/admin/system/settings`
- `PATCH /api/admin/system/settings`
- `POST /api/admin/system/healthcheck`

游客感受度报告基于本地交互日志、反馈样例和 mock 数据生成，包含满意度、正向率、待跟进问题、低置信数量、情绪波动指数、关注点、负向原因、路线体验标签、服务建议和反馈明细。

系统设置保存在 SQLite，用于演示景区名称、provider 模式、avatar 模式、mock 拥挤度、路线拓扑和数据边界提示。healthcheck 检查 backend、database、avatar mock、sidecar status 和 knowledge local，不依赖 API Key。

## Mock / Local 边界

- mock 模式无 API Key 可运行。
- LLM、Embedding、VLM、TTS 默认 provider 为 mock。
- 拥挤度是 mock_simulation，不代表真实现场客流。
- 运营事件是 manual_admin / mock_simulation，不代表真实硬件。
- scenic_graph 是导览图人工抽象，不是 GPS 导航。
- 行为数据是公开样例 / 行业画像，不声称为景区真实运营数据。
- 不记录真实个人身份，不保存图片原始内容。

## 后续接 LLM 的正确位置

可以接入：

- Query Understanding Agent：把自然语言解析为结构化 intent/entities/slots。
- RAG answer style：在 sources 约束下优化表达。
- Route intent parser：更好理解多轮路线需求。

不能接入为：

- 直接生成无来源景区事实。
- 绕过 route constraints 自由规划路线。
- 前端直连模型厂商。
- 把真实 API Key 写入前端、README 或示例代码。

## 评测可信证明

后台评测看板读取 `evals/reports/*_latest.json`，展示 QA、Query Understanding、Query Capability、Vision、Route、Crowd Route、Route Share、Analytics、Route Conversation、Route Constraints、Full Pool、Operation Events、Knowledge Gaps、Eval Reports 等报告。

演示前建议运行：

```powershell
python .\scripts\init_db.py
python .\scripts\validate_api_data.py
python .\scripts\validate_scenic_graph.py
python .\scripts\eval_qa.py
python .\scripts\eval_query_understanding.py
python .\scripts\eval_query_capability.py
python .\scripts\eval_vision.py
python .\scripts\eval_routes.py
python .\scripts\eval_crowd_routes.py
python .\scripts\eval_route_conversation.py
python .\scripts\eval_route_constraints.py
python .\scripts\eval_route_full_pool.py
python .\scripts\eval_route_share.py
python .\scripts\eval_route_topology.py
python .\scripts\eval_analytics.py
python .\scripts\eval_operation_events.py
python .\scripts\eval_knowledge_gaps.py
python .\scripts\eval_eval_reports.py
```

这套报告证明系统不是“看起来像 AI”，而是把事实来源、资料外兜底、路线约束、拥挤分流、知识缺口和评测结果都变成可重复验证的工程闭环。
