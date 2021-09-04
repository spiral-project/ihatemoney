Changelog
#########

This document describes changes between each past release.

5.0.0 (unreleased)
==================

Breaking changes
----------------

- Drop support for Python 2 (#483)
- Drop support for Python 3.5 (#571)
- Drop support for MySQL (#743)
- Require MariaDB version 10.3.2 or above (#632)

The minimum supported version is now Python 3.6, and the project is tested
with up to Python 3.9

See `upgrade instructions <https://ihatemoney.readthedocs.io/en/latest/upgrade.html>`_
to make sure the upgrade goes smoothly.

Security
--------

- Add CSRF validation on destructive actions (#796)
- Ask for private code to delete project or project history (#796)

Added
-----

- Allow to import previously exported json data (#518)
- Add new optional field "external link" in bill form (#429)
- Add currencies to project and bills (#541 #814)
- Add new statistics showing monthly expenses (#526)
- Add pagination to the list of bills (#480)
- Add sorting, pagination, and searching to the admin dashboard (#538)
- Add Project History page that records all changes (#553)
- Add token-based authentication to the API (#504)
- Add translations for Hindi, Portuguese (Brazil), Tamil
- Add illustrations as a showcase, currently only for French (#544)
- Add a page for downloading mobile application (#688)
- Add translations for Greek, Esperanto, Italian, Japanese, Portuguese and Swedish

Changed
-------

- Use the external debts lib to solve settlements (#476)
- Remove balance column in statistics view (#323)
- Make language choice persistent (#547)
- Localize date strings in the current language (#590)
- Differenciate "flash alerts" notifications (#594)
- Improve menu bar spacing, put history and settings in a submenu (#739)
- Change Dockerfile to install python dependencies at build time (#793)
- Project code is not required when updating other project settings (#774)
- Bump dependencies: WTForms (#768) jinja2 (#753) itsdangerous (#756) flask (#755 #757 #764)

Fixed
-----

- Improve input of email addresses when inviting people to join a project (#133)
- Fix order of participants in the statistics page (#608)
- Clarify project edition form: private code is not required (#774)
- Fix Python dependency contraints to be less strict
- Improve documentation (#781 #819 #821)
- Add CSRF protection for destructive actions (#796)

Documentation
-------------

- Reorganize "Contributing" documentation to be more accessible to new contributors
- Improve documentation regarding database migrations (#569)

4.1.5 (2020-07-26)
==================

This release fixes a `serious security issue <https://github.com/spiral-project/ihatemoney/security/advisories/GHSA-67j9-c52g-w2q9>`_.

All users are encouraged to upgrade.

Fixed
-----

- Fix unauthorized access and modification of project data (CVE-2020-15120) (#663)

Changed
-------

- Change mobile icon link (#598)
- Improve French translation of email templates (#593)

Added
-----

- Add translations for Portuguese (Brazil), Tamil, Hindi


4.1.4 (2020-06-07)
==================

This is a bugfix-only release.  It is almost certainly the last release to support Python 2:
you should upgrade to Python 3!

Fixed
-----

- Fix failed installation because dependencies were not being pinned (#540, #545, #558)
- backend: Trim usernames to remove leading or trailing spaces. This avoids a situation where different names can be visually identical (#367)
- backend: Fix API to forbid project creation when the `ALLOW_PUBLIC_PROJECT_CREATION` setting is set to false (#496)
- backend: Fix crash when a localized email template is missing (#592)
- backend: Fix language code parsing (#589)
- backend: Improve error handling when sending emails (#595)
- UI: Fix datepicker that was being displayed twice on some browsers (#221)
- UI: Fix "Submit and add a new one" button that had no effect when adding a bill (#498)
- UI: Prevent bill cancellation when cancelling autocomplete (#506)
- UI: Fix responsive width of homepage on small screns (#549)
- UI: Fix color of the "Add a member" button (#499)
- UI: Fix missing HTML tag (#583)
- UI: Fix a small typo in the french project-reminder email (#486)
- UI: Fix typo on message displayed when adding a member (#575)
- UI: Fix incorrect tool-tip message about the private code (#623)
- UI : Fix bug on tool-tip message (#635)

Added
-----

- Add translations for German, Spanish (latin-america), Norwegian (bokmål), Indonesian, Polish, Russian, Chinese, Turkish, Ukrainian
- Update translations for all languages

4.1.3 (2019-09-18)
==================

Fixed
-----

- Fix packaging. Previous (4.1) release wasn't pip-installable on all systems.
- Fix readme and requirements.txt to upload to PyPI.

Changed
-------

- Display password reminder message on a new page rather than on a flash message (#455, #469)

4.1 (2019-09-08)
================

Added
-----

- Add a ``compress_assets`` target in the makefile to compress PNG (#459)
- Document how to use systemd (#435)
- Add support for python 3.7
- Add links to documentation, mobile app and git repository in the
  footer (#445)
- Use weblate to handle translations
- Add dutch translation
- Add project switcher on login page if already logged (#445)

Changed
-------

- Documentation has been cleaned and reorganised.
- Display a placeholder when no entries are present in the bill
  list. (#457)
- Disable the "add bill" action until members are present (#457)
- Improve invitations UX (#451)
- In the bills list, display the "added on" column as a tooltip (#443)
- Updated bootstrap to latest stable (#440)
- Improved "project already exists" message (#442)
- Improve usability specially for small screen (#441)
- Replace export forms by links (#450)
- Rework homepage design (#445)
- Docker now downloads IHM from PyPI or the reference git repo (#446)
- Arrange navbar items by functions (#445)


4.0 (2019-01-24)
================

Added
-----

- Add CORS headers in the API (#407)
- Document database migrations (#390)
- Allow basic math operations in amount field (#413)
- Add bill.creation_date field (#327)
- Document PostgreSQL configuration (#415)

Fixed
-----

- Do not allow negative weights on users (#366)
- Fix docker image (#398)
- minor documentation changes

Changed
-------

- Update API project list (#405)


3.0 (2018-11-25)
================

Fixed
-----

- Fix broken install with pip ≥ 10 (#340)
- Fix the generation of the supervisord template (#309)
- Fix Apache conf template (#359)

- Regenerate translations and improve fr translations (#338)
- Fix the validation of the hashed password (#310)
- Fix infinite loop that happened when accessing / (#358)
- Fix email validation when sending invites
- Fix double-click when deleting a bill (#349)
- Fix error escaping (#388)
- Fix form error on already existing participant (#370)
- Fix documentation for create bills via api (#391)

- Fix docker ADMIN_PASSWORD configuration (#384)
- Fix docker bug where conf is duplicated at each run (#392)
- Fix cffi installation in Dockerfile (#364)

Added
-----

- Document MySQL setup (#357)
- Add a favicon.ico  (#381)
- Document external mail server configuration (#278)
- Improve settings documentation styling (#251)
- Add a ihatemoney delete-project command to delete a project (#375)
- Add nice 404 error pages (#379)

Changed
-------

- Enhance translation tooling (#360)
- Improve Makefile (#387)
- Sort members alphabetically in the new bill form. (#374)
- Underline actions links on hover (#377)

Removed
-------

- Remove Sentry, as it's not used anymore on prod. (#380)


2.1 (2018-02-16)
================

Changed
-------

- Use flask-restful instead of deprecated flask-rest for the REST API (#315)
- Make sidebar scrollable. Usefull for large groups (#316)

Fixed
-----

- Fix the "IOError" crash when running `ihatemoney generate-config` (#308)
- Made the left-hand sidebar scrollable (#318)
- Fix and enhanche Docker support (#320, #321)

Added
-----

- Statistics API (#343)
- Allow to disable/enable member via API (#301)
- Enable basic Apache auth passthrough for API (#303)


2.0 (2017-12-27)
================

Breaking changes
----------------

- ``ADMIN_PASSWORD`` is now stored hashed. The ``ihatemoney generate_password_hash`` command can now be used to generate a proper password HASH (#236)
- Turn the WSGI file into a python module, renamed from budget/ihatemoney.wsgi to ihatemoney/wsgi.py. Please update your Apache/Gunicorn configuration! (#218)
- Admin privileges are now required to access the dashboard (#262)
- `password` field has been removed from project API GET views (#289)

Changed
-------

- Logged admin can see any project (#262)
- Simpler and safer authentication logic (#270)
- Use token based auth to reset passwords (#269)
- Better install doc (#275)
- Use token based auth in invitation e-mails (#280)
- Use hashed passwords for projects (#286)

Added
-----

- ``ihatemoney generate-config`` to give working examples of config files (#275)
- Statistics tab (#257)
- Python3.6 support (#259)
- ALLOW_PUBLIC_PROJECT_CREATION setting (#262)
- Projects can be edited/deleted from the dashboard (#262)
- ACTIVATE_ADMIN_DASHBOARD setting (#262)
- Link to the dashboard in the navigation bar (#262)
- Dockerfile
- Documentation explaining the upgrade process

Fixed
-----

- Fix `PUT api/project/:code/members/:id` API endpoint (#295)
- Fix member name uniqueness validation on API (#299)

Removed
-------

- Remove unused option in the setup script

1.0 (2017-06-20)
================

Added
-----

- Apache WSGI Support (#191)
- Brush up the Makefile (#207, #201)
- Externalize the settings from source folder (#193)
- Makefile: Add new rule to compile translations (#207)
- Project creation can be restricted to admin (#210)
- More responsive layout (#213)

Changed
-------

- Some README enhancements
- Move tests to budget.tests (#205)
- The demo project can be disabled (#209)

Fixed
-----

- Fix sphinx integration (#208)

0.9 (2017-04-04)
================

- First release of the project.
