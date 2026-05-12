# 灵境导游 7 分钟演示脚本

## 演示前准备

启动前先确认当前分支工作区干净，且没有真实 API Key 写入代码或文档。

```powershell
cd D:\py\dota
python .\scripts\init_db.py
python .\scripts\validate_api_data.py
python .\scripts\eval_qa.py
python .\scripts\eval_query_understanding.py
python .\scripts\eval_query_capability.py
python .\scripts\eval_vision.py
python .\scripts\eval_routes.py
python .\scripts\eval_crowd_routes.py
python .\scripts\eval_route_share.py
python .\scripts\eval_analytics.py
python .\scripts\eval_route_conversation.py
python .\scripts\eval_route_constraints.py
python .\scripts\eval_operation_events.py
python .\scripts\eval_knowledge_gaps.py
python .\scripts\eval_eval_reports.py
python -m compileall backend/app scripts
npm --prefix .\frontend run build
```

启动演示服务：

```powershell
cd D:\py\dota
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix .\frontend run dev -- --host 127.0.0.1 --port 5174
```

演示入口：

- 游客端：http://127.0.0.1:5174/
- Kiosk：http://127.0.0.1:5174/kiosk
- 管理后台：http://127.0.0.1:5174/admin

## 0:00-0:30 开场

一句话：

灵境导游不是普通聊天机器人，而是“手机游客端 + 景区 Kiosk + 管理后台”的景区 AI 数字人闭环：能问、能拍、能听、能规划路线、能避开拥挤，也能把低置信问题沉淀到后台持续改进。

## 0:30-1:40 可信问答与资料外拦截

打开游客端 `/`。

输入：

```text
灵山大佛适合怎么游览？
```

预期现象：

- 数字人进入 thinking，再进入 speaking。
- 问答区出现游客问题和灵境回答。
- 识别标签为本地 RAG 或景区问答。
- 下方出现“来源依据”，至少有 1 条 source。

讲解重点：

事实问题必须经过 Query Gate，再进入本地 RAG。回答不是模型自由编造，而是来自本地知识切片。

继续输入：

```text
海底两万里
```

预期现象：

- 识别为资料外。
- sources 为空。
- 文案明确“不在本地景区知识库范围内，不编造”。

兜底话术：

如果评委问为什么不回答，这正是可信边界：系统宁可承认资料外，也不把非景区内容硬套成景区讲解。

继续输入：

```text
介绍景区
```

预期现象：

- 识别为澄清。
- 出现灵山胜境、拈花湾、两个都介绍等选项。

## 1:40-2:40 自然语言推荐

输入：

```text
我对历史感兴趣，有什么景点推荐？
```

预期现象：

- 识别为兴趣推荐。
- 展示推荐景点列表、规则分、推荐理由和“一键问”按钮。

讲解重点：

这不是 RAG，也不是路线；系统把“历史兴趣”抽成结构化 slots，再基于 22 个景点的标签、类别和简介做规则评分。

输入：

```text
灵山和拈花湾哪个适合拍照？
```

预期现象：

- 识别为景点/景区对比。
- 展示对比建议、对比维度和理由。

输入：

```text
现在人多吗？
```

预期现象：

- 识别为拥挤运营状态。
- 展示 mock_simulation 拥挤点、等待时间和 manual_admin/mock_simulation 运营事件。
- 页面明确说明不代表真实硬件客流。

## 2:40-3:30 图片识景确认

在游客端点击“上传”，选择：

```text
D:\py\dota\evals\vision_samples\lingshan_dafo_mock.jpg
```

预期现象：

- 展示 Top3 候选或至少候选列表。
- 每个候选有景点名、景区、置信度、判断依据和确认按钮。
- 未确认前不直接进入事实讲解。

点击 Top1 的“确认”。

预期现象：

- 当前讲解景点更新为确认景点。
- 出现 suggested questions。
- 点击“一键讲解”后走 RAG 问答。

兜底：

如果样例上传被浏览器限制，可直接说明当前识景是 mock 规则闭环，并展示 `python .\scripts\eval_vision.py` 的通过结果。

## 3:30-4:40 自然语言路线规划

在游客端主输入框输入：

```text
带老人孩子，3小时，灵山大佛一定要去，别太挤
```

预期现象：

- 识别为路线规划。
- 生成路线并滚动到路线区域。
- 路线包含综合评分、score_breakdown、decision_trace。
- 灵山大佛显示“必去”标签。
- 每站显示 crowd_level、crowd_score、wait_minutes、crowd_note。
- 页面明确标注 mock_simulation 拥挤度不是实时客流。

讲解重点：

Route Memory Agent 只记偏好和约束，真正路线由受约束 Route Planner 评分生成。必去点遇到拥挤不会被静默删除，只会错峰、保留提醒或进入澄清。

## 4:40-5:30 Kiosk 到手机接力

打开 `/kiosk`。

点击生成推荐路线。

预期现象：

- Kiosk 大屏生成路线摘要。
- 显示二维码、短码、手机打开链接。
- 文案说明分享码 30 分钟后失效。

复制或打开页面中的 share_url，形如：

```text
http://127.0.0.1:5174/route/{route_id}/share?code={share_code}
```

预期现象：

- 手机分享页显示同一条路线。
- 显示站点时间线、评分、拥挤说明、逐站讲解问题。

兜底：

如果现场扫码不方便，直接点击 Kiosk 上的链接或复制 share_url 到浏览器地址栏。

## 5:30-6:25 Admin 运营闭环

打开 `/admin`。

预期能看到：

- 服务统计和 provider 状态。
- 拥挤点预警。
- 运营事件控制台。
- 知识缺口闭环。
- 评测看板。
- 最近事件和热门问题。

可选操作：

在运营事件控制台创建一条临时关闭或拥挤事件，再生成路线，查看路线 `decision_trace` 是否提到 manual_admin 事件。

讲解重点：

后台不是空壳大屏，而是把游客问答、识景、路线、反馈、知识缺口和评测结果汇成运营改进闭环。

## 6:25-7:00 评测可信证明

在 Admin 评测看板展示：

- QA 准确率。
- Query Understanding / Query Capability 通过率。
- Vision、Route、Crowd、Share、Analytics、Knowledge Gaps 等 report。
- 衍生指标：必去景点保留率、拥挤解释率、澄清通过率、知识缺口闭环通过率。

收尾话术：

灵境导游的核心不是“让 LLM 随便答”，而是 Query Gate 先理解边界，RAG 只用本地来源回答事实，Route Planner 用规则约束规划路线，后台用日志和评测持续改进。mock 模式无 API Key 可运行，后续接 LLM 也只能增强结构化理解和表达，不能绕过证据和约束。

## 常见异常与兜底

| 异常 | 处理 |
|------|------|
| 后端 8000 端口被占用 | 停掉旧 `uvicorn`，或换端口并同步 Vite proxy |
| 前端 5174 端口被占用 | 停掉旧 Vite，或使用 `--port 5175` |
| TTS 没声音 | 说明浏览器语音能力受系统语音包/自动播放策略影响，文本和状态机仍可演示 |
| 图片上传无候选 | 使用 `evals/vision_samples` 的 mock 样例，或展示 `eval_vision.py` 报告 |
| 分享页 code 无效 | 重新在 Kiosk 生成路线；share_code 是当前进程内 30 分钟 mock 机制 |
| Admin 计数为空 | 先在游客端完成几次 QA、路线、反馈，或说明当前为本地演示日志 |
