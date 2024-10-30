
# tests/integration/test_pipeline.py
import pytest
from src.pipeline.collector import DataCollector
from src.pipeline.processor import DataProcessor
from src.pipeline.storage import DataStorage
from src.pipeline.config import DataSourceConfig

def test_full_pipeline_integration(mock_influxdb_client):
    """Test full pipeline integration"""
    # Initialize components
    config = DataSourceConfig()
    collector = DataCollector(config)
    processor = DataProcessor()
    storage = DataStorage()
    storage.client = mock_influxdb_client
    
    # Test pipeline flow
    symbol = 'AAPL'
    start_date = '2024-01-01'
    end_date = '2024-01-10'
    
    # Collect data
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.history.return_value = sample_stock_data
        raw_data = collector.collect_yahoo_finance(symbol, start_date, end_date)
    
    # Process data
    processed_data = processor.process_data(raw_data)
    
    # Store data
    storage.store_data(processed_data, symbol)
    
    # Verify pipeline completion
    assert mock_influxdb_client.write_api.called
    assert mock_influxdb_client.write_api().write.called
