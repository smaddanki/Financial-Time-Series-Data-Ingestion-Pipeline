
# tests/unit/test_processor.py
import pytest
from src.pipeline.processor import DataProcessor

def test_validate_data(sample_stock_data):
    """Test data validation"""
    processor = DataProcessor()
    
    # Test with valid data
    validated_data = processor.validate_data(sample_stock_data)
    assert validated_data is not None
    
    # Test with missing columns
    invalid_data = sample_stock_data.drop(['Close'], axis=1)
    with pytest.raises(ValueError):
        processor.validate_data(invalid_data)

def test_handle_missing_values(sample_stock_data):
    """Test missing value handling"""
    processor = DataProcessor()
    
    # Introduce missing values
    data_with_missing = sample_stock_data.copy()
    data_with_missing.loc[0, 'Close'] = None
    data_with_missing.loc[1, 'Volume'] = None
    
    processed_data = processor.handle_missing_values(data_with_missing)
    
    assert processed_data['Close'].isnull().sum() == 0
    assert processed_data['Volume'].isnull().sum() == 0

def test_calculate_technical_indicators(sample_stock_data):
    """Test technical indicator calculations"""
    processor = DataProcessor()
    
    processed_data = processor.calculate_technical_indicators(sample_stock_data)
    
    assert 'SMA_20' in processed_data.columns
    assert 'RSI' in processed_data.columns
