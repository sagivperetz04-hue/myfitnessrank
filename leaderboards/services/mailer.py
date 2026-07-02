import logging
import os
import smtplib
from datetime import date, timedelta
from email.message import EmailMessage

log = logging.getLogger(__name__)

VERIFICATION_DAYS = 7

_SUBJECT = "You cracked the Top 200 — one week to make it official"

_BODY = """\
Congrats, gym rat.

Your {total_kg:.1f} kg total just landed you at #{rank} on the MyFitnessRank
Top 200 — peak human machinery, a certified problem for gravity. The real
Hulk walks among us, and apparently it's you, {username}.

One thing before the crown is yours: we need to check it's legit.

You have {days} days (until {deadline}) to reply to this email with:

  1. a video of the lift(s)
  2. a photo of today's bodyweight on the scale

We'll review it and stamp your spot. Until then, your place is reserved.

Stay strong,
MyFitnessRank
"""


def render(username: str, rank: int, total_kg: float) -> tuple[str, str]:
    """Build the (subject, body) for the top-200 verification mail."""
    deadline = date.today() + timedelta(days=VERIFICATION_DAYS)
    body = _BODY.format(
        username=username,
        rank=rank,
        total_kg=total_kg,
        days=VERIFICATION_DAYS,
        deadline=deadline.isoformat(),
    )
    return _SUBJECT, body


def send_top200_mail(to_email: str, username: str, rank: int, total_kg: float) -> None:
    """Send the congratulations + verification mail for a top-200 entry.

    Without SMTP_HOST the mail is logged instead of sent, so local and dev
    environments never talk to a real relay. Raises on delivery failure so the
    caller can leave the entry un-notified and retry on the next submit.
    """
    subject, body = render(username, rank, total_kg)

    host = os.environ.get("SMTP_HOST")
    if not host:
        log.info(
            "SMTP_HOST not set — top-200 mail for %s (rank %d) logged only:\n%s",
            to_email,
            rank,
            body,
        )
        return

    msg = EmailMessage()
    msg["From"] = os.environ.get("MAIL_FROM", "no-reply@myfitnessrank.local")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        # Plain-text relays (e.g. a local catcher) opt out via SMTP_STARTTLS=false
        if os.environ.get("SMTP_STARTTLS", "true").lower() != "false":
            smtp.starttls()
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)
