import smtplib
from email.message import EmailMessage

from app.config import settings
from app.models import Notification, User


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_host:
        return False
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = settings.smtp_from, to, subject
    m.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(m)
        return True
    except Exception:
        return False


def notify(db, kind, basis, message, borewell_id=None, users=None):
    """basis is 'measured' (actual threshold exceedance) or 'predicted' (model/risk warning) — never mixed."""
    targets = users or [None]
    for u in targets:
        db.add(Notification(user_id=u.id if u else None, borewell_id=borewell_id,
                            kind=kind, basis=basis, message=f"[{basis.upper()}] {message}"))
        if u and u.email_alerts:
            send_email(u.email, f"Salinity alert ({basis})", message)
    db.commit()
# SMS: plug Twilio/MSG91 in here (optional); intentionally not enabled by default.
