"""
Email Digest Tool — converts the markdown digest to styled HTML and sends it via SMTP.

Required env vars (set in .env or environment):
    EMAIL_TO        Recipient address
    SMTP_USER       Your Gmail address (or other SMTP login)
    SMTP_PASSWORD   Gmail App Password (or SMTP password)

Optional env vars:
    EMAIL_FROM      Sender display address (defaults to SMTP_USER)
    SMTP_HOST       Defaults to smtp.gmail.com
    SMTP_PORT       Defaults to 587
"""

import os
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _md_to_html(md: str) -> str:
    """
    Lightweight markdown-to-HTML converter for the digest format.
    Handles: h1/h2/h3, bold, inline code, blockquote, links, hr, paragraphs.
    No external dependency needed.
    """
    lines = md.splitlines()
    html_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Horizontal rule
        if re.match(r"^---+$", line.strip()):
            html_lines.append('<hr>')
            i += 1
            continue

        # H1
        if line.startswith("# "):
            text = _inline(line[2:])
            html_lines.append(f'<h1>{text}</h1>')
            i += 1
            continue

        # H2
        if line.startswith("## "):
            text = _inline(line[3:])
            html_lines.append(f'<h2>{text}</h2>')
            i += 1
            continue

        # H3
        if line.startswith("### "):
            text = _inline(line[4:])
            html_lines.append(f'<h3>{text}</h3>')
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            text = _inline(line[2:])
            html_lines.append(f'<blockquote>{text}</blockquote>')
            i += 1
            continue

        # Empty line → spacer
        if line.strip() == "":
            html_lines.append("")
            i += 1
            continue

        # Italic line (source attribution: *Source: ..*)
        if line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            text = _inline(line)
            html_lines.append(f'<p class="source">{text}</p>')
            i += 1
            continue

        # Paragraph
        html_lines.append(f'<p>{_inline(line)}</p>')
        i += 1

    return "\n".join(html_lines)


def _inline(text: str) -> str:
    """Process inline markdown: bold, italic, inline code, links."""
    # Inline code
    text = re.sub(r"`([^`]+)`", r'<code>\1</code>', text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r'<em>\1</em>', text)
    # Links [text](url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


