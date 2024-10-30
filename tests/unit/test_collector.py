# tests/unit/test_collector.py
import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.collector import DataCollector
from src.pipeline.config import DataSourceConfig

def test_collect_yahoo_finance(mock_yahoo_finance, sample_stock_data):
    """Test collecting data from Yahoo Finance"""
    config = DataSourceConfig()
    collector = DataCollector(config)
    
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.history.return_value = sample_stock_data
        
        symbol = 'AAPL'
        start_date = '2024-01-01'
        end_date = '2024-01-10'
        
        result = collector.collect_yahoo_finance(symbol, start_date, end_date)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_stock_data)
        assert all(col in result.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])

def test_rate_limiter():
    """Test rate limiter functionality"""
    config = DataSourceConfig()
    collector = DataCollector(config)
    
    # Test rate limiting for Yahoo Finance
    for _ in range(config.config['yahoo_finance']['rate_limit_calls']):
        assert collector.rate_limiters['yahoo_finance'].can_proceed()
    
    # Next call should be rate limited
    assert not collector.rate_limiters['yahoo_finance'].can_proceed()
