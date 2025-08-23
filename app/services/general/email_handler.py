"""email_handler: Functions and classes for sending emails."""

import textwrap
from logging import getLogger

from mailersend import EmailBuilder, MailerSendClient

from app.datastore import db_models
from app.settings import settings

logger = getLogger(__name__)

ContactType = dict[str, str]  # {name: str, email: str}
MailBodyType = dict[str, str | ContactType | list[ContactType]]
TransactionEmailResponse = tuple[MailBodyType, str]

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
        <h1>New comment on <a href="{settings.base_url}/blog/{post.slug}#comments ">{post.title!r}</a></h1>
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


def send_pw_reset_email_to_user(*, user: db_models.User, query: str) -> TransactionEmailResponse:
    """Send a password reset email to a user."""
    subject = "Code With Teddy password reset request"
    reset_url = f"{settings.base_url}/reset-password/{query}"
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
        to_name=user.full_name,
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
    """Send an email to a recipient using MailerSend's API."""
    if not settings.mailersend_api_key:
        return {}, ""

    try:
        return _build_and_send_email(
            from_email=from_email,
            from_name=from_name,
            to_email=to_email,
            to_name=to_name,
            reply_email=reply_email,
            reply_name=reply_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
    except Exception as e:
        error_message = f"Exception occurred while sending email: {e!s}\n"
        logger.exception("Failed to send email: %s", error_message)
        return {}, error_message


def _build_and_send_email(  # noqa: PLR0913 (too-many-arguments)
    *,
    from_email: str,
    from_name: str,
    to_email: str,
    to_name: str,
    reply_email: str,
    reply_name: str,
    subject: str,
    html_content: str,
    text_content: str,
) -> TransactionEmailResponse:
    """Build and send email, return mail_body and response_str."""
    ms = MailerSendClient(api_key=settings.mailersend_api_key)

    # Build email using the new EmailBuilder pattern
    email = (
        EmailBuilder()
        .from_email(from_email, from_name)
        .to_many([{"email": to_email, "name": to_name or to_email}])
        .reply_to(reply_email, reply_name)
        .subject(subject)
        .html(html_content)
        .text(text_content)
        .build()
    )

    # Send the email
    response = ms.emails.send(email)

    # Create mail_body dict for backward compatibility
    mail_body: MailBodyType = {
        "from": {"name": from_name, "email": from_email},
        "to": [{"name": to_name or to_email, "email": to_email}],
        "reply_to": {"name": reply_name, "email": reply_email},
        "subject": subject,
        "html_content": html_content,
        "text_content": text_content,
    }

    # Check response status
    if response.success:
        response_str = f"{response.status_code}\n"
    else:
        response_str = f"Error {response.status_code}: {response.data}\n"
        logger.error("Failed to send email: %s\n\nProblematic email: %s", response_str, mail_body)

    return mail_body, response_str
