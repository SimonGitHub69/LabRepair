from dataclasses import dataclass
from email.message import EmailMessage
import smtplib


@dataclass
class MailSendResult:
    ok: bool
    message: str


def parse_email_destinatari(raw):
    if not raw:
        return []
    text = str(raw).replace(";", ",").replace("\n", ",")
    parts = [part.strip() for part in text.split(",")]
    return [part for part in parts if part and "@" in part]


def config_email_from_post(post, instance=None):
    """Costruisce una config SMTP dai valori del form (anche non salvati)."""
    from apps.agenda.models import ConfigurazioneNotificaEmail

    instance = instance or ConfigurazioneNotificaEmail.get_solo()
    if not post:
        return instance

    porta_raw = (post.get("porta") or "").strip()
    try:
        porta = int(porta_raw) if porta_raw else instance.porta
    except ValueError:
        porta = instance.porta

    password = (post.get("password") or "").strip() or instance.password

    return ConfigurazioneNotificaEmail(
        attiva=True,
        host=(post.get("host") or "").strip() or instance.host,
        porta=porta or 587,
        usa_tls=post.get("usa_tls") == "on",
        usa_ssl=post.get("usa_ssl") == "on",
        username=(post.get("username") or "").strip() or instance.username,
        password=password,
        mittente=(post.get("mittente") or "").strip() or instance.mittente,
        destinatari_default=(post.get("destinatari_default") or "").strip()
        or instance.destinatari_default,
        giorni_preavviso=instance.giorni_preavviso,
    )


def send_smtp_email(*, config, destinatari, subject, body):
    destinatari = [addr for addr in (destinatari or []) if addr]
    if not destinatari:
        return MailSendResult(ok=False, message="Indica almeno un destinatario.")

    if not config or not config.attiva:
        return MailSendResult(
            ok=False,
            message="SMTP non attivo. Configura e attiva i Parametri mail.",
        )

    host = (config.host or "").strip()
    mittente = (config.mittente or "").strip()
    if not host or not mittente:
        return MailSendResult(
            ok=False,
            message="Parametri mail incompleti: servono server SMTP e mittente.",
        )

    message = EmailMessage()
    message["Subject"] = subject or "(senza oggetto)"
    message["From"] = mittente
    message["To"] = ", ".join(destinatari)
    message.set_content(body or "")

    try:
        if config.usa_ssl:
            server = smtplib.SMTP_SSL(host, config.porta or 465, timeout=15)
        else:
            server = smtplib.SMTP(host, config.porta or 587, timeout=15)
        with server:
            server.ehlo()
            if config.usa_tls and not config.usa_ssl:
                server.starttls()
                server.ehlo()
            username = (config.username or "").strip()
            if username:
                server.login(username, config.password or "")
            server.send_message(message)
    except Exception as exc:
        return MailSendResult(
            ok=False,
            message=f"Invio non riuscito: {exc}",
        )

    return MailSendResult(
        ok=True,
        message=f"Mail di prova inviata a {', '.join(destinatari)}.",
    )
