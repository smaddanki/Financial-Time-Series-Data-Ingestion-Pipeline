# src/models/schemas.py

from datetime import datetime
from typing import Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, ConfigDict

class DataSourceType(str, Enum):
    """Enumeration of supported data sources"""
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    FRED = "fred"
    CUSTOM = "custom"

class TimeFrame(str, Enum):
    """Enumeration of supported timeframes"""
    MINUTE = "1min"
    FIVE_MINUTES = "5min"
    FIFTEEN_MINUTES = "15min"
    THIRTY_MINUTES = "30min"
    HOUR = "1hour"
    DAILY = "1day"
    WEEKLY = "1week"
    MONTHLY = "1month"

class StockPrice(BaseModel):
    """Model for stock price data"""
    model_config = ConfigDict(
        title="Stock Price Data",
        validate_assignment=True,
        extra="forbid"
    )

    timestamp: datetime = Field(..., description="Timestamp of the price data")
    open: float = Field(..., ge=0, description="Opening price")
    high: float = Field(..., ge=0, description="Highest price")
    low: float = Field(..., ge=0, description="Lowest price")
    close: float = Field(..., ge=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    adjusted_close: Optional[float] = Field(None, ge=0, description="Adjusted closing price")

    @validator('high')
    def high_must_be_greater_than_low(cls, v, values):
        """Validate that high price is greater than low price"""
        if 'low' in values and v < values['low']:
            raise ValueError('High price must be greater than low price')
        return v

    @validator('close')
    def close_must_be_in_range(cls, v, values):
        """Validate that closing price is within high-low range"""
        if all(key in values for key in ['high', 'low']):
            if not values['low'] <= v <= values['high']:
                raise ValueError('Closing price must be within high-low range')
        return v

class TechnicalIndicators(BaseModel):
    """Model for technical indicators"""
    model_config = ConfigDict(
        title="Technical Indicators",
        validate_assignment=True
    )

    sma_20: Optional[float] = Field(None, description="20-day Simple Moving Average")
    sma_50: Optional[float] = Field(None, description="50-day Simple Moving Average")
    sma_200: Optional[float] = Field(None, description="200-day Simple Moving Average")
    rsi_14: Optional[float] = Field(None, ge=0, le=100, description="14-day Relative Strength Index")
    macd: Optional[float] = Field(None, description="Moving Average Convergence Divergence")
    macd_signal: Optional[float] = Field(None, description="MACD Signal Line")
    macd_histogram: Optional[float] = Field(None, description="MACD Histogram")
    bollinger_upper: Optional[float] = Field(None, description="Bollinger Band Upper")
    bollinger_middle: Optional[float] = Field(None, description="Bollinger Band Middle")
    bollinger_lower: Optional[float] = Field(None, description="Bollinger Band Lower")

class StockData(BaseModel):
    """Model for combined stock data with technical indicators"""
    model_config = ConfigDict(
        title="Stock Data with Technical Indicators",
        validate_assignment=True
    )

    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    price_data: StockPrice
    technical_indicators: Optional[TechnicalIndicators] = None
    source: DataSourceType
    timeframe: TimeFrame
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class DataSourceConfig(BaseModel):
    """Model for data source configuration"""
    model_config = ConfigDict(
        title="Data Source Configuration",
        validate_assignment=True
    )

    api_key: Optional[str] = Field(None, description="API key for the data source")
    base_url: str = Field(..., description="Base URL for the API")
    rate_limit: int = Field(..., gt=0, description="Rate limit for API calls")
    timeout: int = Field(default=30, ge=1, description="Timeout for API calls in seconds")
    retry_attempts: int = Field(default=3, ge=0, description="Number of retry attempts")
    source_type: DataSourceType

class PipelineConfig(BaseModel):
    """Model for pipeline configuration"""
    model_config = ConfigDict(
        title="Pipeline Configuration",
        validate_assignment=True
    )

    data_sources: Dict[DataSourceType, DataSourceConfig]
    symbols: List[str] = Field(..., min_items=1)
    start_date: datetime
    end_date: datetime
    timeframe: TimeFrame
    batch_size: int = Field(default=1000, gt=0)
    parallel_jobs: int = Field(default=1, gt=0)
    retry_delay: int = Field(default=60, ge=0, description="Delay between retries in seconds")

class StorageConfig(BaseModel):
    """Model for storage configuration"""
    model_config = ConfigDict(
        title="Storage Configuration",
        validate_assignment=True
    )

    influxdb_url: str
    influxdb_token: str
    influxdb_org: str
    influxdb_bucket: str
    batch_size: int = Field(default=1000, gt=0)
    timeout: int = Field(default=30, ge=1)

class MetricsData(BaseModel):
    """Model for pipeline metrics data"""
    model_config = ConfigDict(
        title="Pipeline Metrics",
        validate_assignment=True
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_id: str
    symbol: str
    source: DataSourceType
    execution_time: float
    records_processed: int
    success: bool
    error_message: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

class ValidationError(BaseModel):
    """Model for validation errors"""
    model_config = ConfigDict(
        title="Validation Error",
        validate_assignment=True
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_type: str
    error_message: str
    data_point: Optional[Dict] = None
    symbol: str
    source: DataSourceType

class AlertConfig(BaseModel):
    """Model for alert configuration"""
    model_config = ConfigDict(
        title="Alert Configuration",
        validate_assignment=True
    )

    slack_webhook_url: Optional[str] = None
    email_recipients: Optional[List[str]] = None
    alert_levels: Dict[str, int] = Field(
        default={
            "critical": 1,
            "warning": 2,
            "info": 3
        }
    )

# Example usage of the models:

def create_stock_data_example():
    """Example of creating a StockData instance"""
    price_data = StockPrice(
        timestamp=datetime.utcnow(),
        open=100.0,
        high=105.0,
        low=98.0,
        close=102.0,
        volume=1000000
    )

    technical_indicators = TechnicalIndicators(
        sma_20=101.5,
        rsi_14=65.5,
        macd=0.5
    )

    stock_data = StockData(
        symbol="AAPL",
        price_data=price_data,
        technical_indicators=technical_indicators,
        source=DataSourceType.YAHOO_FINANCE,
        timeframe=TimeFrame.DAILY
    )

    return stock_data

def create_pipeline_config_example():
    """Example of creating a PipelineConfig instance"""
    yahoo_config = DataSourceConfig(
        base_url="https://query1.finance.yahoo.com/v8/finance/chart/",
        rate_limit=2000,
        source_type=DataSourceType.YAHOO_FINANCE
    )

    alpha_vantage_config = DataSourceConfig(
        api_key="your_api_key",
        base_url="https://www.alphavantage.co/query",
        rate_limit=500,
        source_type=DataSourceType.ALPHA_VANTAGE
    )

    pipeline_config = PipelineConfig(
        data_sources={
            DataSourceType.YAHOO_FINANCE: yahoo_config,
            DataSourceType.ALPHA_VANTAGE: alpha_vantage_config
        },
        symbols=["AAPL", "GOOGL", "MSFT"],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        timeframe=TimeFrame.DAILY,
        parallel_jobs=3
    )

    return pipeline_config