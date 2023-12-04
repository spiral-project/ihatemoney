from flask import g
from flask_babel import gettext as _
from flask_mail import Message

from ihatemoney.utils import render_localized_template, send_email


def send_creation_email(project):
    g.project = project
    message_title = _(
        "You have just created '%(project)s' " "to share your expenses",
        project=project.name,
    )

    message_body = render_localized_template("reminder_mail", project=project)

    msg = Message(message_title, body=message_body, recipients=[project.contact_email])
    return send_email(msg)
