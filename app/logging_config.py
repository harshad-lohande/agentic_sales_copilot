# app/logging_config.py

import logging
import sys
# from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Configures the application's logger for consistent, structured logging.
    """
    # Create a custom logger
    logger = logging.getLogger("agentic_sales_copilot")
    logger.setLevel(logging.INFO)

    # Prevent logs from being passed to the root logger
    logger.propagate = False

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Create formatters and add it to handlers
    log_format = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s'
    )
    console_handler.setFormatter(log_format)

    # Silence overly verbose third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sendgrid").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Add handlers to the logger
    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(console_handler)

    return logger

# Create a single, importable logger instance
logger = setup_logging()