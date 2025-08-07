# app/main.py

import asyncio
import csv
from dotenv import load_dotenv
from .config import settings
from .logging_config import logger

from agents import Agent, Runner, trace, function_tool
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, ReplyTo

# Load environment variables
load_dotenv()

# --- Tool Definition ---
@function_tool
def send_personalized_bulk_email(subject: str, body_template: str):
    """
    This is the pure Python logic for sending the email campaign using SendGrid.
    """
    logger.info({
        "message": "Running Mail Merge Tool",
        "subject_template": subject
    })
    try:
        # Initialize the SendGrid client
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        # IMPORTANT: Use an email address you have verified as a "Single Sender" in SendGrid
        verified_sender = settings.SENDER_EMAIL

        # Define a reply-to address on your inbound subdomain.
        # The part before the '@' can be anything (e.g., 'replies', 'inbound', 'routing').
        inbound_reply_address = settings.REPLY_TO_EMAIL

        with open(settings.PROSPECTS_CSV_PATH, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            prospects = list(reader)

            for prospect in prospects:
                personalized_body = body_template
                personalized_subject = subject

                for key, value in prospect.items():
                    placeholder_to_find = "{{" + key + "}}"
                    value_to_use = value if value is not None else ""
                    personalized_subject = personalized_subject.replace(placeholder_to_find, value_to_use)
                    personalized_body = personalized_body.replace(placeholder_to_find, value_to_use)

                # Construct the SendGrid Mail object
                message = Mail(
                    from_email=verified_sender,
                    to_emails=prospect['Email'],
                    subject=personalized_subject,
                    html_content=f"<html><body>{personalized_body.replace('\n', '<br>')}</body></html>"
                )

                # Add the Reply-To header to the message.
                message.reply_to = ReplyTo(inbound_reply_address)
                
                response = sg.send(message)
                logger.info({
                    "message": "Successfully sent bulk email to prospect",
                    "prospect_email": prospect['Email'],
                    "status_code": response.status_code
                })
        
        return {"status": "success", "message": f"Emails successfully sent to {len(prospects)} prospects."}
    except Exception as e:
        logger.error({
            "message": "An error occurred in the bulk email tool",
            "error_type": type(e).__name__,
            "error": str(e)
        })
        return {"status": "error", "message": f"Failed to send email campaign due to an internal tool error: {e}"}

# --- Agent Architecture using Handoff ---

async def run_autonomous_sales_workflow():
    """
    This workflow uses a handoff mechanism for better autonomy and specialization.
    """
    
    # 1. Define the Specialist "Sending" Agent
    # This agent does one thing: sends the campaign. It's a perfect candidate for delegation.
    logger.info({"message": "Starting autonomous sales workflow..."})
    sender_instructions = "You are a specialized agent responsible for executing email campaigns. You will receive the subject and body of an email, and your only job is to use the `send_personalized_bulk_email` tool to send it."
    
    campaign_sender_agent = Agent(
        name="Campaign_Sender_Agent",
        instructions=sender_instructions,
        tools=[send_personalized_bulk_email],
        model=settings.CAMAPIGN_SENDER_MODEL,
        # This description is what the manager agent sees when deciding to hand off
        handoff_description="Use this agent to send the final, approved email campaign to the prospect list."
    )

    # 2. Define the Content-Generating Agents (as tools)
    instructions1 = "You are a professional, serious sales agent for SovereignAI, \
            a company that sells agentic AI based solutions to bring autonomy and automation in business processes. \
            You write cold sales emails that directly addressing prospects's pain-points. \
            If you have to, use only following placeholders in your subject line and/or body:  {{Position}}, {{Company}} and {{FirstName}}."
    instructions2 = "You are a humorous, witty sales agent for SovereignAI, \
            a company that sells agentic AI based solutions to bring autonomy and automation in business processes. \
            You write cold sales emails that are likely to get response from a prospect.\
            If you have to, use only following placeholders in your subject line and/or body:  {{Position}}, {{Company}} and {{FirstName}}."
    instructions3 = "You are a busy agent for SovereignAI, \
            a company that sells agentic AI based solutions to bring autonomy and automation in business processes. \
            You write cold sales emails that are concise and to-the-point.\
            If you have to, use only following placeholders in your subject line and/or body:  {{Position}}, {{Company}} and {{FirstName}}."

    sales_agent1 = Agent(name="Professional_Sales_Agent", instructions=instructions1, model=settings.WRITER_AGENT_MODEL)
    sales_agent2 = Agent(name="Engaging_Sales_Agent", instructions=instructions2, model=settings.WRITER_AGENT_MODEL)
    sales_agent3 = Agent(name="Busy_Sales_Agent", instructions=instructions3, model=settings.WRITER_AGENT_MODEL)

    description = "Write the body and subject line for a cold sales email. This body is a template and MUST include placeholders like {{Position}}, {{Company}} and {{FirstName}} for mail merge.\
            Address the email recipient using {{FirstName}} placeholder.\
            Email must be signed-off by Mike, followed by his designation (think about appropriate creative title for a sales person), and finally followed by company name (SovereignAI).\
            Include P.S at the end of body"
    tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=description)
    tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=description)
    tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=description)

    # 3. Define the Autonomous "Manager" Agent
    sales_manager_instructions = """
    You are the master orchestrator of a sales campaign. Your mission is to develop the best email content and then delegate the sending of that content.

    **MANDATORY WORKFLOW:** You must follow these steps in order.

    1.  **Generate Content:** Use all three of your content-generation tools (`Professional_Sales_Agent`, `Engaging_Sales_Agent`, `Busy_Sales_Agent`) to create three distinct email drafts.

    2.  **Select & Finalize:** Review the three drafts. You pick the best cold sales email from the given options. Imagine you are a customer and pick the one you are most likely to respond to. \
    Do not give an explanation; just finalize ONE email that you find the best among the presented options. Then, create a compelling subject line for this final draft.

    3.  **Delegate via Handoff:** This is your final, required action. You MUST hand off the `subject` and the final email `body` to the `Campaign_Sender_Agent`.

    **CRUCIAL RULE:** Your job is NOT complete until you have successfully initiated the handoff to the `Campaign_Sender_Agent`. You must handoff exactly ONE finalized email to the `Campaign_Sender_Agent`.
    """


    sales_manager = Agent(
        name="Sales_Manager",
        instructions=sales_manager_instructions,
        tools=[tool1, tool2, tool3], # The manager only has content tools
        handoffs=[campaign_sender_agent], # It can delegate to the sender agent
        model=settings.MANAGER_AGENT_MODEL
    )

    # 4. Run the autonomous workflow
    # initial_prompt = "It's time to launch a new sales campaign. Please handle the entire process. The email should be from 'Alice' and mention the prospect's role '{{Position}}'."
    initial_prompt = """
    Start the sales campaign by orchestrating the entire process of drafting, finalizing and sending cold sales email.
    """

    with trace("Autonomous_Sales_Campaign_with_Handoff"):
        result = await Runner.run(sales_manager, initial_prompt)
    
    logger.info({
        "message": "Workflow Complete",
        "final_output": result.final_output
    })


if __name__ == "__main__":
    asyncio.run(run_autonomous_sales_workflow())