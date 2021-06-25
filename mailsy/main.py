from email.message import EmailMessage
from imaplib import IMAP4_SSL
import smtplib
from email import message_from_bytes
from mailsy.email_template import get_templated
from mailsy.utils import Config
from pathlib import Path
from os import path, makedirs
import typer
import json
import errno


app = typer.Typer()
APP_NAME = "mailsy"


@app.command()
def setup():
    """Setup gmail account
    asks for name, email, password
    stores it into config file in home
    """
    name = typer.prompt(typer.style("\n\tName: ", fg=typer.colors.MAGENTA, bold=True))
    email = typer.prompt(typer.style("\n\tEmail: ", fg=typer.colors.MAGENTA, bold=True))
    password = typer.prompt(
        typer.style("\n\tPassword: ", fg=typer.colors.MAGENTA, bold=True),
        hide_input=True,
    )
    use_template = typer.confirm(
        typer.style(
            "\tUse HTML Template for sending emails?", fg=typer.colors.BLUE, bold=True
        )
    )
    configs = {
        "EMAIL_ID": email,
        "EMAIL_PASS": password,
        "EMAIL_INBOX_SIZE": 10,
        "COLUMNS": 113,
        "NAME": name,
        "USE_TEMPLATE": use_template,
        "JOB_TITLE": None,
        "COMPANY": None,
        "CONTACT": None,
    }
    if use_template:
        job_title = typer.prompt(
            typer.style("\n\tJob Title: ", fg=typer.colors.MAGENTA, bold=True)
        )
        company = typer.prompt(
            typer.style("\n\tCompany Name: ", fg=typer.colors.MAGENTA, bold=True)
        )
        contact = typer.prompt(
            typer.style("\n\tContact No.: ", fg=typer.colors.MAGENTA, bold=True)
        )
        configs["JOB_TITLE"] = job_title
        configs["COMPANY"] = company
        configs["CONTACT"] = contact

    json_configs = json.dumps(
        configs,
        indent=4,
    )
    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.json"

    # Create config folder
    if not path.exists(path.dirname(config_path)):
        try:
            makedirs(path.dirname(config_path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    with open(config_path, "w") as config:
        config.write(json_configs)
    typer.echo(
        typer.style("\n\tConfigurations Updated!", fg=typer.colors.GREEN, bold=True)
    )


@app.command()
def list(page: int = 1):
    """List unread emails from inbox.
    Has pagination support.

    Args:
        page (int, optional): page number. Defaults to 1.
    """
    config = load_config()
    mail = IMAP4_SSL(config.imap_domain)
    mail.login(config.email_id, config.password)
    mail.select("inbox")
    page -= 1

    # Getting ids
    _, data = mail.search(None, "ALL")
    mail_ids = data[0]
    id_list = mail_ids.split()
    latest_email_id = int(id_list[-1]) - config.inbox_size * page
    first_email_id = max(latest_email_id - config.inbox_size, 0)

    for i in range(latest_email_id, first_email_id, -1):
        _, data = mail.fetch(str(i), "(RFC822)")
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = message_from_bytes(response_part[1])
                email_from_raw = (
                    config.senders_name.search(msg["from"])
                    .group(1)
                    .ljust(config.from_width)
                )
                email_subject = msg["subject"][:60].ljust(config.subject_width)
                email_from = typer.style(
                    email_from_raw, fg=typer.colors.MAGENTA, bold=True
                )
                typer.echo(
                    "["
                    + str(i - first_email_id)
                    + "]\t"
                    + email_from
                    + "\t"
                    + email_subject
                )


@app.command()
def send():
    """Command to send email
    can send with HTML template and attachments
    """
    config = load_config()
    email_id = typer.prompt(
        typer.style("\n\tRecipent(s) ", fg=typer.colors.MAGENTA, bold=True)
    )
    subject = typer.prompt(
        typer.style("\tSubject ", fg=typer.colors.MAGENTA, bold=True)
    )
    body = typer.prompt(typer.style("\tBody ", fg=typer.colors.MAGENTA, bold=True))
    attach = typer.confirm(
        typer.style("\tAttach Files?", fg=typer.colors.BLUE, bold=True)
    )
    if attach:
        attachment = typer.prompt(
            typer.style("\tAttachment (path) ", fg=typer.colors.MAGENTA, bold=True)
        )
        attach_data, attach_name = get_attachment(attachment)
    send = typer.confirm(typer.style("\tSend it?", fg=typer.colors.MAGENTA, bold=True))

    if send:
        try:
            # Connect to GMAIL
            server = smtplib.SMTP(config.smtp_domain, config.smtp_port)
            server.starttls()
            server.login(config.email_id, config.password)
            msg = EmailMessage()
            if config.use_template:
                msg.set_content(
                    get_templated(
                        {
                            "name": config.name,
                            "from": config.email_id,
                            "to": email_id,
                            "msg": body,
                            "job_title": config.job_title,
                            "company": config.company,
                            "contact": config.contact,
                        }
                    ),
                    subtype="html",
                )
            else:
                msg.set_content(body)
            msg["Subject"] = subject
            msg["From"] = config.email_id
            msg["To"] = email_id

            if attach:
                msg.add_attachment(
                    attach_data,
                    maintype="application",
                    subtype="octet-stream",
                    filename=attach_name,
                )

            server.sendmail(config.email_id, email_id, msg.as_string())

            typer.echo(typer.style("\n\tEmail Sent!", fg=typer.colors.GREEN, bold=True))
        except smtplib.SMTPRecipientsRefused:
            typer.echo(
                typer.style(
                    "\n\tInvalid Email! Please check the email!",
                    fg=typer.colors.RED,
                    bold=True,
                )
            )
        finally:
            server.quit()
    else:
        typer.echo(
            typer.style("\n\tEmail was not Sent!", fg=typer.colors.RED, bold=True)
        )


def load_config() -> Config:
    """loads configurations from config file

    Raises:
        typer.Exit: if config file is not fount

    Returns:
        dict: configurations
    """
    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.json"
    if not config_path.is_file():
        typer.echo(
            typer.style(
                "\n\tCan not load config file!", fg=typer.colors.RED, bold=True
            ),
            err=True,
        )
        raise typer.Exit()

    with open(config_path, "r") as configs:
        configs_dict = json.load(configs)
    return Config(**configs_dict)


def get_attachment(attachment_path: str) -> tuple:
    """Helper function to get attachment

    Args:
        attachment_path (path): path to attachment file

    Raises:
        typer.Exit: if file not founnd

    Returns:
        tuple: file_data, file_type, file_name
    """
    attachment_path: Path = Path(attachment_path)
    if not attachment_path.is_file():
        typer.echo(
            typer.style("\n\tCan not find attachment!", fg=typer.colors.RED, bold=True),
            err=True,
        )
        raise typer.Exit()

    with open(attachment_path, "rb") as file:
        file_data = file.read()
        file_name = path.basename(file.name)

    return file_data, file_name


if __name__ == "__main__":
    app()
