"""
Mail Utility Module

This module provides utility functions for sending emails, specifically for email verification in the authentication 
process. It utilizes the FastAPI Mail library for configuring and sending emails.

Components:
    - `mail_conf`: Configuration object for FastAPI Mail.
    - `send_verification`: Function to send an email verification message.

Dependencies:
    - FastAPI Mail: A library for sending emails using SMTP.
    - Settings: Application-specific configuration stored in `config.general`.

Usage:
    Call `send_verification` with an email address and an email body to send a verification email.

Examples:
    from src.auth.mail_utils import send_verification

    await send_verification(
        email="example@example.com",
        email_body="<p>Verify your email by clicking the link.</p>"
    )
"""


from fastapi_mail import ConnectionConfig, MessageSchema, FastMail

from config.general import settings


"""
Configuration for FastAPI Mail

This configuration object sets up the email service with the following parameters:
    - MAIL_USERNAME: SMTP username for authentication.
    - MAIL_PASSWORD: SMTP password for authentication.
    - MAIL_FROM: Sender email address.
    - MAIL_PORT: Port for the SMTP server.
    - MAIL_SERVER: Address of the SMTP server.
    - MAIL_STARTTLS: Whether STARTTLS should be used (disabled in this configuration).
    - MAIL_SSL_TLS: Whether SSL/TLS should be used (disabled in this configuration).
    - USE_CREDENTIALS: Indicates whether to use credentials for authentication.

Note:
    The configuration values are loaded from the application settings.
"""

mail_conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

async def send_verification(
    email: str, 
    email_body: str
):
    """
    Send a verification email to the specified recipient.

    Args:
        email (str): The recipient's email address.
        email_body (str): The body of the email, formatted as HTML.

    Raises:
        Exception: If there is an error in sending the email.
    """
    message = MessageSchema(
        subject="Email verification",
        recipients=[email],
        body=email_body,
        subtype="html",
    )
    fm = FastMail(mail_conf)
    await fm.send_message(message)