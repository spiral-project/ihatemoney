# Contributing

## Current direction (as of 2024)

Ihatemoney was started in 2011, and we believe the project has reached a certain
level of maturity now. The overall energy of contributors is not as high as it
used to be.

In addition, there are now several self-hosted alternatives (for instance
[cospend](https://github.com/julien-nc/cospend-nc/tree/main),
[spliit](https://github.com/spliit-app/spliit)).

As maintainers, we believe that the project is still relevant but should gear
towards some kind of "maintenance mode":

* **Simplicity** is now the main goal of the project. It has always been a compass
for the project, and the resulting software is appreciated by both users and
server administrators. For us, "simplicity" is positive and encompasses both
technical aspects (very few javascript code, manageable dependencies, small code
size...) and user-visible aspects (straightforward interface, no need to create
accounts for people you invite, same web interface on mobile...)

* **Stability** is prioritized over adding major new features. We found ourselves
complexifying the codebase (and the interface) while accepting some
contributions. Our goal now is to have a minimal set of features that do most of
the job. We believe this will help lower the maintainance burden.

* **User interface and user experience improvements** are always super welcome !

It is still possible to propose new features, but they should fit into
this new direction. Simplicity of the UI/UX and simplicity of the technical
implementation will be the main factors when deciding to accept new features.


## How to contribute

You would like to contribute? First, thanks a bunch! This project is a
small project with just a few people behind it, so any help is
appreciated!

There are different ways to help us, regarding if you are a designer, a
developer or an user.

### As a developer

If you want to contribute code, you can write it and then issue a pull
request on github. To get started, please read {ref}`setup-dev-environment` and
{ref}`contributing-as-a-dev`.

### As a designer / Front-end developer

Feel free to provide mockups, or to involve yourself in the discussions
happening on the GitHub issue tracker. All ideas are welcome. Of course,
if you know how to implement them, feel free to fork and make a pull
request.

### As a translator

If you're able to translate Ihatemoney in your own language, head over
to [the website we use for
translations](https://hosted.weblate.org/projects/i-hate-money/i-hate-money/)
and start translating.

All the heavy lifting will be done automatically, and your strings will
eventually be integrated.

Once a language is ready to be integrated, add it to the
`SUPPORTED_LANGUAGES` list, in `ihatemoney/default_settings.py`.

### End-user

You are using the application and found a bug? You have some ideas about
how to improve the project? Please tell us [by filling a new
issue](https://github.com/spiral-project/ihatemoney/issues).

Thanks again!

(setup-dev-environment)=
## Set up a dev environment

### Requirements

In addition to general {ref}`requirements<system-requirements>`, you will need
**uv**. It recommended to install uv [system
wide](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)
as it is a kind of replacement for pip.

### Getting the sources

You must develop on top of the Git main branch:

    git clone https://github.com/spiral-project/ihatemoney.git

Then you need to build your dev environment. Choose your way...

### The quick way

If System {ref}`installation-requirements<system-requirements>` are
fulfilled, you can just issue:

    make serve

It will setup a [Virtual
environment](https://docs.python.org/3/tutorial/venv.html), install
dependencies, and run the test server.

### The hard way

Alternatively, you can use pip to install dependencies yourself. That
would be:

    pip install -e .

And then run the application:

    cd ihatemoney
    python run.py

### The docker way

If you prefer to use docker, then you can build your image with:

    docker build -t ihatemoney .

### Accessing dev server

In any case, you can point your browser at <http://localhost:5000>.
It's as simple as that!

### Updating

In case you want to update to newer versions (from Git), you can just
run the "update" command:

    make update

### Useful settings

It is better to actually turn the debugging mode on when you\'re
developing. You can create a `settings.cfg` file, with the following
content:

    DEBUG = True
    SQLACHEMY_ECHO = DEBUG

Then before running the application, declare its path with :

    export IHATEMONEY_SETTINGS_FILE_PATH="$(pwd)/settings.cfg"

You can also set the `TESTING` flag to `True` so no mails are sent (and
no exception is raised) while you\'re on development mode.

In some cases, you may need to disable secure cookies by setting
`SESSION_COOKIE_SECURE` to `False`. This is needed if you access your
dev server over the network: with the default value of
`SESSION_COOKIE_SECURE`, the browser will refuse to send the session
cookie over insecure HTTP, so many features of Ihatemoney won\'t work
(project login, language change, etc).

(contributing-as-a-dev)=
## Contributing as a developer

All code contributions should be submitted as pull requests on the
[github project](https://github.com/spiral-project/ihatemoney).

Below are some points that you should check to help you prepare your
pull request.

### Running tests

Please, think about updating and running the tests before asking for a
pull request as it will help us to maintain the code clean and running.

To run the tests:

    make test

Tests can be edited in `ihatemoney/tests/tests.py`. If some test cases
fail because of your changes, first check whether your code correctly
handle these cases. If you are confident that your code is correct and
that the test cases simply need to be updated to match your changes,
update the test cases and send them as part of your pull request.

If you are introducing a new feature, you need to either add tests to
existing classes, or add a new class (if your new feature is
significantly different from existing code).

### Formatting code

We are using [black](https://black.readthedocs.io/en/stable/) and
[isort](https://timothycrosley.github.io/isort/) formatters for all the
Python files in this project. Be sure to run it locally on your files.
To do so, just run:

    make lint

You can also integrate them with your dev environment (as a
*format-on-save* hook, for instance).

### Creating database migrations

In case you need to modify the database schema, first make sure that you
have an up-to-date database by running the dev server at least once (the
quick way or the hard way, see above). The dev server applies all
existing migrations when starting up.

You can now update the models in `ihatemoney/models.py`. Then run the
following command to create a new database revision file:

    make create-database-revision

If your changes are simple enough, the generated script will be
populated with the necessary migrations steps. You can view and edit the
generated script, which is useful to review that the expected model
changes have been properly detected. Usually the auto-detection works
well in most cases, but you can of course edit the script to fix small
issues. You could also edit the script to add data migrations.

When you are done with your changes, don't forget to add the migration
script to your final git commit!

If the migration script looks completely wrong, remove the script and
start again with an empty database. The simplest way is to remove or
rename the dev database located at `/tmp/ihatemoney.db`, and run the dev
server at least once.

For complex migrations, it is recommended to start from an empty
revision file which can be created with the following command:

    make create-empty-database-revision

You then need to write the migration steps yourself.

## Repository rules

- Please, try to keep it to **one pull request per feature:** if you want to do more
  than one thing, send multiple pull requests. It will be easier for us to review and
  merge.
- **Document your code:** if you add a new feature, please document it in the
- All the people working on this project do it on their spare time. So please, be
  patient if we don't answer right away.
- We try to have two maintainers review the pull requests before merging it. So please,
  be patient if we don't merge it right away. After one week, only one maintainer approval
  is required.


## How to build the documentation ?

The documentation is using
[sphinx](http://www.sphinx-doc.org/en/stable/) and its source is located
inside the [docs
folder](https://github.com/spiral-project/ihatemoney/tree/main/docs).

Install doc dependencies (within the virtual environment, if any):

    pip install -e .[doc]

And to produce a HTML doc in the [docs/_output]{.title-ref} folder:

    cd docs/
    make html

## How to release?

### Requirements

To create a new release, make sure you fullfil all requirements:

-   Are you a maintainer of the pypi package?

-   Are you sure you have no local tags? They will all be published to
    the github process as part of the release process

-   Make sure you have a `~/.pypirc` file with the following content,
    replacing `YOUR_PYPI_USERNAME` with your real username:

        [distutils]
        index-servers =
            pypi

        [pypi]
        username:YOUR_PYPI_USERNAME

### Choosing a version number

The project follows [semantic versioning](https://semver.org/). To sum
things up:

-   **if there is a breaking change since the last release:** increase
    the major version number (11.X.Y → 12.0.0). Example of breaking
    changes: drop support for an old version of python, new setting
    without default value (requires an admin to configure the new
    setting), changed URL paths, any other incompatible change. Make
    sure to {ref}`document the upgrade process<upgrade:Upgrading>`.
-   **if there is a significant new feature or a new setting:** increase
    the minor version number (11.4.Y → 11.5.0). Make sure to
    {ref}`document any new settings<configuration>`.
-   **if it\'s mostly bugfixes and small changes:** increase the patch
    version number (11.4.8 → 11.4.9)

### Making the release

In order to issue a new release, follow the following steps:

-   Merge remaining pull requests;

-   Switch to the main branch;

-   Update `CHANGELOG.md` with the last changes;

-   If needed, recompress assets. It requires zopflipng and ImageMagick
    `mogrify`:

        make compress-assets

-   Extract the translations:

        make extract-translations

-   If you're not completely sure of yourself at this point, you can
    optionally: create a new branch, push it, open a pull request, check
    the CI result, and then merge the branch to main.

Once this is done, make sure your local git repository is on the main
branch, and let's release!:

    make release

This will publish the new version to [the Python Package
Index](https://pypi.org) (PyPI) and publish a tag in the git repository.

::: {note}

The above command will prompt for version number, handle
`CHANGELOG.md` and `pyproject.toml` updates, package creation,
pypi upload. It will prompt you before each step to get your consent.
:::

Finally, create a release on Github and copy the relevant changelog
extract into it.
