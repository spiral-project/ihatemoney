#!/usr/bin/env python

from getpass import getpass
from flask_script import Manager, Command
from flask_migrate import Migrate, MigrateCommand
from werkzeug.security import generate_password_hash

from ihatemoney.run import app
from ihatemoney.models import db


class GeneratePasswordHash(Command):
    "Get password from user and hash it without printing it in clear text"

    def run(self):
        password = getpass(prompt='Password: ')
        print(generate_password_hash(password))

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('generate_password_hash', GeneratePasswordHash)


def main():
    manager.run()


if __name__ == '__main__':
    main()
