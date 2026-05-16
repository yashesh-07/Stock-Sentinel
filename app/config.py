import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # 1. App Configuration
    APP_NAME: str = "StockSentinel-NotificationService"
    DEBUG: bool = False
    
    # 2. Database & Redis (Required for Figure 10-14)
    # We use Field(..., env=...) to map .env keys to variables
    DATABASE_URL: str
    REDIS_URL: str
    
    # 3. Notification Provider Keys (Placeholders for now)
    # These will be used by the Workers later
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    SENDGRID_API_KEY: str | None = None
    
    # 4. Security
    API_SECRET_KEY: str
    
    # 5. Rate Limiting Constants
    # Industrial practice: Define limits here to change them without redeploying code
    MAX_NOTIFICATIONS_PER_SECOND: int = 500
    
    # Tells Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Global instance to be imported by other files
settings = Settings()