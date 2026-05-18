# 下一轮上下文交接

## 当前一句话

`灵境导游` 是中国软件杯 A5「景区导览服务 AI 数字人」项目：用本地知识库、可信 RAG、Top3 识景确认、受约束路线规划、Kiosk 扫码带走、后台运营闭环和数字人表现层，完成灵山胜境/拈花湾导览演示。

## 最近提交

请以上游 git 记录为准，当前已确认的最近关键提交包括：

- `0e2b98d feat: add admin sentiment and system settings`
- `b0bb722 feat: wire admin core actions`
- `9d294b8 feat: integrate avatar live viewer demo`
- `5afc17a style: show scenic route topology`
- `2303ed3 feat: add trusted avatar speech sidecar demo`

## 当前工作区状态

本次 Round 3 是文档同步任务，不提交、不 push。

开始/执行过程中观察到工作区存在未提交项：

- 本轮文档改动：`docs/DEMO_SCRIPT.md`、`docs/TECHNICAL_STORY.md`、`docs/NEXT_CONTEXT_HANDOFF.md`、新增 `docs/SOFTBEI_REQUIREMENT_MATRIX.md`。
- 既有数字人 sidecar 相关后端改动：`backend/app/services/avatar_clip_player.py`、`backend/app/services/avatar_speaker.py`、`backend/app/services/avatar_webrtc.py`。这些不属于 Round 3 文档任务，本轮没有修改、没有提交，下一轮接手前需要先确认来源。

如果继续开发，请先运行：

```powershell
cd D:\py\dota
git status --short
git diff --stat
```

不要盲目 `git add .`，不要把文档同步和既有 sidecar 代码改动混成一个提交。

## 已完成能力

### 可信导览闭环

- 数据产物：`data/processed/attractions.json` 覆盖 22 个景点，另有 `knowledge_chunks.json`、`behavior_summary.json`。
- Query Understanding Gate：将用户自然语言分流到景区问答、景区总览、兴趣推荐、对比、拥挤/运营状态、路线规划、澄清或资料外兜底。
- 可信 RAG：本地 lexical retrieval + mock 生成，返回 sources，不对资料外问题编造。
- 识景 Top3：`POST /api/vision/recognize` 返回候选、置信度、依据和确认状态，确认后再进入讲解。
- 知识缺口：低置信、无来源、信息不准反馈可沉淀为 knowledge gap，后台可生成 FAQ 草稿并加入评测集。
- 评测看板：后台读取 `evals/reports/*_latest.json` 展示各能力通过率和失败样例。

### 路线分流闭环

- Route Planner：覆盖 22 个景点候选池，支持主题、时间、亲子/老人、强度、兴趣、必去、可选、避开、自然语言 Route Memory、多轮重规划。
- 约束规则：必去点不会因拥挤被静默删除；must/avoid 冲突触发澄清；低优先级推荐点优先被删减。
- 拥挤度：`mock_simulation` 数据提供 crowd level、wait minutes、crowd note，用于演示避峰分流。
- 运营事件：后台可配置 crowd/closed/show/recommendation 事件，路线 decision trace 会解释事件影响。
- Kiosk 接力：Kiosk 生成路线、展示二维码/短码/链接，手机 `/route/:id/share?code=...` 复取同一路线。
- scenic_graph 拓扑：`data/processed/scenic_graph.json` 基于用户提供导览图、手绘观光车图和 Bing 地图人工抽象，覆盖 22 个景点。
- 前端拓扑展示：游客端路线 tab 和分享页展示顺路指数、总步行估算、涉及游线、回头路次数、观光车建议和每站下一段步行估算。

### 运营改进闭环

