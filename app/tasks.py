import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.celery import c_app
import os
import socket

@c_app.task
def send_email_task(email_to: str, subject: str, html_content: str):
    try:
        smtp_server_host = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("EMAILS_FROM_EMAIL", smtp_user)
        sender_name = os.getenv("EMAILS_FROM_NAME", "Wallet Service")

        print(f"DEBUG: Resolving IPv4 for {smtp_server_host}...")
        smtp_server_ip = socket.gethostbyname(smtp_server_host)
        print(f"DEBUG: Connecting to {smtp_server_ip} (IPv4) on port {smtp_port}")

        message = MIMEMultipart()
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = email_to
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server_ip, smtp_port, timeout=30) as server:
            server.set_debuglevel(1)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
            
        print(f"SUCCESS: Email sent to {email_to}")
        return "Sent"

    except Exception as e:
        print(f"CRITICAL FAILURE: {str(e)}")
        return f"Failed: {str(e)}"