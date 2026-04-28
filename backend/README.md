# Backend

FastAPI mock-first backend for `灵境导游`.

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

APIs:

- `GET /api/health`
- `GET /api/provider/status`
