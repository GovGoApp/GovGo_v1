"""
gvg_email.py
Utilitário de envio de email via SMTP.

Lê variáveis de ambiente:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
  SMTP_TLS (true/false), SMTP_USE_SSL (true/false), SMTP_TIMEOUT, SMTP_REPLY_TO, SMTP_SUBJECT_PREFIX

Exposta a função send_html_email(to, subject, html, text_alt=None).
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")

def _get_smtp_config():
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM")
    use_tls = _env_bool("SMTP_TLS", True)
    use_ssl = _env_bool("SMTP_USE_SSL", False)
    timeout = int(os.getenv("SMTP_TIMEOUT", "15"))
    reply_to = os.getenv("SMTP_REPLY_TO")
    subject_prefix = os.getenv("SMTP_SUBJECT_PREFIX", "")
    return {
        "host": host,
        "port": port,
        "user": user,
        "pwd": pwd,
        "from": from_addr,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "timeout": timeout,
        "reply_to": reply_to,
        "subject_prefix": subject_prefix,
    }

def send_html_email(to: str, subject: str, html: str, text_alt: Optional[str] = None) -> bool:
    cfg = _get_smtp_config()
    # Dry-run se faltar configuração crítica
    if not cfg["host"] or not cfg["from"] or (not cfg["use_ssl"] and not cfg["use_tls"] and not cfg["port"]):
        # Log simplificado; o caller deve ter um logger
        print(f"[EMAIL] Dry-run: to={to} subject={subject} (config SMTP ausente)")
        return False

    msg = EmailMessage()
    msg["From"] = cfg["from"]
    msg["To"] = to
    if cfg["subject_prefix"]:
        subject = f"{cfg['subject_prefix']} {subject}"
    msg["Subject"] = subject
    if cfg["reply_to"]:
        msg["Reply-To"] = cfg["reply_to"]

    if not text_alt:
        text_alt = "Veja este boletim em um cliente compatível com HTML."
    msg.set_content(text_alt)
    msg.add_alternative(html, subtype="html")

    try:
        if cfg["use_ssl"]:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=cfg["timeout"]) as server:
                if cfg["user"] and cfg["pwd"]:
                    server.login(cfg["user"], cfg["pwd"])
                server.send_message(msg)
                return True
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=cfg["timeout"]) as server:
                if cfg["use_tls"]:
                    server.starttls(context=ssl.create_default_context())
                if cfg["user"] and cfg["pwd"]:
                    server.login(cfg["user"], cfg["pwd"])
                server.send_message(msg)
                return True
    except Exception as e:
        print(f"[EMAIL] Falha ao enviar para {to}: {e}")
        return False

__all__ = ["send_html_email"]
