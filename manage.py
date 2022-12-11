#!/usr/bin/env python

import datetime
import getpass
import os
import random
import sys

import click
from flask.cli import FlaskGroup
from werkzeug.security import generate_password_hash

from ihatemoney.models import *
from ihatemoney.run import create_app
from ihatemoney.utils import create_jinja_env


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
    click.secho(f'Searching for "{project_name}"', fg="red")
    project = Project.query.get(project_name)
    if project is None:
        click.secho(f'Project "{project_name}" not found', fg="red")
    else:
        db.session.delete(project)
        db.session.commit()


@cli.command()
@click.option(
    "-l", "--bills_low", type=int, required=False, help="The minimum number of bills"
)
@click.option(
    "-h", "--bills_high", type=int, required=False, help="Maximum number of bills"
)
@click.option(
    "-d",
    "--num_days",
    required=False,
    type=int,
    help="Max number of days you want the oldest result to be",
)
@click.option(
    "-e",
    "--emails",
    is_flag=True,
    default=False,
    help="Returns emails rather than project names",
)
@click.option(
    "-n",
    "--names",
    is_flag=True,
    default=False,
    help="Returns list of names of projects",
)
def get_all_projects(
    bills_low=None, bills_high=None, num_days=None, emails=None, names=None
):
    """Displays the number of projects. Options exist to specify for \
        projects within the bounds of the specified number of bills (inclusive) and/or less than x days old. """
    if bills_low and bills_high:

        # Make sure low < high
        if bills_high < bills_low:
            temp = bills_high
            bills_high = bills_low
            bills_low = temp

        if num_days:
            projects = [
                pr
                for pr in Project.query.all()
                if pr.get_bills().count() >= bills_low
                and pr.get_bills().count() <= bills_high
                and pr.get_bills()[0].date
                > datetime.date.today() - datetime.timedelta(days=num_days)
            ]
        else:
            projects = [
                pr
                for pr in Project.query.all()
                if pr.get_bills().count() >= bills_low
                and pr.get_bills().count() <= bills_high
            ]
        click.echo(len(projects))
        if emails:
            list_emails = ", ".join(set([pr.contact_email for pr in projects]))
            click.echo(list_emails)
        if names:
            proj_names = [pr.name for pr in projects]
            click.echo(proj_names)

    elif (bills_low and bills_high == None) or (bills_low == None and bills_high):
        click.secho(
            f"Invalid number of bounds specified. Please include both a \
            low and high bound by using (-l or --low) and (-h or --high)",
            fg="red",
        )

    else:
        if num_days:
            projects = [
                pr
                for pr in Project.query.all()
                if pr.get_bills()[0].date
                > datetime.date.today() - datetime.timedelta(days=num_days)
            ]
        else:
            projects = Project.query.all()

        click.echo(len(projects))
        if emails:
            list_emails = ", ".join(set([pr.contact_email for pr in projects]))
            click.echo(list_emails)
        if names:
            proj_names = [pr.name for pr in projects]
            click.echo(proj_names)


if __name__ == "__main__":
    cli()
