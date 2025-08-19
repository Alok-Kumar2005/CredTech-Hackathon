# import sys
# import os
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import yfinance as yf
import requests
import pandas as pd
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from textblob import TextBlob
from bs4 import BeautifulSoup
from app.config.settings import settings
from app.services.cache_service import cache
from loguru import logger

class DataIngestion:
    def __init__(self):
        self.tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "JPM", "BAC", "WMT", "JNJ", "PFE", "XOM"]
        
    async def get_financial_data(self, ticker: str) -> Dict:
        """get financial data from yahoo finance"""
        c_key = f"financial:{ticker}"
        cached = await cache.get_json(c_key)
        if cached:
            return cached
            
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="30d")
            
            data = {
                'ticker': ticker,
                'market_cap': info.get('marketCap', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'roe': info.get('returnOnEquity', 0),
                'price_change_30d': ((hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0]) * 100,
                'volatility': hist['Close'].std(),
                'volume_avg': hist['Volume'].mean(),
                'last_updated': datetime.now().isoformat()
            }
            
            await cache.set_json(c_key, data, 1800)  ## 30 min cache
            return data
            
        except Exception as e:
            logger.error(f"Financial data error for {ticker}: {e}")
            return {}
    

    async def get_news_sentiment(self, ticker: str) -> Dict:
        """news sentiment analysis"""
        c_key = f"news:{ticker}"
        cached = await cache.get_json(c_key)
        if cached:
            return cached
            
        try:   ## using free news api or webs scraping for news
            url =f"https://finance.yahoo.com/quote/{ticker}/news"
            headers ={'User-Agent': 'Mozilla/5.0'}
            rspnse =requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(rspnse.content, 'html.parser')
            
            head_lines = []
            for item in soup.find_all('h3')[:5]:  ## getting top 5 headline
                if item.text:
                    head_lines.append(item.text.strip())
            
            if not head_lines:
                return {'sentiment_score': 0.5, 'news_count': 0}
            
            sentiments = [TextBlob(headline).sentiment.polarity for headline in head_lines]
            avg_sentiment = sum(sentiments) / len(sentiments)
            
            data = {
                'sentiment_score': (avg_sentiment + 1) / 2,  ## normalze in between 0 and 1
                'news_count': len(head_lines),
                'headlines': head_lines[:3],
                'last_updated': datetime.now().isoformat()
            }
            
            await cache.set_json(c_key, data, 3600)  ### 1 hour chching
            return data
            
        except Exception as e:
            logger.error(f"news sentiment error for ticker {ticker}: {e}")
            return {'sentiment_score': 0.5, 'news_count': 0}
    

    
    async def get_macro_data(self) -> Dict:
        """Getting macro economic indicators"""
        c_key = "macro_data"
        cached = await cache.get_json(c_key)
        if cached:
            return cached
            
        try:   ## simulate real data
            data = {
                'vix': 20.5 + (datetime.now().hour - 12) * 0.5, 
                'treasury_10y': 4.2 + (datetime.now().minute / 60 * 0.2),
                'unemployment': 3.8,
                'inflation': 3.2,
                'gdp_growth': 2.1,
                'last_updated': datetime.now().isoformat()
            }
            
            await cache.set_json(c_key, data, 7200)  ### 2 hour cache
            return data
            
        except Exception as e:
            logger.error(f"macro data error: {e}")
            return {}
    
    async def ingest_all_data(self) -> Dict:
        """Ingesting data for all tickers"""
        logger.info("Starting data ingestio")
        tasks = []
        for ticker in self.tickers:
            tasks.extend([
                self.get_financial_data(ticker),
                self.get_news_sentiment(ticker)
            ])
        tasks.append(self.get_macro_data())
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            ## process results
            financial_data = {}
            news_data = {}
            macro_data = {}
            
            for i, ticker in enumerate(self.tickers):
                fin_idx = i * 2
                news_idx = i * 2 + 1
                
                if fin_idx < len(results) and not isinstance(results[fin_idx], Exception):
                    financial_data[ticker] = results[fin_idx]
                    
                if news_idx < len(results) and not isinstance(results[news_idx], Exception):
                    news_data[ticker] = results[news_idx]
            
            # Last result is macro data
            if results and not isinstance(results[-1], Exception):
                macro_data = results[-1]
            
            ingested_data = {
                'financial': financial_data,
                'news': news_data,
                'macro': macro_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache the complete dataset
            await cache.set_json("latest_data", ingested_data, 600)
            logger.info(f"Data ingestion completed for {len(financial_data)} tickers")
            
            return ingested_data
            
        except Exception as e:
            logger.error(f"Data ingestion error: {e}")
            return {}

data_ingestion = DataIngestion()