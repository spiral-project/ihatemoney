from flaskext.wtf import *
from wtforms.widgets import html_params
from models import Project, Person, Bill
from datetime import datetime


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


class ProjectForm(Form):
    name = TextField("Project name", validators=[Required()])
    id = TextField("Project identifier", validators=[Required()])
    password = PasswordField("Password", validators=[Required()])
    contact_email = TextField("Email", validators=[Required(), Email()])
    submit = SubmitField("Create the project")

    def validate_id(form, field):
        if Project.query.get(field.data):
            raise ValidationError("This project id is already used")

    def save(self):
        """Create a new project with the information given by this form.

        Returns the created instance
        """
        project = Project(name=self.name.data, id=self.id.data, 
                password=self.password.data, 
                contact_email=self.contact_email.data)
        return project


class AuthenticationForm(Form):
    id = TextField("Project identifier", validators=[Required()])
    password = PasswordField("Password", validators=[Required()])
    submit = SubmitField("Get in")


class BillForm(Form):
    date = DateField("Date", validators=[Required()], default=datetime.now)
    what = TextField("What?", validators=[Required()])
    payer = SelectField("Payer", validators=[Required()])
    amount = DecimalField("Amount payed", validators=[Required()])
    payed_for = SelectMultipleField("Who has to pay for this?", 
            validators=[Required()], widget=select_multi_checkbox)
    submit = SubmitField("Send the bill")

    def save(self, bill):
        bill.payer_id=self.payer.data
        bill.amount=self.amount.data
        bill.what=self.what.data
        bill.date=self.date.data
        bill.owers = [Person.query.get(ower) for ower in self.payed_for.data]

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
    def __init__(self, project, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.project = project

    name = TextField("Name", validators=[Required()])
    submit = SubmitField("Add a member")

    def validate_name(form, field):
        if Person.query.filter(Person.name == field.data)\
                .filter(Person.project == form.project).all():
            raise ValidationError("This project already have this member")


class InviteForm(Form):
    emails = TextAreaField("People to notify")
    submit = SubmitField("Send invites")

    def validate_emails(form, field):
        validator = Email()
        for email in [email.strip() for email in form.emails.data.split(",")]:
            if not validator.regex.match(email):
                raise ValidationError("The email %s is not valid" % email)

