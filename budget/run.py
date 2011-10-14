from web import main, db, mail, babel
from api import api
import os

from flask import *

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
babel.init_app(app)

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(['fr', 'en'])


def main():
    app.run(host="0.0.0.0", debug=True)

if __name__ == '__main__':
    main()
