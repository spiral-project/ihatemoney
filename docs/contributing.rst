Contributing
############

Setup a dev environment
=======================

It is better to actually turn the debugging mode on when you're developing.
You can create a ``settings.cfg`` file, with the following content::

    DEBUG = True
    SQLACHEMY_ECHO = DEBUG

You can also set the `TESTING` flag to `True` so no mails are sent
(and no exception is raised) while you're on development mode.
Then before running the application, declare its path with ::

    $ export IHATEMONEY_SETTINGS_FILE_PATH="$(pwd)/settings.cfg"

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
