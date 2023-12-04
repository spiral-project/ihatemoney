from datetime import datetime
import decimal
from re import match
from types import SimpleNamespace

import email_validator
from flask import request
from flask_babel import lazy_gettext as _
from flask_wtf.file import FileAllowed, FileField, FileRequired
from flask_wtf.form import FlaskForm
from markupsafe import Markup
from werkzeug.security import check_password_hash
from wtforms.fields import (
    BooleanField,
    DateField,
    DecimalField,
    Label,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)

try:
    # Compat for WTForms <= 2.3.3
    from wtforms.fields.html5 import URLField
except ModuleNotFoundError:
    from wtforms.fields import URLField

from wtforms.validators import (
    URL,
    DataRequired,
    Email,
    EqualTo,
    NumberRange,
    Optional,
    ValidationError,
)

from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.models import Bill, LoggingMode, Person, Project
from ihatemoney.utils import (
    em_surround,
    eval_arithmetic_expression,
    generate_password_hash,
    render_localized_currency,
    slugify,
)


def strip_filter(string):
    try:
        return string.strip()
    except Exception:
        return string


def get_billform_for(project, set_default=True, **kwargs):
    """Return an instance of BillForm configured for a particular project.

    :set_default: if set to True, it will call set_default on GET methods (usually
                  when we want to display the default form).

    """
    form = BillForm(**kwargs)
    if form.original_currency.data is None:
        form.original_currency.data = project.default_currency

    # Used in validate_original_currency
    form.project_currency = project.default_currency

    show_no_currency = form.original_currency.data == CurrencyConverter.no_currency

    form.original_currency.choices = [
        (currency_name, render_localized_currency(currency_name, detailed=False))
        for currency_name in form.currency_helper.get_currencies(
            with_no_currency=show_no_currency
        )
    ]

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
    current_password = PasswordField(
        _("Current private code"),
        description=_("Enter existing private code to edit project"),
        validators=[DataRequired()],
    )
    # If empty -> don't change the password
    password = PasswordField(
        _("New private code"),
        description=_("Enter a new code if you want to change it"),
    )
    contact_email = StringField(_("Email"), validators=[DataRequired(), Email()])
    project_history = BooleanField(_("Enable project history"))
    ip_recording = BooleanField(_("Use IP tracking for project history"))
    currency_helper = CurrencyConverter()
    default_currency = SelectField(
        _("Default Currency"),
        validators=[DataRequired()],
        default=CurrencyConverter.no_currency,
        description=_(
            "Setting a default currency enables currency conversion between bills"
        ),
    )

    def __init__(self, *args, **kwargs):
        if not hasattr(self, "id"):
            # We must access the project to validate the default currency, using its id.
            # In ProjectForm, 'id' is provided, but not in this base class, so it *must*
            # be provided by callers.
            # Since id can be defined as a WTForms.StringField, we mimics it,
            # using an object that can have a 'data' attribute.
            # It defaults to empty string to ensure that query run smoothly.
            self.id = SimpleNamespace(data=kwargs.pop("id", ""))
        super().__init__(*args, **kwargs)
        self.default_currency.choices = [
            (currency_name, render_localized_currency(currency_name, detailed=True))
            for currency_name in self.currency_helper.get_currencies()
        ]

    def validate_current_password(self, field):
        project = Project.query.get(self.id.data)
        if project is None:
            raise ValidationError(_("Unknown error"))
        if not check_password_hash(project.password, self.current_password.data):
            raise ValidationError(_("Invalid private code."))

    @property
    def logging_preference(self):
        """Get the LoggingMode object corresponding to current form data."""
        if not self.project_history.data:
            return LoggingMode.DISABLED
        else:
            if self.ip_recording.data:
                return LoggingMode.RECORD_IP
            else:
                return LoggingMode.ENABLED

    def validate_default_currency(self, field):
        project = Project.query.get(self.id.data)
        if (
            project is not None
            and field.data == CurrencyConverter.no_currency
            and project.has_multiple_currencies()
        ):
            msg = _(
                "This project cannot be set to 'no currency'"
                " because it contains bills in multiple currencies."
            )
            raise ValidationError(msg)
        if (
            project is not None
            and field.data != CurrencyConverter.no_currency
            and project.has_bills()
        ):
            msg = _(
                "Cannot change project currency because currency conversion is broken"
            )
            raise ValidationError(msg)

    def update(self, project):
        """Update the project with the information from the form"""
        project.name = self.name.data

        if (
            # Only update password if a new one is provided
            self.password.data
            # Only update password if different from the previous one,
            # to prevent spurious log entries
            and not check_password_hash(project.password, self.password.data)
        ):
            project.password = generate_password_hash(self.password.data)

        project.contact_email = self.contact_email.data
        project.logging_preference = self.logging_preference
        project.switch_currency(self.default_currency.data)

        return project


