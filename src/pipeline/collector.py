import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries

from ..models.schemas import DataSourceType, StockPrice
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class DataCollector:
    """Collects financial data from various sources"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.rate_limiters = {
            source: RateLimiter(
                cfg['rate_limit'],
                cfg['timeout']
            )
            for source, cfg in config['data_sources'].items()
        }
        
    def collect_data(self, symbol: str, source: str, 
                    start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Collect data from specified source"""
        try:
            if source == DataSourceType.YAHOO_FINANCE:
                return self._collect_yahoo_finance(symbol, start_date, end_date)
            elif source == DataSourceType.ALPHA_VANTAGE:
                return self._collect_alpha_vantage(symbol, start_date, end_date)
            else:
                raise ValueError(f"Unsupported data source: {source}")
        except Exception as e:
            logger.error(f"Error collecting data for {symbol} from {source}: {e}")
            raise
            
    def _collect_yahoo_finance(self, symbol: str, 
                             start_date: datetime, 
                             end_date: datetime) -> pd.DataFrame:
        """Collect data from Yahoo Finance"""
        self.rate_limiters[DataSourceType.YAHOO_FINANCE].wait_if_needed()
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            df.reset_index(inplace=True)
            return self._standardize_columns(df)
        except Exception as e:
            logger.error(f"Error collecting Yahoo Finance data: {e}")
            raise
            
    def _collect_alpha_vantage(self, symbol: str, 
                              start_date: datetime, 
                              end_date: datetime) -> pd.DataFrame:
        """Collect data from Alpha Vantage"""
        self.rate_limiters[DataSourceType.ALPHA_VANTAGE].wait_if_needed()
        
        try:
            api_key = self.config['data_sources']['alpha_vantage']['api_key']
            ts = TimeSeries(key=api_key)
            data, _ = ts.get_daily(symbol=symbol, outputsize='full')
            df = pd.DataFrame.from_dict(data, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            return self._standardize_columns(df)
        except Exception as e:
            logger.error(f"Error collecting Alpha Vantage data: {e}")
            raise
            
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names across different sources"""
        column_mapping = {
            'Date': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adjusted_close'
        }
        return df.rename(columns=column_mapping)