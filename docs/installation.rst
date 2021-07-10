.. _installation:

Installation
############

We lack some knowledge about packaging to make Ihatemoney installable on mainstream
Linux distributions. If you want to give us a hand on the topic, please
check-out `the issue about debian packaging <https://github.com/spiral-project/ihatemoney/issues/227>`_.

If you are using Yunohost (a server operating system aiming to make self-hosting accessible to anyone),
you can use the `Ihatemoney package <https://github.com/YunoHost-Apps/ihatemoney_ynh>`_.

Otherwise, follow these instructions to install it manually:

.. _installation-requirements:

Requirements
============

«Ihatemoney» depends on:

* **Python**: version 3.6 to 3.9 included will work.
* **A Backend**: to choose among SQLite, PostgreSQL, MariaDB (>= 10.3.2) or Memory.
* **Virtual environment** (recommended): `python3-venv` package under Debian/Ubuntu.

We recommend to use `virtual environment <https://docs.python.org/3/tutorial/venv.html>`_ but
it will work without if you prefer.

If wondering about the backend, SQLite is the simplest and will work fine for
most small to medium setups.

.. note:: If curious, source config templates can be found in the `project git repository <https://github.com/spiral-project/ihatemoney/tree/master/ihatemoney/conf-templates>`_.

.. _virtualenv-preparation:

Prepare virtual environment (recommended)
=========================================

Choose an installation path, here `/home/john/ihatemoney`.

Create a virtual environment::

    python3 -m venv /home/john/ihatemoney

Activate the virtual environment::

    source /home/john/ihatemoney/bin/activate

.. note:: You will have to re-issue that ``source`` command if you open a new
          terminal.

Install
=======

Install the latest release with pip::

  pip install ihatemoney

Test it
=======

Once installed, you can start a test server::

  ihatemoney run

And point your browser at `http://localhost:5000 <http://localhost:5000>`_.

Configure database with MariaDB (optional)
================================================

.. note:: Only required if you use MariaDB.  Make sure to use MariaDB 10.3.2 or newer.

1. Install PyMySQL dependencies. On Debian or Ubuntu, that would be::

    apt install python3-dev libssl-dev

2. Install PyMySQL (within your virtual environment)::

    pip install 'PyMySQL>=0.9,<0.10'

3. Create an empty database and a database user
4. Configure :ref:`SQLALCHEMY_DATABASE_URI <configuration>` accordingly


Configure database with PostgreSQL (optional)
=============================================

.. note:: Only required if you use Postgresql.

1. Install python driver for PostgreSQL (from within your virtual environment)::

    pip install psycopg2

2. Create the users and tables. On the command line, this looks like::

    sudo -u postgres psql
    postgres=# create database mydb;
    postgres=# create user myuser with encrypted password 'mypass';
    postgres=# grant all privileges on database mydb to myuser;

3. Configure :ref:`SQLALCHEMY_DATABASE_URI <configuration>` accordingly.


Deploy it
=========

Now, if you want to deploy it on your own server, you have many options.
Three of them are documented at the moment.

*Of course, if you want to contribute another configuration, feel free
to open a pull-request against this repository!*


Whatever your installation option is…
--------------------------------------

1. Initialize the ihatemoney directories::

    mkdir /etc/ihatemoney /var/lib/ihatemoney

2. Generate settings::

    ihatemoney generate-config ihatemoney.cfg > /etc/ihatemoney/ihatemoney.cfg
    chmod 740 /etc/ihatemoney/ihatemoney.cfg

You probably want to adjust ``/etc/ihatemoney/ihatemoney.cfg`` contents,
you may do it later, see :ref:`configuration`.


With Apache and mod_wsgi
------------------------

1. Fix permissions (considering `www-data` is the user running apache)::

     chgrp www-data /etc/ihatemoney/ihatemoney.cfg
     chown www-data /var/lib/ihatemoney

2. Install Apache and mod_wsgi : ``libapache2-mod-wsgi(-py3)`` for Debian
   based and ``mod_wsgi`` for RedHat based distributions
3. Create an Apache virtual host, the command
   ``ihatemoney generate-config apache-vhost.conf`` will output a good
   starting point (read and adapt it).
4. Activate the virtual host if needed and restart Apache

With Nginx, Gunicorn and Supervisord/systemd
--------------------------------------------

Install Gunicorn::

  pip install gunicorn

1. Create a dedicated unix user (here called `ihatemoney`), required dirs, and fix permissions::

    useradd ihatemoney
    chown ihatemoney /var/lib/ihatemoney/
    chgrp ihatemoney /etc/ihatemoney/ihatemoney.cfg

2. Create gunicorn config file ::

    ihatemoney generate-config gunicorn.conf.py > /etc/ihatemoney/gunicorn.conf.py

3. Setup Supervisord or systemd

   - To use Supervisord, create supervisor config file ::

      ihatemoney generate-config supervisord.conf > /etc/supervisor/conf.d/ihatemoney.conf

   - To use systemd services, create ``ihatemoney.service`` in [#systemd-services]_::

      [Unit]
      Description=I hate money
      Requires=network.target postgresql.service
      After=network.target postgresql.service

      [Service]
      Type=simple
      User=ihatemoney
      ExecStart=/home/john/ihatemoney/bin/gunicorn -c /etc/ihatemoney/gunicorn.conf.py ihatemoney.wsgi:application
      SyslogIdentifier=ihatemoney

      [Install]
      WantedBy=multi-user.target

     Obviously, adapt the ``ExecStart`` path for your installation folder.

     If you use SQLite as database: remove mentions of ``postgresql.service`` in ``ihatemoney.service``.
     If you use MariaDB as database: replace mentions of ``postgresql.service`` by ``mariadb.service`` in ``ihatemoney.service``.

     Then reload systemd, enable and start ``ihatemoney``::

       systemctl daemon-reload
       systemctl enable ihatemoney.service
       systemctl start ihatemoney.service

4. Copy (and adapt) output of ``ihatemoney generate-config nginx.conf``
   with your nginx vhosts [#nginx-vhosts]_
5. Reload nginx (and supervisord if you use it). It should be working ;)

.. [#nginx-vhosts] typically, */etc/nginx/conf.d/* or
   */etc/nginx/sites-available*, depending on your distribution.

.. [#systemd-services] ``/etc/systemd/system/ihatemoney.service``
                       path may change depending on your distribution.

With Docker
-----------

Build the image::

    docker build -t ihatemoney --build-arg INSTALL_FROM_PYPI=True .

Start a daemonized Ihatemoney container::

    docker run -d -p 8000:8000 ihatemoney

Ihatemoney is now available on http://localhost:8000.

All Ihatemoney settings can be passed with ``-e`` parameters
e.g. with a secure ``SECRET_KEY``, an external mail server and an
external database::

    docker run -d -p 8000:8000 \
    -e SECRET_KEY="supersecure" \
    -e SQLALCHEMY_DATABASE_URI="mysql+pymysql://user:pass@172.17.0.5/ihm" \
    -e MAIL_SERVER=smtp.gmail.com \
    -e MAIL_PORT=465 \
    -e MAIL_USERNAME=your-email@gmail.com \
    -e MAIL_PASSWORD=your-password \
    -e MAIL_USE_SSL=True \
    ihatemoney

A volume can also be specified to persist the default database file::

    docker run -d -p 8000:8000 -v /host/path/to/database:/database ihatemoney

If you want to run the latest version, you can pass `-e NIGHTLY="true"`.

Additional gunicorn parameters can be passed using the docker ``CMD``
parameter.
For example, use the following command to add more gunicorn workers::

    docker run -d -p 8000:8000 ihatemoney -w 3
