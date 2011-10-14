from flaskext.wtf import *
from flask import request

from wtforms.widgets import html_params
from models import Project, Person, Bill, db
from datetime import datetime
from jinja2 import Markup
from utils import slugify


def select_multi_checkbox(field, ul_class='', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<ul %s>' % html_params(id=field_id, class_="inputs-list")]
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(u'<li><label for="%s">%s<span>%s</span></label></li>' % (choice_id, '<input %s /> ' % html_params(**options), label))
    html.append(u'</ul>')
    return u''.join(html)


def get_billform_for(project, set_default=True, **kwargs):
    """Return an instance of BillForm configured for a particular project.

    :set_default: if set to True, on GET methods (usually when we want to 
                  display the default form, it will call set_default on it.
    
    """
    form = BillForm(**kwargs)
    form.payed_for.choices = form.payer.choices = [(m.id, m.name) for m in project.active_members]
    form.payed_for.default = [m.id for m in project.active_members]

    if set_default and request.method == "GET":
        form.set_default()
    return form



class EditProjectForm(Form):
    name = TextField("Project name", validators=[Required()])
    password = TextField("Private code", validators=[Required()])
    contact_email = TextField("Email", validators=[Required(), Email()])
    submit = SubmitField("Edit the project")

    def save(self):
        """Create a new project with the information given by this form.

        Returns the created instance
        """
        project = Project(name=self.name.data, id=self.id.data, 
                password=self.password.data, 
                contact_email=self.contact_email.data)
        return project

    def update(self, project):
        """Update the project with the information from the form"""
        project.name = self.name.data
        project.password = self.password.data
        project.contact_email = self.contact_email.data

        return project


class ProjectForm(EditProjectForm):
    id = TextField("Project identifier", validators=[Required()])
    password = PasswordField("Private code", validators=[Required()])
    submit = SubmitField("Create the project")

    def validate_id(form, field):
        form.id.data = slugify(field.data)
        if Project.query.get(form.id.data):
            raise ValidationError(Markup("""The project identifier is used
                                  to log in and for the URL of the project.
                                  We tried to generate an identifier for you but
                                  a project with this identifier already exists.
                                  Please create a new identifier you will be able
                                  to remember.
                                  """))


class AuthenticationForm(Form):
    id = TextField("Project identifier", validators=[Required()])
    password = PasswordField("Private code", validators=[Required()])
    submit = SubmitField("Get in")


class PasswordReminder(Form):
    id = TextField("Project identifier", validators=[Required()])
    submit = SubmitField("Send me the code by email")

    def validate_id(form, field):
        if not Project.query.get(field.data):
            raise ValidationError("This project does not exists")



class BillForm(Form):
    date = DateField("Date", validators=[Required()], default=datetime.now)
    what = TextField("What?", validators=[Required()])
    payer = SelectField("Payer", validators=[Required()], coerce=int)
    amount = DecimalField("Amount payed", validators=[Required()])
    payed_for = SelectMultipleField("Who has to pay for this?", 
            validators=[Required()], widget=select_multi_checkbox, coerce=int)
    submit = SubmitField("Send the bill")

    def save(self, bill, project):
        bill.payer_id=self.payer.data
        bill.amount=self.amount.data
        bill.what=self.what.data
        bill.date=self.date.data
        bill.owers = [Person.query.get(ower, project) 
                for ower in self.payed_for.data]

        return bill

    def fill(self, bill):
        self.payer.data = bill.payer_id
        self.amount.data = bill.amount
        self.what.data = bill.what
        self.date.data = bill.date
        self.payed_for.data = [str(ower.id) for ower in bill.owers]

    def set_default(self):
        self.payed_for.data = self.payed_for.default


class MemberForm(Form):

    name = TextField("Name", validators=[Required()])
    submit = SubmitField("Add a member")

    def __init__(self, project, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.project = project

    def validate_name(form, field):
        if Person.query.filter(Person.name == field.data)\
                .filter(Person.project == form.project)\
                .filter(Person.activated == True).all():
            raise ValidationError("This project already have this member")

    def save(self, project, person):
        # if the user is already bound to the project, just reactivate him
        person.name = self.name.data
        person.project = project

        return person

class InviteForm(Form):
    emails = TextAreaField("People to notify")
    submit = SubmitField("Send invites")

    def validate_emails(form, field):
        validator = Email()
        for email in [email.strip() for email in form.emails.data.split(",")]:
            if not validator.regex.match(email):
                raise ValidationError("The email %s is not valid" % email)


class CreateArchiveForm(Form):
    start_date = DateField("Start date", validators=[Required(),])
    end_date = DateField("End date", validators=[Required(),])
    name = TextField("Name for this archive (optional)")
