import os
import yaml
import logging
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class ConfigLoader:
    """Configuration loader utility"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.getenv('CONFIG_PATH', 'configs')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        load_dotenv()  # Load environment variables from .env file
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration based on current environment"""
        config_file = Path(self.config_path) / f"{self.environment}.yaml"
        
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_file}")
            
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            # Resolve environment variables in the configuration
            config = self._resolve_env_vars(config)
            
            # Validate required configuration
            self._validate_config(config)
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing configuration file: {e}")
            
    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variables in configuration values"""
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(v) for v in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            if env_var not in os.environ:
                raise ConfigurationError(f"Environment variable not found: {env_var}")
            return os.environ[env_var]
        return config
        
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate required configuration values"""
        required_keys = {
            'data_sources',
            'pipeline',
            'storage',
            'monitoring'
        }
        
        missing_keys = required_keys - set(config.keys())
        if missing_keys:
            raise ConfigurationError(f"Missing required configuration keys: {missing_keys}")
            
        # Validate data sources configuration
        for source, source_config in config['data_sources'].items():
            required_source_keys = {'base_url', 'rate_limit', 'timeout'}
            missing_source_keys = required_source_keys - set(source_config.keys())
            if missing_source_keys:
                raise ConfigurationError(
                    f"Missing required configuration for data source {source}: {missing_source_keys}"
                )

# Usage example:
def get_config():
    """Get configuration for current environment"""
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config()
        return config
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise