#!/usr/bin/env python

import getpass
import os
import random
import sys

import click
from flask.cli import FlaskGroup, with_appcontext

from ihatemoney.models import Project, db
from ihatemoney.run import create_app
from ihatemoney.utils import create_jinja_env, generate_password_hash


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """IHateMoney Management script"""


@cli.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.pass_context
def runserver(ctx):
    """Deprecated, use the "run" command instead"""
    click.secho(
        '"runserver" is deprecated, please use the standard "run" flask command',
        fg="red",
    )
    run = cli.get_command(ctx, "run")
    ctx.forward(run)


@click.command(name="generate_password_hash")
@with_appcontext
def password_hash():
    """Get password from user and hash it without printing it in clear text."""
    password = getpass.getpass(prompt="Password: ")
    print(generate_password_hash(password))


@click.command()
@click.argument(
    "config_file",
    type=click.Choice(
        [
            "ihatemoney.cfg",
            "apache-vhost.conf",
            "gunicorn.conf.py",
            "supervisord.conf",
            "nginx.conf",
        ]
    ),
)
def generate_config(config_file):
    """Generate front-end server configuration"""

    def gen_secret_key():
        return "".join(
            [
                random.SystemRandom().choice(
                    "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
                )
                for _ in range(50)
            ]
        )

    env = create_jinja_env("conf-templates", strict_rendering=True)
    template = env.get_template(f"{config_file}.j2")

    bin_path = os.path.dirname(sys.executable)
    pkg_path = os.path.abspath(os.path.dirname(__file__))

    print(
        template.render(
            pkg_path=pkg_path,
            bin_path=bin_path,
            sys_prefix=sys.prefix,
            secret_key=gen_secret_key(),
        )
    )


@cli.command()
@click.argument("project_name")
def delete_project(project_name):
    """Delete a project"""
    project = Project.query.get(project_name)
    if project is None:
        click.secho(f'Project "{project_name}" not found', fg="red")
    else:
        db.session.delete(project)
        db.session.commit()


if __name__ == "__main__":
    cli()
