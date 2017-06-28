import os
import os.path
import warnings

from flask import Flask, g, request, session
from flask_babel import Babel
from flask_migrate import Migrate, upgrade, stamp
from raven.contrib.flask import Sentry

from web import main, db, mail
from api import api
from utils import PrefixedWSGI
from utils import minimal_round

import default_settings

app = Flask(__name__, instance_path='/etc/ihatemoney', instance_relative_config=True)


def pre_alembic_db():
    """ Checks if we are migrating from a pre-alembic ihatemoney
    """
    con = db.engine.connect()
    tables_exist = db.engine.dialect.has_table(con, 'project')
    alembic_setup = db.engine.dialect.has_table(con, 'alembic_version')
    return tables_exist and not alembic_setup


def configure():
    """ A way to (re)configure the app, specially reset the settings
    """
    default_config_file = os.path.join(app.root_path, 'default_settings.py')
    config_file = os.environ.get('IHATEMONEY_SETTINGS_FILE_PATH')

    # Load default settings first
    # Then load the settings from the path set in IHATEMONEY_SETTINGS_FILE_PATH var
    # If not set, default to /etc/ihatemoney/ihatemoney.cfg
    # If the latter doesn't exist no error is raised and the default settings are used
    app.config.from_pyfile(default_config_file)
    if config_file:
        app.config.from_pyfile(config_file)
    else:
        app.config.from_pyfile('ihatemoney.cfg', silent=True)
    app.wsgi_app = PrefixedWSGI(app)

    if app.config['SECRET_KEY'] == default_settings.SECRET_KEY:
        warnings.warn(
            "Running a server without changing the SECRET_KEY can lead to"
            + " user impersonation. Please update your configuration file.",
            UserWarning
        )
    # Deprecations
    if 'DEFAULT_MAIL_SENDER' in app.config:
        # Since flask-mail  0.8
        warnings.warn(
            "DEFAULT_MAIL_SENDER is deprecated in favor of MAIL_DEFAULT_SENDER"
            + " and will be removed in further version",
            UserWarning
        )
        if not 'MAIL_DEFAULT_SENDER' in app.config:
            app.config['MAIL_DEFAULT_SENDER'] = DEFAULT_MAIL_SENDER

    if "pbkdf2:sha256:" not in app.config['ADMIN_PASSWORD'] and app.config['ADMIN_PASSWORD']:
        # Since 2.0
        warnings.warn(
            "The way Ihatemoney stores your ADMIN_PASSWORD has changed. You are using an unhashed"
            + " ADMIN_PASSWORD, which is not supported anymore and won't let you access your admin"
            + " endpoints. Please use the command './budget/manage.py generate_password_hash'"
            + " to generate a proper password HASH and copy the output to the value of"
            + " ADMIN_PASSWORD in your settings file.",
            UserWarning
        )

configure()


app.register_blueprint(main)
app.register_blueprint(api)

# custom jinja2 filters
app.jinja_env.filters['minimal_round'] = minimal_round

# db
db.init_app(app)
db.app = app

# db migrations
migrate = Migrate(app, db)
migrations_path = os.path.join(app.root_path, 'migrations')

if pre_alembic_db():
    with app.app_context():
        # fake the first migration
        stamp(migrations_path, revision='b9a10d5d63ce')

# auto-execute migrations on runtime
with app.app_context():
    upgrade(migrations_path)

# mail
mail.init_app(app)

# translations
babel = Babel(app)

# sentry
sentry = Sentry(app)


@babel.localeselector
def get_locale():
    # get the lang from the session if defined, fallback on the browser "accept
    # languages" header.
    lang = session.get('lang', request.accept_languages.best_match(['fr', 'en']))
    setattr(g, 'lang', lang)
    return lang


def main():
    app.run(host="0.0.0.0", debug=True)

if __name__ == '__main__':
    main()
