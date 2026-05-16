from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Base class for all models
class Base(DeclarativeBase):
    pass

class UserSetting(Base):
    """
    Maps to the 'DB (device setting user info)' box in Figure 10-14.
    Handles user channel settings, opt-out toggles, and device tokens.
    """
    __tablename__ = "user_settings"

    # BigInteger for high scalability. Perfect fit for Snowflake IDs.
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Device Tokens for Push Notifications (FCM / APNs)
    ios_device_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    android_device_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Opt-out Requirements: Globally control user preferences
    is_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationship linkage to notification logs
    logs: Mapped[list["NotificationLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class NotificationLog(Base):
    """
    Maps to the 'Notification log' box in Figure 10-14.
    Essential for tracing delivery status, retry history, and click metrics.
    """
    __tablename__ = "notification_logs"

    # Snowflake ID or autoincrement ID for tracking each sent attempt
    notification_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_settings.user_id"), nullable=False)
    
    # Channel Category
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False) # 'PUSH', 'SMS', 'EMAIL'
    
    # Content Auditing
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Reliability & Delivery Lifecycle Tracking
    status: Mapped[str] = mapped_column(String(20), default="PENDING") # 'PENDING', 'SENT', 'FAILED', 'CLICKED'
    retry_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Back-reference relation
    user: Mapped["UserSetting"] = relationship(back_populates="logs")