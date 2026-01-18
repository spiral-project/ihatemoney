# Installation

There are multiple ways to install «Ihatemoney» on your system :

1.  {ref}`docker`
2.  [Via Yunohost](https://github.com/YunoHost-Apps/ihatemoney_ynh) (a
    server operating system aiming to make self-hosting accessible to
    anyone)
3.  {ref}`cloud`
4.  {ref}`manual-installation`


:::{note}
We lack some knowledge about packaging to make Ihatemoney installable on
mainstream Linux distributions. If you want to give us a hand on the
topic, please check-out [the issue about debian
packaging](https://github.com/spiral-project/ihatemoney/issues/227).
:::

(docker)=
## With Docker

Docker images are published [on the Docker
hub](https://hub.docker.com/r/ihatemoney/ihatemoney/).

This is probably the simplest way to get something running. Once you
have Docker installed on your system, just issue :

    docker run -d -p 8000:8000 ihatemoney/ihatemoney:latest

Ihatemoney is now available on <http://localhost:8000>.

All {ref}`settings<configuration>` can be
passed with `-e` parameters e.g. with a secure `SECRET_KEY`, an external
mail server and an external database:

    docker run -d -p 8000:8000 \
    -e SECRET_KEY="supersecure" \
    -e SQLALCHEMY_DATABASE_URI="mysql+pymysql://user:pass@10.42.58.250/ihm" \
    -e MAIL_SERVER=smtp.gmail.com \
    -e MAIL_PORT=465 \
    -e MAIL_USERNAME=your-email@gmail.com \
    -e MAIL_PASSWORD=your-password \
    -e MAIL_USE_SSL=True \
    ihatemoney/ihatemoney

If you are running this locally, you might need to disable the secure session cookies, as they do not work locally. You need to pass `-e SESSION_COOKIE_SECURE=False` to docker run.

A volume can also be specified to persist the default database file:

    docker run -d -p 8000:8000 -v /host/path/to/database:/database ihatemoney/ihatemoney

To enable the Admin dashboard, first generate a hashed password with:

    docker run -it --rm --entrypoint ihatemoney ihatemoney/ihatemoney generate_password_hash

:::{note}
The generated password hash is salted. Which means that the same password will generate a different hash each time. This is normal and expected behavior.
:::

At the prompt, enter a password to use for the admin dashboard. The
command will print the hashed password string.

Add these additional environment variables to the docker run invocation:

    -e ACTIVATE_ADMIN_DASHBOARD=True \
    -e ADMIN_PASSWORD=<hashed_password_string> \

:::{note}
If you are using a `docker-compose.yml` file and need to include a password hash, use `$$` instead of `$` to escape the dollar sign. This ensures that the hash is treated as a literal string rather than a variable in Bash.
:::

Additional gunicorn parameters can be passed using the docker `CMD`
parameter. For example, use the following command to add more gunicorn
workers:

    docker run -d -p 8000:8000 ihatemoney/ihatemoney -w 3

If needed, there is a `docker-compose.yml` file available as an example on the [project repository](https://github.com/spiral-project/ihatemoney/blob/main/docker-compose.yml)

(cloud)=
## On a Cloud Provider

Some Paas (Platform-as-a-Service), provide a documentation or even a quick installation process to deploy and enjoy your instance within a minute:

  * [alwaysdata](https://www.alwaysdata.com/en/marketplace/ihatemoney/)

(manual-installation)=
## Via a manual installation

(system-requirements)=
### Requirements

«Ihatemoney» depends on:

-   **Python**: any version from 3.8 to 3.12 will work.
-   **A database backend**: choose among SQLite, PostgreSQL, MariaDB (>=
    10.3.2).
-   **Virtual environment** (recommended): [python3-venv]{.title-ref}
    package under Debian/Ubuntu.

We recommend using [virtual
environments](https://docs.python.org/3/tutorial/venv.html) to isolate
the installation from other softwares on your machine, but it\'s not
mandatory.

If wondering about the backend, SQLite is the simplest and will work
fine for most small to medium setups.

::: {note}
If curious, source config templates can be found in the [project git
repository](https://github.com/spiral-project/ihatemoney/tree/main/ihatemoney/conf-templates).
:::

(virtualenv-preparation)=
### Prepare virtual environment (recommended)

Choose an installation path, here the current user's home directory
(~).

Create a virtual environment:

    python3 -m venv ~/ihatemoney
    cd ~/ihatemoney

Activate the virtual environment:

    source bin/activate

::: {note}
You will have to re-issue that `source` command if you open a new
terminal.
:::

(pip)=
### Install

Install the latest release with pip:

    pip install ihatemoney

### Test it

Once installed, you can start a test server:

    ihatemoney generate-config ihatemoney.cfg > ihatemoney.cfg
    export IHATEMONEY_SETTINGS_FILE_PATH=$PWD/ihatemoney.cfg 
    ihatemoney db upgrade head
    ihatemoney runserver

And point your browser at <http://localhost:5000>.

### Generate your configuration

1.  Initialize the ihatemoney directories:

        mkdir /etc/ihatemoney /var/lib/ihatemoney

2.  Generate settings:

        ihatemoney generate-config ihatemoney.cfg > /etc/ihatemoney/ihatemoney.cfg
        chmod 740 /etc/ihatemoney/ihatemoney.cfg

You probably want to adjust `/etc/ihatemoney/ihatemoney.cfg` contents,
you may do it later, see {ref}`configuration`.

(mariadb)=
### Configure database with MariaDB (optional)

::: {note}
Only required if you use MariaDB. Make sure to use MariaDB 10.3.2 or
newer.
:::

1.  Install PyMySQL dependencies. On Debian or Ubuntu, that would be:

        apt install python3-dev libssl-dev

2.  Install PyMySQL (within your virtual environment):

        pip install 'PyMySQL>=0.9,<1.1'

3.  Create an empty database and a database user

4.  Configure
    {ref}`configuration:SQLALCHEMY_DATABASE_URI` accordingly

(postresql)=
### Configure database with PostgreSQL (optional)

::: {note}
Only required if you use Postgresql.
:::

1.  Install python driver for PostgreSQL (from within your virtual
    environment):

        pip install psycopg2

2.  Create the users and tables. On the command line, this looks like:

        sudo -u postgres psql
        postgres=# create database mydb;
        postgres=# create user myuser with encrypted password 'mypass';
        postgres=# grant all privileges on database mydb to myuser;

3.  Configure
    {ref}`configuration:SQLALCHEMY_DATABASE_URI` accordingly.

### Configure a reverse proxy

When deploying this service in production, you want to have a reverse
proxy in front of the python application.

Here are documented two stacks. You can of course use another one if you
want. Don't hesitate to contribute a small tutorial here if you want.

1.  Apache and *mod_wsgi*
2.  Nginx, Gunicorn and Supervisord/Systemd

### With Apache and mod_wsgi

1.  Fix permissions (considering `www-data` is the user running apache):

        chgrp www-data /etc/ihatemoney/ihatemoney.cfg
        chown www-data /var/lib/ihatemoney

2.  Install Apache and mod_wsgi : `libapache2-mod-wsgi(-py3)` for Debian
    based and `mod_wsgi` for RedHat based distributions

3.  Create an Apache virtual host, the command
    `ihatemoney generate-config apache-vhost.conf` will output a good
    starting point (read and adapt it).

4.  Activate the virtual host if needed and restart Apache

### With Nginx, Gunicorn and Supervisord/systemd

Install Gunicorn:

    pip install gunicorn

1.  Create a dedicated unix user (here called `ihatemoney`),
    required dirs, and fix permissions:

        useradd ihatemoney
        chown ihatemoney /var/lib/ihatemoney/
        chgrp ihatemoney /etc/ihatemoney/ihatemoney.cfg

2.  Create gunicorn config file :

        ihatemoney generate-config gunicorn.conf.py > /etc/ihatemoney/gunicorn.conf.py

3.  Setup Supervisord or systemd

    -   To use Supervisord, create supervisor config file :

            ihatemoney generate-config supervisord.conf > /etc/supervisor/conf.d/ihatemoney.conf

    -   To use systemd services, create `ihatemoney.service` in `/etc/systemd/system/ihatemoney.service` [^1]:

            [Unit]
            Description=I hate money
            Requires=network.target postgresql.service
            After=network.target postgresql.service

            [Service]
            Type=simple
            User=ihatemoney
            ExecStart=%h/ihatemoney/bin/gunicorn -c /etc/ihatemoney/gunicorn.conf.py ihatemoney.wsgi:application
            SyslogIdentifier=ihatemoney

            [Install]
            WantedBy=multi-user.target

        Obviously, adapt the `ExecStart` path for your installation
        folder.

        If you use SQLite as database: remove mentions of
        `postgresql.service` in `ihatemoney.service`. If you use MariaDB
        as database: replace mentions of `postgresql.service` by
        `mariadb.service` in `ihatemoney.service`.

        Then reload systemd, enable and start `ihatemoney`:

            systemctl daemon-reload
            systemctl enable ihatemoney.service
            systemctl start ihatemoney.service

4.  Copy (and adapt) output of `ihatemoney generate-config nginx.conf`
    with your nginx vhosts[^2]

5.  Reload nginx (and supervisord if you use it). It should be working
    ;)

[^1]: `/etc/systemd/system/ihatemoney.service` path may change depending
    on your distribution.

[^2]: typically, */etc/nginx/conf.d/* or */etc/nginx/sites-available*,
    depending on your distribution.
