# app/celery_instrumentation.py

from celery import Task
from .logging_config import set_correlation_id, logger


class ContextTask(Task):
    def __call__(self, *args, **kwargs):
        # Accept correlation_id in kwargs or request headers (if using custom send)
        cid = kwargs.pop("correlation_id", None)
        if not cid:
            headers = getattr(self.request, "headers", {}) or {}
            cid = headers.get("correlation_id")
        set_correlation_id(cid)
        logger.info(
            {
                "message": "Celery task START",
                "celery.task_name": self.name,
                "celery.id": self.request.id,
            }
        )
        try:
            result = self.run(*args, **kwargs)
            logger.info(
                {
                    "message": "Celery task SUCCESS",
                    "celery.task_name": self.name,
                    "celery.id": self.request.id,
                }
            )
            return result
        except Exception as e:
            logger.error(
                {
                    "message": "Celery task FAILURE",
                    "error": str(e),
                    "celery.task_name": self.name,
                    "celery.id": self.request.id,
                }
            )
            raise
