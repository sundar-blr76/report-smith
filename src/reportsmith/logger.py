"""
Centralized logging configuration for ReportSmith application.
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

IST_TZ = ZoneInfo("Asia/Kolkata")


class ISTFormatter(logging.Formatter):
    """Formatter that renders %(asctime)s in IST (Asia/Kolkata)."""
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        # Fallback ISO with TZ
        return dt.strftime('%Y-%m-%dT%H:%M:%S %Z')


class LoggerManager:
    """Manages application-wide logging configuration."""
    
    _instance: Optional['LoggerManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logger manager (singleton pattern)."""
        if not LoggerManager._initialized:
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
            LoggerManager._initialized = True
    
    def setup_logging(self, level: str = "INFO") -> None:
        """
        Configure application-wide logging.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create log file path (single log file)
        log_file = self.log_dir / "app.log"
        
        # Create formatters
        detailed_formatter = ISTFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = ISTFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler - detailed logging
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler - simpler logging
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(simple_formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Add handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Log startup information
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info("ReportSmith Application Starting")
        logger.info(f"Log File: {log_file}")
        logger.info(f"Log Level: {level.upper()}")
        # Force IST timezone (Asia/Kolkata)
        try:
            ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
            started_at = ist_now.strftime('%Y-%m-%d %H:%M:%S IST')
        except Exception:
            started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Started at: {started_at}")
        logger.info("=" * 60)
        
        # Suppress noisy third-party loggers
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance for a specific module.
        
        Args:
            name: Logger name (typically __name__ of the module)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Configured logger instance
    """
    manager = LoggerManager()
    return manager.get_logger(name)
