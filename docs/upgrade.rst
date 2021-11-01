.. _upgrade:

Upgrading
#########

We keep `a ChangeLog
<https://github.com/spiral-project/ihatemoney/blob/master/CHANGELOG.rst>`_. Read
it before upgrading.

Ihatemoney follows `semantic versioning <http://semver.org/>`_. So minor/patch
upgrades can be done blindly.

.. _general-procedure:

General procedure
=================

*(sufficient for minor/patch upgrades)*

1. From the virtual environment (if any)::

    pip install -U ihatemoney

2. Restart *supervisor*, or *Apache*, depending on your setup.

You may also want to set new configuration variables (if any). They are
mentioned in the `ChangeLog
<https://github.com/spiral-project/ihatemoney/blob/master/CHANGELOG.rst>`_, but
this is **not required for minor/patch upgrades**, a safe default will be used
automatically.

Version-specific instructions
=============================

*(must read for major upgrades)*

When upgrading from a major version to another, you **must** follow special
instructions:

4.x → 5.x
---------

Switch to a supported version of Python
+++++++++++++++++++++++++++++++++++++++

.. note:: If you are already using Python ≥ 3.6, you can skip this section, no
          special action is required.

If you were running IHateMoney using Python < 3.6, you must, **before** upgrading:

1. Ensure to have a Python ≥ 3.6 available on your system
2. Rebuild your virtual environment (if any). It will *not* alter your database nor configuration. For example, if your virtual environment is in `/home/john/ihatemoney/`::

     rm -rf /home/john/ihatemoney
     pyhton3 -m venv /home/john/ihatemoney
     source /home/john/ihatemoney/bin/activate

  You might need to ``pip install`` additional dependencies if you are using one
  or several of the following deployment options :

  - Gunicorn (Nginx)
  - MariaDB
  - PostgreSQL

If so, pick the ``pip`` commands to use in the relevant section(s) of
:ref:`installation`.

Then follow :ref:`general-procedure` from step 1. in order to complete the update.

Disable session cookie security if running over plain HTTP
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. note:: If you are running Ihatemoney over HTTPS, no special action is required.

Session cookies are now marked "secure" by default to increase security.

If you run Ihatemoney over plain HTTP, you need to explicitly disable this security
feature by setting ``SESSION_COOKIE_SECURE`` to ``False``, see :ref:`configuration`.


Switch to MariaDB >= 10.3.2 instead of MySQL
++++++++++++++++++++++++++++++++++++++++++++

.. note:: If you are using SQLite or PostgreSQL, you can skip this section, no
          special action is required.

If you were running IHateMoney with MySQL, you must switch to MariaDB.
MySQL is no longer a supported database option.

In addition, the minimum supported version of MariaDB is 10.3.2.
See `this MySQL / MariaDB issue <https://github.com/spiral-project/ihatemoney/issues/632>`_
for details.

To upgrade:

1. Ensure you have a MariaDB server installed and configured, and that its
   version is at least 10.3.2.

2. Copy your database from MySQL to MariaDB.

3. Ensure that IHateMoney is correctly configured to use your MariaDB database,
   see :ref:`configuration`.

Then follow :ref:`general-procedure` from step 1. in order to complete the update.

2.x → 3.x
---------

Sentry support has been removed. Sorry if you used it.

Appart from that, :ref:`general-procedure` applies.


1.x → 2.x
---------

Switch from git installation to pip installation
++++++++++++++++++++++++++++++++++++++++++++++++

The recommended installation method is now using *pip*. Git is now intended for
development only.

.. warning:: Be extra careful to not remove your sqlite database nor your
             settings file, if they are stored inside the cloned folder.

1. Delete the cloned folder


.. note:: If you are using a virtual environment, then the following commands should be run inside it (see
          :ref:`virtualenv-preparation`).


2. Install ihatemoney with pip::

    pip install ihatemoney

3. Fix your configuration file (paths *have* changed), depending on
   the software you use in your setup:

   - **gunicorn**: ``ihatemoney generate-config gunicorn.conf.py`` (nothing
     critical changed, keeping your old config might be fine)

   - **supervisor** : ``ihatemoney generate-config supervisord.conf`` (mind the
     ``command=`` line)

   - **apache**: ``ihatemoney generate-config apache-vhost.conf`` (mind the
     ``WSGIDaemonProcess``, ``WSGIScriptAlias`` and ``Alias`` lines)
4. Restart *Apache* or *Supervisor*, depending on your setup.

Upgrade ADMIN_PASSWORD to its hashed form
++++++++++++++++++++++++++++++++++++++++++

.. note:: Not required if you are not using the ADMIN_PASSWORD feature.

``ihatemoney generate_password_hash`` will do the hashing job for you, just put
 its result in the ``ADMIN_PASSWORD`` var from your `ihatemoney.cfg` and
 restart *apache* or the *supervisor* job.
