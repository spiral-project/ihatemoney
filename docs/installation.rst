Installation
############

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
Two of them are documented at the moment.

*Of course, if you want to contribute another configuration, feel free to open a
pull-request against this repository!*.

With Apache and mod_wsgi
------------------------

1. Install Apache and mod_wsgi - libapache2-mod-wsgi(-py3) for Debian based and mod_wsgi for RedHat based distributions -
2. Create an Apache virtual host based on the sample configuration file in `conf/apache-vhost.conf`
3. Adapt it to your paths and specify your virtualenv path if you use one
4. Activate the virtual host if needed and restart Apache

With Nginx, Gunicorn and Supervisord
------------------------------------

.. note:: For the 3 configuration files mentioned below, you will need to fix
          the paths to reflect yours.

1. Copy *conf/gunicorn.conf.py* to */etc/ihatemoney/gunicorn.conf.py*
2. Copy *conf/supervisord.conf* to */etc/supervisor/conf.d/ihatemoney.conf*
3. Copy *conf/nginx.conf* with your nginx vhosts [#nginx-vhosts]_
4. Reload both nginx and supervisord. It should be working ;)

Don't forget to set the right permission for your files !

.. [#nginx-vhosts] typically, */etc/nginx/conf.d/* or
   */etc/nginx/sites-available*, depending on your distribution.

Configuration
=============

ihatemoney relies on a configuration file. If you run the application for the
first time, you will need to take a few moments to configure the application
properly.

.. warning:: You **must** customize the ``SECRET_KEY`` on a production installation.

+----------------------------+---------------------------+----------------------------------------------------------------------------------------+
| Setting name               |  Default                  | What does it do?                                                                       |
+============================+===========================+========================================================================================+
| SQLALCHEMY_DATABASE_URI    |  ``sqlite:///budget.db``  | Specifies the type of backend to use and its location. More information                |
|                            |                           | on the format used can be found on `the SQLAlchemy documentation                       |
|                            |                           | <http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_.              |
+----------------------------+---------------------------+----------------------------------------------------------------------------------------+
| SECRET_KEY                 |  ``tralala``              | The secret key used to encrypt the cookies. **This needs to be changed**.              |
+----------------------------+---------------------------+----------------------------------------------------------------------------------------+
| MAIL_DEFAULT_SENDER        | ``("Budget manager",      | A python tuple describing the name and email adress to use when sending                |
|                            | "budget@notmyidea.org")`` | emails.                                                                                |
+----------------------------+---------------------------+----------------------------------------------------------------------------------------+
| ACTIVATE_DEMO_PROJECT      |  ``True``                 | If set to `True`, a demo project will be available on the frontpage.                   |
+----------------------------+---------------------------+----------------------------------------------------------------------------------------+
|                            |  ``""``                   | If not empty, the specified password must be entered to create new projects.           |
| ADMIN_PASSWORD             |                           | To generate the proper password HASH, use ``ihatemoney generate_password_hash``        |
|                            |                           | and copy its output into the value of *ADMIN_PASSWORD*.                                |
+----------------------------+---------------------------+----------------------------------------------------------------------------------------+
| APPLICATION_ROOT           |  ``""``                   | If empty, ihatemoney will be served at domain root (e.g: *http://domain.tld*), if set  |
|                            |                           | to ``"foo"``, it will be served from a "folder" (e.g: *http://domain.tld/foo*)         |
+----------------------------+---------------------------+----------------------------------------------------------------------------------------+

In a production environment
---------------------------

Make a copy of ``ihatemoney/default_settings.py`` and name it ``ihatemoney.cfg``.
Then adjust the settings to your needs and move this file to
``/etc/ihatemoney/ihatemoney.cfg``.

This is the default path of the settings but you can also place it
elsewhere and pass the configuration file path to the application using
the IHATEMONEY_SETTINGS_FILE_PATH environment variable.

e.g.::

    $ export IHATEMONEY_SETTINGS_FILE_PATH="/path/to/your/conf/file.cfg"