class ImportProjectForm(FlaskForm):
    file = FileField(
        "File",
        validators=[
            FileRequired(),
            FileAllowed(["json", "JSON", "csv", "CSV"], "Incorrect file format"),
        ],
        description=_("Compatible with Cospend"),
    )


class ProjectForm(EditProjectForm):
    id = StringField(_("Project identifier"), validators=[DataRequired()])
    # Remove this field that is inherited from EditProjectForm
    current_password = None
    # This field overrides the one from EditProjectForm (to make it mandatory)
    password = PasswordField(_("Private code"), validators=[DataRequired()])
    submit = SubmitField(_("Create the project"))

    def save(self):
        """Create a new project with the information given by this form.

        Returns the created instance
        """
        # WTForms Boolean Fields don't insert the default value when the
        # request doesn't include any value the way that other fields do,
        # so we'll manually do it here
        self.project_history.data = LoggingMode.default() != LoggingMode.DISABLED
        self.ip_recording.data = LoggingMode.default() == LoggingMode.RECORD_IP
        # Create project
        project = Project(
            name=self.name.data,
            id=self.id.data,
            password=generate_password_hash(self.password.data),
            contact_email=self.contact_email.data,
            logging_preference=self.logging_preference,
            default_currency=self.default_currency.data,
        )
        return project

    def validate_id(self, field):
        self.id.data = slugify(field.data)
        if (self.id.data == "dashboard") or Project.query.get(self.id.data):
            message = _(
                'A project with this identifier ("%(project)s") already exists. '
                "Please choose a new identifier",
                project=self.id.data,
            )
            raise ValidationError(Markup(message))


class ProjectFormWithCaptcha(ProjectForm):
    captcha = StringField(
        _("Which is a real currency: Euro or Petro dollar?"), default=""
    )

    def validate_captcha(self, field):
        if not field.data.lower() == _("euro").lower():
            message = _("Please, validate the captcha to proceed.")
            raise ValidationError(Markup(message))


class DestructiveActionProjectForm(FlaskForm):
    """Used for any important "delete" action linked to a project:

    - delete project itself
    - delete history
    - delete IP addresses in history

    It asks the participant to enter the private code to confirm deletion.
    """

    password = PasswordField(
        _("Private code"),
        description=_("Enter private code to confirm deletion"),
        validators=[DataRequired()],
    )

    def __init__(self, *args, **kwargs):
        # Same trick as EditProjectForm: we need to know the project ID
        self.id = SimpleNamespace(data=kwargs.pop("id", ""))
        super().__init__(*args, **kwargs)

    def validate_password(self, field):
        project = Project.query.get(self.id.data)
        if project is None:
            raise ValidationError(_("Unknown error"))
        if not check_password_hash(project.password, self.password.data):
            raise ValidationError(_("Invalid private code."))


class AuthenticationForm(FlaskForm):
    id = StringField(_("Project identifier"), validators=[DataRequired()])
    password = PasswordField(_("Private code"), validators=[DataRequired()])
    submit = SubmitField(_("Get in"))


class AdminAuthenticationForm(FlaskForm):
    admin_password = PasswordField(
        _("Admin password"), validators=[DataRequired()], render_kw={"autofocus": True}
    )
    submit = SubmitField(_("Get in"))


