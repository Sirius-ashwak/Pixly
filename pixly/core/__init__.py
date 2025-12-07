"""Core components for Pixly."""

from .ocr import OCREngine, OCRResult
from .analyzer import AIAnalyzer, AnalysisResult
from .organizer import FileOrganizer
from .database import ScreenshotDatabase, ScreenshotRecord
from .deduplicator import DuplicateDetector
from .watcher import ScreenshotWatcher, start_monitoring
from .pipeline import ProcessingPipeline
from .config import Config, load_config, save_config, ConfigError

__all__ = [
    "OCREngine",
    "OCRResult",
    "AIAnalyzer",
    "AnalysisResult",
    "FileOrganizer",
    "ScreenshotDatabase",
    "ScreenshotRecord",
    "DuplicateDetector",
    "ScreenshotWatcher",
    "start_monitoring",
    "ProcessingPipeline",
    "Config",
    "load_config",
    "save_config",
    "ConfigError",
]
