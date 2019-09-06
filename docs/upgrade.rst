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

1. From the virtualenv (if any)::

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


.. note:: If you are using a virtualenv, then the following commands should be run inside it (see
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
