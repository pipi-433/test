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

当前执行区正在做 Task 07.8 系列：把数字人主演示路线切换到 LiveTalking + Wav2Lip，并围绕首包延迟做欢迎开场白、预存 wav 和统一音色策略。本轮不提交、不 push。

开始/执行过程中观察到工作区存在未提交项：

- 本轮数字人主线切换相关改动：avatar backend adapter、LiveTalking 启动脚本、游客端/Kiosk 数字人组件文案、`docs/DEMO_SCRIPT.md`、`docs/TECHNICAL_STORY.md`、`docs/NEXT_CONTEXT_HANDOFF.md`、`docs/LIVETALKING_SIDECAR_RESEARCH.md`。
- 07.8E 后续体验修复：欢迎开场白 `welcome_intro_5s`、约 5 秒延迟后接真实播报、停止时取消后续 delayed action、游灵山提问时先播 welcome 缓冲。
- 07.8E 之后的 QA 小修：游客端问题输入默认值已清空；提交时直接读取当前 form input 值，避免 stale state 导致一直发送旧的“灵山大佛适合怎么游览？”。
- 旁路已有未提交项：Vision/eval 相关文件、部分前端页面文件也处于 dirty 状态。继续开发前需要先确认来源，不要盲目覆盖或混入同一提交。

如果继续开发，请先运行：

```powershell
cd D:\py\dota
git status --short
git diff --stat
```

不要盲目 `git add .`，不要把 LiveTalking 主线切换、Vision/eval 旁路改动和 legacy sidecar 研究文件混成一个提交。

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
- 当前主演示路线已切换为 LiveTalking + Wav2Lip，使用本地 ignored 资产 `external/LiveTalking/data/avatars/lingshan_guide_avatar1`。
- 当前演示音色选定为 EdgeTTS `zh-CN-XiaoxiaoNeural`，启动脚本支持 `-Voice zh-CN-XiaoxiaoNeural`。
- 当前交互缓冲采用白名单 clip `welcome_intro_5s`，文案为“您好，我是灵境导游小灵，正在为您准备讲解。”。游客端/Kiosk 播报前先播放该 clip，约 5 秒后再接真实回答、路线摘要或景点讲解。
- 固定景点讲解应优先走预存 wav：`lingshan_buddha_intro_45s`、`fan_gong_intro_45s`、`jiulong_guanyu_intro_30s`。动态问答和路线摘要继续走即时 `/api/avatar/speak`。
- 前端只调用灵境后端 API，如 `/api/avatar/speak`、`/api/avatar/play-clip`、`/api/avatar/webrtc/offer`。
- LiveTalking 只播报灵境后端给出的可信短文本或白名单预存片段，不生成事实、不规划路线、不接管 RAG/识景/路线/运营分析。
- OpenAvatarChat + LiteAvatar 保留为历史预研 / legacy fallback，不再是默认演示主线。

## 关键边界

- `示范景区公开资料包/` 只读，不修改。
- `external/**` 不作为主仓业务代码修改区，不提交第三方源码、模型、日志、音频缓存。
- mock 模式必须无 API Key 可运行。
- 前端只能调用本项目后端 API，不能直连模型厂商或 sidecar。
- 拥挤度和运营事件是 `mock_simulation` / `manual_admin` 演示数据，不代表真实客流、真实硬件、闸机、摄像头或 Wi-Fi 探针。
- scenic_graph 是基于导览图人工抽象的半真实游线拓扑，用于顺路解释、步行估算、回头路风险和观光车建议；不是 GPS 导航、不是地图导航服务、不是实时定位。
- Route Planner 是受约束规则评分器，LLM 后续只能增强结构化意图解析和表达润色，不能自由决定路线点位。
- LiveTalking + Wav2Lip 是当前数字人表现层主线，不是业务大脑。
- LiveTalking `/human` 只能使用 `type="echo"` 播报后端可信文本，禁止使用 `type="chat"` 作为灵境业务入口。

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

数字人 LiveTalking 主演示：

```powershell
cd D:\py\dota
& .\scripts\start_avatar_demo.ps1 -OpenVisitor -ForceLowMemory -Voice zh-CN-XiaoxiaoNeural
```

OpenAvatarChat legacy fallback 如需单独回归：

```powershell
cd D:\py\dota
& .\scripts\start_avatar_demo.ps1 -Engine openavatarchat -OpenWebUI
```

停止数字人演示进程：

```powershell
cd D:\py\dota
& .\scripts\stop_avatar_demo.ps1
```

常用入口：

- 游客端：http://127.0.0.1:5174/
- Kiosk：http://127.0.0.1:5174/kiosk
- Admin：http://127.0.0.1:5174/admin
- LiveTalking WebRTC 页面：http://127.0.0.1:8011/webrtcapi.html
- 后端数字人状态：http://127.0.0.1:8000/api/avatar/status

数字人 clip 检查：

