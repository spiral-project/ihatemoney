Installation
############

We lack some knowledge about packaging to make Ihatemoney installable on mainstream
Linux distributions. If you want to give us a hand on the topic, please check-out
`the issue about debian packaging <https://github.com/spiral-project/ihatemoney/issues/227>`_.

If you are using Yunohost (a server operating system aiming to make self-hosting accessible to anyone),
you can use the `Ihatemoney package <https://github.com/YunoHost-Apps/ihatemoney_ynh>`_.

Otherwise, follow these instructions to install it manually:

.. _installation-requirements:

Requirements
============

«Ihatemoney» depends on:

* **Python**: either 2.7, 3.4, 3.5, 3.6 will work.
* **A Backend**: to choose among MySQL, PostgreSQL, SQLite or Memory.
* **Virtualenv** (recommended): `virtualenv` package under Debian/Ubuntu.

We recommend to use `virtualenv <https://pypi.python.org/pypi/virtualenv>`_ but
it will work without if you prefer.

If wondering about the backend, SQLite is the simplest and will work fine for
most small to medium setups.

.. note:: If curious, source config templates can be found in the `project git repository <https://github.com/spiral-project/ihatemoney/tree/master/ihatemoney/conf-templates>`_.

.. _virtualenv-preparation:

Prepare virtualenv (recommended)
================================

Choose an installation path, here `/home/john/ihatemoney`.

Create a virtualenv::

    virtualenv  -p /usr/bin/python3 /home/john/ihatemoney

Activate the virtualenv::

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

  ihatemoney runserver

And point your browser at `http://localhost:5000 <http://localhost:5000>`_.

Deploy it
=========

Now, if you want to deploy it on your own server, you have many options.
Three of them are documented at the moment.

*Of course, if you want to contribute another configuration, feel free to open a
pull-request against this repository!*


Whatever your installation option is…
--------------------------------------

1. Initialize the ihatemoney directories::

    mkdir /etc/ihatemoney /var/lib/ihatemoney

2. Generate settings::

    ihatemoney generate-config ihatemoney.cfg > /etc/ihatemoney/ihatemoney.cfg
    chmod 740 /etc/ihatemoney/ihatemoney.cfg

You probably want to adjust `/etc/ihatemoney/ihatemoney.cfg` contents, you may
do it later, see `Configuration`_.


With Apache and mod_wsgi
------------------------

1. Fix permissions (considering `www-data` is the user running apache)::

     chgrp www-data /etc/ihatemoney/ihatemoney.cfg
     chown www-data /var/lib/ihatemoney

2. Install Apache and mod_wsgi - libapache2-mod-wsgi(-py3) for Debian based and mod_wsgi for RedHat based distributions -
3. Create an Apache virtual host, the command ``ihatemoney generate-config apache-vhost.conf`` will output a good starting point (read and adapt it)
4. Activate the virtual host if needed and restart Apache

With Nginx, Gunicorn and Supervisord
------------------------------------

1. Create a dedicated unix user (here called `ihatemoney`), required dirs, and fix permissions::

    useradd ihatemoney
    chown ihatemoney /var/lib/ihatemoney/
    chgrp ihatemoney /etc/ihatemoney/ihatemoney.cfg

2. Create gunicorn config file ::

     ihatemoney generate-config gunicorn.conf.py > /etc/ihatemoney/gunicorn.conf.py

3. Create supervisor config file ::

     ihatemoney generate-config supervisord.conf > /etc/supervisor/conf.d/ihatemoney.conf

4. Copy (and adapt) output of ``ihatemoney generate-config conf/nginx.conf`` with your nginx vhosts [#nginx-vhosts]_
5. Reload both nginx and supervisord. It should be working ;)

