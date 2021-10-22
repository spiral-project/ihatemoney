Contributing
############

.. _how-to-contribute:

How to contribute
=================

You would like to contribute? First, thanks a bunch! This project is a small
project with just a few people behind it, so any help is appreciated!

There are different ways to help us, regarding if you are a designer,
a developer or an user.

As a developer
--------------

If you want to contribute code, you can write it and then issue a pull request
on github. To get started, please read :ref:`setup-dev-environment` and
:ref:`contributing-developer`.

As a designer / Front-end developer
-----------------------------------

Feel free to provide mockups, or to involve yourself in the discussions
happening on the GitHub issue tracker. All ideas are welcome. Of course, if you
know how to implement them, feel free to fork and make a pull request.

As a translator
---------------

If you're able to translate Ihatemoney in your own language,
head over to `the website we use for translations <https://hosted.weblate.org/projects/i-hate-money/i-hate-money/>`_
and start translating.

All the heavy lifting will be done automatically, and your strings will
eventually be integrated.

Once a language is ready to be integrated, add it to the
``SUPPORTED_LANGUAGES`` list, in ``ihatemoney/default_settings.py``.

End-user
--------

You are using the application and found a bug? You have some ideas about how to
improve the project? Please tell us `by filling a new issue <https://github.com/spiral-project/ihatemoney/issues>`_.
Or, if you prefer, you can send me an e-mail to `alexis@notmyidea.org` and I
will update the issue tracker with your feedback.

Thanks again!

.. _setup-dev-environment:

Set up a dev environment
========================

You must develop on top of the Git master branch::

  git clone https://github.com/spiral-project/ihatemoney.git

Then you need to build your dev environment. Choose your way…

The quick way
-------------

If System :ref:`installation-requirements` are fulfilled, you can just issue::

    make serve

It will setup a `Virtual environment <https://docs.python.org/3/tutorial/venv.html>`_,
install dependencies, and run the test server.

The hard way
------------

Alternatively, you can use pip to install dependencies yourself. That would be::

     pip install -e .

And then run the application::

    cd ihatemoney
    python run.py

The docker way
--------------

If you prefer to use docker, then you can build your image with::

  docker build -t ihatemoney .
  
Accessing dev server
--------------------

In any case, you can point your browser at `http://localhost:5000 <http://localhost:5000>`_.
It's as simple as that!

Updating
--------

In case you want to update to newer versions (from Git), you can just run the "update" command::

  make update

Useful settings
----------------

It is better to actually turn the debugging mode on when you're developing.
You can create a ``settings.cfg`` file, with the following content::

    DEBUG = True
    SQLACHEMY_ECHO = DEBUG

Then before running the application, declare its path with ::

  export IHATEMONEY_SETTINGS_FILE_PATH="$(pwd)/settings.cfg"

You can also set the ``TESTING`` flag to ``True`` so no mails are sent
(and no exception is raised) while you're on development mode.

In some cases, you may need to disable secure cookies by setting
``SESSION_COOKIE_SECURE`` to ``False``. This is needed if you
access your dev server over the network: with the default value
of ``SESSION_COOKIE_SECURE``, the browser will refuse to send
the session cookie over insecure HTTP, so many features of Ihatemoney
won't work (project login, language change, etc).

.. _contributing-developer:

Contributing as a developer
===========================

All code contributions should be submitted as Pull Requests on the
`github project <https://github.com/spiral-project/ihatemoney>`_.

Below are some points that you should check to help you prepare your Pull Request.

Running tests
-------------

Please, think about updating and running the tests before asking for a pull request
as it will help us to maintain the code clean and running.

To run the tests::

    make test

Tests can be edited in ``ihatemoney/tests/tests.py``. If some test cases fail because
of your changes, first check whether your code correctly handle these cases.
If you are confident that your code is correct and that the test cases simply need
to be updated to match your changes, update the test cases and send them as part of
your pull request.

If you are introducing a new feature, you need to either add tests to existing classes,
or add a new class (if your new feature is significantly different from existing code).

Formatting code
---------------

We are using `black <https://black.readthedocs.io/en/stable/>`_ and
`isort <https://timothycrosley.github.io/isort/>`_ formatters for all the Python
files in this project. Be sure to run it locally on your files.
To do so, just run::

    make black isort

You can also integrate them with your dev environment (as a *format-on-save*
hook, for instance).

Creating database migrations
----------------------------

In case you need to modify the database schema, first make sure that you have
an up-to-date database by running the dev server at least once (the quick way
or the hard way, see above).  The dev server applies all existing migrations
when starting up.

You can now update the models in ``ihatemoney/models.py``. Then run the following
command to create a new database revision file::

  make create-database-revision

If your changes are simple enough, the generated script will be populated with
the necessary migrations steps. You can view and edit the generated script, which
is useful to review that the expected model changes have been properly detected.
Usually the auto-detection works well in most cases, but you can of course edit the
script to fix small issues.  You could also edit the script to add data migrations.

When you are done with your changes, don't forget to add the migration script to
your final git commit!

If the migration script looks completely wrong, remove the script and start again
with an empty database.  The simplest way is to remove or rename the dev database
located at ``/tmp/ihatemoney.db``, and run the dev server at least once.

For complex migrations, it is recommended to start from an empty revision file
which can be created with the following command::

  make create-empty-database-revision

You then need to write the migration steps yourself.


How to build the documentation ?
================================

The documentation is using `sphinx <http://www.sphinx-doc.org/en/stable/>`_ and
its source is located inside the `docs folder
<https://github.com/spiral-project/ihatemoney/tree/master/docs>`_.

Install doc dependencies (within the virtual environment, if any)::

  pip install -e .[doc]

And to produce a HTML doc in the `docs/_output` folder::

   cd docs/
   make html

How to release?
===============

In order to issue a new release, follow the following steps:

- Merge remaining pull requests;
- Switch to the master branch;
- Update :file:`CHANGELOG.rst` with the last changes;
- Update :file:`CONTRIBUTORS` (instructions inside the file);
- If needed, recompress assets. It requires zopflipng::

    make compress-assets

- Build the translations::

    make update-translations
    make build-translations

Once this is done, let's release!::

    make release

This will publish the new version to `the Python Package Index <https://pypi.org>`_ (PyPI).

.. note:: The above command will prompt for version number, handle
          :file:`CHANGELOG.rst` and :file:`setup.cfg` updates, package creation,
          pypi upload. It will prompt you before each step to get your consent.
