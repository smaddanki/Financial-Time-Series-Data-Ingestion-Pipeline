import logging
from typing import Dict, List
from datetime import datetime
import pandas as pd

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

class DataStorage:
    """Handles data storage in InfluxDB"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = InfluxDBClient(
            url=config['storage']['influxdb']['url'],
            token=config['storage']['influxdb']['token'],
            org=config['storage']['influxdb']['org']
        )
        self.bucket = config['storage']['influxdb']['bucket']
        
    def store_data(self, df: pd.DataFrame, symbol: str) -> None:
        """Store data in InfluxDB"""
        try:
            print('connecting to db')
            write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            points = []
            for _, row in df.iterrows():
                point = Point("stock_prices")\
                    .tag("symbol", symbol)\
                    .field("open", float(row['open']))\
                    .field("high", float(row['high']))\
                    .field("low", float(row['low']))\
                    .field("close", float(row['close']))\
                    .field("volume", int(row['volume']))\
                    .time(row['timestamp'], WritePrecision.NS)
                    
                if 'adjusted_close' in row:
                    point = point.field("adjusted_close", float(row['adjusted_close']))
                    
                points.append(point)
            
            write_api.write(bucket=self.bucket, record=points)
            print('completed')
            logger.info(f"Successfully stored {len(points)} points for {symbol}")
            
        except Exception as e:
            logger.error(f"Error storing data for {symbol}: {e}")
            raise