from email.message import EmailMessage
from .exception import ConfigError
from imaplib import IMAP4_SSL
from re import compile
from smtplib import SMTP
from email import message_from_bytes
from pathlib import Path
from os import path, makedirs
from imghdr import what
import typer
import json
import errno


app = typer.Typer()
APP_NAME = 'mailsy'


class Mailsy:

    def __init__(self):
        self.smtp = 'smtp.gmail.com'
        self.smtp_port = 587
        self.app_name = 'mailsy'
        self.senders_name_re = compile('(.*)<')
        self._config()

    def _config(self):
        app_dir = typer.get_app_dir(APP_NAME)
        config_path: Path = Path(app_dir) / "config.json"
        if not config_path.is_file():
            raise ConfigError('Config file not found! Please setup')

        with open(config_path, 'r') as configs:
            configs_dict = json.load(configs)

        self.email_id = configs_dict['EMAIL_ID']
        self.email_pass = configs_dict['EMAIL_PASS']
        self.columns = int(configs_dict['COLUMNS']) - 12
        self.inbox_size = configs_dict['EMAIL_INBOX_SIZE']
        self.from_width = int(self.columns*0.25)

    def _setup_config(self, email, password):
        json_configs = json.dumps({
            'EMAIL_ID': email,
            'EMAIL_PASS': password,
            'EMAIL_INBOX_SIZE': 10,
            'COLUMNS': 113
        }, indent=4)
        app_dir = typer.get_app_dir(APP_NAME)
        config_path: Path = Path(app_dir) / "config.json"

        if not path.exists(path.dirname(config_path)):
            try:
                makedirs(path.dirname(config_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        with open(config_path, "w") as config:
            config.write(json_configs)

    def list_email(self, page=1):
        mail = IMAP4_SSL(self.smtp)
        mail.login(self.email_id, self.email_pass)
        mail.select('inbox')
        subject_width = self.columns - self.from_width
        page -= 1

        _, data = mail.search(None, 'ALL')
        mail_ids = data[0]
        id_list = mail_ids.split()
        latest_email_id = int(id_list[-1]) - self.inbox_size*page
        first_email_id = max(latest_email_id-self.inbox_size, 0)

    def _send_email(self, body: str, subject: str, email_id: str, attach_data: str = None, attach_name: str = None, attach_type: str = None):
        server = SMTP(self.smtp, self.smtp_port)
        server.starttls()
        server.login(self.email_id, self.email_pass)
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = self.email_id
        msg['To'] = email_id
        if attach_data:
            msg.add_attachment(attach_data, maintype='image',
                               subtype=attach_type, filename=attach_name)
        server.sendmail(self.email_id, email_id, msg.as_string())
        server.quit()


@app.command()
def setup():
    email = typer.prompt(typer.style(
        "\n\tEmail: ", fg=typer.colors.MAGENTA, bold=True))
    password = typer.prompt(typer.style(
        "\n\tPassword: ", fg=typer.colors.MAGENTA, bold=True), hide_input=True)

    json_configs = json.dumps({
        'EMAIL_ID': email,
        'EMAIL_PASS': password,
        'EMAIL_INBOX_SIZE': 10,
        'COLUMNS': 113
    }, indent=4)
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


@app.command()
def list(page: int = 1):
    config = load_config()
    mail = IMAP4_SSL('imap.gmail.com')
    mail.login(config['EMAIL_ID'], config['EMAIL_PASS'])
    mail.select('inbox')

    # SETTINGS
    inbox_size = int(config['EMAIL_INBOX_SIZE'])
    columns = int(config['COLUMNS']) - 12
    senders_name = compile('(.*)<')
    from_width = int(columns*0.25)
    subject_width = columns - from_width
    page = page - 1

    # Getting ids
    _, data = mail.search(None, 'ALL')
    mail_ids = data[0]
    id_list = mail_ids.split()
    latest_email_id = int(id_list[-1]) - inbox_size*page
    first_email_id = max(latest_email_id-inbox_size, 0)

    for i in range(latest_email_id, first_email_id, -1):
        _, data = mail.fetch(str(i), '(RFC822)')
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = message_from_bytes(response_part[1])
                email_from_raw = senders_name.search(
                    msg['from']).group(1).ljust(from_width)
                email_subject = msg['subject'][:60].ljust(subject_width)
                email_from = typer.style(
                    email_from_raw, fg=typer.colors.MAGENTA, bold=True)
                typer.echo("[" + str(i-first_email_id) + "]\t" +
                           email_from + "\t" + email_subject)


@app.command()
def send():
    config = load_config()
    email_id = typer.prompt(typer.style(
        "\n\tRecipent(s) ", fg=typer.colors.MAGENTA, bold=True))
    subject = typer.prompt(typer.style(
        "\tSubject ", fg=typer.colors.MAGENTA, bold=True))
    body = typer.prompt(typer.style(
        "\tBody ", fg=typer.colors.MAGENTA, bold=True))
    attach = typer.confirm(typer.style(
        "\tAttach Files?", fg=typer.colors.BLUE, bold=True))
    if attach:
        attachment = typer.prompt(typer.style(
            "\tAttachment (path) ", fg=typer.colors.MAGENTA, bold=True))
        attach_data, attach_type, attach_name = get_attachment(attachment)
    send = typer.confirm(typer.style(
        "\tSend it?", fg=typer.colors.MAGENTA, bold=True))

    if(send):
        try:
            # Connect to GMAIL
            server = SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(config['EMAIL_ID'], config['EMAIL_PASS'])
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = config['EMAIL_ID']
            msg['To'] = email_id

            if attach:
                msg.add_attachment(attach_data, maintype='image',
                                   subtype=attach_type, filename=attach_name)

            server.sendmail(config['EMAIL_ID'], email_id, msg.as_string())

            typer.echo(typer.style("\n\tEmail Sent!",
                       fg=typer.colors.GREEN, bold=True))
        except:
            typer.echo(typer.style("\n\tThere was a problem sending you mail!",
                                   fg=typer.colors.RED, bold=True))
        finally:
            server.quit()
    else:
        typer.echo(typer.style("\n\tEmail was not Sent!",
                   fg=typer.colors.RED, bold=True))


def load_config():
    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config.json"
    if not config_path.is_file():
        typer.echo(typer.style("\n\tCan not load config file!",
                               fg=typer.colors.RED, bold=True), err=True)
        raise typer.Exit()

    with open(config_path, 'r') as configs:
        configs_dict = json.load(configs)
    return configs_dict


def get_attachment(attachment_path):
    attachment_path: Path = Path(attachment_path)
    if not attachment_path.is_file():
        typer.echo(typer.style("\n\tCan not find attachment!",
                   fg=typer.colors.RED, bold=True), err=True)

    with open(attachment_path, 'rb') as file:
        image_data = file.read()
        image_type = what(file.name)
        image_name = file.name

    return image_data, image_type, image_name


if __name__ == "__main__":
    app()
