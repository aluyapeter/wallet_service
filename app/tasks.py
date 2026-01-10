import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.celery import c_app
import os

@c_app.task
def send_email_task(email_to: str, subject: str, html_content: str):
    """
    Sends an email using Gmail SMTP via a background worker.
    """
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("EMAILS_FROM_EMAIL")
        sender_name = os.getenv("EMAILS_FROM_NAME")

        print(f"DEBUG: Attempting to connect to '{smtp_server}' on port {smtp_port}")

        message = MIMEMultipart()
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = email_to
        message["Subject"] = subject

        message.attach(MIMEText(html_content, "html"))

        print(f"Connecting to Gmail for {email_to}...")
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.set_debuglevel(1)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
            
        print(f"Email sent to {email_to}")
        return "Sent"

    except Exception as e:
        print(f"CRITICAL FAILURE: {str(e)}")
        if not smtp_server:
            print("ERROR: SMTP_SERVER variable is None/Empty in the Worker process!")
        return f"Failed: {str(e)}"