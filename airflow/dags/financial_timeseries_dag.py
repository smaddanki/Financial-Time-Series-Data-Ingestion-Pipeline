from datetime import datetime, timedelta
from typing import Dict, List

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.models import Variable
from airflow.hooks.base import BaseHook
from airflow.utils.task_group import TaskGroup
from airflow.sensors.time_delta import TimeDeltaSensor
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from influxdb_client import InfluxDBClient, Point, WritePrecision

# Import the pipeline classes from the previous implementation
from financial_pipeline import (
    DataCollector, DataProcessor, DataStorage, 
    PipelineMonitor, DataSourceConfig
)

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
    'email': ['your-email@example.com']
}

# Create the DAG
dag = DAG(
    'financial_timeseries_pipeline',
    default_args=default_args,
    description='Financial Time Series Data Ingestion Pipeline',
    schedule_interval='0 0 * * *',  # Daily at midnight
    catchup=False,
    tags=['finance', 'data_ingestion'],
    max_active_runs=1
)

# Get configurations from Airflow Variables
def get_config():
    return {
        'symbols': Variable.get('stock_symbols', deserialize_json=True),
        'sources': Variable.get('data_sources', deserialize_json=True),
        'influxdb_conn': BaseHook.get_connection('influxdb'),
        'slack_conn': BaseHook.get_connection('slack_webhook')
    }

def validate_config(**context):
    """Validate the configuration parameters"""
    config = get_config()
    if not config['symbols']:
        raise ValueError("No symbols configured")
    if not config['sources']:
        raise ValueError("No data sources configured")
    return config

def initialize_components(**context):
    """Initialize pipeline components"""
    config = context['task_instance'].xcom_pull(task_ids='validate_config')
    source_config = DataSourceConfig()
    collector = DataCollector(source_config)
    processor = DataProcessor()
    storage = DataStorage()
    monitor = PipelineMonitor()
    
    return {
        'collector': collector,
        'processor': processor,
        'storage': storage,
        'monitor': monitor
    }

def collect_data(symbol: str, source: str, **context) -> dict:
    """Collect data for a specific symbol from a specific source"""
    components = context['task_instance'].xcom_pull(task_ids='initialize_components')
    collector = components['collector']
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)  # Get last day's data
    
    try:
        if source == 'yahoo_finance':
            df = collector.collect_yahoo_finance(symbol, start_date, end_date)
        elif source == 'alpha_vantage':
            df = collector.collect_alpha_vantage(symbol)
        else:
            raise ValueError(f"Unsupported data source: {source}")
        
        return {'symbol': symbol, 'data': df.to_dict()}
    except Exception as e:
        raise Exception(f"Data collection failed for {symbol} from {source}: {e}")

def process_data(**context):
    """Process the collected data"""
    raw_data = context['task_instance'].xcom_pull(task_ids='collect_data')
    components = context['task_instance'].xcom_pull(task_ids='initialize_components')
    processor = components['processor']
    
    df = pd.DataFrame.from_dict(raw_data['data'])
    processed_df = processor.process_data(df)
    
    return {
        'symbol': raw_data['symbol'],
        'data': processed_df.to_dict()
    }

def store_data(**context):
    """Store the processed data"""
    processed_data = context['task_instance'].xcom_pull(task_ids='process_data')
    components = context['task_instance'].xcom_pull(task_ids='initialize_components')
    storage = components['storage']
    
    df = pd.DataFrame.from_dict(processed_data['data'])
    storage.store_data(df, processed_data['symbol'])
    
    return f"Data stored for {processed_data['symbol']}"

def monitor_pipeline(**context):
    """Monitor the pipeline execution"""
    components = context['task_instance'].xcom_pull(task_ids='initialize_components')
    monitor = components['monitor']
    processed_data = context['task_instance'].xcom_pull(task_ids='process_data')
    
    df = pd.DataFrame.from_dict(processed_data['data'])
    issues = monitor.check_data_quality(df)
    
    if issues:
        # Send alert to Slack if there are issues
        slack_message = f"Data quality issues detected for {processed_data['symbol']}:\n"
        slack_message += "\n".join(issues)
        
        slack_webhook = SlackWebhookOperator(
            task_id='slack_alert',
            http_conn_id='slack_webhook',
            message=slack_message,
            dag=dag
        )
        slack_webhook.execute(context)
    
    return issues

# Create tasks
start_pipeline = DummyOperator(
    task_id='start_pipeline',
    dag=dag
)

validate_config_task = PythonOperator(
    task_id='validate_config',
    python_callable=validate_config,
    dag=dag
)

initialize_components_task = PythonOperator(
    task_id='initialize_components',
    python_callable=initialize_components,
    dag=dag
)

end_pipeline = DummyOperator(
    task_id='end_pipeline',
    dag=dag
)

# Create dynamic tasks for each symbol and source
config = get_config()
for symbol in config['symbols']:
    with TaskGroup(group_id=f'process_{symbol}', dag=dag) as symbol_group:
        collect_data_task = PythonOperator(
            task_id=f'collect_data_{symbol}',
            python_callable=collect_data,
            op_kwargs={'symbol': symbol, 'source': config['sources'][symbol]},
        )
        
        process_data_task = PythonOperator(
            task_id=f'process_data_{symbol}',
            python_callable=process_data,
        )
        
        store_data_task = PythonOperator(
            task_id=f'store_data_{symbol}',
            python_callable=store_data,
        )
        
        monitor_task = PythonOperator(
            task_id=f'monitor_{symbol}',
            python_callable=monitor_pipeline,
        )
        
        # Set dependencies within the symbol group
        collect_data_task >> process_data_task >> store_data_task >> monitor_task
    
    # Set dependencies for the symbol group
    initialize_components_task >> symbol_group >> end_pipeline

# Set the main pipeline dependencies
start_pipeline >> validate_config_task >> initialize_components_task