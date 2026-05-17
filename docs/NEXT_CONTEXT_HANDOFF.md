# 新对话项目接力摘要

## 项目一句话

`灵境导游` 是中国软件杯 A5「景区导览服务 AI 数字人」项目：面向灵山胜境与拈花湾，提供可信 RAG 问答、拍照识景、自然语言路线规划、Kiosk 到手机路线接力、后台运营洞察和评测看板。

## 技术栈

- 后端：FastAPI、SQLite、Python 标准库为主。
- 前端：React、Vite、TypeScript、纯 CSS。
- 图标：游客端底部导航和文化按钮优先使用 `frontend/public/assets/icons/lingshan/` 下 PNG 图标；通用小动作可用 lucide。
- 默认模式：mock provider，无 API Key 可运行。
- 路由：`/` 游客端，`/kiosk` 终端，`/admin` 后台，`/route/:id/share?code=...` 路线分享页。

## 当前主线叙事

演示只围绕三条闭环：

1. 可信导览闭环：游客提问 -> Query Understanding -> RAG 检索 -> 来源卡片 -> 数字人语音讲解 -> 低置信澄清 -> 后台知识缺口 -> 评测看板证明准确率。
2. 路线分流闭环：自然语言偏好 -> Route Planner 评分 -> 导览图拓扑顺路约束 -> 拥挤点错峰/替代 -> Kiosk 二维码带走 -> 手机逐站讲解。
3. 运营改进闭环：交互日志 -> 热门问题/低置信问题/反馈趋势 -> 知识缺口 -> FAQ 草稿 -> 加入评测集 -> 持续提升可信度。

## 已完成能力

- 资料解析：`data/processed/attractions.json` 覆盖 22 个景点，另有 `knowledge_chunks.json`、`behavior_summary.json`。
- RAG 问答：本地 lexical retrieval + mock 生成，返回 sources，不相干问题不编造。
- Query Understanding Gate：分流景区问答、景区总览、兴趣推荐、对比、拥挤运营状态、路线规划、澄清和资料外兜底。
- 识景：`POST /api/vision/recognize`，mock Top3 候选确认，确认后再讲解。
- 路线：5 类主题、全量 22 景点候选池、必去/可选/避开、Route Memory、多轮重规划、约束护栏。
- 拥挤分流：`mock_simulation` 拥挤度、等待时间、路线评分和 decision_trace。
- 运营事件：后台可配置 crowd/closed/show/recommendation，路线规划会读取并解释。
- 路线分享：Kiosk 生成二维码/短码，手机分享页用短期 code 复取同一路线。
- 景区拓扑：`data/processed/scenic_graph.json` 基于导览图、观光车图和 Bing 地图抽象，22 个景点全部映射。
- 路线拓扑前端展示：Task UI-06 已完成，提交 `5afc17a style: show scenic route topology`；游客端路线 tab 和分享页展示顺路指数、总步行估算、涉及游线、回头路风险、观光车建议和非 GPS 导航说明。
- 后台：analytics overview、运营事件、知识缺口、评测看板。
- 游客 UI：`/` 已改为五 tab，推荐 tab 和底部 PNG 导航基本通过；字体分层已落地。
- 数字人：游客端“游灵山”tab 和 Kiosk 左侧主视觉区已从 07.6H iframe 面板升级为 07.6I 本页 WebRTC 观看播放器。播放器通过 `POST /api/avatar/webrtc/offer` 走灵境后端 signaling 代理，不调用 `getUserMedia`，不请求摄像头/麦克权限，并保留 React/SVG/CSS fallback。游客端和 Kiosk 播报按钮已接入后端 `/api/avatar/speak`、`/api/avatar/play-clip`，本地浏览器 TTS 已关闭。OpenAvatarChat + LiteAvatar sidecar 可播可信短句和白名单预存 wav；Task 07.6G 已修正 clip `AVATAR_AUDIO` finish 语义并默认优先使用 fast 配置，人工确认 clip 流畅度达到演示合格。

## 当前关键文件

- 项目约束：`AGENTS.md`
- 战略计划：`SOFTBEI_A5_PLAN.md`
- PRD 与任务：`SOFTBEI_A5_PRD.md`
- 启动与能力说明：`README.md`
- 游客 UI 规范：`docs/VISITOR_UI_SPEC.md`
- 演示脚本：`docs/DEMO_SCRIPT.md`
- 技术叙事：`docs/TECHNICAL_STORY.md`
- 游客端：`frontend/src/pages/MobileHomePage.tsx`
- 分享页：`frontend/src/pages/RouteSharePage.tsx`
- API client：`frontend/src/api/client.ts`
- 设计 token：`frontend/src/styles/tokens.css`
- 页面样式：`frontend/src/styles/pages.css`
- 路线服务：`backend/app/services/route_service.py`
- 拓扑服务：`backend/app/services/scenic_graph_service.py`
- 拓扑数据：`data/processed/scenic_graph.json`
- 拓扑校验：`scripts/validate_scenic_graph.py`
- 拓扑评测：`scripts/eval_route_topology.py`
- 数字人启动：`scripts/start_avatar_demo.ps1`
- 数字人停止：`scripts/stop_avatar_demo.ps1`
- 数字人性能记录：`docs/AVATAR_LITEAVATAR_PERFORMANCE_TUNING.md`

## 当前 UI 状态

