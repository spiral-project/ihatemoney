from flask import g, render_template
from flask_babel import gettext as _
from flask_mail import Message

from ihatemoney.utils import send_email


def send_creation_email(project):
    g.project = project
    message_title = _(
        "You have just created '%(project)s' " "to share your expenses",
        project=project.name,
    )

    message_body = render_template("reminder_mail.j2", project=project)

    msg = Message(message_title, body=message_body, recipients=[project.contact_email])
    return send_email(msg)
