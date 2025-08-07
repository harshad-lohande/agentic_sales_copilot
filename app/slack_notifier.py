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
        
        cleaned_sender = html.unescape(original_sender)
        
        # Parse name and email for better formatting
        sender_name = cleaned_sender
        prospect_email = ""
        
        email_match = re.search(r'<(.+?)>', cleaned_sender)
        if email_match:
            prospect_email = email_match.group(1)
            sender_name = cleaned_sender.split('<')[0].strip()

        classification = analysis_json.get("classification", "N/A")
        summary = analysis_json.get("summary", "No summary provided.")
        draft_reply = analysis_json.get("draft_reply", "No draft reply provided.")

        # Check if the subject already starts with "Re: " (case-insensitive)
        if original_subject.lower().startswith('re: '):
            reply_subject = original_subject
        else:
            reply_subject = f"Re: {original_subject}"

        button_payload = {
            "prospect_email": prospect_email,
            "draft_reply": draft_reply,
            "reply_subject": reply_subject
        }

        await client.chat_postMessage(
            channel=settings.SLACK_CHANNEL_ID,
            text=f"New Email Reply from {sender_name}",
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": ":email: New Email Reply"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*From:*\n{sender_name}"},
                        {"type": "mrkdwn", "text": f"*Email:*\n<mailto:{prospect_email}|{prospect_email}>"}
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Subject:*\n{original_subject}"}
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
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "Approve & Send"}, "style": "primary", "value": json.dumps(button_payload), "action_id": "approve_send"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Edit & Send"}, "value": json.dumps(button_payload), "action_id": "edit_send"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Discard"}, "style": "danger", "value": "discard", "action_id": "discard"}
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
        logger.error({
            "message": "Error sending Slack notification",
            "error": str(e)
        })
