from flaskext.wtf import *
from models import Project, Person

# define forms
class ProjectForm(Form):
    name = TextField("Project name", validators=[Required()])
    id = TextField("Project identifier", validators=[Required()])
    password = PasswordField("Password", validators=[Required()])
    contact_email = TextField("Email", validators=[Required(), Email()])
    submit = SubmitField("Get in")

    def save(self):
        """Create a new project with the information given by this form.

        Returns the created instance
        """
        project = Project(name=self.name.data, id=self.id.data, 
                password=self.password.data, 
                contact_email=self.contact_email.data)
        return project


class AuthenticationForm(Form):
    password = TextField("Password", validators=[Required()])
    submit = SubmitField("Get in")


class BillForm(Form):
    what = TextField("What?", validators=[Required()])
    payer = SelectField("Payer", validators=[Required()])
    amount = DecimalField("Amount payed", validators=[Required()])
    payed_for = SelectMultipleField("Who has to pay for this?", 
            validators=[Required()])
    submit = SubmitField("Add the bill")


class MemberForm(Form):
    def __init__(self, project, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.project = project

    name = TextField("Name", validators=[Required()])
    submit = SubmitField("Add a member")

    def validate_name(form, field):
        if Person.query.filter(
                Person.name == field.data and Person.project == self.project).all():
            raise ValidationError("This project already have this member")
