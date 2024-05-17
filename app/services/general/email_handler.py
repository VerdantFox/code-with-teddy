"""email_handler: Functions and classes for sending emails."""

import textwrap
from logging import getLogger

from mailersend import emails as mailersend_emails

from app.datastore import db_models
from app.settings import settings

logger = getLogger(__name__)

ContactType = dict[str, str]  # {name: str, email: str}
MailBodyType = dict[str, str | ContactType | list[ContactType]]
TransactionEmailResponse = tuple[MailBodyType, str]

WEBSITE_URL = "https://codewithteddy.dev"
TEST_MESSAGE = "temporary test comment…"
EMAIL_CSS = """\
<style>
    /* General styles */
    body {
        font-family: Arial, sans-serif;
        background-color: #f6f6f6;
        margin: 0;
        padding: 0;
        -webkit-text-size-adjust: 100%;
        -ms-text-size-adjust: 100%;
    }

    table {
        border-collapse: collapse;
        width: 100%;
    }
    td {
        background-color: #ffffff;
        padding: 20px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    }

    h1 {
        font-size: 24px;
        margin: 0;
        padding-bottom: 20px;
    }

    h2 {
        font-size: 20px;
        margin-top: 0;
    }

    p {
        font-size: 16px;
        line-height: 1.5;
        color: #555555;
        margin: 0 0 15px;
    }

    footer {
        text-align: center;
        padding-top: 20px;
        border-top: 1px solid #e6e6e6;
        font-size: 12px;
        color: #999999;
    }

    a {
        color: #3498db;
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    .comment {
        background-color: #f2f2f2; /* Light gray */
        padding: 10px;
    }


    blockquote {
        padding: 10px 20px;
        margin: 0 0 20px;
        border-left: 5px solid #b3b3b3; /* Light gray */
        background-color: #f9f9f9; /* Lighter gray */
        font-style: italic;
    }

    /* Responsive styles */
    @media only screen and (max-width: 600px) {
        td {
            padding: 10px !important;
        }

        p {
            font-size: 14px !important;
        }
    }
</style>
"""


def send_comment_notification_emails(
    *, comment: db_models.BlogPostComment, post: db_models.BlogPost
) -> TransactionEmailResponse:
    """Send an email to me and others on the post."""
    if comment.md_content == TEST_MESSAGE:
        return {}, ""

    subject = f"New comment on {post.title}"

    html_content = textwrap.dedent(
        f"""\
        {EMAIL_CSS}
        </style>
        <h1>New comment on <a href="{WEBSITE_URL}/blog/{post.slug}#comments ">{post.title!r}</a></h1>
        <p>Commenter: {comment.name}</p>
        <p>comment:</p>
        <div class="comment">{comment.html_content}</div>
        <br><br>
        """  # noqa: E501 (line too long)
    )

    text_content = textwrap.dedent(
        f"""\
        New comment on {post.title}
        Commenter: {comment.name}

        {comment.md_content}
        """
    )
    if not settings.mailersend_api_key:
        return {}, ""

    return send_transaction_email(
        to_email=settings.my_email_address,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )


def send_pw_reset_email_to_user(
    *, user: db_models.User, pw_reset_token: db_models.PasswordResetToken
) -> TransactionEmailResponse:
    """Send a password reset email to a user."""
    subject = "Password reset request"
    reset_url = f"{WEBSITE_URL}/reset-password/{pw_reset_token.query}"
    html_content = textwrap.dedent(
        f"""\
        {EMAIL_CSS}
        <h1>Password reset request</h1>
        <p>Hi {user.username},</p>
        <p>Someone requested a password reset for your account.</p>
        <p>If this was you, click the link below to reset your password:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>If you didn't request a password reset, you can ignore this email.</p>
        <footer>This email was sent to {user.email}.</footer>
        """
    )

    text_content = textwrap.dedent(
        f"""\
        Password reset request
        Hi {user.username},
        Someone requested a password reset for your account.
        If this was you, click the link below to reset your password (or copy and paste it into your browser):
        {reset_url}
        If you didn't request a password reset, you can ignore this email.
        This email was sent to {user.email}.
        """  # noqa: E501 (line too long)
    )

    return send_transaction_email(
        to_email=user.email,
        subject=subject,
        to_name=user.username,
        html_content=html_content,
        text_content=text_content,
    )


def send_transaction_email(  # noqa: PLR0913 (too-many-arguments)
    *,
    to_email: str,
    subject: str,
    to_name: str = "",
    html_content: str = "",
    text_content: str = "",
    from_email: str = settings.site_email_address,
    from_name: str = "Code with Teddy",
    reply_email: str = settings.site_email_address,
    reply_name: str = "Code with Teddy",
) -> TransactionEmailResponse:
    """Send an email to a recipient."""
    mailer = mailersend_emails.NewEmail(settings.mailersend_api_key)

    mail_body: MailBodyType = {}
    mail_from = {
        "name": from_name,
        "email": from_email,
    }
    recipients = [
        {
            "name": to_name or to_email,
            "email": to_email,
        }
    ]
    reply_to = {
        "name": reply_name,
        "email": reply_email,
    }
    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject(subject, mail_body)
    mailer.set_html_content(html_content, mail_body)
    mailer.set_plaintext_content(text_content, mail_body)
    mailer.set_reply_to(reply_to, mail_body)

    response_str = mailer.send(mail_body)

    if response_str != "202\n":  # pragma: no cover
        logger.error("Failed to send email: %s\n\nProblematic email: %s", response_str, mail_body)

    return mail_body, response_str
