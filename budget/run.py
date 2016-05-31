import os
import warnings

from flask import Flask, g, request, session
from flask.ext.babel import Babel
from flask.ext.migrate import Migrate, upgrade
from raven.contrib.flask import Sentry

from web import main, db, mail
from api import api
from utils import PrefixedWSGI

app = Flask(__name__)


def configure():
    """ A way to (re)configure the app, specially reset the settings
    """
    config_obj = os.environ.get('FLASK_SETTINGS_MODULE', 'merged_settings')
    app.config.from_object(config_obj)
    app.wsgi_app = PrefixedWSGI(app)

    # Deprecations
    if 'DEFAULT_MAIL_SENDER' in app.config:
        # Since flask-mail  0.8
        warnings.warn(
            "DEFAULT_MAIL_SENDER is deprecated in favor of MAIL_DEFAULT_SENDER"
            +" and will be removed in further version",
            UserWarning
        )
        if not 'MAIL_DEFAULT_SENDER' in app.config:
            app.config['MAIL_DEFAULT_SENDER'] = DEFAULT_MAIL_SENDER

configure()


app.register_blueprint(main)
app.register_blueprint(api)

# db
db.init_app(app)
db.app = app

# db migrations
migrate = Migrate(app, db)

# auto-execute migrations on runtime
with app.app_context():
    upgrade()

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
