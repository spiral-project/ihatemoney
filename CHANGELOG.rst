Changelog
=========

This document describes changes between each past release.

2.0 (unreleased)
----------------

Breaking changes
================

- ``ADMIN_PASSWORD`` is now hashed rather than plain text. The ``ihatemoney generate_password_hash`` command can now be used to generate a proper password HASH (#236)
- Turn the WSGI file into a python module, renamed from budget/ihatemoney.wsgi to ihatemoney/wsgi.py. Please update your Apache configuration! (#218)
- Admin privileges are now required to access the dashboard (#262)

Changed
=======

- Changed the recommended gunicorn configuration to use the wsgi module as an entrypoint (#218)

Added
=====

- Add a statistics tab (#257)
- Add python3.6 support (#259)
- Public project creation can now be deactivated using the ALLOW_PUBLIC_PROJECT_CREATION setting (#262)
- If admin credentials are defined, they can be used to access any project (#262)
- It is now possible to edit and delete projects directly from the dashboard (#262)
- The dashboard can now be deactivated using the ACTIVATE_ADMIN_DASHBOARD setting (#262)
- When activated, a link to the dashboard appears in the navigation bar (#262)

Removed
=======

- Remove unused option in the setup script

1.0 (2017-06-20)
----------------

Added
=====

- Apache WSGI Support (#191)
- Brush up the Makefile (#207, #201)
- Externalize the settings from source folder (#193)
- Makefile: Add new rule to compile translations (#207)
- Project creation can be restricted to admin (#210)
- More responsive layout (#213)

Changed
=======

- Some README enhancements
- Move tests to budget.tests (#205)
- The demo project can be disabled (#209)

Fixed
=====

- Fix sphinx integration (#208)

0.9 (2017-04-04)
----------------

- First release of the project.
