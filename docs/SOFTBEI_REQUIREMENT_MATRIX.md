# 中国软件杯 A5 赛题需求对照表

## 使用说明

本文用于答辩时把赛题要求逐项映射到当前系统能力。所有条目均按“当前实现、演示方式、数据/模型边界、未实现或后续扩展”描述，避免把 mock/local 演示能力夸大为生产接入能力。

## 游客交互侧

| 赛题需求 | 当前实现页面 / API / 模块 | 演示方式 | 数据 / 模型边界 | 未实现或后续扩展 |
| --- | --- | --- | --- | --- |
| 多模态交互：文本 | 游客端 `/` 主输入框；`POST /api/qa`、`POST /api/guide/query`、`POST /api/query/understand` | 输入“灵山大佛适合怎么游览？”展示回答和 sources；输入“海底两万里”展示资料外兜底 | 文本先过 Query Understanding Gate；事实问答必须走本地 RAG sources；不让前端直连模型厂商 | 后续可接 LLM Query Understanding Agent，但只能输出结构化意图 |
| 多模态交互：语音 / 数字人播报 | 游客端“游灵山”tab、Kiosk 数字人区域；`POST /api/avatar/speak`、`POST /api/avatar/play-clip`、`POST /api/avatar/webrtc/offer` | 启动数字人直播后，点击路线播报或预存景点讲解，数字人表现层发声和口型 | OpenAvatarChat + LiteAvatar 只是 sidecar/表现层；可信文本由灵境后端生成；sidecar 不接管 RAG、路线、识景、运营分析 | 可继续优化音色、模型形象和长讲解 clip 管理 |
| 多模态交互：图片识景 | 游客端“识景”tab；`POST /api/vision/recognize` | 上传 `evals/vision_samples` 样例，显示 Top3 候选、置信度和确认按钮 | 当前是 mock 规则候选，基于文件名、hint、text_hint、标签和景点名匹配；不接真实 VLM；确认后再进入 RAG 讲解 | 后续可替换为真实 VLM provider，但 VLM 只负责候选识别 |
| 智能问答与讲解 | Query Understanding Gate、本地 lexical RAG、数字人表现层；`backend/app/services/qa_service.py` | 问景点事实问题，展示 answer、sources、数字人状态；资料外问题 sources 为空 | 资料来自只读解析后的 `data/processed/knowledge_chunks.json` 和 SQLite；无 sources 不编造 | 后续可接 embedding / rerank / LLM 风格润色，但不能绕过 sources |
| 个性化推荐：兴趣推荐 | Natural Language Capability Matrix；`recommendation_service.py`；游客端推荐卡片 | 输入“我对历史感兴趣，有什么景点推荐？”展示 3-5 个景点和理由 | 基于 22 个景点的 tags、category、summary 规则评分，不是 LLM 自由推荐 | 可补充更多游客画像维度和真实行为偏好模型 |
| 个性化推荐：路线规划 | `POST /api/routes/recommend`、`POST /api/routes/conversation`；Route Planner、Route Memory、route constraints | 输入“带老人孩子，3小时，灵山大佛一定要去，别太挤”生成可解释路线 | 路线是受约束规则评分器；经典模板只是 seed；全量 22 景点都可参与必去 / 可选 / 避开 | 后续可接更精细的体力、演艺时间和交通约束 |
| Kiosk 到手机接力 | `/kiosk`、`/route/:id/share?code=...`；`GET /api/routes/{id}/share` | Kiosk 生成路线，展示二维码 / 短码 / share_url，手机打开同一条路线 | 分享码为当前后端进程内 mock 短期有效机制，默认 30 分钟；不接真实账号系统 | 可接短信、微信小程序码或真实设备扫码部署 |

## 管理后台侧

