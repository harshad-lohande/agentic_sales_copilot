# app/main.py

import asyncio
import csv
from dotenv import load_dotenv
from .config import settings
from .logging_config import logger, setup_logging
setup_logging()

import markdown2
from agents import Agent, Runner, trace, function_tool
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, ReplyTo
from .prompt_loader import load_prompt

load_dotenv()

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
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        from_email_with_name = (settings.SENDER_EMAIL, settings.SENDER_NAME)
        inbound_reply_address = settings.REPLY_TO_EMAIL

        with open(settings.PROSPECTS_CSV_PATH, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            prospects = list(reader)

            for prospect in prospects:
                personalized_body_md = body_template
                personalized_subject = subject

                for key, value in prospect.items():
                    # This prevents errors if the CSV has trailing commas.
                    if key is None:
                        continue
                    placeholder_to_find = "{{" + key + "}}"
                    value_to_use = value if value is not None else ""
                    personalized_subject = personalized_subject.replace(placeholder_to_find, value_to_use)
                    personalized_body_md = personalized_body_md.replace(placeholder_to_find, value_to_use)

                personalized_body_html = markdown2.markdown(personalized_body_md)

                message = Mail(
                    from_email=from_email_with_name,
                    to_emails=prospect['Email'],
                    subject=personalized_subject,
                    html_content=personalized_body_html
                )
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

async def run_autonomous_sales_workflow():
    logger.info({"message": "Starting autonomous sales workflow..."})
    
    sender_instructions = "You are a specialized agent responsible for executing email campaigns. You will receive the subject and body of an email, and your only job is to use the `send_personalized_bulk_email` tool to send it."
    campaign_sender_agent = Agent(name="Campaign_Sender_Agent", instructions=sender_instructions, tools=[send_personalized_bulk_email], model=settings.CAMPAIGN_SENDER_MODEL, handoff_description="Use this agent to send the final, approved email campaign to the prospect list.")
    
    # Using f-strings to inject settings directly into the loaded prompts
    instructions1 = load_prompt("professional_sales_agent.txt").format(sales_rep_name=settings.SALES_REP_NAME)
    instructions2 = load_prompt("engaging_sales_agent.txt").format(sales_rep_name=settings.SALES_REP_NAME)
    instructions3 = load_prompt("busy_sales_agent.txt").format(sales_rep_name=settings.SALES_REP_NAME)

    
    sales_agent1 = Agent(name="Professional_Sales_Agent", instructions=instructions1, model=settings.WRITER_AGENT_MODEL)
    sales_agent2 = Agent(name="Engaging_Sales_Agent", instructions=instructions2, model=settings.WRITER_AGENT_MODEL)
    sales_agent3 = Agent(name="Busy_Sales_Agent", instructions=instructions3, model=settings.WRITER_AGENT_MODEL)
    
    description = """Write a complete cold sales email, including a subject line and a body."""

    tool1 = sales_agent1.as_tool(tool_name="Professional_Sales_Agent", tool_description=description)
    tool2 = sales_agent2.as_tool(tool_name="Engaging_Sales_Agent", tool_description=description)
    tool3 = sales_agent3.as_tool(tool_name="Busy_Sales_Agent", tool_description=description)

    # Create a new, specialized Selector Agent
    selector_instructions = load_prompt("email_selector.txt")
    email_selector_agent = Agent(
        name="Email_Selector_Agent",
        instructions=selector_instructions,
        model=settings.MANAGER_AGENT_MODEL # Use a powerful model for decision making
    )
    selector_tool = email_selector_agent.as_tool(
        tool_name="Email_Selector",
        tool_description="Use this tool to select the single best email draft from a list of options."
    )

    # Update the Sales Manager's instructions and tools
    sales_manager_instructions = load_prompt("sales_manager.txt")
    sales_manager = Agent(
        name="Sales_Manager",
        instructions=sales_manager_instructions,
        tools=[tool1, tool2, tool3, selector_tool],
        handoffs=[campaign_sender_agent],
        model=settings.MANAGER_AGENT_MODEL
    )

    initial_prompt = """
    You are master orchestrator for running email campaign for SovereignAI. A company that sells agentic AI based solutions to bring autonomy and automation in business processes.
    Target companies or businesses that are in tech industry and looking for AI automation to increase their productivity.
    Start the sales campaign by orchestrating the entire process of drafting, finalizing and sending cold sales email.
    """

    with trace("Autonomous_Sales_Campaign_with_Handoff_v3"):
        result = await Runner.run(sales_manager, initial_prompt)
    
    logger.info({
        "message": "Workflow Complete. Finalized cold sales email sent to prospects"
    })

if __name__ == "__main__":
    asyncio.run(run_autonomous_sales_workflow())
