# tests/conftest.py
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock

@pytest.fixture
def sample_stock_data():
    """Fixture providing sample stock data"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-10')
    data = {
        'Date': dates,
        'Open': [100 + i for i in range(10)],
        'High': [105 + i for i in range(10)],
        'Low': [95 + i for i in range(10)],
        'Close': [102 + i for i in range(10)],
        'Volume': [1000000 + i * 1000 for i in range(10)]
    }
    return pd.DataFrame(data)

@pytest.fixture
def mock_influxdb_client():
    """Fixture providing a mock InfluxDB client"""
    mock_client = MagicMock()
    mock_write_api = MagicMock()
    mock_client.write_api.return_value = mock_write_api
    return mock_client

@pytest.fixture
def mock_yahoo_finance():
    """Fixture providing a mock Yahoo Finance client"""
    mock_yf = MagicMock()
    return mock_yf


