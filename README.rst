Budget-manager
##############

:author: Alexis Métaireau
:date: 10/03/2010
:technologies: Python, Flask, SQLAlchemy, WTForm

This is a really tiny app to ease the shared houses budget management. Keep
track of who bought what, when, and for who to then compute the balance of each
person.

Make it run!
============

To make it run, you just have to do something like::

    $ virtualenv venv
    $ source budget/bin/activate
    $ pip install flask flask-wtf flask-sqlalchemy
    $ cd budget
    $ python budget.py

Deploy it
=========

To deploy it, I'm using gunicorn and supervisord::

1. Add the lines in conf/supervisord.conf to your supervisord.conf file.
   **adapt them to your paths!**
2. Copy and paste the content of conf/nginx.conf in your nginx conf file.
   **adapt them to your paths!**
3. reload both nginx and supervisord. It should be working ;)
