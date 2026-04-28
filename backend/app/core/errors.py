from fastapi import status

from app.core.config import ErrorResponse


class ApiError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        cause: str,
        fix: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        self.status_code = status_code
        self.payload = ErrorResponse(code=code, message=message, cause=cause, fix=fix)
        super().__init__(cause)
