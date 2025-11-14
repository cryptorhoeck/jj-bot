"""
Centralized logging configuration for JJ-Bot
Provides structured logging with JSON support and file rotation
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import os

# Import config (will fall back to defaults if not available)
try:
    import config
    LOG_LEVEL = config.LOG_LEVEL
    LOG_FORMAT = config.LOG_FORMAT
    LOG_FILE = config.LOG_FILE
    LOG_MAX_SIZE = config.LOG_MAX_SIZE
    LOG_BACKUP_COUNT = config.LOG_BACKUP_COUNT
    LOG_TO_CONSOLE = config.LOG_TO_CONSOLE
    LOG_TO_FILE = config.LOG_TO_FILE
except ImportError:
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'text')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/jj-bot.log')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', 10485760))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
    LOG_TO_CONSOLE = os.getenv('LOG_TO_CONSOLE', 'true').lower() in ('true', '1', 'yes')
    LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() in ('true', '1', 'yes')


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for better readability
    """

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Color the level name
        record.levelname = f"{color}{record.levelname}{reset}"

        return super().format(record)


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    """
    Setup and configure a logger with consistent formatting

    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Override default log file path
        log_format: Format type ('json' or 'text')
        extra_fields: Additional fields to include in logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Use configured level or default
    level = level or LOG_LEVEL
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Determine format
    log_format = log_format or LOG_FORMAT

    # Console handler
    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logger.level)

        if log_format == 'json':
            console_handler.setFormatter(JSONFormatter())
        else:
            # Text format with colors
            text_format = '%(asctime)s [%(levelname)8s] %(name)s - %(message)s'
            date_format = '%Y-%m-%d %H:%M:%S'
            console_handler.setFormatter(ColoredFormatter(text_format, date_format))

        logger.addHandler(console_handler)

    # File handler with rotation
    if LOG_TO_FILE:
        log_file_path = log_file or LOG_FILE
        log_dir = Path(log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logger.level)

        if log_format == 'json':
            file_handler.setFormatter(JSONFormatter())
        else:
            # Text format without colors for file
            text_format = '%(asctime)s [%(levelname)8s] %(name)s - %(message)s'
            date_format = '%Y-%m-%d %H:%M:%S'
            file_handler.setFormatter(logging.Formatter(text_format, date_format))

        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Get or create a logger with standard configuration

    Args:
        name: Logger name (typically __name__)
        **kwargs: Additional arguments to pass to setup_logger

    Returns:
        Configured logger instance
    """
    return setup_logger(name, **kwargs)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds extra context to all log messages
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add extra fields to log message"""
        # Merge extra fields
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def get_logger_with_context(
    name: str,
    context: Dict[str, Any],
    **kwargs
) -> LoggerAdapter:
    """
    Get a logger with additional context fields

    Args:
        name: Logger name
        context: Context dictionary to add to all log messages
        **kwargs: Additional arguments to pass to setup_logger

    Returns:
        Logger adapter with context
    """
    logger = get_logger(name, **kwargs)
    return LoggerAdapter(logger, context)


# Module-level logger for this file
logger = get_logger(__name__)


if __name__ == "__main__":
    # Test the logging configuration
    test_logger = get_logger("test_logger")

    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    test_logger.critical("This is a critical message")

    # Test with context
    context_logger = get_logger_with_context(
        "context_test",
        {"service": "test_service", "version": "1.0.0"}
    )
    context_logger.info("Message with context")

    print("\n✅ Logging test complete. Check logs/ directory for output.")
