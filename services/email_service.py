"""
SMTP Email Dispatch Service.
Sends formal academic collaboration pitches.
Supports mock transmission if SMTP credentials are not configured in settings.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings
from core.logger import logger

class EmailService:
    @staticmethod
    def send_pitch(subject: str, body: str, recipients: list[str]) -> bool:
        """
        Sends the email draft using smtplib to actual recipient list.
        Falls back to mock mode if SMTP settings are missing.
        """
        if not settings.has_smtp:
            logger.warning("[EmailService] SMTP credentials not configured. Running in MOCK mode.")
            logger.info(f"[EmailService] [MOCK SEND] Subject: {subject}")
            logger.info(f"[EmailService] [MOCK SEND] Recipients: {', '.join(recipients)}")
            logger.info(f"[EmailService] [MOCK SEND] Body:\n{body}")
            return True

        logger.info(f"[EmailService] Sending email to {', '.join(recipients)} via SMTP...")
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            # Establish SMTP Connection
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            # Send email
            server.sendmail(settings.SMTP_FROM, recipients, msg.as_string())
            server.quit()
            
            logger.info("[EmailService] Email successfully sent.")
            return True
        except Exception as e:
            logger.error(f"[EmailService] SMTP Transmission failed: {e}")
            return False