| 赛题需求 | 当前实现页面 / API / 模块 | 演示方式 | 数据 / 模型边界 | 未实现或后续扩展 |
| --- | --- | --- | --- | --- |
| 管理后台基础 | `/admin` 多 tab 控制台 | 展示首页概览、知识库、数字人、运营事件、游客感受度、数据大屏、系统设置 | 后台数据来自 SQLite 本地演示日志、公开样例和 mock 数据 | 可继续拆分权限、账号和审计流 |
| 知识库管理 | `/admin/knowledge`；`GET/POST/PATCH /api/admin/knowledge/assets`、`/faqs`、`/reindex`、`/publish` | 点击上传文档创建本地资产；保存 FAQ 草稿；重建索引；发布到后台管理视图 | Round 1 是后台本地管理闭环，不直接写入现有 RAG `knowledge_chunks`，不修改原始资料包 | 后续可接真实文件上传解析、审核流和索引重建 |
| 知识缺口闭环 | `/admin/knowledge`；`/api/admin/knowledge/gaps` 系列 API | 低置信 / 无来源 / 信息不准反馈进入缺口；生成 FAQ 草稿；加入评测集 | FAQ 草稿为规则/mock 生成，需管理员确认；不会编造资料包外事实 | 后续可接人工审核发布和 RAG 索引重建 |
| 数字人形象管理 | `/admin/avatar`；`GET/PATCH /api/admin/avatar/profile`、`POST /voice-test`、`POST /clips/generate` | 修改名称、服装、声音等配置并保存；试听音色；生成预存讲解 mock job | 配置保存在本地 SQLite；voice-test 走后端 `/api/avatar/speak`；sidecar 不在线时 mock accepted | 后续可接真实音色库、clip 生成流水线和形象资产管理 |
| 游客感受度报告 | `/admin/sentiment`；`GET /api/admin/sentiment/report`、`POST /generate` | 点击“生成周报”展示满意度、正向率、待跟进问题、负向原因、服务建议、反馈明细 | 基于本地演示交互日志 / 反馈样例 / mock 数据，不代表真实全园运营数据 | PDF 导出目前是安全 stub；后续可生成正式报告文件 |
| 数据大屏概览 | `/admin/dashboard`、`GET /api/analytics/overview`、`GET /api/admin/evals/overview` | 展示服务人次、热门问答、满意度、路线偏好、评测看板 | 本地 logs + eval reports；公开行为数据只能作为行业样例，不声称为景区真实运营数据 | 可接真实 BI 数据源、分时趋势和权限控制 |
| 运营事件控制台 | `/admin/operations`；`/api/admin/operations/events` | 创建 crowd / closed / show / recommendation 事件，路线 decision_trace 读取并解释 | 事件来源为 `manual_admin` / `mock_simulation`，不代表真实硬件或客流采集 | 后续可接人工审核、事件模板和外部告警系统 |
| 系统设置闭环 | `/admin/settings`；`GET/PATCH /api/admin/system/settings`、`POST /healthcheck` | 保存景区名称、provider 模式、avatar 模式、mock 拥挤度、路线拓扑、数据边界说明；运行健康检查 | 设置保存在本地 SQLite；healthcheck 不依赖 API Key | 后续可接权限、配置版本和变更审计 |

## 非功能需求

| 赛题需求 | 当前实现页面 / API / 模块 | 演示方式 | 数据 / 模型边界 | 未实现或后续扩展 |
| --- | --- | --- | --- | --- |
| 多模态大模型支撑 | Provider 抽象、mock VLM、OpenAvatarChat + LiteAvatar sidecar 预研 | 展示 provider status、识景候选、数字人 sidecar readiness | 默认 mock，无 API Key 可运行；sidecar 只做表现层；前端不直连模型厂商 | 后续接真实 VLM / LLM / TTS 时仍走后端 provider |
| 本地知识库 | `data/processed/*.json`、SQLite、`knowledge_chunks`、RAG services | 运行 `init_db.py`，问答展示 sources | 资料包只读解析；不修改 `示范景区公开资料包/` | 后续支持真实上传资料审核入库 |
| 事实准确率 | `evals/reports/*_latest.json`、`/admin` 评测看板 | 展示 QA、Query、Vision、Route、Constraints、Knowledge Gaps 等 report | 评测为本地样例集和 mock/local 报告，不代表生产 SLA | 扩展题库、人工标注和线上回归 |
| 自然度 | 2D 数字人、trusted text speak、preset clip、状态机 | 数字人观看播放器展示发声 / 口型 / fallback | 当前是演示级 sidecar + fallback，不是生产级 3D 数字人 | 后续优化音色、表情、长文本切片和动作 |
| 响应延迟 | API `latency_ms`、eval reports、mock provider | 演示本地 mock 响应和评测平均延迟 | 本地机器表现不等于线上 SLA；真实模型接入后需重新压测 | 后续做缓存、异步队列和模型延迟监控 |
| 稳定性 | mock provider、统一错误结构、fallback、eval scripts | 断开 sidecar 或无 API Key 仍可完成主流程 | 外部 sidecar 不稳定时自动降级；不影响 QA、路线、识景和后台 | 后续接进程守护、日志采集、端到端监控 |
| GPS / 定位可选场景 | scenic_graph 拓扑、路线分享、起点上下文 | 展示顺路指数、总步行估算、所属游线和回头路风险 | scenic_graph 是基于导览图、观光车图和地图人工抽象的半真实游线拓扑，不是 GPS 导航，不是地图导航服务，不代表实时定位 | 后续如接定位，应作为可选 provider，且保持导览边界提示 |
| 安全与隐私 | 后端 provider、短期 share_code、Kiosk 匿名会话、settings 边界 | Admin 系统设置展示边界；Kiosk 分享码 30 分钟有效 | 不记录手机号、身份证、账号身份；不保存原图内容 | 后续可接权限、脱敏、审计和合规说明 |

## 总结

当前版本已覆盖赛题要求的游客交互端、管理后台、多模态交互、智能问答、个性路线、知识库、数字人配置、游客感受度报告与数据大屏概览。演示版核心能力均可在 mock/local 模式下无 API Key 运行。仍需在答辩中明确：拥挤度、运营事件、行为画像和路线拓扑均为本地演示或人工抽象能力，不代表真实硬件、真实客流或真实地图导航。
