DEBUG = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///budget.db'
SQLACHEMY_ECHO = DEBUG
# Will likely become the default value in flask-sqlalchemy >=3 ; could be removed
# then:
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = "tralala"

MAIL_DEFAULT_SENDER = ("Budget manager", "budget@notmyidea.org")

ACTIVATE_DEMO_PROJECT = True

ADMIN_PASSWORD = "pbkdf2:sha256:50000$jc3isZTD$b3be8d04ed5c2c1ac89d5eb777facc94adaee48d473c9620f1e0cb73f3dcfa11"

ALLOW_PUBLIC_PROJECT_CREATION = True

ACTIVATE_DASHBOARD = False
