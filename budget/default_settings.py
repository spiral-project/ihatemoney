DEBUG = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///budget.db'
SQLACHEMY_ECHO = DEBUG
SECRET_KEY = "tralala"

MAIL_DEFAULT_SENDER = ("Budget manager", "budget@notmyidea.org")

try:
    from settings import *
except ImportError:
    pass
