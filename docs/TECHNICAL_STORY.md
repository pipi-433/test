# 灵境导游技术叙事

## 一句话

灵境导游不是让大模型自由讲解景区，而是用 `Query Understanding Gate + 本地 RAG 来源 + 受约束 Route Planner + 本地 eval reports` 组成可解释、可评测、可运营的景区 AI 数字人导览系统。

## 三大闭环

### 1. 可信导览闭环

游客自然语言输入会先进入问题理解门控。系统识别这是景区事实问答、景区总览、兴趣推荐、景点对比、拥挤运营状态、路线规划、澄清追问，还是资料外问题。

只有通过门控且确认属于本地资料范围的问题，才会进入 RAG 检索。回答必须带 sources；没有来源或低置信时，系统给出不编造的兜底，并沉淀为知识缺口。

### 2. 路线分流闭环

路线规划不是 LLM 自由生成路径。系统使用经典路线模板作为 seed，再结合 22 个已解析景点候选池、必去/可选/避开约束、时间预算、拥挤度、运营事件和人群偏好做规则评分。

每条路线返回 `recommendation_score`、`score_breakdown`、`decision_trace`、`constraint_summary`、`route_topology` 和每站的拥挤/运营/拓扑解释。必去点不会因为拥挤被静默删除；如果受临时关闭或拥挤影响，会保留提示或触发澄清。

### 3. 运营改进闭环

游客问答、识景、路线、二维码带走、反馈会沉淀为本地交互日志。后台可以看到服务统计、拥挤预警、运营事件、知识缺口和评测看板。

当系统遇到无来源、低置信或“信息不准”反馈，会进入知识缺口列表。管理员可以生成 FAQ 草稿、标记状态并加入评测集，为后续资料补充和索引重建提供依据。

## Query Understanding Gate

问题理解门控是所有自然语言入口的第一道边界。当前实现为本地 `mock_rule_gate`，后续可替换或增强为 LLM Query Understanding Agent，但输出必须仍是结构化字段：

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

因此，`海底两万里`、`天上适合怎么游览？`、`这个电影适合怎么游览？` 会进入资料外兜底；`介绍景区` 会进入澄清；`灵山大佛适合怎么游览？` 才会进入 RAG。

## RAG 可信问答

资料包只读解析后生成 `data/processed/*.json`，再初始化到 SQLite。问答时使用本地 lexical retrieval 检索 `knowledge_chunks`，mock 生成器只基于命中的 chunks 组织中文回答。

关键约束：

- 没有 sources 时不编造。
- sources 展示 `source_file`、`source_section`、`title`。
- 低置信或无来源问题进入 knowledge gap。
- 前端只调用后端 API，不直连模型厂商。

## 识景确认

当前识景仍是 mock 规则候选，不接真实 VLM。它基于文件名、hint、text hint、景点名、id、标签计算 Top3 候选。

系统不会把一次识别结果直接当成事实讲解，而是让用户确认候选后，再进入该景点讲解或 suggested questions。未来接真实 VLM 时，VLM 也只负责候选识别，事实讲解仍由 RAG sources 生成。

## Route Planner 为什么不是 LLM 自由规划

路线智能体在产品上叫 Route Memory Agent，但工程上是受约束规则评分器。

规划流程：

1. 解析自然语言路线意图。
2. 更新 session 级 Route Memory。
3. 使用路线模板 seed 和全量景点候选池。
4. 应用约束优先级：数据不可用、避开、必去、时间、拥挤、主题、模板默认。
5. 融合拥挤度与运营事件。
6. 输出可解释路线和 decision trace。

后续 LLM 可以增强意图解析，但不能绕过 Route Planner 直接生成路线。

## 景区导览图拓扑路线规划

路线规划在全量 22 个景点候选池之上，增加了 `data/processed/scenic_graph.json`。它不是外部地图服务，而是基于三类资料人工抽象出的半真实游线拓扑：

- 用户提供的灵山胜境线路导览图。
- 用户提供的手绘观光车图，用于理解观光车站点、观光车线路和出口假日广场关系。
- Bing 地图截图，用于人工参考景点相对位置、道路/步道布局、湖面和停车场边界。

拓扑线路包括：

- 线路1 中轴线：从入口、五明桥、菩提大道、九龙灌浴、祥符禅寺一路推进到灵山大佛。
- 线路2 宝藏东线：连接九龙灌浴/百子戏弥勒一带到五印坛城、灵山梵宫、曼飞龙塔等东侧点位。
- 线路3 愿心西线：覆盖无尽意斋等西侧静心支线。
- 出口假日广场线：用于解释从中轴/东线回到出口方向的收束路线。
- 拈花湾禅意小镇环线：覆盖资料包中的拈花湾 6 个景点，作为独立环线处理。

这个拓扑服务给 Route Planner 做三件事：

1. 顺路解释：说明路线为什么沿某条游线推进，哪里属于跨线或跨区。
2. 步行估算：给出到下一站的大致分钟数，帮助游客理解节奏。
3. 轻量评分修正：顺路指数高时小幅加分，回头路风险高时小幅扣分，但不覆盖必去/避开/时间/拥挤等核心约束。

路线顶层返回：

- `route_topology.route_smoothness_score`
- `route_topology.total_walking_minutes`
- `route_topology.line_names`
- `route_topology.backtrack_count`
- `route_topology.sightseeing_bus_suggestion`
- `route_topology.source_note`

每站返回：

- `stop.topology_line_name`
- `stop.walking_minutes_to_next`
- `stop.transport_hint`
- `stop.backtrack_risk`
- `stop.smoothness_reason`

工程边界必须讲清楚：

- 这不是 GPS 导航。
- 这不是地图导航服务。
- 没有接入高德或百度地图。
- 不代表实时定位。
- 不代表现场客流或硬件采集数据。
- 它只用于顺路解释、步行估算、回头路风险提示、观光车建议和 Route Planner 的轻量评分修正。

## Mock 数据边界

当前系统明确处于比赛演示 mock/local 模式：

- 无 API Key 也能运行。
- LLM、Embedding、VLM、TTS provider 默认 mock。
- 拥挤度来自 `mock_simulation`，不代表现场硬件采集数据。
- 运营事件来源为 `manual_admin` 或 `mock_simulation`，不代表真实硬件。
- 不接真实闸机、摄像头、Wi-Fi 探针、GPS、IoT。
- 不记录真实个人身份。

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

后台评测看板读取 `evals/reports/*_latest.json`，展示 QA、识景、路线、拥挤分流、分享、Analytics、路线对话、路线约束、全量候选池、运营事件、知识缺口等报告。

演示前建议运行：

```powershell
python .\scripts\init_db.py
python .\scripts\validate_api_data.py
python .\scripts\eval_qa.py
python .\scripts\eval_query_understanding.py
python .\scripts\eval_query_capability.py
python .\scripts\eval_vision.py
python .\scripts\eval_routes.py
python .\scripts\eval_crowd_routes.py
python .\scripts\validate_scenic_graph.py
python .\scripts\eval_route_topology.py
python .\scripts\eval_route_share.py
python .\scripts\eval_analytics.py
python .\scripts\eval_route_conversation.py
python .\scripts\eval_route_constraints.py
python .\scripts\eval_operation_events.py
python .\scripts\eval_knowledge_gaps.py
python .\scripts\eval_eval_reports.py
```

这套报告的作用是证明：系统不是“看起来像 AI”，而是把关键边界、兜底策略和路线约束都变成可重复验证的测试样例。