class PasswordReminder(FlaskForm):
    id = StringField(_("Project identifier"), validators=[DataRequired()])
    submit = SubmitField(_("Send me the code by email"))

    def validate_id(self, field):
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
    date = DateField(_("When?"), validators=[DataRequired()], default=datetime.now)
    what = StringField(_("What?"), validators=[DataRequired()])
    payer = SelectField(_("Who paid?"), validators=[DataRequired()], coerce=int)
    amount = CalculatorStringField(_("How much?"), validators=[DataRequired()])
    currency_helper = CurrencyConverter()
    original_currency = SelectField(_("Currency"), validators=[DataRequired()])
    external_link = URLField(
        _("External link"),
        default="",
        validators=[Optional(), URL()],
        description=_("A link to an external document, related to this bill"),
    )
    payed_for = SelectMultipleField(
        _("For whom?"), validators=[DataRequired()], coerce=int
    )
    submit = SubmitField(_("Submit"))
    submit2 = SubmitField(_("Submit and add a new one"))

    def export(self, project):
        return Bill(
            amount=float(self.amount.data),
            date=self.date.data,
            external_link=self.external_link.data,
            original_currency=str(self.original_currency.data),
            owers=Person.query.get_by_ids(self.payed_for.data, project),
            payer_id=self.payer.data,
            project_default_currency=project.default_currency,
            what=self.what.data,
        )

    def save(self, bill, project):
        bill.payer_id = self.payer.data
        bill.amount = self.amount.data
        bill.what = self.what.data
        bill.external_link = self.external_link.data
        bill.date = self.date.data
        bill.owers = Person.query.get_by_ids(self.payed_for.data, project)
        bill.original_currency = self.original_currency.data
        bill.converted_amount = self.currency_helper.exchange_currency(
            bill.amount, bill.original_currency, project.default_currency
        )
        return bill

    def fill(self, bill, project):
        self.payer.data = bill.payer_id
        self.amount.data = bill.amount
        self.what.data = bill.what
        self.external_link.data = bill.external_link
        self.original_currency.data = bill.original_currency
        self.date.data = bill.date
        self.payed_for.data = [int(ower.id) for ower in bill.owers]

        self.original_currency.label = Label("original_currency", _("Currency"))
        self.original_currency.description = _(
            "Project default: %(currency)s",
            currency=render_localized_currency(
                project.default_currency, detailed=False
            ),
        )

    def set_default(self):
        self.payed_for.data = self.payed_for.default

    def validate_amount(self, field):
        if decimal.Decimal(field.data) > decimal.MAX_EMAX:
            # See https://github.com/python-babel/babel/issues/821
            raise ValidationError(f"Result is too high: {field.data}")

    def validate_original_currency(self, field):
        # Workaround for currency API breakage
        # See #1232
        if field.data not in [CurrencyConverter.no_currency, self.project_currency]:
            msg = _(
                "Failed to convert from %(bill_currency)s currency to %(project_currency)s",
                bill_currency=field.data,
                project_currency=self.project_currency,
            )
            raise ValidationError(msg)


class MemberForm(FlaskForm):
    name = StringField(_("Name"), validators=[DataRequired()], filters=[strip_filter])

    weight_validators = [NumberRange(min=0.1, message=_("Weights should be positive"))]
    weight = CommaDecimalField(_("Weight"), default=1, validators=weight_validators)
    submit = SubmitField(_("Add"))

    def __init__(self, project, edit=False, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.project = project
        self.edit = edit

    def validate_name(self, field):
        if field.data == self.name.default:
            raise ValidationError(_("The participant name is invalid"))
        if (
            not self.edit
            and Person.query.filter(
                Person.name == field.data,
                Person.project == self.project,
                Person.activated,
            ).all()
        ):  # NOQA
            raise ValidationError(_("This project already have this participant"))

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
    submit = SubmitField(_("Send the invitations"))

    def validate_emails(self, field):
        for email in [email.strip() for email in self.emails.data.split(",")]:
            try:
                email_validator.validate_email(email)
            except email_validator.EmailNotValidError:
                raise ValidationError(
                    _("The email %(email)s is not valid", email=em_surround(email))
                )


class LogoutForm(FlaskForm):
    submit = SubmitField(_("Logout"))


class EmptyForm(FlaskForm):
    """Used for CSRF validation"""

    pass
