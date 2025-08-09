# app/tasks.py

import json
import asyncio
from celery import Celery
from .logging_config import logger, setup_logging
setup_logging()

from .config import settings
from .reply_agent import SDR_Agent
from .slack_notifier import send_slack_notification
from .email_utils import send_single_email
from agents import Runner, trace

# Configure Celery to use the Redis URL from our settings
celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL)

@celery_app.task
def process_inbound_email(sender: str, subject: str, body: str):
    """
    This background task runs the SDR_Agent, parses its output,
    and triggers the Slack notification.
    """
    try:
        logger.info({"message": "Starting SDR_Agent task", "sender": sender})
        
        # Runner.run is an async function, so we need to run it in an event loop
        with trace("SDR_Agent_Reply_Processing_Task"):
            result = asyncio.run(Runner.run(SDR_Agent, body))
        
        raw_output = result.final_output
        logger.info({"message": "SDR_Agent analysis complete", "sender": sender})

        if raw_output.startswith("```json"):
            cleaned_json_string = raw_output.strip("```json\n").strip("```")
        else:
            cleaned_json_string = raw_output
        
        try:
            analysis_json = json.loads(cleaned_json_string)
            logger.info({
                "message": "Successfully parsed JSON from agent", 
                "classification": analysis_json.get("classification")
            })
            
            # send_slack_notification is async, so we run it in an event loop
            asyncio.run(send_slack_notification(analysis_json, sender, subject))

        except json.JSONDecodeError:
            logger.error({"message": "Failed to parse JSON from agent", "raw_output": raw_output})

    except Exception as e:
        logger.error({"message": "An error occurred in the process_inbound_email task", "error": str(e)})

@celery_app.task
def send_approved_email(to_email: str, subject: str, body: str):
    """
    This background task sends the final approved/edited email.
    """
    logger.info({
        "message": "Starting send_approved_email task",
        "to_email": to_email,
        "subject": subject
    })
    send_single_email(to_email, subject, body)
