import logging
import sys
from src.common.config import get_settings


def get_logger(name: str) -> logging.Logger:
    """Configures structured logger for FastRoute services."""
    settings = get_settings()
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(settings.log_level.upper())
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