```powershell
cd D:\py\dota
powershell -ExecutionPolicy Bypass -File .\scripts\avatar_clip_inventory.ps1
```

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

1. **Task 07.8F：统一预存 wav 音色**。用 `zh-CN-XiaoxiaoNeural` 重新生成/补齐 `welcome_intro_5s.wav`、`lingshan_buddha_intro_45s.wav`、`fan_gong_intro_45s.wav`、`jiulong_guanyu_intro_30s.wav`，都放在 ignored `external/avatar-clips/`，不进 git。
2. **Task QA-Avatar-Live**：只开一个 WebRTC 页面，完整验收游客端和 Kiosk 的 welcome -> 真实播报、stop、刷新重连、固定讲解延迟和音色一致性。
3. **Task QA-UI**：完整走游客端 `/`、Kiosk、Admin、分享页 7 分钟演示流程，记录演示风险、按钮可用性、移动端溢出、console error。
4. 单独确认既有未提交数字人 sidecar 后端改动来源，决定是否分批提交；不要把 Vision/eval 旁路改动混入数字人提交。
5. 如答辩需要，可制作 PPT 或答辩讲稿，基于 `docs/DEMO_SCRIPT.md`、`docs/TECHNICAL_STORY.md`、`docs/SOFTBEI_REQUIREMENT_MATRIX.md`。

## Task 07.8 LiveTalking mainline handoff

LiveTalking + Wav2Lip is now the main digital-human demo route. It remains a presentation sidecar only and does not replace RAG, Route Planner, Vision, Analytics, or factual QA. OpenAvatarChat + LiteAvatar remains available only as legacy fallback / historical research.

Start command:

```powershell
cd D:\py\dota
.\scripts\start_avatar_demo.ps1 -OpenVisitor
```

Backend mapping:

- `POST /api/avatar/speak` -> LiveTalking `POST /human` with `type="echo"` only. `type="chat"` is forbidden for Lingjing trusted content.
- `POST /api/avatar/play-clip` -> LiveTalking `POST /humanaudio`, after backend whitelist resolution of `clip_id`.
- `POST /api/avatar/webrtc/offer` -> LiveTalking `POST /offer`, proxied by Lingjing backend so frontend does not call the sidecar business API directly.
- `POST /api/avatar/stop` -> LiveTalking `POST /interrupt_talk`, scoped to the current session id when available.
- `POST /api/avatar/warmup` -> short LiveTalking `POST /human type="echo"` warmup, usually `text="您好。"` and `interrupt=false`; failure falls back and never blocks the page.

Keep `external/LiveTalking`, model weights, avatar assets, venvs, caches, and logs ignored.

Current local demo constraint: LiveTalking is started with `--max_session 1` on this 6 GB 3060 Laptop setup. For the safest demo, keep only one active visitor/Kiosk WebRTC view at a time; refresh/reconnect if the session is taken by another page.

Task 07.8B latency note: visitor and Kiosk pages now warm up once after a WebRTC `sessionid` is received, then give immediate "正在生成语音" feedback before `/api/avatar/speak` returns. Its short-text Kiosk approach was superseded by 07.8C because LiveTalking EdgeTTS still generates full audio before playback.

Task 07.8C low-latency note: fixed scenic explanations are back on preset wav playback through `/api/avatar/play-clip`. Kiosk's three scenic buttons and visitor vision-confirmed "数字人讲解" should use whitelist `clip_id` -> `external/avatar-clips/*.wav` -> LiveTalking `/humanaudio`. Dynamic QA and route summaries still use `/api/avatar/speak` and may wait for full EdgeTTS generation. Required local ignored wav files:

```text
external/avatar-clips/welcome_intro_5s.wav
external/avatar-clips/lingshan_buddha_intro_45s.wav
external/avatar-clips/fan_gong_intro_45s.wav
external/avatar-clips/jiulong_guanyu_intro_30s.wav
```

Use `scripts/avatar_clip_inventory.ps1` to check presence before demo. Missing files must fallback cleanly, not 500.

Task 07.8E welcome buffer note: visitor and Kiosk playback actions now first trigger whitelist clip `welcome_intro_5s`, then wait about 5 seconds before sending the original speak/play-clip request. The clip text is `您好，我是灵境导游小灵，正在为您准备讲解。`, generated for the demo with target voice `zh-CN-XiaoxiaoNeural`. The local wav is about 4.6 seconds, so this leaves a small buffer while keeping the follow-up responsive. This is an interaction buffer to reduce perceived waiting; it does not mean the model answer, route summary, or scenic explanation has already finished. The stop control clears the delayed follow-up so a stopped welcome clip does not continue into the original broadcast.

Follow-up fix: mobile "游灵山" question submit now starts `welcome_intro_5s` immediately while the backend is understanding/retrieving/planning. When the answer returns, the page reuses the in-flight welcome buffer instead of starting a duplicate intro. If the clip is unavailable, it falls back to the same short line through `/api/avatar/speak` and waits longer before the real answer.
