Changelog
=========

This document describes changes between each past release.

2.0 (unreleased)
----------------

### Changed

- **BREAKING CHANGE** Use a hashed ``ADMIN_PASSWORD`` instead of a clear text one, ``./budget/manage.py generate_password_hash`` can be used to generate a proper password HASH (#236)

### Removed

- Remove unused option in the setup script

1.0 (2017-06-20)
----------------

### Added

- Apache WSGI Support (#191)
- Brush up the Makefile (#207, #201)
- Externalize the settings from source folder (#193)
- Makefile: Add new rule to compile translations (#207)
- Project creation can be restricted to admin (#210)
- More responsive layout (#213)

### Changed

- Some README enhancements
- Move tests to budget.tests (#205)
- The demo project can be disabled (#209)

### Fixed

- Fix sphinx integration (#208)

0.9 (2017-04-04)
----------------

- First release of the project.
