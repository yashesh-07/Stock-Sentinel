import random
import time
from celery import Celery
from sqlalchemy.orm import Session

from app.config import settings
from app.database import models
from app.database.session import SessionLocal

from app.services.metrics import NOTIFICATION_TASKS_TOTAL, NOTIFICATION_RETRY_TOTAL, ACTIVE_WORKER_TASKS

# 1. Initialize Celery Application Instance connected to Redis
celery_app = Celery(
    "notification_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Optional configuration settings for enterprise task control
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,          # Task acknowledged only AFTER successful execution
    worker_prefetch_multiplier=1, # One task per worker thread at a time to optimize throughput
)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5  # Base delay of 5 seconds before trying a failed task again
)
def send_background_notification(self, log_id: int):
    """
    Independent distributed worker process execution block.
    Picks up queued items, connects to network providers, and updates state history.
    """
    print(f"[WORKER] Activating transaction context lookup for Log Record: {log_id}")

    # Increment our concurrent execution gauge
    ACTIVE_WORKER_TASKS.inc()
    
    # Create an isolated database connection session for this independent thread loop
    db: Session = SessionLocal()
    
    try:
        # Fetch the notification details recorded by the API layer
        log_record = db.query(models.NotificationLog).filter(models.NotificationLog.notification_id == log_id).first()
        
        if not log_record:
            print(f"[WORKER][ERROR] Log record ID {log_id} was not found inside database registry.")
            return False
            
        # Update internal record state to 'PROCESSING'
        log_record.status = "PROCESSING"
        db.commit()

        # 2. Simulate Network Infrastructure Provider Handoff 
        # (This is where you execute real external requests via Twilio, SendGrid, etc.)
        channel = log_record.channel_type
        print(f"[WORKER] Route verified. Dispatching payload over provider tunnel: {channel}")
        
        # Simulating external network latency drops / successes
        time.sleep(0.4) # Simulates a 400ms connection round-trip 
        
        # Simulation: Inject a random network failure (15% chance) to showcase our Retry Loop
        if random.random() < 0.15:
            raise ConnectionError("Gateway timeout received from remote network infrastructure endpoint.")

        # 3. Successful Execution Path Update
        log_record.status = "SENT"
        log_record.sent_at = models.datetime.now(models.timezone.utc)
        db.commit()

        # 🚀 Record Successful Telemetry
        NOTIFICATION_TASKS_TOTAL.labels(channel=channel, status="SENT").inc()

        print(f"[WORKER][SUCCESS] Packet transmitted successfully for Log ID: {log_id}")
        return True

    except Exception as exc:
        # 4. Error Catching & Automatic Retry Loop Execution
        db.rollback() # Reset active session transactions safely
        NOTIFICATION_RETRY_TOTAL.labels(channel=log_record.channel_type).inc()
        
        # Re-fetch the target log record using a clean context session frame
        log_record = db.query(models.NotificationLog).filter(models.NotificationLog.notification_id == log_id).first()
        
        if log_record:
            log_record.retry_count += 1
            log_record.error_message = str(exc)
            
            if self.request.retries >= self.max_retries:
                # Max retry count exhausted completely - Mark as permanently unrecoverable
                log_record.status = "FAILED"
                # 🚀 Record Failed Telemetry
                NOTIFICATION_TASKS_TOTAL.labels(channel=log_record.channel_type, status="FAILED").inc()
                print(f"[WORKER][FATAL] Task execution failed completely after max retries for Log ID: {log_id}")
            else:
                log_record.status = "RETRY_PENDING"
                
            db.commit()

        # Command Celery to re-queue this specific task back into Redis with exponential backing delays
        # Exponential calculation: 5 seconds * (2 ** current_retry_count)
        retry_delay = self.default_retry_delay * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)
        
    finally:
        # Decrement active gauge since processing ended
        ACTIVE_WORKER_TASKS.dec()
        db.close() # Securely return database link resources back into the allocation pool