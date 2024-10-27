import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from fredapi import Fred
from influxdb_client import InfluxDBClient, Point, WritePrecision
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API calls"""
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.timestamps = []

    def can_proceed(self) -> bool:
        current_time = time.time()
        # Remove timestamps older than the period
        self.timestamps = [ts for ts in self.timestamps 
                         if current_time - ts < self.period]
        
        if len(self.timestamps) < self.calls:
            self.timestamps.append(current_time)
            return True
        return False

    def wait_if_needed(self):
        while not self.can_proceed():
            time.sleep(1)

class DataSourceConfig:
    """Configuration for data sources"""
    def __init__(self):
        self.config = {
            'yahoo_finance': {
                'rate_limit_calls': 2000,
                'rate_limit_period': 3600,
            },
            'alpha_vantage': {
                'api_key': os.getenv('ALPHA_VANTAGE_API_KEY'),
                'rate_limit_calls': 500,
                'rate_limit_period': 86400,
            },
            'fred': {
                'api_key': os.getenv('FRED_API_KEY'),
                'rate_limit_calls': 1000,
                'rate_limit_period': 86400,
            }
        }

class DataCollector:
    """Collects data from various financial data sources"""
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.rate_limiters = {
            source: RateLimiter(
                cfg['rate_limit_calls'],
                cfg['rate_limit_period']
            )
            for source, cfg in config.config.items()
        }

    def collect_yahoo_finance(self, symbol: str, start_date: str, 
                            end_date: str) -> pd.DataFrame:
        """Collect data from Yahoo Finance"""
        self.rate_limiters['yahoo_finance'].wait_if_needed()
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            df.reset_index(inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error collecting Yahoo Finance data: {e}")
            raise

    def collect_alpha_vantage(self, symbol: str) -> pd.DataFrame:
        """Collect data from Alpha Vantage"""
        self.rate_limiters['alpha_vantage'].wait_if_needed()
        try:
            ts = TimeSeries(key=self.config.config['alpha_vantage']['api_key'])
            data, _ = ts.get_daily(symbol=symbol, outputsize='full')
            df = pd.DataFrame.from_dict(data, orient='index')
            df.index = pd.to_datetime(df.index)
            df.reset_index(inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error collecting Alpha Vantage data: {e}")
            raise

class DataProcessor:
    """Processes financial time series data"""
    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data quality"""
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns 
                         if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        return df

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset"""
        # Forward fill price data
        price_columns = ['Open', 'High', 'Low', 'Close']
        df[price_columns] = df[price_columns].ffill()
        
        # Fill volume with 0
        df['Volume'] = df['Volume'].fillna(0)
        return df

    def normalize_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize timezone to UTC"""
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize('UTC')
        return df

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        # Simple Moving Average
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
        # Relative Strength Index
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df

    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main data processing pipeline"""
        df = self.validate_data(df)
        df = self.handle_missing_values(df)
        df = self.normalize_timezone(df)
        df = self.calculate_technical_indicators(df)
        return df

class DataStorage:
    """Handles data storage in InfluxDB"""
    def __init__(self):
        self.client = InfluxDBClient(
            url=os.getenv('INFLUXDB_URL'),
            token=os.getenv('INFLUXDB_TOKEN'),
            org=os.getenv('INFLUXDB_ORG')
        )
        self.bucket = os.getenv('INFLUXDB_BUCKET')

    def store_data(self, df: pd.DataFrame, symbol: str):
        """Store data in InfluxDB"""
        write_api = self.client.write_api()
        
        # Convert DataFrame to InfluxDB points
        points = []
        for _, row in df.iterrows():
            point = Point("stock_prices")\
                .tag("symbol", symbol)\
                .field("open", float(row['Open']))\
                .field("high", float(row['High']))\
                .field("low", float(row['Low']))\
                .field("close", float(row['Close']))\
                .field("volume", float(row['Volume']))\
                .time(row['Date'], WritePrecision.NS)
            points.append(point)
        
        try:
            write_api.write(bucket=self.bucket, record=points)
        except Exception as e:
            logger.error(f"Error storing data in InfluxDB: {e}")
            raise

class PipelineMonitor:
    """Monitors pipeline health and data quality"""
    def __init__(self):
        self.alerts = []

    def check_data_quality(self, df: pd.DataFrame) -> List[str]:
        """Check data quality metrics"""
        issues = []
        
        # Check for missing values
        missing_pct = df.isnull().mean() * 100
        if missing_pct.max() > 5:
            issues.append(f"High missing values: {missing_pct.max()}%")
        
        # Check for duplicate dates
        if df['Date'].duplicated().any():
            issues.append("Duplicate dates found")
        
        # Check for price anomalies
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            zscore = abs((df[col] - df[col].mean()) / df[col].std())
            if (zscore > 3).any():
                issues.append(f"Price anomalies detected in {col}")
        
        return issues

    def log_pipeline_metrics(self, start_time: float, 
                           end_time: float, symbol: str):
        """Log pipeline performance metrics"""
        duration = end_time - start_time
        logger.info(f"Pipeline completed for {symbol} in {duration:.2f} seconds")

class FinancialTimeSeriesPipeline:
    """Main pipeline class orchestrating the entire process"""
    def __init__(self):
        self.config = DataSourceConfig()
        self.collector = DataCollector(self.config)
        self.processor = DataProcessor()
        self.storage = DataStorage()
        self.monitor = PipelineMonitor()

    def run(self, symbol: str, start_date: str, end_date: str, 
            source: str = 'yahoo_finance'):
        """Run the pipeline for a given symbol"""
        start_time = time.time()
        logger.info(f"Starting pipeline for {symbol}")

        try:
            # Collect data
            if source == 'yahoo_finance':
                df = self.collector.collect_yahoo_finance(
                    symbol, start_date, end_date
                )
            elif source == 'alpha_vantage':
                df = self.collector.collect_alpha_vantage(symbol)
            else:
                raise ValueError(f"Unsupported data source: {source}")

            # Process data
            df = self.processor.process_data(df)

            # Check data quality
            issues = self.monitor.check_data_quality(df)
            if issues:
                for issue in issues:
                    logger.warning(f"Data quality issue for {symbol}: {issue}")

            # Store data
            self.storage.store_data(df, symbol)

            # Log metrics
            end_time = time.time()
            self.monitor.log_pipeline_metrics(start_time, end_time, symbol)

        except Exception as e:
            logger.error(f"Pipeline failed for {symbol}: {e}")
            raise

def main():
    """Main function to run the pipeline"""
    # Configuration
    symbols = ['AAPL', 'GOOGL', 'MSFT']  # Example symbols
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    # Initialize pipeline
    pipeline = FinancialTimeSeriesPipeline()

    # Run pipeline for each symbol
    for symbol in symbols:
        try:
            pipeline.run(symbol, start_date, end_date)
            logger.info(f"Successfully processed {symbol}")
        except Exception as e:
            logger.error(f"Failed to process {symbol}: {e}")

if __name__ == "__main__":
    main()