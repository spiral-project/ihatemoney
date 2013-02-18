from flask import Flask, g, request, session
from flask.ext.babel import Babel
from raven.contrib.flask import Sentry

from web import main, db, mail
from api import api


app = Flask(__name__)
app.config.from_object("default_settings")

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
