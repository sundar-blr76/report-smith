"""
Centralized logging configuration for ReportSmith application.
"""

import logging
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from contextvars import ContextVar

# Context var to hold request/trace id
REQUEST_ID: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

IST_TZ = ZoneInfo("Asia/Kolkata")


class ISTFormatter(logging.Formatter):
    """Formatter that renders %(asctime)s in IST (Asia/Kolkata)."""
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        # Fallback ISO with TZ
        return dt.strftime('%Y-%m-%dT%H:%M:%S %Z')


class RequestIdFilter(logging.Filter):
    """Inject request_id from contextvar into log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        rid = REQUEST_ID.get()
        if not hasattr(record, "request_id"):
            record.request_id = rid or "-"
        return True


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
            '%(asctime)s - %(name)s - %(levellevel)s - [%(filename)s:%(lineno)d] - [rid:%(request_id)s] - %(message)s'.replace('levellevel','levelname'),
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = ISTFormatter(
            '%(asctime)s - %(levellevel)s - [rid:%(request_id)s] - %(message)s'.replace('levellevel','levelname'),
            datefmt='%H:%M:%S'
        )
        
        req_filter = RequestIdFilter()
        
        # File handler - detailed logging
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        file_handler.addFilter(req_filter)
        
        # If terminal does not support ANSI, strip codes from console output
        supports_color = sys.stdout.isatty() and os.getenv("TERM") not in (None, "dumb")
        class _StripANSIFormatter(ISTFormatter):
            ansi_re = re.compile(r"\x1b\[[0-9;]*m")
            def format(self, record):
                s = super().format(record)
                return s if supports_color else self.ansi_re.sub("", s)

        # Console handler - simpler logging
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(_StripANSIFormatter(simple_formatter._fmt, datefmt='%H:%M:%S'))
        console_handler.addFilter(req_filter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Add handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Also attach handlers to FastAPI/Uvicorn loggers so they write to app.log
        for lname in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
            lg = logging.getLogger(lname)
            try:
                lg.setLevel(log_level)
                # Avoid duplicate file handler for same path
                if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == str(log_file) for h in lg.handlers):
                    lg.addHandler(file_handler)
                # Ensure console output consistent
                if not any(isinstance(h, logging.StreamHandler) for h in lg.handlers):
                    lg.addHandler(console_handler)
                lg.propagate = False
            except Exception:
                pass
        
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



# Request ID helpers (used by API middleware)

def bind_request_id(request_id: Optional[str]) -> None:
    try:
        REQUEST_ID.set(request_id)
    except Exception:
        pass


def clear_request_id() -> None:
    try:
        REQUEST_ID.set(None)
    except Exception:
        pass




# Export helpers for external use
__all__ = [
    "LoggerManager",
    "get_logger",
    "bind_request_id",
    "clear_request_id",
]
