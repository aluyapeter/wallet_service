import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.celery import c_app
from sqlmodel import Session, select
from app.models.core import User, Wallet, Transaction, TransactionType, TransactionStatus
from app.database import engine
import asyncio
from datetime import datetime, timedelta, timezone
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

        message = MIMEMultipart()
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = email_to
        message["Subject"] = subject

        message.attach(MIMEText(html_content, "html"))

        print(f"Connecting to Gmail for {email_to}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls() # Secure the connection (Encrypts the line)
            server.login(smtp_user, smtp_password)
            server.send_message(message)
            
        print(f"Email sent to {email_to}")
        return "Sent"

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return f"Failed: {str(e)}"
    
@c_app.task
def resolve_stuck_withdrawals():
    """
    Scans for PENDING withdrawals older than 5 minutes.
    Checks Paystack status and either Refunds or Confirms them.
    """
    from app.services.paystack import PaystackService

    with Session(engine) as session:
        five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        statement = (
            select(Transaction)
            .where(Transaction.status == TransactionStatus.PENDING)
            .where(Transaction.transaction_type == "withdrawal")
            .where(Transaction.created_at < five_mins_ago)
        )
        stuck_txns = session.exec(statement).all()
        
        if not stuck_txns:
            return "No stuck transactions found."

        paystack = PaystackService()
        processed_count = 0

        loop = asyncio.get_event_loop() 

        for txn in stuck_txns:
            try:
                status = loop.run_until_complete(paystack.verify_transaction(txn.reference))
                
                wallet = session.get(Wallet, txn.wallet_id)
                if not wallet:
                    continue

                if status == "success":
                    txn.status = TransactionStatus.SUCCESS
                    session.add(txn)
                    
                elif status in ["failed", "reversed", "not_found"]:
                    wallet.balance += abs(txn.amount)
                    txn.status = TransactionStatus.FAILED
                    session.add(wallet)
                    session.add(txn)
                    
                session.commit()
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing stuck txn {txn.reference}: {e}")
                session.rollback()

        return f"Resolved {processed_count} stuck transactions."