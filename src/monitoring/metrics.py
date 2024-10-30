import logging
import time
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and reports pipeline metrics"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.metrics: Dict = {}
        
    def start_operation(self, operation: str, symbol: str) -> str:
        """Start timing an operation"""
        operation_id = f"{operation}_{symbol}_{datetime.utcnow().timestamp()}"
        self.metrics[operation_id] = {
            'operation': operation,
            'symbol': symbol,
            'start_time': time.time(),
            'status': 'started'
        }
        return operation_id
        
    def end_operation(self, operation_id: str, 
                     success: bool = True, 
                     error: Optional[str] = None) -> None:
        """End timing an operation"""
        if operation_id in self.metrics:
            self.metrics[operation_id].update({
                'end_time': time.time(),
                'duration': time.time() - self.metrics[operation_id]['start_time'],
                'status': 'success' if success else 'error',
                'error': error
            })
            
    def get_metrics(self) -> Dict:
        """Get collected metrics"""
        return self.metrics