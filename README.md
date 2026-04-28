# 灵境导游

中国软件杯 A5「景区导览服务 AI 数字人」项目。当前版本已完成游客端 QA、mock 识景和 mock 路线推荐闭环；默认无 API Key 可运行。

## 本轮实现

- 游客手机端 `/`：数字人主区域、景点选择、RAG 问答、拍照识景、路线推荐、逐站讲解入口。
- 景区终端 `/kiosk`：横屏触控欢迎态、大数字人、大按钮、热门问题、路线摘要、二维码占位。
- 管理后台 `/admin`：左侧导航、顶部状态栏、指标卡、mock 图表、热门问题、provider 状态。
- 后端 API：health、provider、景点、知识切片、QA、识景、路线推荐。
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

Task 06 提供亲子、历史、自然、祈福、拍照 5 类路线模板，不需要真实 GPS 或真实模型：

```powershell
python .\scripts\eval_routes.py
```

路线 API：

- `GET /api/routes/themes`
- `POST /api/routes/recommend`
- `GET /api/routes/{id}/share`

请求示例：

```json
{
  "theme": "family",
  "time_budget_minutes": 240,
  "group_type": "family",
  "intensity": "easy",
  "interests": ["亲子轻松", "佛教文化"],
  "start_attraction_id": "lingshan-ls-011"
}
```

返回会包含路线名称、主题、预计时长、逐站点位、停留时间、讲解重点、适合原因和 30 分钟有效的 mock 分享码。

## 后续任务

Task 07 将在当前 mock QA、识景和路线基础上继续补数字人语音/TTS 状态机或终端路线二维码带走；原始资料包仍作为只读来源。