def _wrap_html(body: str, date_str: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Upskill Digest — {date_str}</title>
<style>
  body {{
    margin: 0; padding: 0;
    background: #f7f8fa;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 15px; line-height: 1.65; color: #1a202c;
  }}
  .wrapper {{
    max-width: 640px; margin: 32px auto; padding: 0 16px 48px;
  }}
  .header {{
    background: #1a202c; border-radius: 12px 12px 0 0;
    padding: 28px 32px; margin-bottom: 0;
  }}
  .header h1 {{
    margin: 0; font-size: 20px; font-weight: 700; color: #f7fafc; letter-spacing: -0.3px;
  }}
  .header .tagline {{
    margin: 6px 0 0; color: #718096; font-size: 13px;
  }}
  .header .date {{
    display: inline-block; margin-top: 10px;
    background: #2d3748; border-radius: 6px;
    padding: 3px 10px; font-size: 12px; color: #a0aec0;
  }}
  .body {{ background: #ffffff; padding: 28px 32px; border: 1px solid #e2e8f0; }}
  .footer {{
    background: #f0f4f8; border: 1px solid #e2e8f0; border-top: none;
    border-radius: 0 0 12px 12px; padding: 14px 32px;
    font-size: 11px; color: #a0aec0; text-align: center;
  }}
  h1 {{ font-size: 20px; color: #1a202c; margin: 0 0 4px; }}
  h2 {{
    font-size: 10px; font-weight: 700; letter-spacing: 1.4px;
    text-transform: uppercase; color: #a0aec0;
    border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;
    margin: 28px 0 14px;
  }}
  h3 {{ font-size: 15px; font-weight: 600; margin: 0 0 2px; }}
  h3 a {{ color: #2b6cb0; text-decoration: none; }}
  h3 a:hover {{ text-decoration: underline; }}
  p {{ margin: 0 0 10px; color: #4a5568; font-size: 14px; }}
  p.source {{ font-size: 11px; color: #a0aec0; margin: 2px 0 8px; }}
  strong {{ color: #1a202c; }}
  blockquote {{
    margin: 0 0 16px; padding: 10px 16px;
    border-left: 3px solid #bee3f8; background: #ebf8ff;
    border-radius: 0 6px 6px 0; font-size: 14px; color: #2c5282;
  }}
  code {{
    background: #edf2f7; border-radius: 4px;
    padding: 1px 5px; font-size: 12px; font-family: "SF Mono", "Fira Code", monospace;
    color: #c53030;
  }}
  .card {{
    background: #f7f8fa; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
  }}
  .takeaway {{
    margin-top: 8px; padding: 8px 12px;
    border-left: 3px solid #3182ce; background: #ebf8ff;
    border-radius: 0 6px 6px 0; font-size: 13px; color: #2c5282;
  }}
  .takeaway .label {{
    display: block; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.8px;
    color: #3182ce; margin-bottom: 3px;
  }}
  hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>🧠 AI Upskill Digest</h1>
    <p class="tagline">What to learn and build with AI today.</p>
    <span class="date">{date_str}</span>
  </div>
  <div class="body">
    {body}
  </div>
  <div class="footer">
    AI Upskill Digest &nbsp;·&nbsp; Sources: Hacker News, Simon Willison, Hugging Face Blog, Sebastian Raschka
  </div>
</div>
</body>
</html>"""


def _render_digest_html(md_content: str) -> str:
    """
    Parse the structured digest markdown into card-based HTML.
    Falls back to generic markdown conversion if parsing fails.
    """
    # Split into sections by ## headings
    sections = re.split(r"\n(?=## )", md_content.strip())

    html_parts = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Header block (h1 + blockquote)
        if section.startswith("# "):
            lines = section.splitlines()
            for line in lines:
                if line.startswith("# "):
                    html_parts.append(f'<h1>{_inline(line[2:])}</h1>')
                elif line.startswith("> "):
                    html_parts.append(f'<blockquote>{_inline(line[2:])}</blockquote>')
            continue

        # Section with ## heading
        if section.startswith("## "):
            lines = section.splitlines()
            section_title = _inline(lines[0][3:])
            html_parts.append(f'<h2>{section_title}</h2>')

            # Split stories by ### headings within the section
            stories_text = "\n".join(lines[1:])
            stories = re.split(r"\n(?=### )", stories_text.strip())

            for story in stories:
                story = story.strip()
                if not story:
                    continue

                story_lines = story.splitlines()
                card_html = ['<div class="card">']

                in_takeaway = False
                takeaway_lines = []
                body_lines = []

                for sline in story_lines:
                    if sline.startswith("### "):
                        card_html.append(f'<h3>{_inline(sline[4:])}</h3>')
                    elif sline.startswith("*Source:") or (sline.startswith("*") and "Source:" in sline):
                        card_html.append(f'<p class="source">{_inline(sline)}</p>')
                    elif sline.startswith("**Takeaway:**"):
                        in_takeaway = True
                        rest = sline[len("**Takeaway:**"):].strip()
                        if rest:
                            takeaway_lines.append(rest)
                    elif in_takeaway and sline.strip():
                        takeaway_lines.append(sline.strip())
                    elif sline.startswith("---"):
                        continue
                    elif sline.strip():
                        body_lines.append(sline.strip())

                if body_lines:
                    card_html.append(f'<p>{_inline(" ".join(body_lines))}</p>')

                if takeaway_lines:
                    takeaway_text = _inline(" ".join(takeaway_lines))
                    card_html.append(
                        f'<div class="takeaway">'
                        f'<span class="label">Takeaway</span>{takeaway_text}'
                        f'</div>'
                    )

                card_html.append('</div>')
                html_parts.append("\n".join(card_html))

    return "\n".join(html_parts)


def send_digest_email(md_content: str) -> bool:
    """
    Convert the markdown digest to styled HTML and send via SMTP.

    Reads credentials from environment (or .env file):
        EMAIL_TO, SMTP_USER, SMTP_PASSWORD
        EMAIL_FROM, SMTP_HOST, SMTP_PORT (optional)

    Returns True on success, False if skipped or failed.
    """
    email_to   = os.environ.get("EMAIL_TO")
    smtp_user  = os.environ.get("SMTP_USER")
    smtp_pass  = os.environ.get("SMTP_PASSWORD")

    if not all([email_to, smtp_user, smtp_pass]):
        missing = [k for k, v in {
            "EMAIL_TO": email_to,
            "SMTP_USER": smtp_user,
            "SMTP_PASSWORD": smtp_pass,
        }.items() if not v]
        print(f"  ⚠ Email skipped — missing env vars: {', '.join(missing)}")
        print("    Set them in a .env file (see .env.example)")
        return False

    email_from = os.environ.get("EMAIL_FROM", smtp_user)
    smtp_host  = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port  = int(os.environ.get("SMTP_PORT", "587"))

    date_str = datetime.now().strftime("%B %d, %Y")
    subject  = f"🧠 AI Upskill Digest — {date_str}"

    body_html = _render_digest_html(md_content)
    html_email = _wrap_html(body_html, date_str)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = email_from
    msg["To"]      = email_to

    msg.attach(MIMEText(md_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_email, "html",  "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(email_from, email_to, msg.as_string())
        print(f"  ✓ Digest emailed to {email_to}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("  ✗ Email failed — authentication error.")
        print("    For Gmail: use an App Password, not your account password.")
        print("    https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        print(f"  ✗ Email failed — {e}")
        return False
