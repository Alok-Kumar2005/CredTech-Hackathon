import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple
from datetime import datetime
from app.config.settings import settings
from app.services.cache_service import cache
from loguru import logger

class CreditScorer:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
        self.scaler = StandardScaler()    ## to standadize the data
        self.feature_names = [         ## featured of our data
            'market_cap_log', 'debt_to_equity', 'current_ratio', 'roe',
            'price_change_30d', 'volatility', 'volume_avg_log',
            'sentiment_score', 'news_count', 'vix', 'treasury_10y'
        ]
        self.is_trained = False
        self._train_initial_model()
    
    def _train_initial_model(self):
        """Train initial model with synthetic data"""
        try:
            ### generating synthetic data for training
            n_samples = 1000
            np.random.seed(42)
            market_cap_log = np.random.normal(10, 2, n_samples)
            debt_to_equity = np.random.exponential(1, n_samples)
            current_ratio = np.random.normal(2, 0.5, n_samples)
            roe = np.random.normal(0.15, 0.1, n_samples)
            price_change_30d = np.random.normal(0, 10, n_samples)
            volatility = np.random.exponential(5, n_samples)
            volume_avg_log = np.random.normal(12, 1, n_samples)
            sentiment_score = np.random.beta(2, 2, n_samples)
            news_count = np.random.poisson(3, n_samples)
            vix = np.random.normal(20, 5, n_samples)
            treasury_10y = np.random.normal(4, 1, n_samples)
            ### stack them in column form
            X = np.column_stack([
                market_cap_log, debt_to_equity, current_ratio, roe,
                price_change_30d, volatility, volume_avg_log,
                sentiment_score, news_count, vix, treasury_10y
            ])
            
            ### now generating target column
            y = (
                market_cap_log*50 +current_ratio*100 + roe*1000 + sentiment_score* 200 +
                -debt_to_equity *50 +
                -volatility*20 +
                -vix*10 + treasury_10y*30 + np.random.normal(0, 50, n_samples)
            )
            
            ### clipped data in between 0 to 1000
            y = np.clip((y - y.min()) / (y.max() - y.min()) * 1000, 0, 1000)
            
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True
            
            logger.info("model train with synthetic data") 
        except Exception as e:
            logger.error(f"Error in model training: {e}")
    
    def _extract_features(self, financial_data: Dict, news_data: Dict, macro_data: Dict) -> np.ndarray:
        """Collecting raw features from raw data"""
        try:
            market_cap = financial_data.get('market_cap', 1e9)
            market_cap_log = np.log(max(market_cap, 1e6))
            
            debt_to_equity = min(financial_data.get('debt_to_equity', 1), 10)
            current_ratio = max(financial_data.get('current_ratio', 1), 0.1)
            roe = financial_data.get('roe', 0.1)
            price_change_30d = financial_data.get('price_change_30d', 0)
            volatility = financial_data.get('volatility', 1)
            
            volume_avg = financial_data.get('volume_avg', 1e6)
            volume_avg_log = np.log(max(volume_avg, 1000))
            
            sentiment_score = news_data.get('sentiment_score', 0.5)
            news_count = news_data.get('news_count', 0)
            
            vix = macro_data.get('vix', 20)
            treasury_10y = macro_data.get('treasury_10y', 4)
            
            features = np.array([
                market_cap_log, debt_to_equity, current_ratio, roe,
                price_change_30d, volatility, volume_avg_log,
                sentiment_score, news_count, vix, treasury_10y
            ]).reshape(1, -1)
            return features
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return np.zeros((1, len(self.feature_names)))
    
    def calculate_score(self, ticker: str, financial_data: Dict, news_data: Dict, macro_data: Dict) -> Dict:
        """calc credit score with proper explaination"""
        try:
            if not self.is_trained:
                logger.warning("model not trained, using fallback score")
                return self._fallback_score(financial_data, news_data)
            
            ### features
            features = self._extract_features(financial_data, news_data, macro_data)
            features_scaled = self.scaler.transform(features)
            ### overall score
            score = self.model.predict(features_scaled)[0]
            score = max(0, min(1000, score)) ## clamp for valid range
            
            #### features importance
            feature_importance = self.model.feature_importances_
            
            ### calculateing features contribution
            contributions = {}
            for i, feature_name in enumerate(self.feature_names):
                contribution = features_scaled[0][i] * feature_importance[i] * 100
                contributions[feature_name] = round(contribution, 2)
            
            ### risk level
            if score >= 750:
                risk_level = "Low Risk"
                color = "green"
            elif score >= 500:
                risk_level = "Medium Risk"
                color = "yellow"
            else:
                risk_level = "High Risk"
                color = "red"
            
            explanation = self._generate_explanation(
                ticker, score, contributions, financial_data, news_data
            )
            
            result = {
                'ticker': ticker,
                'score': round(score, 1),
                'risk_level': risk_level,
                'color': color,
                'contributions': contributions,
                'explanation': explanation,
                'timestamp': datetime.now().isoformat()
            }
            return result
        except Exception as e:
            logger.error(f"score calculation {ticker}: {e}")
            return self._fallback_score(financial_data, news_data, ticker)
    
    def _fallback_score(self, financial_data: Dict, news_data: Dict, ticker: str = "UNKNOWN") -> Dict:
        """fallback score when model fails"""
        try:
            base_score = 500   ## simple rule based score
            
            # Adjust based on financial metrics
            debt_to_equity = financial_data.get('debt_to_equity', 1)
            if debt_to_equity < 0.5:
                base_score += 100
            elif debt_to_equity > 2:
                base_score -= 150
            
            roe = financial_data.get('roe', 0)
            if roe > 0.15:
                base_score += 100
            elif roe < 0:
                base_score -= 200
            
            sentiment = news_data.get('sentiment_score', 0.5)
            if sentiment > 0.6:
                base_score += 50
            elif sentiment < 0.4:
                base_score -= 50
            
            score = max(0, min(1000, base_score))
            
            if score >= 750:
                risk_level = "Low Risk"
                color = "green"
            elif score >= 500:
                risk_level = "Medium Risk"
                color = "yellow"
            else:
                risk_level = "High Risk"
                color = "red"
            
            return {
                'ticker': ticker,
                'score': score,
                'risk_level': risk_level,
                'color': color,
                'contributions': {'fallback': 1.0},
                'explanation': f"Fallback scoring used. Score: {score}/1000",
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fallback scoring error: {e}")
            return {
                'ticker': ticker,
                'score': 500,
                'risk_level': 'Medium Risk',
                'color': 'yellow',
                'contributions': {},
                'explanation': 'Error in scoring',
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_explanation(self, ticker: str, score: float, contributions: Dict, 
                            financial_data: Dict, news_data: Dict) -> str:
        """Generate human-readable explanation"""
        try:
            # Find top positive and negative contributors
            sorted_contributions = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
            top_factors = sorted_contributions[:3]
            
            explanation = f"{ticker} credit score: {score:.0f}/1000. "
            
            if score >= 750:
                explanation += "Strong creditworthiness. "
            elif score >= 500:
                explanation += "Moderate credit risk. "
            else:
                explanation += "Higher credit risk concerns. "
            
            # Add key factors
            key_factors = []
            for factor, contribution in top_factors:
                if abs(contribution) > 10:  # Only significant factors
                    impact = "positive" if contribution > 0 else "negative"
                    factor_readable = factor.replace('_', ' ').title()
                    key_factors.append(f"{factor_readable} ({impact})")
            
            if key_factors:
                explanation += f"Key factors: {', '.join(key_factors[:2])}. "
            
            # Add news sentiment if available
            if news_data.get('headlines'):
                sentiment = news_data.get('sentiment_score', 0.5)
                if sentiment > 0.6:
                    explanation += "Recent news sentiment is positive. "
                elif sentiment < 0.4:
                    explanation += "Recent news sentiment shows concerns. "
            
            return explanation
            
        except Exception as e:
            logger.error(f"Explanation generation error: {e}")
            return f"{ticker} credit score: {score:.0f}/1000"

credit_scorer = CreditScorer()