from web import main, db, mail
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

def main():
    app.run(host="0.0.0.0", debug=True)

if __name__ == '__main__':
    main()
