# You can find more information about what these settings mean in the
# documentation, available online at
# http://ihatemoney.readthedocs.io/en/latest/installation.html#configuration

# Turn this on if you want to have more output on what's happening under the
# hood.
DEBUG = False

# The database URI, reprensenting the type of database and how to connect to it.
# Enter an absolute path here.
SQLALCHEMY_DATABASE_URI = 'sqlite:///budget.db'
SQLACHEMY_ECHO = DEBUG

# Will likely become the default value in flask-sqlalchemy >=3 ; could be removed
# then:
SQLALCHEMY_TRACK_MODIFICATIONS = False

# You need to change this secret key, otherwise bad things might happen to your
# users.
SECRET_KEY = "tralala"

# A python tuple describing the name and email adress of the sender of the mails.
MAIL_DEFAULT_SENDER = ("Budget manager", "budget@notmyidea.org")

# If set to True, a demonstration project will be activated.
ACTIVATE_DEMO_PROJECT = True

# If not empty, the specified password must be entered to create new projects.
# DO NOT enter the password in cleartext. Generate a password hash with
# "ihatemoney generate_password_hash" instead.
ADMIN_PASSWORD = ""
