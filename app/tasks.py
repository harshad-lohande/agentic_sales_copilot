import asyncio
import re
from celery import Celery
from agents import Runner, trace

from .config import settings
from .logging_config import (
    logger,
    setup_logging,
    get_correlation_id,
    set_correlation_id,
)
from .database import (
    add_message_to_conversation,
    get_conversation_history,
    init_db,
    mark_research_performed,
)
from .utils import normalize_subject, get_prospect_details_by_email
from .slack_notifier import send_slack_notification
from .email_utils import send_single_email
from .reply_agent import (
    SDR_Agent,
    Research_Agent,
    Personalized_Writer_Agent,
    SdrAnalysis,
    ResearchOutput,
    FinalReply,
)
from .celery_instrumentation import ContextTask

setup_logging()
init_db()

celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL)
celery_app.Task = ContextTask


def _ensure_correlation(correlation_id):
    if correlation_id:
        set_correlation_id(correlation_id)
    else:
        set_correlation_id(get_correlation_id())


@celery_app.task
def add_approved_reply_to_history(
    prospect_email: str, subject: str, body: str, correlation_id=None
):
    _ensure_correlation(correlation_id)
    try:
        logger.info(
            {
                "message": "Saving approved reply to history",
                "prospect_email": prospect_email,
            }
        )
        add_message_to_conversation(prospect_email, subject, "sales_rep", body)
    except Exception as e:
        logger.error({"message": "Error saving approved reply", "error": str(e)})


@celery_app.task
def process_inbound_email(sender: str, subject: str, body: str, correlation_id=None):
    _ensure_correlation(correlation_id)
    try:
        match = re.search(r"<(.+?)>", sender)
        prospect_email = match.group(1) if match else sender
        normalized_subject = normalize_subject(subject)

        add_message_to_conversation(
            prospect_email, normalized_subject, "prospect", body
        )
        conversation = get_conversation_history(prospect_email, normalized_subject)
        if not conversation:
            logger.error(
                {
                    "message": "Could not find or create conversation record",
                    "prospect_email": prospect_email,
                }
            )
            return

        conversation_history_str = conversation.conversation_history

        with trace("Step1_Initial_SDR_Analysis"):
            run_result = asyncio.run(Runner.run(SDR_Agent, conversation_history_str))
            initial_result: SdrAnalysis = run_result.final_output

        logger.info(
            {
                "message": "Initial analysis complete",
                "prospect_email": prospect_email,
                "classification": initial_result.classification,
                "research_performed": conversation.research_performed,
            }
        )

        final_draft_for_slack = initial_result.draft_reply

        if (
            initial_result.classification in ["POSITIVE_INTEREST", "QUESTION"]
            and not conversation.research_performed
        ):
            logger.info(
                {
                    "message": "Qualified lead and no prior research. Triggering research workflow.",
                    "prospect_email": prospect_email,
                }
            )

            prospect_details = get_prospect_details_by_email(prospect_email)
            if prospect_details:
                research_input = (
                    f"FirstName: {prospect_details.get('FirstName', '')}, "
                    f"LastName: {prospect_details.get('LastName', '')}, "
                    f"Company: {prospect_details.get('Company', '')}"
                )

                logger.info(
                    {
                        "message": "Triggering research.",
                        "research_input": research_input,
                    }
                )

                with trace("Step2a_Lead_Research"):
                    research_run_result = asyncio.run(
                        Runner.run(Research_Agent, research_input)
                    )
                    research_output: ResearchOutput = research_run_result.final_output

                logger.info(
                    {
                        "message": "Research complete",
                        "findings": research_output.research_summary,
                    }
                )

                writer_input = (
                    f"Conversation History: {conversation_history_str}\n"
                    f"Research Summary: {research_output.research_summary}"
                )
                with trace("Step2b_Personalized_Writing"):
                    writer_run_result = asyncio.run(
                        Runner.run(Personalized_Writer_Agent, writer_input)
                    )
                    final_reply_output: FinalReply = writer_run_result.final_output

                final_draft_for_slack = final_reply_output.draft_reply
                mark_research_performed(prospect_email, normalized_subject)
                logger.info(
                    {
                        "message": "Personalized draft created and research flag set",
                        "prospect_email": prospect_email,
                    }
                )
            else:
                logger.warning(
                    {
                        "message": "Prospect not found in CSV. Skipping research.",
                        "prospect_email": prospect_email,
                    }
                )
        else:
            logger.info(
                {
                    "message": "Using standard draft (not qualified or already researched).",
                    "prospect_email": prospect_email,
                }
            )

        final_analysis_for_slack = {
            "classification": initial_result.classification,
            "summary": initial_result.summary,
            "draft_reply": final_draft_for_slack,
        }
        asyncio.run(send_slack_notification(final_analysis_for_slack, sender, subject))

    except Exception as e:
        logger.error(
            {
                "message": "Error in process_inbound_email task",
                "error": str(e),
                "sender": sender,
            }
        )


@celery_app.task
def send_approved_email(to_email: str, subject: str, body: str, correlation_id=None):
    _ensure_correlation(correlation_id)
    logger.info({"message": "Executing send_approved_email task", "to_email": to_email})
    send_single_email(to_email, subject, body)
