# webhook_server.py

import uvicorn
import asyncio
import json
import aiohttp
from fastapi import FastAPI, Form, Request, Response
from app.logging_config import logger

from slack_sdk.web.async_client import AsyncWebClient
from app.email_utils import send_single_email
from app.reply_agent import SDR_Agent
from agents import Runner, trace
from app.slack_notifier import send_slack_notification
from app.config import settings
from dotenv import load_dotenv
load_dotenv(override=True)

app = FastAPI()

# Initialize Slack client for use in action handlers
slack_client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)

# Helper function to update the Slack message
async def update_slack_message(response_url: str, blocks: list):
    """Sends a POST request to the response_url to update the original message."""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(response_url, json={"blocks": blocks, "replace_original": "true"})
    except Exception as e:
        logger.error({"message": "Error updating Slack message", "error": str(e)})


@app.post("/webhook/inbound-email")
async def receive_inbound_email(request: Request):
    """
    This endpoint will receive the inbound email data from Resend's webhook.
    It expects the data to be in multipart/form-data format.
    """
    try:
        # Resend sends data as a form. We parse it here.
        form_data = await request.form()
        
        sender = form_data.get('from')
        subject = form_data.get('subject')
        body = form_data.get('text') # 'text' for plain text, 'html' for HTML
        
        logger.info({
            "message": "Inbound email webhook received",
            "sender": sender,
            "subject": subject
        })

        # We now trigger the SDR_Agent with the body of the reply.
        if body:
            logger.info({"message": "Triggering SDR_Agent to process reply..."})
            with trace("SDR_Agent_Reply_Processing"):
                # The email body is the prompt for our agent
                result = await Runner.run(SDR_Agent, body)

            raw_output = result.final_output
            logger.info({"message": "SDR_Agent analysis complete"})
            # We pretty-print the JSON output from the agent
            if raw_output.startswith("```json"):
                cleaned_json_string = raw_output.strip("```json\n").strip("```")
            else:
                cleaned_json_string = raw_output
            
            try:
                # Attempt to parse the cleaned string
                analysis_json = json.loads(cleaned_json_string)
                logger.info({
                    "message": "Successfully parsed JSON from agent output",
                    "classification": analysis_json.get("classification")
                })
                
                # Send the successfully parsed analysis to Slack
                await send_slack_notification(analysis_json, sender, subject)

            except json.JSONDecodeError:
                # This will catch errors if the string is still not valid JSON after cleaning
                logger.error({
                    "message": "Failed to parse JSON from agent output",
                    "raw_output": raw_output
                })
        
        # We must return a 200 OK status to let Resend know we received it.
        return {"status": "success", "message": "Email reply received and processed."}

    except Exception as e:
        logger.error({"message": "An error occurred in inbound email webhook", "error": str(e)})
        return {"status": "error", "message": str(e)}, 500


@app.post("/slack/actions")
async def slack_action_handler(request: Request):
    try:
        form_data = await request.form()
        payload = json.loads(form_data.get("payload"))
        
        interaction_type = payload.get("type")
        user_name = payload["user"]["name"]

        # --- Case 1: A user clicked a button on the message ---
        if interaction_type == "block_actions":
            response_url = payload["response_url"]
            action = payload["actions"][0]
            action_id = action["action_id"]

            log_context = {"action_id": action_id, "user_name": user_name}

            if action_id in ["approve_send", "edit_send"]:
                action_value = json.loads(action["value"])
                prospect_email = action_value["prospect_email"]
                draft_reply = action_value["draft_reply"]
                reply_subject = action_value["reply_subject"]
                log_context["prospect_email"] = prospect_email

                if action_id == "approve_send":
                    logger.info({**log_context, "message": "Approve & Send button clicked"})
                    send_single_email(to_email=prospect_email, subject=reply_subject, body=draft_reply)   
                    # NEW: Update the original message to show confirmation
                    confirmation_blocks = payload["message"]["blocks"][:-1] # Get all blocks except the action block
                    confirmation_blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f":white_check_mark: Approved and sent by @{user_name}"}]})
                    await update_slack_message(response_url, confirmation_blocks)

                elif action_id == "edit_send":
                    logger.info({**log_context, "message": "Edit & Send button clicked, opening modal"})
                    trigger_id = payload.get("trigger_id")
                    # NEW: We must pass the response_url to the modal so we can use it on submission
                    private_metadata = {
                        "prospect_email": prospect_email, 
                        "reply_subject": reply_subject,
                        "response_url": response_url # Pass the URL through
                    }
                    
                    await slack_client.views_open(
                        trigger_id=trigger_id,
                        view={
                            "type": "modal", "callback_id": "submit_edited_email",
                            "title": {"type": "plain_text", "text": "Edit & Send Reply"},
                            "submit": {"type": "plain_text", "text": "Send"}, "close": {"type": "plain_text", "text": "Cancel"},
                            "private_metadata": json.dumps(private_metadata), # Embed our enhanced metadata
                            "blocks": [
                                {
                                    "type": "input", "block_id": "edited_reply_block",
                                    "element": {"type": "plain_text_input", "action_id": "edited_reply_input", "multiline": True, "initial_value": draft_reply},
                                    "label": {"type": "plain_text", "text": "Email Body"}
                                }
                            ]
                        }
                    )

            elif action_id == "discard":
                logger.info({**log_context, "message": "Discard button clicked"})
                # NEW: Update the original message to show it was discarded
                confirmation_blocks = payload["message"]["blocks"][:-1] # Get all blocks except the action block
                confirmation_blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f":wastebasket: Discarded by @{user_name}"}]})
                await update_slack_message(response_url, confirmation_blocks)
        
        # --- Case 2: A user submitted the editing modal ---
        elif interaction_type == "view_submission":
            # NEW: Extract the response_url from the metadata we passed
            private_metadata = json.loads(payload["view"]["private_metadata"])
            prospect_email = private_metadata["prospect_email"]
            logger.info({
                "message": "Edit modal submitted",
                "user_name": user_name,
                "prospect_email": prospect_email
            })
            response_url = private_metadata["response_url"]
            reply_subject = private_metadata["reply_subject"]           
            edited_text = payload["view"]["state"]["values"]["edited_reply_block"]["edited_reply_input"]["value"]
            send_single_email(to_email=prospect_email, subject=reply_subject, body=edited_text)
            
            # Create a confirmation message that includes the edited, sent text
            confirmation_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":white_check_mark: *Edited reply sent to {prospect_email} by @{user_name}*"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"```{edited_text}```"
                        }
                    ]
                }
            ]

            await update_slack_message(response_url, confirmation_blocks)
            
        return Response(status_code=200)

    except Exception as e:
        logger.error({"message": "Error handling Slack action", "error": str(e)})
        return Response(status_code=500)


if __name__ == "__main__":
    uvicorn.run("webhook_server:app", host="0.0.0.0", port=8000, reload=True)