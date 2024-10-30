
# tests/unit/test_storage.py
import pytest
from src.pipeline.storage import DataStorage

def test_store_data(mock_influxdb_client, sample_stock_data):
    """Test data storage in InfluxDB"""
    storage = DataStorage()
    storage.client = mock_influxdb_client
    
    symbol = 'AAPL'
    storage.store_data(sample_stock_data, symbol)
    
    # Verify write_api was called
    assert mock_influxdb_client.write_api.called
    assert mock_influxdb_client.write_api().write.called
