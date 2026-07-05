from datetime import date, timedelta

import smtplib

from services import mailer


class TestRender:
    def test_body_contains_rank_total_username_deadline(self):
        subject, body = mailer.render("hulk", 42, 700.0)
        deadline = (date.today() + timedelta(days=mailer.VERIFICATION_DAYS)).isoformat()
        assert "#42" in body
        assert "700.0 kg" in body
        assert "hulk" in body
        assert deadline in body
        assert "Top 200" in subject

    def test_body_asks_for_video_and_bodyweight_proof(self):
        _, body = mailer.render("hulk", 1, 900.0)
        assert "video" in body
        assert "bodyweight" in body
        assert "reserved" in body


class FakeSMTP:
    """Stands in for smtplib.SMTP; records the session."""

    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.started_tls = False
        self.login_args = None
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)


class TestSend:
    def setup_method(self):
        FakeSMTP.instances = []

    def test_without_smtp_host_logs_instead_of_sending(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
        mailer.send_top200_mail("a@b.com", "hulk", 3, 800.0)
        assert FakeSMTP.instances == []

    def test_sends_via_configured_relay(self, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "mail.example.com")
        monkeypatch.setenv("SMTP_PORT", "2525")
        monkeypatch.setenv("MAIL_FROM", "board@myfitnessrank.app")
        monkeypatch.setenv("SMTP_USER", "board")
        monkeypatch.setenv("SMTP_PASSWORD", "hunter2")
        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

        mailer.send_top200_mail("a@b.com", "hulk", 3, 800.0)

        (smtp,) = FakeSMTP.instances
        assert (smtp.host, smtp.port) == ("mail.example.com", 2525)
        assert smtp.started_tls
        assert smtp.login_args == ("board", "hunter2")
        (msg,) = smtp.sent
        assert msg["To"] == "a@b.com"
        assert msg["From"] == "board@myfitnessrank.app"
        assert "Top 200" in msg["Subject"]

    def test_starttls_can_be_disabled_for_plain_relays(self, monkeypatch):
        monkeypatch.setenv("SMTP_HOST", "mailcatcher.local")
        monkeypatch.setenv("SMTP_STARTTLS", "false")
        monkeypatch.delenv("SMTP_USER", raising=False)
        monkeypatch.delenv("SMTP_PASSWORD", raising=False)
        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

        mailer.send_top200_mail("a@b.com", "hulk", 3, 800.0)

        (smtp,) = FakeSMTP.instances
        assert not smtp.started_tls
        assert smtp.login_args is None
        assert len(smtp.sent) == 1
