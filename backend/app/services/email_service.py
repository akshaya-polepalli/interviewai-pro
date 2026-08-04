"""
Email delivery abstraction.

Development: log messages (and optionally print verification links).
Production: SMTP when SMTP_HOST is configured.
"""

from __future__ import annotations

import html
import smtplib
from email.message import EmailMessage

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def send(self, *, to: str, subject: str, body: str, html_body: str | None = None) -> None:
        if not self.settings.smtp_host:
            logger.info(
                "email_console_fallback",
                to=to,
                subject=subject,
                body=body,
            )
            return

        message = EmailMessage()
        message["From"] = self.settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_user:
                smtp.login(self.settings.smtp_user, self.settings.smtp_password)
            smtp.send_message(message)

        logger.info("email_sent", to=to, subject=subject)

    def _wrap_html(self, *, title: str, intro: str, link: str, cta: str, note: str) -> str:
        safe_title = html.escape(title)
        safe_intro = html.escape(intro)
        safe_link = html.escape(link)
        safe_cta = html.escape(cta)
        safe_note = html.escape(note)
        brand = html.escape(self.settings.app_name)
        return f"""<!DOCTYPE html>
<html><body style="font-family:Segoe UI,Helvetica,Arial,sans-serif;background:#0f1419;color:#e8eef5;padding:32px">
  <div style="max-width:520px;margin:0 auto;background:#1a222c;border-radius:16px;padding:28px">
    <p style="margin:0 0 8px;letter-spacing:.12em;text-transform:uppercase;color:#7d8fa3;font-size:12px">{brand}</p>
    <h1 style="margin:0 0 12px;font-size:22px;color:#f4f7fb">{safe_title}</h1>
    <p style="margin:0 0 20px;line-height:1.5;color:#b8c4d1">{safe_intro}</p>
    <p style="margin:0 0 24px"><a href="{safe_link}" style="display:inline-block;background:#3d8bfd;color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:600">{safe_cta}</a></p>
    <p style="margin:0;font-size:12px;color:#7d8fa3;word-break:break-all">{safe_link}</p>
    <p style="margin:16px 0 0;font-size:12px;color:#7d8fa3">{safe_note}</p>
  </div>
</body></html>"""

    def send_verification(self, *, to: str, token: str) -> None:
        link = f"{self.settings.frontend_url}/verify-email?token={token}"
        hours = self.settings.email_verification_expire_hours
        plain = (
            f"Welcome to {self.settings.app_name}.\n\n"
            f"Verify your email by opening this link:\n{link}\n\n"
            f"This link expires in {hours} hours.\n"
            "If you did not create an account, ignore this email.\n"
        )
        html_body = self._wrap_html(
            title="Verify your email",
            intro=f"Welcome to {self.settings.app_name}. Confirm your address to activate your account.",
            link=link,
            cta="Verify email",
            note=f"This link expires in {hours} hours. If you did not sign up, ignore this message.",
        )
        self.send(
            to=to,
            subject=f"Verify your {self.settings.app_name} email",
            body=plain,
            html_body=html_body,
        )

    def send_password_reset(self, *, to: str, token: str) -> None:
        link = f"{self.settings.frontend_url}/reset-password?token={token}"
        hours = self.settings.password_reset_expire_hours
        plain = (
            f"We received a password reset request.\n\n"
            f"Reset your password here:\n{link}\n\n"
            f"This link expires in {hours} hour(s).\n"
            "If you did not request this, ignore this email.\n"
        )
        html_body = self._wrap_html(
            title="Reset your password",
            intro="We received a request to reset your InterviewAI Pro password.",
            link=link,
            cta="Choose new password",
            note=f"This link expires in {hours} hour(s). If you did not request a reset, ignore this message.",
        )
        self.send(
            to=to,
            subject=f"Reset your {self.settings.app_name} password",
            body=plain,
            html_body=html_body,
        )
