import warnings

from flask import Flask, g, request, session
from flask.ext.babel import Babel
from raven.contrib.flask import Sentry

from web import main, db, mail
from api import api


app = Flask(__name__)


def configure():
    """ A way to (re)configure the app, specially reset the settings
    """
    app.config.from_object("default_settings")

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
db.create_all()

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
