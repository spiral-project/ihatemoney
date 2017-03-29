Budget-manager
##############

.. image:: https://travis-ci.org/spiral-project/ihatemoney.svg?branch=master
   :target: https://travis-ci.org/spiral-project/ihatemoney
   :alt: Travis CI Build Status

This is a really tiny app to ease the shared houses budget management. Keep
track of who bought what, when, and for who to then compute the balance of each
person.

The code is distributed under a BSD beerware derivative: if you meet the people
in person and you want to pay them a beer, you are encouraged to do so (see
LICENSE for more details).

Make it run!
============

With a `Python 3 <https://www.python.org/>` environment,
`pip <https://pypi.python.org/pypi/pip/>` and
`virtualenv <https://pypi.python.org/pypi/virtualenv>` installed,
you just have to run the following command::

    $ make serve

This will run a Flask app available at `http://localhost:5000`.

Deploy it
=========

You have multiple options to deploy ihatemoney. Two of them are documented at the moment:

With Apache and mod_wsgi
------------------------

1. Install Apache and mod_wsgi - libapache2-mod-wsgi(-py3) for Debian based and mod_wsgi for RedHat based distributions -

2. Create an Apache virtual host based on the sample configuration file in conf/apache-vhost.conf

3. Adapt it to your paths and specify your virtualenv path if you use one

4. Activate the virtual host if needed and restart Apache

With Nginx, Gunicorn and Supervisord
------------------------------------

1. Add the lines in conf/supervisord.conf to your supervisord.conf file.
   **adapt them to your paths!**
2. Copy and paste the content of conf/nginx.conf in your nginx conf file.
   **adapt them to your paths!**
3. reload both nginx and supervisord. It should be working ;)

Don't forget to set the right permission for your files !

Configure it
============

In a production environment
---------------------------

Make a copy of ``budget/default_settings.py`` and name it ``ihatemoney.cfg``.
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

In a dev environment
--------------------

It is better to actually turn the debugging mode on when you're developing.
You can create a ``settings.cfg`` file, with the following content::

    DEBUG = True
    SQLACHEMY_ECHO = DEBUG

You can also set the `TESTING` flag to `True` so no mails are sent
(and no exception is raised) while you're on development mode.
Then before running the application, declare its path with ::

    $ export IHATEMONEY_SETTINGS_FILE_PATH="$(pwd)/settings.cfg"

The REST API?
=============

Yep, you're right, there is a REST API with this. Head to the `api
documentation <https://ihatemoney.readthedocs.io/en/latest/api.html>`_ to know more.

How to contribute
=================

You would like to contribute? First, thanks a bunch! This project is a small
project with just a few people behind it, so any help is appreciated!

There are different ways to help us, regarding if you are a designer,
a developer or an user.

As a developer
--------------

If you want to contribute code, you can write it and then issue a pull request on
github. Please, think about updating and running the tests before asking for
a pull request as it will help us to maintain the code clean and running.

To do so::

    $ make test

As a designer / Front-end developer
-----------------------------------

Feel free to provide us mockups or to involve yourself into the discussions
hapenning on the github issue tracker. All ideas are welcome. Of course, if you
know how to implement them, feel free to fork and make a pull request.

End-user
--------

You are using the application and found a bug? You have some ideas about how to
improve the project? Please tell us [by filling a new issue](https://github.com/spiral-project/ihatemoney/issues).
Or, if you prefer, you can send me an email to `alexis@notmyidea.org` and I will
update the issue tracker with your feedback.

Thanks again!

How to release?
===============

In order to prepare a new release, we are following the following steps:

- Merge remaining pull requests;
- Update :file:`CHANGELOG.rst` with the last changes;
- Update :file:`CONTRIBUTORS`;
- Update known good versions of dependencies in ``requirements.txt`` with this command (from inside the venv):

.. code-block:: bash

     $ pip freeze | grep -v -- '-e' > requirements.txt

Once this is done, use the "release" instruction:

.. code-block:: bash

     $ make release 

And the new version should be published on PyPI.
