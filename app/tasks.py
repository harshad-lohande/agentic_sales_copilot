# app/tasks.py

import json
import asyncio
import re
from celery import Celery
from .logging_config import logger, setup_logging
from .database import add_message_to_conversation, get_conversation_history, init_db

setup_logging()
init_db()

from .config import settings
from .reply_agent import SDR_Agent, SdrAnalysis # Import the Pydantic model
from .slack_notifier import send_slack_notification
from .email_utils import send_single_email
from agents import Runner, trace

# Configure Celery to use the Redis URL from our settings
celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL)

@celery_app.task
def process_inbound_email(sender: str, subject: str, body: str):
    """
    Saves email to DB, gets full history, runs agent with context, and notifies Slack.
    """
    try:
        # Extract the pure email address from the sender string
        match = re.search(r'<(.+?)>', sender)
        prospect_email = match.group(1) if match else sender

        # 1. Add the new message to the conversation history
        add_message_to_conversation(prospect_email, "prospect", body)
        logger.info({"message": "Saved new message to conversation history", "prospect_email": prospect_email})

        # 2. Get the full conversation history
        conversation_history_str = get_conversation_history(prospect_email)
        
        logger.info({"message": "Starting SDR_Agent task with full conversation history", "prospect_email": prospect_email})
        
        # 3. Run the agent. The result will now be an instance of SdrAnalysis.
        with trace("SDR_Agent_Reply_Processing_Task"):
            result = asyncio.run(Runner.run(SDR_Agent, conversation_history_str))

        logger.info({"SDR agent response": result.final_output})

        analysis_result: SdrAnalysis = result.final_output

        logger.info({"analysis_result": analysis_result})
        
        logger.info({
            "message": "SDR_Agent analysis complete",
            "prospect_email": prospect_email,
            "classification": analysis_result.classification
        })

        # The output is already a structured object, so no parsing is needed.
        if analysis_result:
            draft_reply = analysis_result.draft_reply
            if draft_reply:
                add_message_to_conversation(prospect_email, "ai_agent_suggestion", draft_reply)
            
            # Convert the Pydantic model to a dictionary for the slack notifier
            analysis_json = analysis_result.model_dump()
            asyncio.run(send_slack_notification(analysis_json, sender, subject))

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