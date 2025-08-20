from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List
from datetime import datetime
from app.services.processing import processing_service
from app.services.data_ingestion import data_ingestion
from app.api.schemas import *
from loguru import logger

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Credit Intelligence Platform API", "version": "1.0.0"}

@router.get("/scores", response_model=ProcessedData)
async def get_scores():
    """Get latest credit scores for all tickers"""
    try:
        scores = await processing_service.get_latest_scores()
        if not scores:
            raise HTTPException(status_code=404, detail="No scores available")
        return scores
    except Exception as e:
        logger.error(f"Get scores API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scores/{ticker}")
async def get_ticker_score(ticker: str):
    """Get credit score for specific ticker"""
    try:
        scores = await processing_service.get_latest_scores()
        ticker_scores = scores.get('scores', {})
        
        if ticker.upper() not in ticker_scores:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        
        return ticker_scores[ticker.upper()]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get ticker score API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{ticker}")
async def get_ticker_history(ticker: str):
    """Get historical scores for a ticker"""
    try:
        history = await processing_service.get_ticker_history(ticker.upper())
        return {
            "ticker": ticker.upper(),
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Get history API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
async def refresh_scores(background_tasks: BackgroundTasks):
    """Trigger score refresh"""
    try:
        # Run processing in background
        background_tasks.add_task(processing_service.process_all_scores)
        
        return {
            "success": True,
            "message": "Score refresh triggered",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Refresh API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get system processing status"""
    try:
        status = await processing_service.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Status API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tickers")
async def get_available_tickers():
    """Get list of available tickers"""
    try:
        scores = await processing_service.get_latest_scores()
        ticker_scores = scores.get('scores', {})
        
        tickers = []
        for ticker, data in ticker_scores.items():
            tickers.append({
                "ticker": ticker,
                "score": data.get('score', 0),
                "risk_level": data.get('risk_level', 'Unknown'),
                "last_updated": data.get('timestamp')
            })
        
        # Sort by score descending
        tickers.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            "tickers": tickers,
            "count": len(tickers),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get tickers API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_analytics():
    """Get analytics and summary statistics"""
    try:
        scores = await processing_service.get_latest_scores()
        ticker_scores = scores.get('scores', {})
        
        if not ticker_scores:
            return {"message": "No data available"}
        
        # Calculate analytics
        all_scores = [data.get('score', 0) for data in ticker_scores.values()]
        risk_levels = [data.get('risk_level', 'Unknown') for data in ticker_scores.values()]
        
        risk_distribution = {}
        for level in risk_levels:
            risk_distribution[level] = risk_distribution.get(level, 0) + 1
        
        analytics = {
            "total_issuers": len(all_scores),
            "average_score": sum(all_scores) / len(all_scores) if all_scores else 0,
            "highest_score": max(all_scores) if all_scores else 0,
            "lowest_score": min(all_scores) if all_scores else 0,
            "risk_distribution": risk_distribution,
            "last_updated": scores.get('processing_timestamp'),
            "timestamp": datetime.now().isoformat()
        }
        
        return analytics
    except Exception as e:
        logger.error(f"Analytics API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))