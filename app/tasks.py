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
        # 1. Load Config
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("EMAILS_FROM_EMAIL")
        sender_name = os.getenv("EMAILS_FROM_NAME")

        # 2. Build the Email
        message = MIMEMultipart()
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = email_to
        message["Subject"] = subject

        # Attach HTML content
        message.attach(MIMEText(html_content, "html"))

        # 3. Connect to Gmail & Send
        print(f"📧 Connecting to Gmail for {email_to}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls() # Secure the connection (Encrypts the line)
            server.login(smtp_user, smtp_password)
            server.send_message(message)
            
        print(f"✅ Email sent to {email_to}")
        return "Sent"

    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return f"Failed: {str(e)}"