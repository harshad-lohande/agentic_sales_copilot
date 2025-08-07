# app/logging_config.py

import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configures a structured JSON logger."""
    logger = logging.getLogger()
    
    # Avoid adding duplicate handlers if this function is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logHandler = logging.StreamHandler(sys.stdout)
    
    # This formatter creates logs in JSON format
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    
    # Silence overly verbose third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sendgrid").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    return logger

# Create a single, importable logger instance
logger = setup_logging()