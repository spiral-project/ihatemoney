# Verbose and documented settings are in conf-templates/ihatemoney.cfg.j2
DEBUG = SQLACHEMY_ECHO = False
SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/ihatemoney.db"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "tralala"
MAIL_DEFAULT_SENDER = ("Budget manager", "budget@notmyidea.org")
ACTIVATE_DEMO_PROJECT = True
ADMIN_PASSWORD = ""
ALLOW_PUBLIC_PROJECT_CREATION = True
ACTIVATE_ADMIN_DASHBOARD = False
SESSION_COOKIE_SECURE = True
SUPPORTED_LANGUAGES = [
    "de",
    "el",
    "en",
    "eo",
    "es_419",
    "fr",
    "hi",
    "id",
    "it",
    "ja",
    "nb_NO",
    "nl",
    "pl",
    "pt",
    "pt_BR",
    "ru",
    "sv",
    "ta",
    "tr",
    "uk",
    "zh_Hans",
]
ENABLE_CAPTCHA = False
LEGAL_LINK = ""
