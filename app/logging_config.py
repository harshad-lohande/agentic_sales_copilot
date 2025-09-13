# app/logging_config.py

import logging
import sys
import uuid
import contextvars
from pythonjsonlogger import jsonlogger
from datetime import datetime, timezone
from .config import settings

# Context variable for correlation ID
correlation_id_var = contextvars.ContextVar("correlation_id", default=None)

SERVICE_NAME = getattr(settings, "SERVICE_NAME", "agentic-sales-copilot")
APP_ENV = getattr(settings, "APP_ENV", "dev")


class CorrelationFilter(logging.Filter):
    def filter(self, record):
        cid = correlation_id_var.get()
        if cid:
            record.correlation_id = cid
        else:
            record.correlation_id = None
        record.service_name = SERVICE_NAME
        record.env = APP_ENV
        # Use UTC timestamp; Logstash pipeline adds timezone offset as needed
        record.utc_time = datetime.now(timezone.utc).isoformat()
        return True


class ECSJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        # Map to ECS-like naming
        if "log.level" not in log_record:
            log_record["log.level"] = record.levelname
        if "service.name" not in log_record:
            log_record["service.name"] = getattr(record, "service_name", SERVICE_NAME)
        if "correlation.id" not in log_record and getattr(
            record, "correlation_id", None
        ):
            log_record["correlation.id"] = record.correlation_id
        # Provide @timestamp aligned to UTC
        if "@timestamp" not in log_record:
            log_record["@timestamp"] = getattr(record, "utc_time")
        if "env" not in log_record:
            log_record["env"] = getattr(record, "env", APP_ENV)


def setup_logging():
    if getattr(setup_logging, "_configured", False):
        return
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = ECSJsonFormatter("%(message)s %(filename)s %(funcName)s %(lineno)d")
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())
    logger.handlers = [handler]

    # Silence overly verbose third-party libs if needed
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    setup_logging._configured = True


logger = logging.getLogger("agentic_sales_copilot")


def set_correlation_id(correlation_id: str | None):
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id():
    return correlation_id_var.get()
