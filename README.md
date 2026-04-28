# 灵境导游

中国软件杯 A5「景区导览服务 AI 数字人」项目骨架。当前版本完成 Task 01 + Task 01.5：React/Vite/TypeScript 前端三端展示壳、FastAPI 最小后端、mock provider 状态、设计 token 与基础组件。

## 本轮实现

- 游客手机端 `/`：数字人主区域、mock 讲解、文本输入、语音/文本/拍照/路线主入口、景点推荐卡。
- 景区终端 `/kiosk`：横屏触控欢迎态、大数字人、大按钮、热门问题、路线摘要、二维码占位。
- 管理后台 `/admin`：左侧导航、顶部状态栏、指标卡、mock 图表、热门问题、provider 状态。
- 后端 API：`GET /api/health`、`GET /api/provider/status`。
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

## 后续任务

Task 04.5 将在当前 mock provider 基础上实现多模态识景最小闭环；原始资料包仍作为只读来源。
