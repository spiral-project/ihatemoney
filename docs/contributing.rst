Contributing
############

Set up a dev environment
========================

You must develop on top of the Git master branch::

  git clone https://github.com/spiral-project/ihatemoney.git

Then you need to build your dev environment. Choose your way…

The quick way
-------------

If System :ref:`installation-requirements` are fulfilled, you can just issue::

    make serve

It will setup a `virtualenv <https://pypi.python.org/pypi/virtualenv>`_,
install dependencies, and run the test server.

The hard way
------------

Alternatively, you can use pip to install dependencies yourself. That would be::

     pip install -e .

And then run the application::

    cd ihatemoney
    python run.py

Accessing dev server
--------------------

In any case, you can point your browser at `http://localhost:5000 <http://localhost:5000>`_.
It's as simple as that!

Updating
--------

In case you want to update to newer versions (from Git), you can just run the "update" command::

  make update

Create database migrations
--------------------------

In case you need to modify the database schema, first update the models in
``ihatemoney/models.py``. Then run the following command to create a new
database revision file::

  make create-database-revision

If your changes are simple enough, the generated script will be populated with
the necessary migrations steps. You can edit the generated script. e.g: To add
data migrations.

For complex migrations, it is recommended to start from an empty revision file
which can be created with the following command::

  make create-empty-database-revision

Useful settings
----------------

It is better to actually turn the debugging mode on when you're developing.
You can create a ``settings.cfg`` file, with the following content::

    DEBUG = True
    SQLACHEMY_ECHO = DEBUG

You can also set the `TESTING` flag to `True` so no mails are sent
(and no exception is raised) while you're on development mode.
Then before running the application, declare its path with ::

  export IHATEMONEY_SETTINGS_FILE_PATH="$(pwd)/settings.cfg"

How to contribute
=================

You would like to contribute? First, thanks a bunch! This project is a small
project with just a few people behind it, so any help is appreciated!

There are different ways to help us, regarding if you are a designer,
a developer or an user.

As a developer
--------------

If you want to contribute code, you can write it and then issue a pull request
on github. Please, think about updating and running the tests before asking for
a pull request as it will help us to maintain the code clean and running.

To do so::

    make test

We are using the `black <https://black.readthedocs.io/en/stable/>`_ formatter
for all the Python files in this project. Be sure to run it locally on your
files. To do so, just run::

    black ihatemoney

You can also integrate it with your dev environment (as a *format-on-save*
hook, for instance).

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

How to build the documentation ?
================================

The documentation is using `sphinx <http://www.sphinx-doc.org/en/stable/>`_ and
its source is located inside the `docs folder
<https://github.com/spiral-project/ihatemoney/tree/master/docs>`_.

Install doc dependencies (within the virtualenv, if any)::

  pip install -r docs/requirements.txt

And to produce a HTML doc in the `docs/_output` folder::

   cd docs/
   make html

How to release?
===============

In order to prepare a new release, we are following the following steps:

- Merge remaining pull requests;
- Update :file:`CHANGELOG.rst` with the last changes;
- Update :file:`CONTRIBUTORS`;
- Update known good versions of dependencies in ``requirements.txt`` with this
  command (from inside the venv)::

    make build-requirements

- If needed, recompress assets. It requires zopflipng::

    make compress-assets

- Build the translations::
 
    make update-translations
    make build-translations

Once this is done, use the "release" instruction::

    make release

And the new version should be published on PyPI.

.. note:: The above command will prompt for version number, handle
          :file:`CHANGELOG.rst` and :file:`setup.cfg` updates, package creation,
          pypi upload. It will prompt you before each step to get your consent.
