import json
import aiohttp
from fastapi import FastAPI, Request, Response, status
from contextlib import asynccontextmanager
from slack_sdk.web.async_client import AsyncWebClient

from app.config import settings
from app.tasks import (
    process_inbound_email,
    send_approved_email,
    add_approved_reply_to_history,
)
from app.database import init_db
from app.logging_config import logger, setup_logging, set_correlation_id, get_correlation_id
from app.middleware import CorrelationIdMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}

slack_client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)

async def update_slack_message(response_url: str, blocks: list):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(response_url, json={"blocks": blocks, "replace_original": "true"})
    except Exception as e:
        logger.error({"message": "Error updating Slack message", "error": str(e)})

@app.post("/webhook/inbound-email")
async def receive_inbound_email(request: Request):
    try:
        cid = get_correlation_id()
        form_data = await request.form()
        sender = form_data.get("from")
        subject = form_data.get("subject")
        body = form_data.get("text")

        logger.info({
            "message": "Inbound email webhook received, queueing for processing.",
            "sender": sender,
            "subject": subject
        })

        if body:
            process_inbound_email.delay(sender, subject, body, correlation_id=cid)

        return {"status": "success", "message": "Email reply successfully queued."}
    except Exception as e:
        logger.error({"message": "Inbound email webhook error", "error": str(e)})
        return {"status": "error", "message": str(e)}, 500

@app.post("/slack/actions")
async def slack_action_handler(request: Request):
    try:
        cid = get_correlation_id()
        form_data = await request.form()
        payload = json.loads(form_data.get("payload"))
        interaction_type = payload.get("type")
        user_name = payload["user"]["name"]

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
                    logger.info({**log_context, "message": "Approve & Send clicked"})
                    send_approved_email.delay(
                        to_email=prospect_email,
                        subject=reply_subject,
                        body=draft_reply,
                        correlation_id=cid
                    )
                    add_approved_reply_to_history.delay(
                        prospect_email, reply_subject, draft_reply, correlation_id=cid
                    )
                    confirmation_blocks = payload["message"]["blocks"][:-1]
                    confirmation_blocks.append({
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": f":white_check_mark: Approved and sent by @{user_name}"}],
                    })
                    await update_slack_message(response_url, confirmation_blocks)

                elif action_id == "edit_send":
                    logger.info({**log_context, "message": "Edit & Send clicked"})
                    trigger_id = payload.get("trigger_id")
                    private_metadata = {
                        "prospect_email": prospect_email,
                        "reply_subject": reply_subject,
                        "response_url": response_url,
                        "correlation_id": cid
                    }
                    await slack_client.views_open(
                        trigger_id=trigger_id,
                        view={
                            "type": "modal",
                            "callback_id": "submit_edited_email",
                            "title": {"type": "plain_text", "text": "Edit & Send Reply"},
                            "submit": {"type": "plain_text", "text": "Send"},
                            "close": {"type": "plain_text", "text": "Cancel"},
                            "private_metadata": json.dumps(private_metadata),
                            "blocks": [
                                {
                                    "type": "input",
                                    "block_id": "edited_reply_block",
                                    "element": {
                                        "type": "plain_text_input",
                                        "action_id": "edited_reply_input",
                                        "multiline": True,
                                        "initial_value": draft_reply,
                                    },
                                    "label": {"type": "plain_text", "text": "Email Body"},
                                }
                            ],
                        },
                    )

            elif action_id == "discard":
                logger.info({**log_context, "message": "Discard clicked"})
                confirmation_blocks = payload["message"]["blocks"][:-1]
                confirmation_blocks.append({
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f":wastebasket: Discarded by @{user_name}"}],
                })
                await update_slack_message(response_url, confirmation_blocks)

        elif interaction_type == "view_submission":
            private_metadata = json.loads(payload["view"]["private_metadata"])
            correlation_id = private_metadata.get("correlation_id")
            if correlation_id:
                set_correlation_id(correlation_id)
            prospect_email = private_metadata["prospect_email"]
            response_url = private_metadata["response_url"]
            reply_subject = private_metadata["reply_subject"]
            edited_text = payload["view"]["state"]["values"]["edited_reply_block"]["edited_reply_input"]["value"]
            logger.info({
                "message": "Edit modal submitted",
                "prospect_email": prospect_email
            })
            send_approved_email.delay(
                to_email=prospect_email,
                subject=reply_subject,
                body=edited_text,
                correlation_id=correlation_id or cid
            )
            add_approved_reply_to_history.delay(
                prospect_email, reply_subject, edited_text, correlation_id=correlation_id or cid
            )
            confirmation_blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f":white_check_mark: *Edited reply sent to {prospect_email}*"},
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": "```[REDACTED_CONTENT]```"}],
                },
            ]
            await update_slack_message(response_url, confirmation_blocks)
        return Response(status_code=200)

    except Exception as e:
        logger.error({"message": "Error handling Slack action", "error": str(e)})
        return Response(status_code=500)