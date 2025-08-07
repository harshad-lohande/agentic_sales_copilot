# app/email_utils.py

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, ReplyTo
from .config import settings
from .logging_config import logger
import markdown2

def send_single_email(to_email: str, subject: str, body: str):
    """
    Sends a single email using SendGrid.
    """
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        from_email_with_name = (settings.SENDER_EMAIL, settings.SENDER_NAME)
        reply_to_address = settings.REPLY_TO_EMAIL

        # Convert markdown body to HTML
        html_body = markdown2.markdown(body)

        message = Mail(
            from_email=from_email_with_name,
            to_emails=to_email,
            subject=subject,
            html_content=html_body
        )
        message.reply_to = ReplyTo(reply_to_address)
        
        response = sg.send(message)
        logger.info({
            "message": "Successfully sent single email",
            "to_email": to_email,
            "subject": subject,
            "status_code": response.status_code
        })
        return True
    except Exception as e:
        logger.error({
            "message": "Error sending single email",
            "to_email": to_email,
            "error": str(e)
        })
        return False
