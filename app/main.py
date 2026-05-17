import time
from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.database import models
from app.schemas.notification import NotificationRequest, NotificationResponse, ChannelType
from app.services.rate_limiter import is_rate_limited
from app.services.utils import sanitize_notification_body, safely_truncate_text
from app.workers.tasks import send_background_notification

from app.services.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

# 🚀 Prometheus Scraping Endpoint
@app.get("/metrics")
async def metrics():
    """
    Exposes application metrics to the Prometheus scraper cluster.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# 🚀 Middleware to automatically log latency and request counts
@app.middleware("http")
async def monitor_requests_middleware(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path
    method = request.method
    
    response = await call_next(request)
    
    # Calculate execution time delta
    duration = time.time() - start_time
    status_code = str(response.status_code)
    
    # Record metrics data points
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, http_status=status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response

# Mock database tracking token for local simulation testing
# In full deployment, this would be a Redis ZSET lookup query.
USER_TRAFFIC_LOGS: dict[int, list[float]] = {}

def authenticate_client(api_key: str = Header(None, alias="X-Sentinel-API-Key")):
    """
    Secures the entry point to protect against unauthorized requests.
    """
    if not api_key or api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security handshake failed: Invalid or missing API credential key."
        )
    return api_key


@app.post(
    "/api/v1/notifications/dispatch",
    response_model=NotificationResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def dispatch_notification(
    payload: NotificationRequest,
    api_key: str = Depends(authenticate_client),
    db: Session = Depends(get_db)
):
    # 1. User Preference Verification & Resilient Auto-Initialization
    user_prefs = db.query(models.UserSetting).filter(models.UserSetting.user_id == payload.user_id).first()
    
    if not user_prefs:
        print(f"[API] Encountered new User ID {payload.user_id}. Auto-initializing a default opt-in profile.")
        try:
            user_prefs = models.UserSetting(
                user_id=payload.user_id,
                is_email_enabled=True,
                is_sms_enabled=True,
                is_push_enabled=True
            )
            db.add(user_prefs)
            db.commit()
            db.refresh(user_prefs)
        except Exception as db_exc:
            db.rollback()  
            print(f"[API][CONCURRENCY NOTICE] Race-condition detected for user {payload.user_id}. Fetching existing record...")
            user_prefs = db.query(models.UserSetting).filter(models.UserSetting.user_id == payload.user_id).first()
            if not user_prefs:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database isolation failure: Could not verify or establish target user state preferences."
                )

    # 2. Verification Step: Validate against Opt-Out criteria
    if payload.channel_type == ChannelType.EMAIL and not user_prefs.is_email_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transmission rejected: User opted out of EMAIL alerts.")
    if payload.channel_type == ChannelType.SMS and not user_prefs.is_sms_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transmission rejected: User opted out of SMS alerts.")
    if payload.channel_type == ChannelType.PUSH and not user_prefs.is_push_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transmission rejected: User opted out of PUSH alerts.")

    # 3. Safety Intercept: Execute sliding-window rate limiter
    current_timestamp = time.time()
    user_history = USER_TRAFFIC_LOGS.get(payload.user_id, [])
    
    if is_rate_limited(user_history, current_timestamp):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate allocation exhausted: Sub-minute message density threshold exceeded."
        )
        
    user_history.append(current_timestamp)
    USER_TRAFFIC_LOGS[payload.user_id] = user_history

    # 4. Data Transformation & Sanitization Layer
    clean_body = sanitize_notification_body(payload.title, payload.body)
    if payload.channel_type == ChannelType.SMS:
        clean_body = safely_truncate_text(clean_body, max_chars=160)

    # 5. Persistence Log Entry creation
    db_log = models.NotificationLog(
        user_id=payload.user_id,
        channel_type=payload.channel_type.value,
        title=payload.title,
        body=clean_body,
        status="PENDING",
        retry_count=0
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    # 6. Queue Dispatch Hand-off (The Message Queue step)
    send_background_notification.delay(db_log.notification_id)
    print(f"[QUEUE DISPATCH] Handed off Log ID {db_log.notification_id} to Redis for asynchronous worker lane processing.")

    return NotificationResponse(
        success=True,
        notification_id=db_log.notification_id,
        status="PENDING"
    )