import smtplib
import sentry_sdk
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from api.config import settings


def _build_message(to: str, subject: str, html_body: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.SMTP_FROM
    msg["To"]      = to
    msg.attach(MIMEText(html_body, "html"))
    return msg


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send a single transactional email. Returns True on success."""
    try:
        msg = _build_message(to, subject, html_body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [to], msg.as_string())
        return True
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Email send failed to {to}: {e}")
        return False


def send_password_reset_email(to: str, username: str, reset_token: str) -> bool:
    ### Reset link points to the frontend route that will call POST /api/auth/reset-password
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto">
      <h2>SFA — Password Reset</h2>
      <p>Hi <strong>{username}</strong>,</p>
      <p>Click the button below to reset your password. This link expires in
         <strong>{settings.RESET_TOKEN_EXPIRE_MINUTES} minutes</strong>.</p>
      <a href="{reset_url}"
         style="display:inline-block;padding:12px 24px;background:#0ea5e9;
                color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">
        Reset Password
      </a>
      <p style="margin-top:24px;color:#6b7280;font-size:13px">
        If you did not request this, ignore this email — your password will not change.
      </p>
    </div>
    """
    return send_email(to, "SFA — Reset your password", html)


def send_welcome_email(to: str, username: str) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto">
      <h2>Welcome to SFA!</h2>
      <p>Hi <strong>{username}</strong>,</p>
      <p>Your account is ready. Log in and start querying your financial data.</p>
      <a href="{settings.FRONTEND_URL}/login"
         style="display:inline-block;padding:12px 24px;background:#0ea5e9;
                color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">
        Go to SFA
      </a>
    </div>
    """
    return send_email(to, "Welcome to SFA", html)
