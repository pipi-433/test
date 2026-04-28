from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import ErrorResponse, get_settings
from app.core.errors import ApiError

settings = get_settings()

app = FastAPI(
    title="Lingjing Guide API",
    description="Mock-first backend for the Scenic-area AI Digital Human Guide.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def api_error_handler(_request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.payload.model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP request failed."
    payload = ErrorResponse(
        code="HTTP_ERROR",
        message="请求未能完成。",
        cause=detail,
        fix="检查请求路径、参数和数据库初始化状态。",
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request, exc: Exception) -> JSONResponse:
    payload = ErrorResponse(
        code="INTERNAL_ERROR",
        message="服务暂时不可用，请稍后重试。",
        cause=str(exc),
        fix="查看后端日志，确认数据库、mock provider 和配置文件是否正常。",
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


app.include_router(router)