.. [#nginx-vhosts] typically, */etc/nginx/conf.d/* or
   */etc/nginx/sites-available*, depending on your distribution.

With Docker
-----------

Build the image::

    docker build -t ihatemoney --build-arg INSTALL_FROM_PYPI=True .

Start a daemonized Ihatemoney container::

    docker run -d -p 8000:8000 ihatemoney

Ihatemoney is now available on http://localhost:8000.

All Ihatemoney settings can be passed with ``-e`` parameters
e.g. with a secure ``SECRET_KEY``, an external mail server and an external database::

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

Additional gunicorn parameters can be passed using the docker ``CMD`` parameter.
For example, use the following command to add more gunicorn workers::

    docker run -d -p 8000:8000 ihatemoney -w 3

Configuration
=============

ihatemoney relies on a configuration file. If you run the application for the
first time, you will need to take a few moments to configure the application
properly.

Defaults given here, are those for development mode. To know defaults on your
deployed instance, simply look at your *ihatemoney.cfg*.

Production values are recommended values for use in production.


+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
| Setting name                  |  Default                        | What does it do?                                                                       |
+===============================+=================================+========================================================================================+
| SQLALCHEMY_DATABASE_URI       | ``sqlite:///tmp/ihatemoney.db`` | Specifies the type of backend to use and its location. More information on the         |
|                               |                                 | format used can be found on `the SQLAlchemy documentation`_.                           |
|                               |                                 |                                                                                        |
|                               |                                 | **Production value:** Set it to some path on your disk. Typically                      |
|                               |                                 | ``sqlite:///home/ihatemoney/ihatemoney.db``. Do *not* store it under ``/tmp`` as this  |
|                               |                                 | folder is cleared at each boot.                                                        |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
| SECRET_KEY                    |  ``tralala``                    | The secret key used to encrypt the cookies.                                            |
|                               |                                 |                                                                                        |
|                               |                                 | **Production value:** `ihatemoney conf-example ihatemoney.cfg` sets it to something    |
|                               |                                 | random, which is good.                                                                 |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
| MAIL_DEFAULT_SENDER           | ``("Budget manager",            | A python tuple describing the name and email address to use when sending                |
|                               | "budget@notmyidea.org")``       | emails.                                                                                |
|                               |                                 |                                                                                        |
|                               |                                 |  **Production value:** Any tuple you want.                                             |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
| ACTIVATE_DEMO_PROJECT         |  ``True``                       | If set to `True`, a demo project will be available on the frontpage.                   |
|                               |                                 |                                                                                        |
|                               |                                 | **Production value:** Usually, you will want to set it to ``False`` for a private      |
|                               |                                 |  instance.                                                                             |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
|                               |                                 | Hashed password to access protected endpoints. If left empty, all administrative       |
| ADMIN_PASSWORD                |  ``""``                         | tasks are disabled.                                                                    |
|                               |                                 |                                                                                        |
|                               |                                 | **Production value:** To generate the proper password HASH, use                        |
|                               |                                 | ``ihatemoney generate_password_hash`` and copy the output into the value of            |
|                               |                                 | *ADMIN_PASSWORD*.                                                                      |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
| ALLOW_PUBLIC_PROJECT_CREATION |  ``True``                       | If set to ``True``, everyone can create a project without entering the admin password  |
|                               |                                 | If set to ``False``, the password needs to be entered (and as such, defined in the     |
|                               |                                 | settings).                                                                             |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
| ACTIVATE_ADMIN_DASHBOARD      |  ``False``                      | If set to `True`, the dashboard will become accessible entering the admin password     |
|                               |                                 | If set to `True`, a non empty ADMIN_PASSWORD needs to be set                           |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+
| APPLICATION_ROOT              |  ``""``                         | If empty, ihatemoney will be served at domain root (e.g: *http://domain.tld*), if set  |
|                               |                                 | to ``"foo"``, it will be served from a "folder" (e.g: *http://domain.tld/foo*)         |
+-------------------------------+---------------------------------+----------------------------------------------------------------------------------------+

.. _the SQLAlchemy documentation: http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls

Using an alternate settings path
--------------------------------

You can put your settings file where you want, and pass its path to the
application using the ``IHATEMONEY_SETTINGS_FILE_PATH`` environment variable.

e.g.::

    $ export IHATEMONEY_SETTINGS_FILE_PATH="/path/to/your/conf/file.cfg"
