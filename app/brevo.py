"""
Thin wrapper around Brevo's transactional email API. No SDK dependency --
it's a single JSON POST, so `requests` (already a dependency) is enough.
"""
import requests
from app import app

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to_email, subject, html_content):
    """
    Sends one HTML email via Brevo. Raises requests.HTTPError on failure
    so callers can log/skip per-recipient without the whole batch dying.
    """
    api_key = app.config["BREVO_API_KEY"]
    sender_email = app.config["BREVO_SENDER_EMAIL"]
    sender_name = app.config["BREVO_SENDER_NAME"]

    response = requests.post(
        BREVO_SEND_URL,
        json={
            "sender": {"name": sender_name, "email": sender_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content,
        },
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
