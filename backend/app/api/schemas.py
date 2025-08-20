from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class CreditScore(BaseModel):
    ticker: str
    score: float
    risk_level: str
    color: str
    contributions: Dict[str, float]
    explanation: str
    timestamp: str

class HistoricalPoint(BaseModel):
    timestamp: str
    score: float
    risk_level: str

class ProcessedData(BaseModel):
    scores: Dict[str, CreditScore]
    data_timestamp: Optional[str]
    processing_timestamp: str
    ticker_count: int

class SystemStatus(BaseModel):
    processing: bool
    last_update: Optional[str]
    cache_status: str
    timestamp: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: str

class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None