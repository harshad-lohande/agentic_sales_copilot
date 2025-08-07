# app/slack_notifier.py

import json
import re
import html
from slack_sdk.web.async_client import AsyncWebClient
from .config import settings
from .logging_config import logger

async def send_slack_notification(analysis_json: dict, original_sender: str, original_subject: str):
    """
    Formats the agent's analysis and sends an interactive notification to a Slack channel.
    """
    try:
        client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
        channel_id = settings.SLACK_CHANNEL_ID
        
        # The sender string is often formatted as "Name <email@address.com>"
        # We need to extract just the email address for our button payload.
        cleaned_sender = html.unescape(original_sender)
        prospect_email = cleaned_sender
        email_match = re.search(r'<(.+?)>', cleaned_sender)

        if email_match:
            prospect_email = email_match.group(1)

        classification = analysis_json.get("classification", "N/A")
        summary = analysis_json.get("summary", "No summary provided.")
        draft_reply = analysis_json.get("draft_reply", "No draft reply provided.")

        # --- NEW: Create a data payload for our buttons ---
        # We serialize a dictionary into the button's value string to pass data
        button_payload = {
            "prospect_email": prospect_email,
            "draft_reply": draft_reply,
            "reply_subject": f"Re: {original_subject}"
        }

        await client.chat_postMessage(
            channel=channel_id,
            text=f"New Email Reply from {cleaned_sender}",
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f":email: New Reply from: {cleaned_sender}"}
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Subject:*\n{original_subject}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Classification:*\n`{classification}`"},
                        {"type": "mrkdwn", "text": f"*Summary:*\n{summary}"}
                    ]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Suggested Draft Reply:*\n```{draft_reply}```"}
                },
                {"type": "divider"},
                # --- NEW: Interactive Buttons Block ---
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve & Send"},
                            "style": "primary",
                            "value": json.dumps(button_payload), # Embed our data here
                            "action_id": "approve_send"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Edit & Send"},
                            "value": json.dumps(button_payload),
                            "action_id": "edit_send"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Discard"},
                            "style": "danger",
                            "value": "discard",
                            "action_id": "discard"
                        }
                    ]
                }
            ]
        )
        logger.info({
            "message": "Successfully sent interactive notification to Slack",
            "channel_id": settings.SLACK_CHANNEL_ID,
            "sender": cleaned_sender
        })
    except Exception as e:
        print(f"!!! Error sending Slack notification: {e}")