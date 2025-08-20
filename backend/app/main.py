from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import uvicorn
import schedule
import time
import threading
from loguru import logger
from app.api.routes import router
from app.services.processing import processing_service
from app.config.settings import settings

### scheduler for updates
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  ### check after every one minute

async def periodic_update():
    logger.info("running periodic score update")
    try:
        await processing_service.process_all_scores()
    except Exception as e:
        logger.error(f"Periodic update error: {e}")

def schedule_periodic_updates():
    """Schedule periodic updates"""
    # Update every 5 minutes
    schedule.every(5).minutes.do(lambda: asyncio.create_task(periodic_update()))
    
    # Start scheduler thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Credit Intelligence Platform...")
    
    # Initial data processing
    try:
        await processing_service.process_all_scores()
        logger.info("Initial score processing completed")
    except Exception as e:
        logger.error(f"Initial processing failed: {e}")
    
    # Start periodic updates
    schedule_periodic_updates()
    logger.info("Periodic updates scheduled")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Credit Intelligence Platform...")

# Create FastAPI app
app = FastAPI(
    title="Credit Intelligence Platform",
    description="Real-Time Explainable Credit Scoring System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Credit Scoring"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": time.time()
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app",host="0.0.0.0",port=8000,reload=True,log_level="info")