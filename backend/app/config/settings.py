
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = os.getenv("REDIS_URL")
    alpha_vantage_key: str = os.getenv("ALPHA_VANTAGE_KEY")
    news_api_key: str = os.getenv("NEWS_API_KEY")
    update_interval: int = 300  ### for 5 minute
    max_issuers: int = 50
    
    ### model settings
    score_scale: tuple = (0, 1000)
    risk_threshold: float = 0.6
    
    class Config:
        env_file = ".env"

settings = Settings()