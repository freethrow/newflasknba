from __future__ import annotations

import os


def send_password_reset(to_username: str, reset_url: str) -> None:
    """Send a password reset link via Resend."""
    import resend

    resend.api_key = os.environ["RESEND_API_KEY"]
    mail_from = os.environ["MAIL_FROM"]

    resend.Emails.send(
        {
            "from": mail_from,
            "to": to_username,
            "subject": "Resetuj lozinku",
            "html": (
                f"<p>Klikni <a href='{reset_url}'>ovde</a> da resetuješ lozinku.</p>"
                "<p>Link važi 1 sat.</p>"
            ),
        }
    )
