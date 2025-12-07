import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional, Union

from dotenv import load_dotenv
from rich.logging import RichHandler

load_dotenv()
LogLevel = Union[int, str]

LOGGER_NAME = os.getenv("LOGGER_NAME", "app")
LOG_FILE = os.getenv("LOG_FILE", "starwarden.log")
ENABLE_CONSOLE_LOGGING = os.getenv("ENABLE_CONSOLE_LOGGING", "true").lower() in ("true", "1", "t")
CONSOLE_LEVEL = os.getenv("CONSOLE_LEVEL", "WARNING")
FILE_LEVEL = os.getenv("FILE_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
MAX_BYTES = int(os.getenv("MAX_BYTES", 10 * 1024 * 1024))  # 10MB
BACKUP_COUNT = int(os.getenv("BACKUP_COUNT", 2))

_logger: Optional[logging.Logger] = None


def setup_logging(
    *,  # Enforce keyword-only arguments
    logger_name: str = LOGGER_NAME,
    log_file: str = LOG_FILE,
    enable_console_logging: bool = ENABLE_CONSOLE_LOGGING,
    console_level: LogLevel = CONSOLE_LEVEL,
    file_level: LogLevel = FILE_LEVEL,
    log_format: str = LOG_FORMAT,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(log_format)

    # Console handler
    if enable_console_logging and not any(isinstance(h, RichHandler) for h in logger.handlers):
        console_handler = RichHandler(rich_tracebacks=True)
        console_handler.setLevel(console_level)
        logger.addHandler(console_handler)

    # Rotating File handler
    try:
        if not any(
            isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == os.path.abspath(log_file)
            for h in logger.handlers
        ):
            file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
            file_handler.setLevel(file_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        import sys

        # stderr as fallback
        sys.stderr.write(f"Failed to create log file handler for '{log_file}': {e}\n")
        logger.warning(f"Failed to create log file handler for '{log_file}': {e}", exc_info=False)

    logger.propagate = False
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger
