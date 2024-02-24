# Verbose and documented settings are in conf-templates/ihatemoney.cfg.j2
DEBUG = SQLACHEMY_ECHO = False
SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/ihatemoney.db"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "tralala"
MAIL_DEFAULT_SENDER = "Budget manager <admin@example.com>"
SHOW_ADMIN_EMAIL = True
ACTIVATE_DEMO_PROJECT = True
ACTIVATE_ADMIN_DASHBOARD = False
ADMIN_PASSWORD = ""
ALLOW_PUBLIC_PROJECT_CREATION = True
SESSION_COOKIE_SECURE = True
APPLICATION_ROOT = "/"
ENABLE_CAPTCHA = False
LEGAL_LINK = ""
SUPPORTED_LANGUAGES = [
    "ca",
    "cs",
    "de",
    "el",
    "en",
    "eo",
    "es",
    "es_419",
    "fa",
    "fr",
    "he",
    "hi",
    "hu",
    "id",
    "it",
    "ja",
    "kn",
    "nb_NO",
    "nl",
    "pl",
    "pt",
    "pt_BR",
    "ru",
    "sr",
    "sv",
    "ta",
    "te",
    "th",
    "tr",
    "uk",
    "zh_Hans",
]
