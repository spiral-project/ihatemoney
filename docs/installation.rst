Installation
############

First, you need to get the source files. One way to get them is to download
them from the github repository, using git::

  git clone https://github.com/spiral-project/ihatemoney.git

Requirements
============

«Ihatemoney» depends on:

* **Python**: either 2.7, 3.4, 3.5 will work.
* **A Backend**: to choose among MySQL, PostgreSQL, SQLite or Memory.

We recommend to use `pip <https://pypi.python.org/pypi/pip/>`_ and
`virtualenv <https://pypi.python.org/pypi/virtualenv>`_ but it will work
without if you prefer.

If you have everything installed, you can just issue::

    make serve

Alternatively, you can also use the `requirements.txt` file to install the
dependencies yourself (that's what the `make serve` does). That would be::

     pip install -r requirements.txt

And then run the application::

    cd ihatemoney
    python run.py

In any case, you can point your browser at `http://localhost:5000 <http://localhost:5000>`_.
It's as simple as that!

In case you want to update to newer versions, you can just run the "update" command::

  make update

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

1. Add the lines in conf/supervisord.conf to your supervisord.conf file.
2. Copy and paste the content of conf/nginx.conf in your nginx conf file.
3. reload both nginx and supervisord. It should be working ;)

Don't forget to set the right permission for your files !

Configuration
=============

ihatemoney relies on a configuration file. If you run the application for the
first time, you will need to take a few moments to configure the application
properly.

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

Note that you can also pass additional flask parameters with this file.
e.g. If you want to prefix your URLs to serve ihatemonney in the *folder*
of a domain, use the following: ::

    APPLICATION_ROOT='/budget'
