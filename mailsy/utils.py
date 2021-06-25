import re


class Config:
    def __init__(
        self,
        EMAIL_ID,
        EMAIL_PASS,
        EMAIL_INBOX_SIZE,
        COLUMNS,
        NAME,
        USE_TEMPLATE,
        JOB_TITLE,
        COMPANY,
        CONTACT,
    ):
        self.email_id = EMAIL_ID
        self.password = EMAIL_PASS
        self.inbox_size = EMAIL_INBOX_SIZE
        self.columns = int(COLUMNS)
        self.from_width = int((self.columns - 12) * 0.25)
        self.subject_width = self.columns - self.from_width - 12
        self.name = NAME
        self.senders_name = re.compile("(.*)<")
        self.imap_domain = "imap.gmail.com"
        self.smtp_domain = "smtp.gmail.com"
        self.smtp_port = 587
        self.use_template = USE_TEMPLATE
        self.job_title = JOB_TITLE
        self.company = COMPANY
        self.contact = CONTACT
