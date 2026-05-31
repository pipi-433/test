# 灵境导游 7 分钟演示脚本

## 演示前准备

先确认不提交真实 API Key，并尽量保证主仓库工作区只包含本轮计划内改动。

```powershell
cd D:\py\dota
git status --short
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

启动主服务：

```powershell
cd D:\py\dota
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix .\frontend run dev -- --host 127.0.0.1 --port 5174
```

如需演示 LiveTalking + Wav2Lip 数字人表现层：

```powershell
cd D:\py\dota
& .\scripts\stop_avatar_demo.ps1
& .\scripts\start_avatar_demo.ps1 -OpenVisitor -ForceLowMemory -Voice zh-CN-XiaoxiaoNeural
```

演示入口：

- 游客端：http://127.0.0.1:5174/
- Kiosk：http://127.0.0.1:5174/kiosk
- 管理后台：http://127.0.0.1:5174/admin
- 数字人状态：http://127.0.0.1:8000/api/avatar/status
- LiveTalking WebRTC 页面：http://127.0.0.1:8011/webrtcapi.html

关键边界开场就要记住：拥挤度是 `mock_simulation`，运营事件是 `manual_admin` 或 `mock_simulation`，路线拓扑是导览图人工抽象，不是 GPS 导航；LiveTalking + Wav2Lip 只是数字人表现层，不接管业务大脑。

## 0:00-0:40 开场：定位和国一卖点

一句话：

灵境导游是面向灵山胜境与拈花湾的“手机游客端 + 景区 Kiosk + 管理后台 + 数字人表现层”一体化 AI 导览系统。它不只是聊天机器人，而是能问答、识景、讲解、规划路线、错峰分流、扫码带走路线，并把游客反馈沉淀为后台知识改进闭环。

展示页面：

- 快速打开 `/`、`/kiosk`、`/admin` 三个入口。
- 指出 mock 模式无 API Key 可运行，前端只调用灵境后端 API。

## 0:40-1:40 游客端数字人问答 / 讲解

打开游客端 `/`。

输入：

```text
灵山大佛适合怎么游览？
```

预期现象：

- 用户问题立即出现在问答区。
- 数字人状态从 thinking 到 speaking；LiveTalking 在线时可发声和口型，离线时保留前端 fallback。
- 回答区展示 RAG 回答和 sources。

继续输入：

```text
海底两万里
```

预期现象：

- Query Understanding Gate 识别资料外。
- sources 为空。
- 文案明确“不在本地景区知识库范围内，不编造”。

继续输入：

```text
介绍景区
```

预期现象：

- 触发澄清，给出“灵山胜境 / 拈花湾 / 两个都介绍”等选项。

讲解重点：

系统不是让 LLM 自由回答。所有文本先经过 Query Understanding Gate；事实类问题必须进入本地 RAG 并展示来源；范围外问题宁可兜底，也不编造景区知识。

## 1:40-2:40 识景 Top3 确认 + 景点讲解

切到游客端“识景”tab，上传样例：

```text
D:\py\dota\evals\vision_samples\lingshan_dafo_mock.jpg
```

预期现象：

- 展示 1-3 个候选景点。
- 每个候选有景点名、景区、置信度、判断依据和确认按钮。
- 低置信或候选接近时提示用户确认。

点击 Top1 “确认”后：

- 当前讲解景点切换到确认景点。
- 展示 suggested questions。
- 点击“一键讲解”后进入 RAG 问答，仍展示 sources。

讲解重点：

当前识景是 mock 规则候选，不接真实 VLM。它为后续真实 VLM 预留稳定 UX：VLM 只负责候选识别，事实讲解仍由 RAG sources 生成。

## 2:40-3:50 个性化路线 + 拥挤度分流 + 导览图拓扑

在游客端输入：

```text
带老人孩子，3小时，灵山大佛一定要去，别太挤
```

预期现象：

- 自然语言被识别为路线规划。
- Route Memory 保存老人孩子、3 小时、避拥挤、灵山大佛必去等约束。
- 生成路线，展示综合评分、评分拆解、必去标签、拥挤状态、等待时间和 decision_trace。
- 显示“导览图拓扑”模块：顺路指数、总步行估算、涉及游线、回头路次数、观光车建议。
- 时间线每站展示所属游线、下一站步行估算、交通方式、回头路风险和顺路原因。

必须说清：

- 拥挤度来自 `mock_simulation`，不代表真实客流，也没有接入闸机、摄像头、Wi-Fi 探针、GPS 或 IoT。
- 运营事件来自 `manual_admin` / `mock_simulation`，是后台演示配置。
- scenic_graph 是基于线路导览图、手绘观光车图和地图人工抽象的半真实游线拓扑，用于顺路解释、步行估算、回头路风险和观光车建议；它不是 GPS 导航，不是地图导航服务，也不代表实时定位。
- 路线规划由受约束 Route Planner 生成，LLM 不能自由决定路线点位；必去点不会因为拥挤被静默删除。

## 3:50-4:40 Kiosk 生成路线 + 手机扫码带走

打开 `/kiosk`。

操作：

- 点击生成推荐路线。
- 展示路线名称、评分、拥挤说明、二维码、短码和手机链接。

打开 Kiosk 上的 share_url，形如：

```text
http://127.0.0.1:5174/route/{route_id}/share?code={share_code}
```

预期现象：

- 手机分享页显示同一条路线。
- 展示同样的路线评分、站点、拥挤说明和分享校验结果。
- 分享页也展示拓扑摘要：顺路指数、总步行估算、涉及游线、观光车建议。
- 每站展示所属游线、到下一站的步行估算、交通方式和回头路风险。

兜底：

现场扫码不方便时，直接复制 Kiosk 的 share_url 到浏览器地址栏。share_code 是当前后端进程内 mock 短期有效机制，默认 30 分钟。

## 4:40-5:40 Admin 知识库 / 数字人 / 运营事件

打开 `/admin`。

知识库管理：

- 切到“知识库管理”。
- 点击“上传文档”创建本地演示资产。
- 点击“新增 FAQ / 保存草稿”。
- 点击“重建索引”或“发布到知识库”。

说明：

Round 1 的知识库管理是后台本地闭环，不直接写入现有 RAG `knowledge_chunks`，不修改原始资料包。FAQ 草稿需要管理员确认后才进入后续发布流程。

数字人管理：

- 切到“数字人管理”。
- 修改数字人 profile 并保存。
- 点击“试听音色”。
- 点击“生成预存讲解”创建 mock job。

说明：

数字人配置保存在本地 SQLite。LiveTalking + Wav2Lip 只接收灵境后端的可信短文本或白名单预存 clip，负责发声和口型表现，不接管 RAG、路线、识景、运营分析。可信文本入口强制使用 `/human type=echo`，禁止走 LiveTalking 的 chat/LLM 路径。

运营事件：

- 切到“运营事件”。
- 创建 crowd / closed / show / recommendation 事件。
- 再回游客端生成路线，看 `decision_trace` 是否出现 `manual_admin` 事件影响。

说明：

运营事件是人工配置或 mock 演示，不代表真实硬件或客流采集。

## 5:40-6:30 游客感受度报告 + 数据大屏 + 系统设置

游客感受度：

- 切到“游客感受度”。
- 点击“生成周报”。
- 展示满意度、正向反馈占比、待跟进问题、低置信问答、情绪波动指数、关注点、负向原因、路线体验标签和反馈明细。

说明：

报告来自本地演示交互日志、反馈样例和 mock 数据，不代表真实全园运营数据。PDF 导出当前是安全 stub。

数据大屏：

- 切到“数据大屏”。
- 展示服务人次、热门问答、路线偏好、满意度趋势和评测看板。

系统设置：

- 切到“系统设置”。
- 修改演示景区名称或数据边界提示，点击保存。
- 点击“运行健康检查”，展示 backend、database、avatar mock、sidecar status、knowledge local。

说明：

系统设置保存在本地 SQLite，healthcheck 不依赖 API Key。页面明确 mock 模式、前端只调后端、不接真实 GPS/客流/硬件/地图导航。

## 6:30-7:00 技术闭环和边界说明

收尾话术：

灵境导游的核心是三条闭环：

1. 可信导览：Query Gate 先判断边界，RAG 只基于本地 sources 回答，低置信进入知识缺口和评测。
2. 路线分流：Route Planner 不是 LLM 自由规划，而是全量 22 景点候选池 + 必去/可选/避开 + 拥挤度 + 运营事件 + 导览图拓扑。
3. 运营改进：游客问答、识景、路线、扫码带走和反馈沉淀到后台，管理员能补 FAQ、配置事件、看评测、生成感受度报告。

最后强调：

- mock 模式无 API Key 可运行。
- 前端只调用后端 API。
- scenic_graph 是导览图人工抽象拓扑，不是 GPS 导航。
- 拥挤度与运营事件是 mock/local 演示，不代表真实客流或硬件。
- LiveTalking + Wav2Lip 是数字人表现层，不是业务大脑。

## 常见异常与兜底

| 异常 | 处理 |
| --- | --- |
| 后端 8000 端口被占用 | 停掉旧 `uvicorn`，或换端口并同步 Vite proxy |
| 前端 5174 端口被占用 | 停掉旧 Vite，或使用 `--port 5175` |
| 识景没有候选 | 使用 `evals/vision_samples` 样例，或展示 `eval_vision.py` 报告 |
| 分享页 code 无效 | 重新在 Kiosk 生成路线；share_code 是当前进程内 30 分钟 mock 机制 |
| Admin 计数为空 | 先在游客端完成几次 QA、路线、反馈，或说明当前为本地演示日志 |
| 数字人表现层无法连接 | 运行 `scripts/stop_avatar_demo.ps1` 后重新 `scripts/start_avatar_demo.ps1 -OpenVisitor -ForceLowMemory -Voice zh-CN-XiaoxiaoNeural`；主流程仍可用前端 fallback 和 mock accepted |
| 数字人没声音 | 确认浏览器未静音、LiveTalking 页面已有 session；如仍异常，说明表现层 / WebRTC 受本机环境影响，QA、路线、识景和后台主流程不受影响 |

## 2026-05-22 数字人演示补充

当前主演示数字人路线是 LiveTalking + Wav2Lip，默认音色统一为 `zh-CN-XiaoxiaoNeural`。OpenAvatarChat + LiteAvatar 只作为 legacy fallback，不再是默认演示路线。

游客端和 Kiosk 的数字人播报分两段：

1. 先播放固定开场白 clip：`welcome_intro_5s`，文本为“您好，我是灵境导游小灵，正在为您准备讲解。”
2. 约 5 秒后继续原本的真实动作：动态问答/路线走 `POST /api/avatar/speak`，固定景点讲解走 `POST /api/avatar/play-clip`。

这个开场白只是降低体感等待，不代表最终业务回答已经生成。点击停止播报应同时中断当前播报并取消延迟中的后续动作。

演示前建议检查 clip 资产：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\avatar_clip_inventory.ps1
```

下一步若要统一音色，需要重新生成或补齐 `external/avatar-clips/` 下的 `welcome_intro_5s.wav`、`lingshan_buddha_intro_45s.wav`、`fan_gong_intro_45s.wav`、`jiulong_guanyu_intro_30s.wav`，并保持前端只传 `clip_id`、后端白名单解析路径。
