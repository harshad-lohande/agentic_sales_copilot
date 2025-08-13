# app/tasks.py

import json
import asyncio
import re
from celery import Celery
from .logging_config import logger, setup_logging
from .database import add_message_to_conversation, get_conversation_history, init_db
from .utils import normalize_subject

setup_logging()
init_db()

from .config import settings
from .reply_agent import SDR_Agent, SdrAnalysis # Import the Pydantic model
from .slack_notifier import send_slack_notification
from .email_utils import send_single_email
from agents import Runner, trace

# Configure Celery to use the Redis URL from our settings
celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL)

# A dedicated task to save the final, approved reply to the database.
@celery_app.task
def add_approved_reply_to_history(prospect_email: str, subject: str, body: str):
    """
    Saves the final, human-approved or edited reply to the conversation history.
    """
    try:
        logger.info({
            "message": "Saving approved reply to conversation history",
            "prospect_email": prospect_email
        })
        # The sender is the sales rep (or the system acting on their behalf)
        add_message_to_conversation(prospect_email, subject, "sales_rep", body)
    except Exception as e:
        logger.error({"message": "Error saving approved reply to history", "error": str(e)})

@celery_app.task
def process_inbound_email(sender: str, subject: str, body: str):
    """
    Saves email to DB, gets full history, runs agent with context, and notifies Slack.
    """
    try:
        # Extract the pure email address from the sender string
        match = re.search(r'<(.+?)>', sender)
        prospect_email = match.group(1) if match else sender

        # Normalize the subject to identify the conversation thread
        normalized_subject = normalize_subject(subject)

        # 1. Add the new message to the conversation history
        add_message_to_conversation(prospect_email, normalized_subject, "prospect", body)
        logger.info({"message": "Saved new message to conversation history", 
                     "prospect_email": prospect_email,
                     "subject": normalized_subject,
                })

        # 2. Get the full conversation history for this specific prospect and subject
        conversation_history_str = get_conversation_history(prospect_email, normalized_subject)
        
        # Determine the correct input for the agent
        # If history is just the first message, use the body. Otherwise, use the full history.
        history = json.loads(conversation_history_str)
        if len(history) <= 1:
            agent_input = body
            logger.info({"message": "First reply in thread. Using email body as agent input.", "prospect_email": prospect_email})
        else:
            agent_input = conversation_history_str
            logger.info({"message": "Continuing conversation. Using full history as agent input.", "prospect_email": prospect_email})
        
        # 3. Run the agent. The result will now be an instance of SdrAnalysis.
        with trace("SDR_Agent_Reply_Processing_Task"):
            result = asyncio.run(Runner.run(SDR_Agent, agent_input))

        analysis_result: SdrAnalysis = result.final_output
        
        logger.info({
            "message": "SDR_Agent analysis complete",
            "prospect_email": prospect_email,
            "classification": analysis_result.classification
        })

        # The output is already a structured object, so no parsing is needed.
        if analysis_result:          
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