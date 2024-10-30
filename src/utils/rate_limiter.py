import time
from collections import deque
from datetime import datetime, timedelta
from typing import Deque

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.timestamps: Deque[float] = deque()
        
    def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded"""
        current_time = time.time()
        
        # Remove timestamps older than the period
        while self.timestamps and current_time - self.timestamps[0] >= self.period:
            self.timestamps.popleft()
            
        if len(self.timestamps) >= self.calls:
            sleep_time = self.timestamps[0] + self.period - current_time
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        self.timestamps.append(current_time)
