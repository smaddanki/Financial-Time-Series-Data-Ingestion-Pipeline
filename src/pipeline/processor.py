import logging
from typing import Dict, List

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes financial time series data"""
    
    def __init__(self, config: Dict):
        self.config = config
        
    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main data processing pipeline"""
        try:
            df = self.validate_data(df)
            df = self.handle_missing_values(df)
            df = self.calculate_technical_indicators(df)
            df = self.normalize_data(df)
            return df
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            raise
            
    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data quality"""
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        # Validate data types
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
        
        # Validate price relationships
        invalid_prices = df[df['low'] > df['high']].index
        if len(invalid_prices) > 0:
            logger.warning(f"Found invalid price relationships at: {invalid_prices}")
            
        return df
        
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset"""
        # Forward fill price data
        price_columns = ['open', 'high', 'low', 'close']
        df[price_columns] = df[price_columns].ffill()
        
        # Fill volume with 0
        df['volume'] = df['volume'].fillna(0)
        
        return df
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        # Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Relative Strength Index
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        return df
        
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize data for consistency"""
        # Convert timestamp to UTC
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('UTC')
        
        # Round numeric values
        # price_columns = ['open', 'high', 'low', 'close', 'adjusted_close']
        # df[price_columns] = df[price_columns].round(2)
        
        # Ensure volume is integer
        # df['volume'] = df['volume'].astype(int)
        
        return df