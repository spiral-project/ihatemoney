from flaskext.wtf import *

# define forms
class CreationForm(Form):
    name = TextField("Project name", validators=[Required()])
    id = TextField("Project identifier", validators=[Required()])
    password = PasswordField("Password", validators=[Required()])
    contact_email = TextField("Email", validators=[Required(), Email()])
    submit = SubmitField("Get in")


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

