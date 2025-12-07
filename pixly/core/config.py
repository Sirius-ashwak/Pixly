"""Configuration Manager component."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# Load .env file from current directory or parent directories
load_dotenv()


@dataclass
class Config:
    """Application configuration."""
    monitored_dirs: list[Path] = field(default_factory=list)
    screenshots_dir: Path = field(default_factory=lambda: Path.home() / "Screenshots")
    db_path: Path = field(default_factory=lambda: Path.home() / ".pixly" / "screenshots.db")
    gemini_api_key: str = ""
    tesseract_path: Optional[str] = None
    ocr_min_confidence: int = 60
    ai_model: str = "gemini-1.5-flash"
    ai_rate_limit_rpm: int = 15


DEFAULT_CONFIG_PATH = Path.home() / ".pixly" / "config.yaml"


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from file and environment.
    
    Args:
        config_path: Path to config file. Uses default if None.
        
    Returns:
        Config object with loaded settings.
        
    Raises:
        ConfigError: If API key is missing from environment.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    config = Config()
    
    # Load from file if exists
    if path.exists():
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        if 'monitored_dirs' in data:
            config.monitored_dirs = [Path(d).expanduser() for d in data['monitored_dirs']]
        if 'screenshots_dir' in data:
            config.screenshots_dir = Path(data['screenshots_dir']).expanduser()
        if 'db_path' in data:
            config.db_path = Path(data['db_path']).expanduser()
        if 'tesseract_path' in data:
            config.tesseract_path = data['tesseract_path']
        
        # OCR settings
        ocr_settings = data.get('ocr', {})
        if 'min_confidence' in ocr_settings:
            config.ocr_min_confidence = ocr_settings['min_confidence']
        
        # AI settings
        ai_settings = data.get('ai', {})
        if 'model' in ai_settings:
            config.ai_model = ai_settings['model']
        if 'rate_limit_rpm' in ai_settings:
            config.ai_rate_limit_rpm = ai_settings['rate_limit_rpm']
    
    # Load API key from environment (required)
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        raise ConfigError(
            "GEMINI_API_KEY environment variable not set. "
            "Please set it to your Gemini API key to enable AI analysis."
        )
    config.gemini_api_key = api_key
    
    # Set default monitored dirs if none specified
    if not config.monitored_dirs:
        config.monitored_dirs = [
            Path.home() / "Desktop",
            Path.home() / "Screenshots",
            Path.home() / "Downloads",
        ]
    
    return config


def save_config(config: Config, config_path: Path | None = None) -> None:
    """Save configuration to file.
    
    Args:
        config: Config object to save.
        config_path: Path to save config. Uses default if None.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'monitored_dirs': [str(d) for d in config.monitored_dirs],
        'screenshots_dir': str(config.screenshots_dir),
        'db_path': str(config.db_path),
        'tesseract_path': config.tesseract_path,
        'ocr': {
            'min_confidence': config.ocr_min_confidence,
        },
        'ai': {
            'model': config.ai_model,
            'rate_limit_rpm': config.ai_rate_limit_rpm,
        },
    }
    
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
