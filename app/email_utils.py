# app/email_utils.py

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, ReplyTo
from .config import settings
from .logging_config import logger # Import the logger

def send_single_email(to_email: str, subject: str, body: str):
    """
    Sends a single email using SendGrid.
    """
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        
        from_email = settings.SENDER_EMAIL
        reply_to_address = settings.REPLY_TO_EMAIL

        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=f"<html><body>{body.replace('\n', '<br>')}</body></html>"
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
