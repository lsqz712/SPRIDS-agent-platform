from fastapi import HTTPException
from app.entity.schemas import ApiResponse


def success_response(data=None, message: str = "success", code: int = 200):
    return ApiResponse(code=code, message=message, data=data).model_dump()


def error_response(message: str, code: int = 400):
    raise HTTPException(status_code=code, detail=message)


def api_response(data=None, message: str = "success", code: int = 200):
    return {"code": code, "message": message, "data": data}
