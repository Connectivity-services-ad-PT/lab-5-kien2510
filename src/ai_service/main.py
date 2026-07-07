from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import uuid

app = FastAPI(
    title="A7 - Notification Service",
    description="Dịch vụ gửi thông báo và cảnh báo đa kênh - Smart Campus",
    version="1.0.0"
)

class NotificationRequest(BaseModel):
    user_id: str
    title: str
    message: str
    channel: str = "inapp"      # inapp, push, email, sms
    priority: str = "normal"    # low, normal, high
    source_service: str = "unknown"

class NotificationResponse(BaseModel):
    notification_id: str
    status: str
    channel: str
    sent_at: datetime

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "A7-Notification",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/notifications")
async def send_notification(request: NotificationRequest):
    notification_id = str(uuid.uuid4())
    
    print(f"[A7-NOTIFICATION] 📨 Nhận từ {request.source_service} → {request.user_id} | {request.title}")

    return NotificationResponse(
        notification_id=notification_id,
        status="sent",
        channel=request.channel,
        sent_at=datetime.now()
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8007)