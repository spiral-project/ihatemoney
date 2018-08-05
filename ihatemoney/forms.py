from flask_wtf.form import FlaskForm
from wtforms.fields.core import SelectField, SelectMultipleField
from wtforms.fields.html5 import DateField, DecimalField
from wtforms.fields.simple import PasswordField, SubmitField, TextAreaField, StringField
from wtforms.validators import Email, Required, ValidationError, EqualTo, NumberRange
from flask_babel import lazy_gettext as _
from flask import request
from werkzeug.security import generate_password_hash

from datetime import datetime
from jinja2 import Markup

import email_validator

from ihatemoney.models import Project, Person
from ihatemoney.utils import slugify


def get_billform_for(project, set_default=True, **kwargs):
    """Return an instance of BillForm configured for a particular project.

    :set_default: if set to True, on GET methods (usually when we want to
                  display the default form, it will call set_default on it.

    """
    form = BillForm(**kwargs)
    active_members = [(m.id, m.name) for m in project.active_members]

    form.payed_for.choices = form.payer.choices = active_members
    form.payed_for.default = [m.id for m in project.active_members]

    if set_default and request.method == "GET":
        form.set_default()
    return form


class CommaDecimalField(DecimalField):

    """A class to deal with comma in Decimal Field"""

    def process_formdata(self, value):
        if value:
            value[0] = str(value[0]).replace(',', '.')
        return super(CommaDecimalField, self).process_formdata(value)


class EditProjectForm(FlaskForm):
    name = StringField(_("Project name"), validators=[Required()])
    password = StringField(_("Private code"), validators=[Required()])
    contact_email = StringField(_("Email"), validators=[Required(), Email()])

    def save(self):
        """Create a new project with the information given by this form.

        Returns the created instance
        """
        project = Project(name=self.name.data, id=self.id.data,
                          password=generate_password_hash(self.password.data),
                          contact_email=self.contact_email.data)
        return project

    def update(self, project):
        """Update the project with the information from the form"""
        project.name = self.name.data
        project.password = generate_password_hash(self.password.data)
        project.contact_email = self.contact_email.data

        return project


class ProjectForm(EditProjectForm):
    id = StringField(_("Project identifier"), validators=[Required()])
    password = PasswordField(_("Private code"), validators=[Required()])
    submit = SubmitField(_("Create the project"))

    def validate_id(form, field):
        form.id.data = slugify(field.data)
        if (form.id.data == "dashboard") or Project.query.get(form.id.data):
            message = _("The project identifier is used to log in and for the "
                        "URL of the project. "
                        "We tried to generate an identifier for you but a "
                        "project with this identifier already exists. "
                        "Please create a new identifier that you will be able "
                        "to remember")
            raise ValidationError(Markup(message))


class AuthenticationForm(FlaskForm):
    id = StringField(_("Project identifier"), validators=[Required()])
    password = PasswordField(_("Private code"), validators=[Required()])
    submit = SubmitField(_("Get in"))


class AdminAuthenticationForm(FlaskForm):
    admin_password = PasswordField(_("Admin password"), validators=[Required()])
    submit = SubmitField(_("Get in"))


class PasswordReminder(FlaskForm):
    id = StringField(_("Project identifier"), validators=[Required()])
    submit = SubmitField(_("Send me the code by email"))

    def validate_id(form, field):
        if not Project.query.get(field.data):
            raise ValidationError(_("This project does not exists"))


class ResetPasswordForm(FlaskForm):
    password_validators = [Required(),
                           EqualTo('password_confirmation', message=_("Password mismatch"))]
    password = PasswordField(_("Password"), validators=password_validators)
    password_confirmation = PasswordField(_("Password confirmation"), validators=[Required()])
    submit = SubmitField(_("Reset password"))


class BillForm(FlaskForm):
    date = DateField(_("Date"), validators=[Required()], default=datetime.now)
    what = StringField(_("What?"), validators=[Required()])
    payer = SelectField(_("Payer"), validators=[Required()], coerce=int)
    amount = CommaDecimalField(_("Amount paid"), validators=[Required()])
    payed_for = SelectMultipleField(_("For whom?"),
                                    validators=[Required()], coerce=int)
    submit = SubmitField(_("Submit"))
    submit2 = SubmitField(_("Submit and add a new one"))

    def save(self, bill, project):
        bill.payer_id = self.payer.data
        bill.amount = self.amount.data
        bill.what = self.what.data
        bill.date = self.date.data
        bill.owers = [Person.query.get(ower, project)
                      for ower in self.payed_for.data]

        return bill

    def fill(self, bill):
        self.payer.data = bill.payer_id
        self.amount.data = bill.amount
        self.what.data = bill.what
        self.date.data = bill.date
        self.payed_for.data = [int(ower.id) for ower in bill.owers]

    def set_default(self):
        self.payed_for.data = self.payed_for.default

    def validate_amount(self, field):
        if field.data == 0:
            raise ValidationError(_("Bills can't be null"))


class MemberForm(FlaskForm):
    name = StringField(_("Name"), validators=[Required()])

    weight_validators = [NumberRange(min=0.1, message=_("Weights should be positive"))]
    weight = CommaDecimalField(_("Weight"), default=1,
                               validators=weight_validators)
    submit = SubmitField(_("Add"))

    def __init__(self, project, edit=False, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.project = project
        self.edit = edit

    def validate_name(form, field):
        if field.data == form.name.default:
            raise ValidationError(_("User name incorrect"))
        if (not form.edit and Person.query.filter(
                Person.name == field.data,
                Person.project == form.project,
                Person.activated == True).all()):  # NOQA
            raise ValidationError(_("This project already have this member"))

    def save(self, project, person):
        # if the user is already bound to the project, just reactivate him
        person.name = self.name.data
        person.project = project
        person.weight = self.weight.data

        return person

    def fill(self, member):
        self.name.data = member.name
        self.weight.data = member.weight


class InviteForm(FlaskForm):
    emails = TextAreaField(_("People to notify"))
    submit = SubmitField(_("Send invites"))

    def validate_emails(form, field):
        for email in [email.strip() for email in form.emails.data.split(",")]:
            try:
                email_validator.validate_email(email)
            except email_validator.EmailNotValidError:
                raise ValidationError(_("The email %(email)s is not valid",
                                        email=email))


class ExportForm(FlaskForm):
    export_type = SelectField(
        _("What do you want to download ?"),
        validators=[Required()],
        coerce=str,
        choices=[("bills", _("bills")), ("transactions", _("transactions"))])
    export_format = SelectField(
        _("Export file format"),
        validators=[Required()],
        coerce=str,
        choices=[("csv", "csv"), ("json", "json")])
