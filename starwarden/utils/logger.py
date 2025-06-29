import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, Union

LogLevel = Union[int, str]

_logger: Optional[logging.Logger] = None


def setup_logging(
    *, # Enforce keyword-only arguments
    logger_name: str = os.getenv("LOGGER_NAME", "app"),
    log_file: str = os.getenv("LOG_FILE", "starwarden.log"),
    enable_console_logging: bool = os.getenv("ENABLE_CONSOLE_LOGGING", "false").lower() in ('true', '1', 't'),
    console_level: LogLevel = os.getenv("CONSOLE_LEVEL", "INFO"),
    file_level: LogLevel = os.getenv("FILE_LEVEL", "DEBUG"),
    log_format: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    max_bytes: int = int(os.getenv("MAX_BYTES", 10 * 1024 * 1024)),  # 10MB
    backup_count: int = int(os.getenv("BACKUP_COUNT", 2))
) -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    # Configure the logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  
    formatter = logging.Formatter(log_format)
    logger.handlers.clear()

    # Console handler
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Rotating File handler
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        logger.warning(f"Failed to create log file handler for '{log_file}': {e}", exc_info=False)

    logger.propagate = False
    _logger = logger
    return logger

def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger

