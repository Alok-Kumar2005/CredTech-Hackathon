import asyncio
from typing import Dict, List
from datetime import datetime, timedelta
from app.services.data_ingestion import data_ingestion
from app.models.credit_scorer import credit_scorer
from app.services.cache_service import cache
from loguru import logger

class ProcessingService:
    def __init__(self):
        self.processing = False
        self.last_update = None
    
    async def process_all_scores(self) -> Dict:
        if self.processing:
            logger.warning("already in progress")
            return await cache.get_json("latest_scores") or {}
        
        self.processing = True
        logger.info("Start score processing ")
        
        try:
            data = await data_ingestion.ingest_all_data()
            if not data:
                logger.error("data not available")
                return {}
            
            financial_data = data.get('financial', {})
            news_data = data.get('news', {})
            macroData = data.get('macro', {})
            
            ### process score for each ticker
            scores = {}
            tasks = []
            for ticker in financial_data.keys():
                finData = financial_data.get(ticker, {})
                newsDataTicker = news_data.get(ticker, {})
                
                if finData:  ## Only process if we have finDAta
                    task = self._calculate_score_async(ticker, finData, newsDataTicker, macroData)
                    tasks.append(task)
            
            # Execute all scoring tasks concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, dict) and 'ticker' in result:
                        scores[result['ticker']] = result
                    elif isinstance(result, Exception):
                        logger.error(f"Scoring error: {result}")
            
            processedData = {
                'scores': scores,
                'data_timestamp': data.get('timestamp'),
                'processing_timestamp': datetime.now().isoformat(),
                'ticker_count': len(scores)
            }
            await cache.set_json("latest_scores", processedData, 3600)
            await self._store_historical_scores(scores)
            self.last_update = datetime.now()
            logger.info(f"scoring completed for {len(scores)} tickers")
            return processedData

        except Exception as e:
            logger.error(f"Processing error: {e}")
            return {}
        finally:
            self.processing = False
    
    
    async def _calculate_score_async(self, ticker: str, financial_data: Dict,news_data: Dict, macro_data: Dict) -> Dict:
        """score calculation"""
        try:
            loop = asyncio.get_event_loop()
            score_result = await loop.run_in_executor(
                None, 
                credit_scorer.calculate_score,
                ticker, financial_data, news_data, macro_data
            )
            return score_result
        except Exception as e:
            logger.error(f"scorring error for ticker {ticker}: {e}")
            return {}
    

    async def _store_historical_scores(self, scores: Dict):
        try:
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d_%H-%M")
            for ticker, score_data in scores.items():
                hist_key = f"history:{ticker}"
                
                ### using existing history
                history = await cache.get_json(hist_key) or []
                ### addition of new score
                history.append({
                    'timestamp': now.isoformat(),
                    'score': score_data.get('score', 0),
                    'risk_level': score_data.get('risk_level', 'Unknown')
                })
                
                # Keep only last 100 entries
                if len(history) > 100:
                    history = history[-100:]
                await cache.set_json(hist_key, history, 86400)
        except Exception as e:
            logger.error(f"Historical storage error: {e}")
    

    async def get_ticker_history(self, ticker: str) -> List[Dict]:
        """Get historical scores for a ticker"""
        try:
            hist_key = f"history:{ticker}"
            history = await cache.get_json(hist_key) or []
            return history[-50:]  # Return last 50 points
        except Exception as e:
            logger.error(f"History retrieval error for {ticker}: {e}")
            return []
    
    async def get_latest_scores(self) -> Dict:
        """Get latest processed scores"""
        try:
            scores = await cache.get_json("latest_scores")
            if scores:
                return scores
            
            # If no cached scores, trigger processing
            logger.info("No cached scores found, triggering processing")
            return await self.process_all_scores()
            
        except Exception as e:
            logger.error(f"Get latest scores error: {e}")
            return {}
    
    async def get_system_status(self) -> Dict:
        """Get system processing status"""
        try:
            return {
                'processing': self.processing,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'cache_status': 'connected' if await cache.get_json("latest_scores") else 'empty',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return {'processing': False, 'last_update': None, 'cache_status': 'error'}

processing_service = ProcessingService()