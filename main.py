from src.pipeline.collector import DataCollector
from src.pipeline.processor import DataProcessor
from src.pipeline.storage import DataStorage
from src.monitoring.metrics import MetricsCollector
from src.monitoring.alerts import AlertManager
from src.utils.config import  get_config

# Initialize components
config = get_config()
collector = DataCollector(config)
processor = DataProcessor(config)
storage = DataStorage(config)
metrics = MetricsCollector(config)
alerts = AlertManager(config)

start_date = '2024-01-01'
end_date = '2024-01-10'

# Access configuration values
data_sources = config['data_sources']


pipeline_config = config['pipeline']

# Collect and process data

# Start metrics collection
operation_id = metrics.start_operation('data_collection', 'AAPL')

# Collect data
data = collector.collect_data('AAPL', 'yahoo_finance', 
                            start_date, end_date)



# Process data
processed_data = processor.process_data(data)

print(processed_data)


# Store data
storage.store_data(processed_data, 'AAPL')