- 游客端不是长滚动主页，而是五个移动 tab：推荐、游灵山、识景、路线、我的。
- 推荐 tab 和底部导航已经基本通过人工确认，后续不要大动。
- 底部导航使用 PNG 图标 + CSS，不是整张截图背景。
- 字体分层：
  - 标题、底部导航、文化按钮、景点名：`--font-cultural`，本地绑定 `Lingjing Cultural Serif` / `Noto Serif SC`。
  - 正文、长回答、输入框：`--font-readable`。
  - 数字、日期、接口信息：`--font-numeric`。

## 路线拓扑状态

- 已完成 Task 06.15。
- 拓扑来源：用户提供的原始导览图、手绘观光车图、Bing 地图截图。
- 拓扑线路：
  - 线路1 中轴线
  - 线路2 宝藏东线
  - 线路3 愿心西线
  - 出口假日广场线
  - 拈花湾禅意小镇环线
- 22 个 `attraction_id` 全部映射到 `attraction_node_map`。
- 路线返回新增 `route_topology` 和每站拓扑字段。
- 明确边界：这是导览图人工抽象拓扑，不是 GPS 导航，不是地图导航服务，也不代表实测步行时间。

## 数字人策略

- 当前数字人分为两层：主前端 fallback 状态位，以及 OpenAvatarChat + LiteAvatar sidecar 表现层。
- 游客端和 Kiosk 的数字人按钮只调用灵境后端 API；实际发声/口型由后端转发到 sidecar，前端不直连模型厂商或 OpenAvatarChat API。
- 游客端和 Kiosk 的直播式画面使用本页 WebRTC 观看播放器，不再 iframe 嵌入 8282 WebUI；signaling 只走 `POST /api/avatar/webrtc/offer` 后端代理。新增 `GET /api/avatar/status` 只用于判断 sidecar ready/active session 并驱动 fallback。
- 当前 OAC sidecar 的 FastRTC 路由是 `send-receive/audio-video`；纯 recvonly offer 能拿到 answer 但不会创建 active Lingjing session。07.6I 播放器因此生成静音音轨和空白 canvas 视频轨作为无权限 session bootstrap，不读取真实摄像头或麦克风。
- OpenAvatarChat + LiteAvatar 已完成本机演示 spike：可信短句和预存 clip 都能驱动发声/口型表现。
- Task 07.6G 结论：clip 卡顿/无口型的关键修复是 sidecar `AVATAR_AUDIO` 先发音频包 `finish_stream=False`，再发 10ms 静音结束包 `finish_stream=True`；`start_avatar_demo.ps1` 默认优先用 ignored fast 配置并对齐游客端后端端口 `8000`。
- 正确接法：作为 avatar sidecar/表现层，不接管业务大脑。
- 业务大脑仍是当前 FastAPI：Query Understanding、RAG、Route Planner、Vision、Analytics。
- sidecar 失败时必须 fallback 当前 mock 数字人。
- 不把大模型权重、商业字体、真实 API Key 或大体积第三方源码直接提交主仓库。
- tracked 提交：`2303ed3 feat: add trusted avatar speech sidecar demo`。
- ignored sidecar patch、音频、日志仍在 `external/`，不进入 git。

## 重要边界

- 不修改 `示范景区公开资料包/`。
- mock 模式必须无 API Key 可运行。
- 前端只调用后端 API，不直连模型厂商。
- 不声称现场客流数据、GPS 导航、地图导航服务或硬件接入。
- 行为数据是公开样例/行业画像，不能声称为灵山或拈花湾真实运营数据。
- Route Planner 是受约束规则评分器，LLM 只能用于结构化意图解析和表达润色，不能自由决定路线点位。

## 下一步建议

优先执行：

1. Task QA-UI：完整走游客端 `/`、Kiosk、Admin、分享页、数字人 WebUI 演示流程，确认 UI 按钮返回 `mode=sidecar` 且 8282 WebUI 有声音/口型。
2. Task Voice/Avatar Config：研究音色和数字人模型配置化，但不要在答辩前大改主链路。
3. Task Docs：提交前同步 README/演示脚本/技术叙事中的 07.6G fast 配置和游客端接入状态。
4. 必要时再做局部 UI 细修。

## 启动命令

后端：

```powershell
cd D:\py\dota
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd D:\py\dota
npm --prefix .\frontend run dev -- --host 127.0.0.1 --port 5174
```

常用入口：

- 游客端：http://127.0.0.1:5174/
- Kiosk：http://127.0.0.1:5174/kiosk
- Admin：http://127.0.0.1:5174/admin

数字人表现层：

```powershell
cd D:\py\dota
& .\scripts\start_avatar_demo.ps1 -OpenWebUI -OpenVisitor
```

入口：

- OpenAvatarChat WebUI：http://127.0.0.1:8282
- 游客端数字人入口：http://127.0.0.1:5174/

停止：

```powershell
& .\scripts\stop_avatar_demo.ps1
```

## 验证命令

常用完整链路：

```powershell
cd D:\py\dota
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
python -m compileall backend/app scripts
npm --prefix .\frontend run build
```

文档或小改至少运行：

```powershell
python -m compileall backend/app scripts
npm --prefix .\frontend run build
```

## 新对话第一步建议

1. 先读 `AGENTS.md`、`SOFTBEI_A5_PLAN.md`、`SOFTBEI_A5_PRD.md`、`README.md`、`docs/NEXT_CONTEXT_HANDOFF.md`。
2. 运行 `git status --short`。
3. 如果有未提交 UI 改动，先确认来源，不要覆盖。
4. 优先执行 Task QA-UI：真实走完 7 分钟演示流程，并记录风险和局部细修项。
