# app/tasks.py (Updated with Conversation History)

import json
import asyncio
import re
from celery import Celery
from .logging_config import logger, setup_logging
from .database import add_message_to_conversation, get_conversation_history
from .database import init_db

setup_logging()
init_db()

from .config import settings
from .reply_agent import SDR_Agent
from .slack_notifier import send_slack_notification
from .email_utils import send_single_email
from agents import Runner, trace

# Configure Celery to use the Redis URL from our settings
celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL)

def parse_agent_json_output(raw_output: str) -> dict | None:
    """
    Cleans and parses a JSON string from an agent's raw output.
    """
    logger.debug(f"Raw agent output to parse: {raw_output}")
    if raw_output.startswith("```json"):
        cleaned_json_string = raw_output.strip("```json\n").strip("```")
    else:
        cleaned_json_string = raw_output

    try:
        analysis_json = json.loads(cleaned_json_string)
        logger.info({
            "message": "Successfully parsed JSON from agent output",
            "classification": analysis_json.get("classification")
        })
        return analysis_json
    except json.JSONDecodeError:
        logger.error({
            "message": "Failed to parse JSON from agent output",
            "raw_output": raw_output
        })
        return None

@celery_app.task
def process_inbound_email(sender: str, subject: str, body: str):
    """
    Saves email to DB, gets full history, runs agent with context, and notifies Slack.
    """
    try:
        # Extract the pure email address from the sender string (e.g., "John Doe <john@example.com>")
        match = re.search(r'<(.+?)>', sender)
        prospect_email = match.group(1) if match else sender

        # 1. Add the new incoming message to the conversation history
        add_message_to_conversation(prospect_email, "prospect", body)
        logger.info({"message": "Saved new message to conversation history", "prospect_email": prospect_email})

        # 2. Get the full conversation history from the database
        conversation_history_str = get_conversation_history(prospect_email)
        
        logger.info({"message": "Starting SDR_Agent task with full conversation history", "prospect_email": prospect_email})
        
        # 3. Run the agent with the full history as the prompt for context
        with trace("SDR_Agent_Reply_Processing_Task"):
            result = asyncio.run(Runner.run(SDR_Agent, conversation_history_str))
        
        raw_output = result.final_output
        logger.info({"message": "SDR_Agent analysis complete", "prospect_email": prospect_email})

        analysis_json = parse_agent_json_output(raw_output)
        
        if analysis_json:
            # 4. Also save the agent's suggested reply to the history for complete context
            draft_reply = analysis_json.get("draft_reply", "")
            if draft_reply:
                add_message_to_conversation(prospect_email, "ai_agent_suggestion", draft_reply)
            
            # 5. Send the interactive notification to Slack
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