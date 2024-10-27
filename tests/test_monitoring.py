# tests/test_monitoring.py
import pytest
from src.monitoring.metrics import PipelineMonitor

def test_data_quality_checks(sample_stock_data):
    """Test data quality monitoring"""
    monitor = PipelineMonitor()
    
    # Test with good data
    issues = monitor.check_data_quality(sample_stock_data)
    assert len(issues) == 0
    
    # Test with problematic data
    bad_data = sample_stock_data.copy()
    bad_data.loc[0, 'Close'] = bad_data['Close'].max() * 10  # Create anomaly
    
    issues = monitor.check_data_quality(bad_data)
    assert len(issues) > 0
    assert any('anomalies' in issue.lower() for issue in issues)