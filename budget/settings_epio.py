from bundle_config import config

SQLALCHEMY_DATABASE_URI = 'postgresql://%(username)s:%(password)s@%(host)s:%(port)s/%(database)s' % config['postgres']
SECRET_KEY = "yosh"

MAIL_SERVER = "yourhost"
MAIL_PORT = 110
MAIL_USERNAME = 'foo'
MAIL_PASSWORD = 'bar'
MAIL_USE_TLS = True
SITE_URL = "http://ihatemoney.notmyidea.org"
DEBUG = True
