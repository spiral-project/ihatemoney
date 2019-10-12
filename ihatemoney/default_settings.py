# Verbose and documented settings are in conf-templates/ihatemoney.cfg.j2
DEBUG = SQLACHEMY_ECHO = False
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ihatemoney.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "tralala"
MAIL_DEFAULT_SENDER = ("Budget manager", "budget@notmyidea.org")
ACTIVATE_DEMO_PROJECT = True
ADMIN_PASSWORD = ""
ALLOW_PUBLIC_PROJECT_CREATION = True
ACTIVATE_ADMIN_DASHBOARD = False
SUPPORTED_LANGUAGES = ['en', 'fr', 'de', 'nl', 'es_419']
