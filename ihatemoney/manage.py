#!/usr/bin/env python

import getpass
import os
import random
import sys
import datetime

import click
from flask.cli import FlaskGroup

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


@cli.command(name="generate_password_hash")
def password_hash():
    """Get password from user and hash it without printing it in clear text."""
    password = getpass.getpass(prompt="Password: ")
    print(generate_password_hash(password))


@cli.command()
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


@cli.command()
@click.argument("print_emails", default=False)
@click.argument("bills", default=0)  # default values will get total projects
@click.argument("days", default=73000)  # approximately 200 years
def get_project_count(print_emails, bills, days):
    """Count projets with at least x bills and at less than x days old"""
    projects = [
        pr
        for pr in Project.query.all()
        if pr.get_bills().count() > bills
        and pr.get_bills()[0].date
        > datetime.date.today() - datetime.timedelta(days=days)
    ]
    click.secho("Number of projects: " + str(len(projects)))

    if print_emails:
        emails = set([pr.contact_email for pr in projects])
        emails_str = ", ".join(emails)
        if len(emails) > 1:
            click.secho("Contact emails: " + emails_str)
        elif len(emails) == 1:
            click.secho("Contact email: " + emails_str)
        else:
            click.secho("No contact emails found")


if __name__ == "__main__":
    cli()
