import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "notify")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

app = FastAPI(
    title="A7 - Notification Service",
    version=SERVICE_VERSION,
    description="Notification Service for Smart Campus",
)


class NotificationChannel(str, Enum):
    inapp = "inapp"
    push = "push"
    email = "email"
    sms = "sms"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class NotificationCreate(BaseModel):
    user_id: str = Field(..., examples=["user-001"])
    title: str = Field(..., examples=["Cảnh báo nhiệt độ"])
    message: str = Field(..., examples=["Nhiệt độ vượt ngưỡng 70°C"])
    channel: Optional[NotificationChannel] = Field(default=None, examples=["inapp"])


class NotificationCreated(BaseModel):
    notification_id: str
    status: str


NOTIFICATIONS: List[Dict] = []


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title="HTTP Error",
            detail=str(exc.detail),
            instance=str(request.url.path),
        )
    problem.setdefault("status", exc.status_code)
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))
    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(i) for i in first_error.get("loc", []))
    message = first_error.get("msg", "Validation error")
    detail = f"{location}: {message}" if location else message
    return JSONResponse(
        status_code=422,
        content=build_problem(
            status_code=422,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail=build_problem(
                status_code=401,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(
            status_code=401,
            detail=build_problem(
                status_code=401,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, version=SERVICE_VERSION)


@app.post(
    "/api/notifications",
    response_model=NotificationCreated,
    status_code=201,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
    },
)
def send_notification(payload: NotificationCreate, request: Request) -> NotificationCreated:
    notification_id = f"N-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8]}"
    item = {
        "notification_id": notification_id,
        "user_id": payload.user_id,
        "title": payload.title,
        "message": payload.message,
        "channel": payload.channel.value if payload.channel else "inapp",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    NOTIFICATIONS.append(item)
    return NotificationCreated(notification_id=notification_id, status="sent")