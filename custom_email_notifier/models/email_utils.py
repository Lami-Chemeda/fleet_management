import json
import smtplib
import socket
import threading
from datetime import datetime, timezone
from email.utils import formataddr, formatdate, make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
from html import escape

_logger = logging.getLogger(__name__)


def _build_html(subject, body, base_url, sender_name):
    """Build a premium HTML email template with structured detail."""
    # Current timestamp for the email footer
    now_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    <title>{escape(subject)}</title>
</head>
<body style="margin:0; padding:0; background-color:#f0f4f8; font-family:Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif; -webkit-font-smoothing:antialiased;">

    <!-- Outer wrapper -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f0f4f8; padding:32px 16px;">
        <tr>
            <td align="center">

                <!-- Main card -->
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px; width:100%; background-color:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.06);">

                    <!-- Header banner -->
                    <tr>
                        <td style="background:linear-gradient(135deg, #1e3a5f 0%, #2563eb 50%, #0ea5e9 100%); padding:40px 36px 36px 36px; text-align:center;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td align="center" style="padding-bottom:16px;">
                                        <!-- Logo circle -->
                                        <div style="display:inline-block; width:52px; height:52px; border-radius:50%; background-color:rgba(255,255,255,0.15); line-height:52px; text-align:center; font-size:24px; color:#ffffff; font-weight:700;">O</div>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center">
                                        <div style="font-size:11px; letter-spacing:3px; text-transform:uppercase; color:rgba(224,242,254,0.85); font-weight:600; margin-bottom:10px;">OTECH ERP SYSTEM</div>
                                        <div style="font-size:26px; line-height:1.3; color:#ffffff; font-weight:700;">{escape(subject)}</div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Timestamp bar -->
                    <tr>
                        <td style="background-color:#f8fafc; padding:14px 36px; border-bottom:1px solid #e2e8f0;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td style="font-size:13px; color:#64748b;">
                                        &#128197; {now_str}
                                    </td>
                                    <td align="right" style="font-size:13px; color:#64748b;">
                                        Sent by {escape(sender_name)}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body content -->
                    <tr>
                        <td style="padding:36px 36px 28px 36px;">
                            <div style="font-size:15px; line-height:1.8; color:#334155; white-space:pre-wrap;">{escape(body)}</div>
                        </td>
                    </tr>

                    <!-- CTA button -->
                    <tr>
                        <td align="center" style="padding:0 36px 36px 36px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td style="border-radius:10px; background-color:#2563eb;">
                                        <a href="{base_url}" target="_blank" style="display:inline-block; padding:14px 32px; color:#ffffff; text-decoration:none; font-weight:600; font-size:15px; letter-spacing:0.3px;">Open Dashboard &rarr;</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8fafc; padding:28px 36px; border-top:1px solid #e2e8f0; text-align:center;">
                            <div style="color:#475569; font-size:13px; font-weight:600; margin-bottom:6px;">Otech Fleet Management &amp; ERP</div>
                            <div style="color:#94a3b8; font-size:12px; line-height:1.6;">
                                This is an automated notification. Please do not reply to this email.
                            </div>
                        </td>
                    </tr>

                </table>
                <!-- End main card -->

            </td>
        </tr>
    </table>

</body>
</html>"""


def _send_email(smtp_server, smtp_port, smtp_user, smtp_password,
                reply_to, sender_name, target_emails, subject, body,
                base_url="https://erp.otech.et"):
    """Send one notification to all resolved recipients through Gmail SMTP.

    Includes proper email headers (Message-ID, Date, MIME-Version) to
    maximize inbox delivery and avoid Gmail spam filters.
    """
    server = None
    try:
        if not target_emails:
            return

        if base_url and not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)

        # Build HTML once; it's the same for every recipient
        html_body = _build_html(subject, body, base_url, sender_name)
        plain_body = (
            f"{subject}\n"
            f"{'=' * len(subject)}\n\n"
            f"{body}\n\n"
            f"---\n"
            f"Open Dashboard: {base_url}\n\n"
            f"This is an automated notification from Otech ERP.\n"
            f"Please do not reply to this email.\n"
        )

        domain = smtp_user.split('@')[-1] if '@' in smtp_user else socket.getfqdn()

        for email_addr in target_emails:
            msg = MIMEMultipart('alternative')

            # ── Anti-spam headers ──────────────────────────────
            msg['From'] = formataddr((sender_name, smtp_user))
            msg['To'] = email_addr
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain=domain)
            msg['MIME-Version'] = '1.0'
            msg['X-Mailer'] = 'Otech-ERP-Notifier/1.0'
            msg['Precedence'] = 'bulk'

            if reply_to:
                msg['Reply-To'] = reply_to

            # Plain text first, then HTML (RFC 2046 best practice)
            msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            server.send_message(msg)
            _logger.info("Email sent to %s — subject: %s", email_addr, subject)

    except Exception:
        _logger.exception("SMTP error in custom_email_notifier")
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


def send_custom_email(env, users, subject, body):
    """
    Reads email.json and dispatches an email using SMTP.
    Uses Reply-To to masquerade the current user.

    All Odoo record field reads are done synchronously (before the
    background thread starts) to avoid 'Cursor already closed' errors.
    """
    email_config_path = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'email.json'
    )
    email_config_path = os.path.abspath(email_config_path)
    if not os.path.exists(email_config_path):
        _logger.error("Email configuration file not found: %s", email_config_path)
        return

    try:
        with open(email_config_path, 'r') as f:
            email_config = json.load(f)

        smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        smtp_port = email_config.get('smtp_port', 587)
        smtp_user = email_config.get('smtp_user')
        smtp_password = email_config.get('smtp_password')

        if not smtp_user or not smtp_password:
            _logger.error("SMTP user or password is missing in email.json")
            return

        sender_name = email_config.get('sender_name', 'Otech ERP')
        reply_to = email_config.get('reply_to') or smtp_user

        # ── Resolve target emails synchronously ──────────────
        target_emails = []
        for recipient in users:
            candidates = []
            if recipient._name == 'hr.employee':
                candidates.extend((recipient.work_email, recipient.private_email))
                if recipient.user_id:
                    candidates.extend((
                        recipient.user_id.partner_id.email,
                        recipient.user_id.login,
                    ))
            else:
                employee = getattr(recipient, 'employee_id', False)
                if employee:
                    candidates.extend((employee.work_email, employee.private_email))
                partner = getattr(recipient, 'partner_id', False)
                candidates.extend((
                    getattr(partner, 'email', False),
                    getattr(recipient, 'login', False),
                ))
                candidates.extend((
                    getattr(recipient, 'work_email', False),
                    getattr(recipient, 'private_email', False),
                ))

            target_email = next(
                (e.strip() for e in candidates if e and '@' in e), False
            )
            if target_email and target_email.lower() not in {
                e.lower() for e in target_emails
            }:
                target_emails.append(target_email)

        if not target_emails:
            return

        base_url = env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://erp.otech.et'
        )
        if base_url and not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"

        # ── Fire in a background thread ──────────────────────
        thread = threading.Thread(
            target=_send_email,
            args=(
                smtp_server, smtp_port, smtp_user, smtp_password,
                reply_to, sender_name, target_emails, subject, body,
                base_url,
            ),
            daemon=True,
        )
        thread.start()

    except Exception:
        _logger.exception("Failed to read email.json or process emails")
