DEBUG = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///budget.db'
SQLACHEMY_ECHO = DEBUG
SECRET_KEY = "tralala"

DEFAULT_MAIL_SENDER = ("Budget manager", "budget@notmyidea.org")

try:
    from settings import *
except ImportError:
    pass
