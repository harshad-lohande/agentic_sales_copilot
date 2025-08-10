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
    campaign_sender_agent = Agent(name="Campaign_Sender_Agent", instructions=sender_instructions, tools=[send_personalized_bulk_email], model=settings.CAMAPIGN_SENDER_MODEL, handoff_description="Use this agent to send the final, approved email campaign to the prospect list.")
    
    instructions1 = f"""You are a professional, serious sales agent for SovereignAI.
            A company that sells agentic AI based solutions to bring autonomy and automation in business processes.
            You write cold sales emails that directly addressing prospects's pain-points.
            This email is a template and MUST include placeholders like {{{{Position}}}}, {{{{Company}}}} and {{{{FirstName}}}} in subject and/or body for mail merge.
            Address the email recipient using {{{{FirstName}}}} placeholder.
            Email must be signed-off by {settings.SALES_REP_NAME}, followed by his designation (e.g. Sales Development Representative), and finally followed by company name (SovereignAI).
            Include P.S at the end of body."""
    instructions2 = f"""You are a humorous, witty sales agent for SovereignAI.
            A company that sells agentic AI based solutions to bring autonomy and automation in business processes.
            You write cold sales emails that are likely to get response from a prospect.
            This email is a template and MUST include placeholders like {{{{Position}}}}, {{{{Company}}}} and {{{{FirstName}}}} in subject and/or body for mail merge.
            Address the email recipient using {{{{FirstName}}}} placeholder.
            Email must be signed-off by {settings.SALES_REP_NAME}, followed by his designation (e.g. Sales Development Representative), and finally followed by company name (SovereignAI).
            Include P.S at the end of body."""
    instructions3 = f"""You are a busy agent for SovereignAI.
            A company that sells agentic AI based solutions to bring autonomy and automation in business processes.
            You write cold sales emails that are concise and to-the-point.
            This email is a template and MUST include placeholders like {{{{Position}}}}, {{{{Company}}}} and {{{{FirstName}}}} in subject and/or body for mail merge.
            Address the email recipient using {{{{FirstName}}}} placeholder.
            Email must be signed-off by {settings.SALES_REP_NAME}, followed by his designation (e.g. Sales Development Representative), and finally followed by company name (SovereignAI).
            Include P.S at the end of body."""

    
    sales_agent1 = Agent(name="Professional_Sales_Agent", instructions=instructions1, model=settings.WRITER_AGENT_MODEL)
    sales_agent2 = Agent(name="Engaging_Sales_Agent", instructions=instructions2, model=settings.WRITER_AGENT_MODEL)
    sales_agent3 = Agent(name="Busy_Sales_Agent", instructions=instructions3, model=settings.WRITER_AGENT_MODEL)
    
    description = """Write a complete cold sales email, including a subject line and a body."""

    tool1 = sales_agent1.as_tool(tool_name="Professional_Sales_Agent", tool_description=description)
    tool2 = sales_agent2.as_tool(tool_name="Engaging_Sales_Agent", tool_description=description)
    tool3 = sales_agent3.as_tool(tool_name="Busy_Sales_Agent", tool_description=description)

    # Create a new, specialized Selector Agent
    selector_instructions = """
    You are a decisive expert. You will be given a list of email drafts.
    Your SOLE task is to choose the single best email from the options.
    Imagine you are a customer and pick the one you are most likely to respond to.
    You MUST respond with ONLY the full text of the winning email (including its subject and body).
    Do not add any explanation, preamble, or formatting.
    """
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
    sales_manager_instructions = """
    You are an expert orchestrator. Your purpose is to generate multiple email options, use a specialist to select the best one, and then delegate the sending of that single email.

    **Your operational protocol is as follows:**

    1.  **GENERATE DRAFTS:** Call all three of your content-generation tools (`Professional_Sales_Agent`, `Engaging_Sales_Agent`, `Busy_Sales_Agent`) to get three complete email options.

    2.  **SELECT THE WINNER:** Combine all three drafts into a single text block. Then, you MUST use the `Email_Selector` tool to choose the single best email from the drafts.

    3.  **PARSE THE WINNER:** From the selector tool's output, you must extract the `subject` and the `body_template` of the winning email.

    4.  **EXECUTE HANDOFF:** You must hand off the extracted `subject` and `body_template` of the single winning email to the `Campaign_Sender_Agent`.

    **SUCCESS CONDITION:** Your only successful output is the confirmation message from the `Campaign_Sender_Agent` after you have handed off the single, selected task.
    """
    sales_manager = Agent(
        name="Sales_Manager",
        instructions=sales_manager_instructions,
        tools=[tool1, tool2, tool3, selector_tool], # Add the new selector tool
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
