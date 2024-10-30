# airflow/dags/financial_timeseries_dag.py

from datetime import datetime, timedelta
from typing import Dict, List, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.models import Variable
from airflow.hooks.base import BaseHook
from airflow.utils.task_group import TaskGroup
from airflow.exceptions import AirflowException

import pandas as pd
from pathlib import Path
import sys

# Add src directory to Python path
sys.path.append(str(Path(__file__).parents[2]))

from src.pipeline.collector import DataCollector
from src.pipeline.processor import DataProcessor
from src.pipeline.storage import DataStorage
from src.monitoring.metrics import MetricsCollector
from src.monitoring.alerts import AlertManager
from src.utils.config import ConfigLoader

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
    # 'email': Variable.get('alert_email', 'alerts@company.com'),
    'execution_timeout': timedelta(hours=1),
    'sla': timedelta(hours=2)
}

class FinancialPipelineDAG:
    """Financial Time Series Pipeline DAG"""
    
    def __init__(self):
        self.dag_id = 'financial_timeseries_pipeline'
        self.schedule_interval = '0 0 * * *'  # Daily at midnight
        self.config = self._load_config()
        self.components = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load pipeline configuration"""
        config_loader = ConfigLoader()
        return config_loader.load_config()
        
    def _initialize_components(self, **context) -> Dict[str, Any]:
        """Initialize pipeline components"""
        self.components = {
            'collector': DataCollector(self.config),
            'processor': DataProcessor(self.config),
            'storage': DataStorage(self.config),
            'metrics': MetricsCollector(self.config),
            'alerts': AlertManager(self.config)
        }
        return self.components
        
    def _collect_data(self, symbol: str, **context) -> Dict[str, Any]:
        """Collect data for a specific symbol"""
        components = context['task_instance'].xcom_pull(
            task_ids='initialize_components'
        )
        metrics = components['metrics']
        collector = components['collector']
        
        try:
            operation_id = metrics.start_operation('collect_data', symbol)
            
            # Get date range for collection
            end_date = datetime.now()
            start_date = end_date - timedelta(
                days=self.config['pipeline']['lookback_days']
            )
            
            # Collect data
            data = collector.collect_data(
                symbol=symbol,
                source='yahoo_finance',
                start_date=start_date,
                end_date=end_date
            )
            
            metrics.end_operation(operation_id, success=True)
            
            return {
                'symbol': symbol,
                'data': data.to_dict()
            }
            
        except Exception as e:
            metrics.end_operation(operation_id, success=False, error=str(e))
            raise AirflowException(f"Data collection failed for {symbol}: {e}")
            
    def _process_data(self, **context) -> Dict[str, Any]:
        """Process collected data"""
        components = context['task_instance'].xcom_pull(
            task_ids='initialize_components'
        )
        metrics = components['metrics']
        processor = components['processor']
        
        # Get collected data
        collected_data = context['task_instance'].xcom_pull(
            task_ids=context['task'].upstream_task_ids.pop()
        )
        symbol = collected_data['symbol']
        
        try:
            operation_id = metrics.start_operation('process_data', symbol)
            
            # Convert dict back to DataFrame
            df = pd.DataFrame.from_dict(collected_data['data'])
            
            # Process data
            processed_data = processor.process_data(df)
            
            metrics.end_operation(operation_id, success=True)
            
            return {
                'symbol': symbol,
                'data': processed_data.to_dict()
            }
            
        except Exception as e:
            metrics.end_operation(operation_id, success=False, error=str(e))
            raise AirflowException(f"Data processing failed for {symbol}: {e}")
            
    def _store_data(self, **context) -> None:
        """Store processed data"""
        components = context['task_instance'].xcom_pull(
            task_ids='initialize_components'
        )
        metrics = components['metrics']
        storage = components['storage']
        
        # Get processed data
        processed_data = context['task_instance'].xcom_pull(
            task_ids=context['task'].upstream_task_ids.pop()
        )
        symbol = processed_data['symbol']
        
        try:
            operation_id = metrics.start_operation('store_data', symbol)
            
            # Convert dict back to DataFrame
            df = pd.DataFrame.from_dict(processed_data['data'])
            
            # Store data
            storage.store_data(df, symbol)
            
            metrics.end_operation(operation_id, success=True)
            
        except Exception as e:
            metrics.end_operation(operation_id, success=False, error=str(e))
            raise AirflowException(f"Data storage failed for {symbol}: {e}")
            
    def _monitor_metrics(self, **context) -> None:
        """Monitor pipeline metrics"""
        components = context['task_instance'].xcom_pull(
            task_ids='initialize_components'
        )
        metrics = components['metrics']
        alerts = components['alerts']
        
        try:
            # Analyze metrics
            all_metrics = metrics.get_metrics()
            
            # Check for issues
            issues = []
            for operation_id, metric in all_metrics.items():
                if metric['status'] == 'error':
                    issues.append(
                        f"Operation {metric['operation']} failed for "
                        f"{metric['symbol']}: {metric.get('error')}"
                    )
                elif metric['duration'] > self.config['monitoring']['sla'][metric['operation']]:
                    issues.append(
                        f"Operation {metric['operation']} exceeded SLA for "
                        f"{metric['symbol']}: {metric['duration']:.2f}s"
                    )
                    
            # Send alerts if there are issues
            if issues:
                alerts.send_alert(
                    level='warning',
                    message='Pipeline issues detected',
                    details={'issues': issues}
                )
                
        except Exception as e:
            raise AirflowException(f"Metrics monitoring failed: {e}")
            
    def generate_dag(self) -> DAG:
        """Generate the Airflow DAG"""
        dag = DAG(
            dag_id=self.dag_id,
            default_args=default_args,
            description='Financial Time Series Data Ingestion Pipeline',
            schedule_interval=self.schedule_interval,
            catchup=False,
            tags=['finance', 'data_ingestion'],
            max_active_runs=1
        )
        
        with dag:
            # Start pipeline
            start_pipeline = EmptyOperator(
                task_id='start_pipeline'
            )
            
            # Initialize components
            initialize_components = PythonOperator(
                task_id='initialize_components',
                python_callable=self._initialize_components
            )
            
            # Create tasks for each symbol
            for symbol in self.config['pipeline']['symbols']:
                with TaskGroup(group_id=f'process_{symbol}') as symbol_group:
                    # Collect data
                    collect_data = PythonOperator(
                        task_id=f'collect_data_{symbol}',
                        python_callable=self._collect_data,
                        op_kwargs={'symbol': symbol}
                    )
                    
                    # Process data
                    process_data = PythonOperator(
                        task_id=f'process_data_{symbol}',
                        python_callable=self._process_data
                    )
                    
                    # Store data
                    store_data = PythonOperator(
                        task_id=f'store_data_{symbol}',
                        python_callable=self._store_data
                    )
                    
                    # Set dependencies
                    collect_data >> process_data >> store_data
                    
                # Add symbol group to main flow
                initialize_components >> symbol_group
                
            # # Monitor metrics
            # monitor_metrics = PythonOperator(
            #     task_id='monitor_metrics',
            #     python_callable=self._monitor_metrics
            # )
            
            # End pipeline
            end_pipeline = EmptyOperator(
                task_id='end_pipeline'
            )
            
            # # Set final dependencies
            # start_pipeline >> initialize_components >> end_pipeline
            
        return dag

# Create DAG instance
financial_pipeline_dag = FinancialPipelineDAG()
dag = financial_pipeline_dag.generate_dag()