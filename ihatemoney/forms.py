from flask_wtf.form import FlaskForm
from wtforms.fields.core import SelectField, SelectMultipleField
from wtforms.fields.html5 import DateField, DecimalField, URLField
from wtforms.fields.simple import PasswordField, SubmitField, StringField
from wtforms.validators import (
    Email,
    DataRequired,
    ValidationError,
    EqualTo,
    NumberRange,
    Optional,
)
from flask_wtf.file import FileField, FileAllowed, FileRequired

from flask_babel import lazy_gettext as _
from flask import request
from werkzeug.security import generate_password_hash

from datetime import datetime
from re import match
from jinja2 import Markup

import email_validator

from ihatemoney.models import Project, Person
from ihatemoney.utils import slugify, eval_arithmetic_expression, LoggingMode


def strip_filter(string):
    try:
        return string.strip()
    except Exception:
        return string


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
            value[0] = str(value[0]).replace(",", ".")
        return super(CommaDecimalField, self).process_formdata(value)


class CalculatorStringField(StringField):
    """
    A class to deal with math ops (+, -, *, /)
    in StringField
    """

    def process_formdata(self, valuelist):
        if valuelist:
            message = _(
                "Not a valid amount or expression. "
                "Only numbers and + - * / operators "
                "are accepted."
            )
            value = str(valuelist[0]).replace(",", ".")

            # avoid exponents to prevent expensive calculations i.e 2**9999999999**9999999
            if not match(r"^[ 0-9\.\+\-\*/\(\)]{0,200}$", value) or "**" in value:
                raise ValueError(Markup(message))

            valuelist[0] = str(eval_arithmetic_expression(value))

        return super(CalculatorStringField, self).process_formdata(valuelist)


class EditProjectForm(FlaskForm):
    name = StringField(_("Project name"), validators=[DataRequired()])
    password = StringField(_("Private code"), validators=[DataRequired()])
    contact_email = StringField(_("Email"), validators=[DataRequired(), Email()])
    logging_preferences = SelectField(
        _("Logging Preferences"),
        choices=LoggingMode.choices(),
        coerce=LoggingMode.coerce,
        default=LoggingMode.default(),
    )

    def save(self):
        """Create a new project with the information given by this form.

        Returns the created instance
        """
        project = Project(
            name=self.name.data,
            id=self.id.data,
            password=generate_password_hash(self.password.data),
            contact_email=self.contact_email.data,
            logging_preference=self.logging_preferences.data,
        )
        return project

    def update(self, project):
        """Update the project with the information from the form"""
        project.name = self.name.data
        project.password = generate_password_hash(self.password.data)
        project.contact_email = self.contact_email.data
        project.logging_preference = self.logging_preferences.data

        return project


class UploadForm(FlaskForm):
    file = FileField(
        "JSON", validators=[FileRequired(), FileAllowed(["json", "JSON"], "JSON only!")]
    )


class ProjectForm(EditProjectForm):
    id = StringField(_("Project identifier"), validators=[DataRequired()])
    password = PasswordField(_("Private code"), validators=[DataRequired()])
    submit = SubmitField(_("Create the project"))

    def validate_id(form, field):
        form.id.data = slugify(field.data)
        if (form.id.data == "dashboard") or Project.query.get(form.id.data):
            message = _(
                'A project with this identifier ("%(project)s") already exists. '
                "Please choose a new identifier",
                project=form.id.data,
            )
            raise ValidationError(Markup(message))


class AuthenticationForm(FlaskForm):
    id = StringField(_("Project identifier"), validators=[DataRequired()])
    password = PasswordField(_("Private code"), validators=[DataRequired()])
    submit = SubmitField(_("Get in"))


class AdminAuthenticationForm(FlaskForm):
    admin_password = PasswordField(_("Admin password"), validators=[DataRequired()])
    submit = SubmitField(_("Get in"))


class PasswordReminder(FlaskForm):
    id = StringField(_("Project identifier"), validators=[DataRequired()])
    submit = SubmitField(_("Send me the code by email"))

    def validate_id(form, field):
        if not Project.query.get(field.data):
            raise ValidationError(_("This project does not exists"))


class ResetPasswordForm(FlaskForm):
    password_validators = [
        DataRequired(),
        EqualTo("password_confirmation", message=_("Password mismatch")),
    ]
    password = PasswordField(_("Password"), validators=password_validators)
    password_confirmation = PasswordField(
        _("Password confirmation"), validators=[DataRequired()]
    )
    submit = SubmitField(_("Reset password"))


class BillForm(FlaskForm):
    date = DateField(_("Date"), validators=[DataRequired()], default=datetime.now)
    what = StringField(_("What?"), validators=[DataRequired()])
    payer = SelectField(_("Payer"), validators=[DataRequired()], coerce=int)
    amount = CalculatorStringField(_("Amount paid"), validators=[DataRequired()])
    external_link = URLField(
        _("External link"),
        validators=[Optional()],
        description=_("A link to an external document, related to this bill"),
    )
    payed_for = SelectMultipleField(
        _("For whom?"), validators=[DataRequired()], coerce=int
    )
    submit = SubmitField(_("Submit"))
    submit2 = SubmitField(_("Submit and add a new one"))

    def save(self, bill, project):
        bill.payer_id = self.payer.data
        bill.amount = self.amount.data
        bill.what = self.what.data
        bill.external_link = self.external_link.data
        bill.date = self.date.data
        bill.owers = [Person.query.get(ower, project) for ower in self.payed_for.data]
        return bill

    def fake_form(self, bill, project):
        bill.payer_id = self.payer
        bill.amount = self.amount
        bill.what = self.what
        bill.external_link = ""
        bill.date = self.date
        bill.owers = [Person.query.get(ower, project) for ower in self.payed_for]

        return bill

    def fill(self, bill):
        self.payer.data = bill.payer_id
        self.amount.data = bill.amount
        self.what.data = bill.what
        self.external_link.data = bill.external_link
        self.date.data = bill.date
        self.payed_for.data = [int(ower.id) for ower in bill.owers]

    def set_default(self):
        self.payed_for.data = self.payed_for.default

    def validate_amount(self, field):
        if field.data == 0:
            raise ValidationError(_("Bills can't be null"))


class MemberForm(FlaskForm):
    name = StringField(_("Name"), validators=[DataRequired()], filters=[strip_filter])

    weight_validators = [NumberRange(min=0.1, message=_("Weights should be positive"))]
    weight = CommaDecimalField(_("Weight"), default=1, validators=weight_validators)
    submit = SubmitField(_("Add"))

    def __init__(self, project, edit=False, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.project = project
        self.edit = edit

    def validate_name(form, field):
        if field.data == form.name.default:
            raise ValidationError(_("User name incorrect"))
        if (
            not form.edit
            and Person.query.filter(
                Person.name == field.data,
                Person.project == form.project,
                Person.activated == True,
            ).all()
        ):  # NOQA
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
    emails = StringField(_("People to notify"), render_kw={"class": "tag"})
    submit = SubmitField(_("Send invites"))

    def validate_emails(form, field):
        for email in [email.strip() for email in form.emails.data.split(",")]:
            try:
                email_validator.validate_email(email)
            except email_validator.EmailNotValidError:
                raise ValidationError(
                    _("The email %(email)s is not valid", email=email)
                )