- Analytics overview：服务量、QA、识景、路线、分享打开、反馈、热门问题、低置信问题、路线偏好、拥挤分流、最近事件。
- 运营事件控制台：管理员可发布拥挤、临时关闭、演出提醒、推荐分流事件。
- 知识库管理 Round 1：后台资产、FAQ 草稿、mock 重建索引、mock 发布闭环。
- 数字人管理 Round 1：数字人 profile、试听音色、预存讲解 mock job。
- 游客感受度 Round 2：本地日志/反馈汇总为满意度、正向率、待处理问题、负面原因、服务建议。
- 系统设置 Round 2：后台可读取/保存系统设置，并运行本地健康检查。

### 数字人表现层

- 前端保留 React/SVG/CSS 数字人 fallback 状态机。
- OpenAvatarChat + LiteAvatar 已作为 sidecar/live viewer demo 接入。
- 前端只调用灵境后端 API，如 `/api/avatar/speak`、`/api/avatar/play-clip`、`/api/avatar/webrtc/offer`。
- sidecar 只播报灵境后端给出的可信短文本或预存片段，不生成事实、不规划路线、不接管 RAG/识景/路线/运营分析。

## 关键边界

- `示范景区公开资料包/` 只读，不修改。
- `external/**` 不作为主仓业务代码修改区，不提交第三方源码、模型、日志、音频缓存。
- mock 模式必须无 API Key 可运行。
- 前端只能调用本项目后端 API，不能直连模型厂商或 sidecar。
- 拥挤度和运营事件是 `mock_simulation` / `manual_admin` 演示数据，不代表真实客流、真实硬件、闸机、摄像头或 Wi-Fi 探针。
- scenic_graph 是基于导览图人工抽象的半真实游线拓扑，用于顺路解释、步行估算、回头路风险和观光车建议；不是 GPS 导航、不是地图导航服务、不是实时定位。
- Route Planner 是受约束规则评分器，LLM 后续只能增强结构化意图解析和表达润色，不能自由决定路线点位。
- OpenAvatarChat + LiteAvatar 是数字人表现层 sidecar，不是业务大脑。

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

数字人 sidecar 演示：

```powershell
cd D:\py\dota
& .\scripts\start_avatar_demo.ps1 -OpenWebUI -OpenVisitor
```

停止 sidecar：

```powershell
cd D:\py\dota
& .\scripts\stop_avatar_demo.ps1
```

常用入口：

- 游客端：http://127.0.0.1:5174/
- Kiosk：http://127.0.0.1:5174/kiosk
- Admin：http://127.0.0.1:5174/admin
- OpenAvatarChat WebUI：http://127.0.0.1:8282/ui/index.html

## 验收命令

文档/轻量验收：

```powershell
cd D:\py\dota
git diff --check
rg -n "真实GPS|真实客流|真实硬件|实时定位|真实地图导航" docs README.md
rg -n "(sk-[A-Za-z0-9_-]{16,}|ark-[A-Za-z0-9_-]{16,}|DASHSCOPE_API_KEY\s*=\s*[^\s#]+|OPENAI_API_KEY\s*=\s*[^\s#]+)" -g "!external/**" -g "!node_modules/**" -g "!frontend/dist/**" .
```

完整演示前建议：

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

## 不要碰的目录和文件

- `D:\py\dota\示范景区公开资料包\`
- `D:\py\dota\external\`
- `.env`、真实 API Key、模型权重、音频缓存、logs、dist、`data/app.db`
- 与当前任务无关的 backend/frontend 改动，尤其是已有未提交 sidecar 文件。

## 下一步建议

1. **Task QA-UI**：完整走游客端 `/`、Kiosk、Admin、分享页 7 分钟演示流程，记录演示风险、按钮可用性、移动端溢出、console error。
2. 单独确认既有未提交数字人 sidecar 后端改动来源，决定是否单独提交或继续调试。
3. 如答辩需要，可制作 PPT 或答辩讲稿，基于 `docs/DEMO_SCRIPT.md`、`docs/TECHNICAL_STORY.md`、`docs/SOFTBEI_REQUIREMENT_MATRIX.md`。
4. 只做局部 UI/文案修复，不再在答辩前新增大功能。
