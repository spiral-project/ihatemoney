#!/usr/bin/env python

import getpass
import os
import random
import sys

from flask_migrate import Migrate, MigrateCommand
from flask_script import Command, Manager, Option
from werkzeug.security import generate_password_hash

from ihatemoney.models import Project, db
from ihatemoney.run import create_app
from ihatemoney.utils import create_jinja_env


class GeneratePasswordHash(Command):

    """Get password from user and hash it without printing it in clear text."""

    def run(self):
        password = getpass.getpass(prompt="Password: ")
        print(generate_password_hash(password))


class GenerateConfig(Command):
    def get_options(self):
        return [
            Option(
                "config_file",
                choices=[
                    "ihatemoney.cfg",
                    "apache-vhost.conf",
                    "gunicorn.conf.py",
                    "supervisord.conf",
                    "nginx.conf",
                ],
            )
        ]

    @staticmethod
    def gen_secret_key():
        return "".join(
            [
                random.SystemRandom().choice(
                    "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
                )
                for i in range(50)
            ]
        )

    def run(self, config_file):
        env = create_jinja_env("conf-templates", strict_rendering=True)
        template = env.get_template(f"{config_file}.j2")

        bin_path = os.path.dirname(sys.executable)
        pkg_path = os.path.abspath(os.path.dirname(__file__))

        print(
            template.render(
                pkg_path=pkg_path,
                bin_path=bin_path,
                sys_prefix=sys.prefix,
                secret_key=self.gen_secret_key(),
            )
        )


class DeleteProject(Command):
    def run(self, project_name):
        demo_project = Project.query.get(project_name)
        db.session.delete(demo_project)
        db.session.commit()


def main():
    QUIET_COMMANDS = ("generate_password_hash", "generate-config")

    exception = None
    backup_stderr = sys.stderr
    # Hack to divert stderr for commands generating content to stdout
    # to avoid confusing the user
    if len(sys.argv) > 1 and sys.argv[1] in QUIET_COMMANDS:
        sys.stderr = open(os.devnull, "w")

    try:
        app = create_app()
        Migrate(app, db)
    except Exception as e:
        exception = e

    # Restore stderr
    sys.stderr = backup_stderr

    if exception:
        raise exception

    manager = Manager(app)
    manager.add_command("db", MigrateCommand)
    manager.add_command("generate_password_hash", GeneratePasswordHash)
    manager.add_command("generate-config", GenerateConfig)
    manager.add_command("delete-project", DeleteProject)
    manager.run()


if __name__ == "__main__":
    main()
