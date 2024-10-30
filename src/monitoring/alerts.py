import logging
from typing import Dict, List
import requests

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages alerts for the pipeline"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.slack_webhook = config.get('monitoring', {}).get('alerting', {}).get('slack_webhook')
        self.email_recipients = config.get('monitoring', {}).get('alerting', {}).get('email_recipients', [])
        
    def send_alert(self, level: str, message: str, details: Dict = None) -> None:
        """Send alert through configured channels"""
        if level not in self.config['monitoring']['alert_levels']:
            raise ValueError(f"Invalid alert level: {level}")
            
        alert_data = {
            'level': level,
            'message': message,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.config['monitoring']['slack_alerts']:
            self._send_slack_alert(alert_data)
            
        if self.config['monitoring']['email_alerts']:
            self._send_email_alert(alert_data)
            
    def _send_slack_alert(self, alert_data: Dict) -> None:
        """Send alert to Slack"""
        if not self.slack_webhook:
            logger.warning("Slack webhook not configured")
            return
            
        try:
            response = requests.post(
                self.slack_webhook,
                json={
                    'text': f"*{alert_data['level'].upper()}*: {alert_data['message']}\n"
                           f"Details: {alert_data['details']}"
                }
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            
    def _send_email_alert(self, alert_data: Dict) -> None:
        """Send alert via email"""
        if not self.email_recipients:
            logger.warning("No email recipients configured")
            return
            
        # Implement email sending logic here
        pass
