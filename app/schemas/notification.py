from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field, model_validator


class ChannelType(str, Enum):
    PUSH = "PUSH"
    SMS = "SMS"
    EMAIL = "EMAIL"


class NotificationRequest(BaseModel):
    """
    Validates inbound alert dispatches from 'Service N' (Stock Sentinel Engine).
    Fails early if required fields are missing or improperly formatted.
    """
    user_id: int = Field(..., description="Unique Snowflake ID of the target user", example=84392019482)
    channel_type: ChannelType = Field(..., description="Target delivery network channel")
    
    # Text payload configurations
    title: str = Field(..., min_length=1, max_length=255, description="Notification header title")
    body: str = Field(..., min_length=1, description="Raw core notification text payload")
    
    # Metadata payloads (Optional fields depending on the target delivery type chosen)
    email_recipient: Optional[EmailStr] = Field(None, description="Required only if channel_type is EMAIL")
    phone_number: Optional[str] = Field(None, description="Required only if channel_type is SMS, must match E.164 format")
    
    # Flexible container payload for target device identifiers or template custom attributes
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom properties or tracking links")

    @model_validator(mode="after")
    def validate_channel_requirements(self) -> "NotificationRequest":
        """
        Cross-field business validation rule matching your HLD channel rules.
        Guarantees contact route details exist for chosen notification systems.
        """
        if self.channel_type == ChannelType.EMAIL and not self.email_recipient:
            raise ValueError("An 'email_recipient' address is strictly required when channel_type is set to EMAIL.")
            
        if self.channel_type == ChannelType.SMS and not self.phone_number:
            raise ValueError("A 'phone_number' string attribute is strictly required when channel_type is set to SMS.")
            
        return self


class NotificationResponse(BaseModel):
    """
    Unified response template sent back to calling microservices instantly.
    """
    success: bool = True
    message: str = "Notification successfully queued for transmission."
    notification_id: Optional[int] = None
    status: str = "PENDING"