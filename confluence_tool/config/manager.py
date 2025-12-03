"""Configuration manager for the Confluence tool."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, searches for config.yaml
                        in current directory, then user home directory.
        """
        self.config_path = self._find_config_path(config_path)
        self.config = self._load_config()
    
    @classmethod
    def create_multi_env_manager(cls, source_config: Optional[str] = None, 
                                target_config: Optional[str] = None):
        """Create a manager that supports multiple environment configurations.
        
        Args:
            source_config: Path to source environment configuration
            target_config: Path to target environment configuration
            
        Returns:
            Tuple of (source_manager, target_manager)
        """
        source_manager = cls(source_config) if source_config else None
        target_manager = cls(target_config) if target_config else None
        return source_manager, target_manager
    
    def _find_config_path(self, config_path: Optional[str]) -> str:
        """Find configuration file path."""
        if config_path:
            # If a specific path is provided, it must exist
            if os.path.exists(config_path):
                return config_path
            else:
                raise FileNotFoundError(
                    f"Specified configuration file not found: {config_path}\n"
                    f"Please check the path and try again."
                )
        
        # Search in current directory first
        current_dir_config = os.path.join(os.getcwd(), "config.yaml")
        if os.path.exists(current_dir_config):
            return current_dir_config
        
        # Then in user home directory
        home_config = os.path.join(Path.home(), ".confluence_tool_config.yaml")
        if os.path.exists(home_config):
            return home_config
        
        # Finally, try the package directory
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        package_config = os.path.join(package_dir, "config.yaml")
        if os.path.exists(package_config):
            return package_config
        
        raise FileNotFoundError(
            "Configuration file not found. Please create config.yaml in:\n"
            f"  - Current directory: {current_dir_config}\n"
            f"  - Home directory: {home_config}\n"
            f"  - Or specify path with --config option"
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError("Configuration file is empty")
            
            # Validate required sections
            self._validate_config(config)
            return config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {self.config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading config file {self.config_path}: {e}")
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration structure."""
        required_sections = ['confluence', 'export', 'import', 'general']
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate Confluence connection settings
        confluence_config = config['confluence']
        if 'base_url' not in confluence_config or not confluence_config['base_url']:
            raise ValueError("Confluence base_url is required")
        
        if 'auth' not in confluence_config:
            raise ValueError("Confluence auth configuration is required")
        
        auth_config = confluence_config['auth']
        if not auth_config.get('username'):
            raise ValueError("Confluence username is required")
        
        if not auth_config.get('api_token') and not auth_config.get('password'):
            raise ValueError("Either api_token or password is required for authentication")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'confluence.base_url')
            default: Default value if key is not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_confluence_config(self) -> Dict[str, Any]:
        """Get Confluence connection configuration."""
        return self.config['confluence']
    
    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration."""
        return self.config['export']
    
    def get_import_config(self) -> Dict[str, Any]:
        """Get import configuration."""
        return self.config['import']
    
    def get_general_config(self) -> Dict[str, Any]:
        """Get general configuration."""
        return self.config['general']
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.config.get('logging', {})
    
    def create_sample_config(self, path: str) -> None:
        """Create a sample configuration file.
        
        Args:
            path: Path where to create the sample config file
        """
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        sample_config_path = os.path.join(package_dir, "config.yaml")
        
        if os.path.exists(sample_config_path):
            import shutil
            shutil.copy2(sample_config_path, path)
            logger.info(f"Sample configuration created at: {path}")
        else:
            raise FileNotFoundError("Sample configuration file not found in package")