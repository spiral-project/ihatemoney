Budget-manager
##############

This is a really tiny app to ease the shared houses budget management. Keep
track of who bought what, when, and for who to then compute the balance of each
person.

Make it run!
============

To make it run, you just have to do something like::

    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt
    $ cd budget
    $ python run.py

Deploy it
=========

To deploy it, I'm using gunicorn and supervisord::

    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt

1. Add the lines in conf/supervisord.conf to your supervisord.conf file.
   **adapt them to your paths!**
2. Copy and paste the content of conf/nginx.conf in your nginx conf file.
   **adapt them to your paths!**
3. reload both nginx and supervisord. It should be working ;)

Don't forget to set the right permission for your files !

How to contribute
=================

There are different ways to help us, regarding if you are a designer,
a developer or just an user.

As a developer
--------------

The best way to contribute code is to write it and to make a pull request on
github. Please, think about updating and running the tests before asking for 
a pull request as it will help us to maintain the code clean and running.

As a designer / Front-end developer
-----------------------------------

Feel free to provide us mockups or to involve yourself into the discussions
hapenning on the github issue tracker. All ideas are welcome. Of course, if you
know how to implement them, feel free to fork and make a pull request.

End-user
--------

You just wanted to have a look at the application and found a bug? Please tell
us and go fill a new issue:
https://github.com/ametaireau/budget-manager/issues/new
