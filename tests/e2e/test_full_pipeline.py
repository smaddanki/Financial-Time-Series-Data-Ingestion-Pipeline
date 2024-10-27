
# tests/e2e/test_full_pipeline.py
import pytest
from airflow.models import DagBag
from airflow.utils.dates import days_ago
from airflow.utils.state import State

def test_dag_loads_with_no_errors():
    """Test that the DAG can be loaded without errors"""
    dag_bag = DagBag(dag_folder='dags', include_examples=False)
    assert len(dag_bag.import_errors) == 0
    assert 'financial_timeseries_pipeline' in dag_bag.dags

def test_dag_structure():
    """Test the structure of the DAG"""
    dag_bag = DagBag(dag_folder='dags', include_examples=False)
    dag = dag_bag.get_dag('financial_timeseries_pipeline')
    
    # Test task dependencies
    assert len(dag.tasks) > 0
    assert any(task.task_id == 'start_pipeline' for task in dag.tasks)
    assert any(task.task_id == 'end_pipeline' for task in dag.tasks)
