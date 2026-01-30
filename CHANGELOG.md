# Changelog

This document describes changes between each past release.

## 7.0.0 (2026-01-30)

### Breaking changes

- Remove support for python 3.7, 3.9 and 3.10

### Added

- Add "reimbursement" bills and allow to create them directly from the "Settle" page (#1290)
- Add support for python 3.13 (#1392)
- Add support for python 3.12 (#757)
- Add translations for Azerbaijani, Breton, Danish, Basque, and Occitan

## Changed

  Portuguese, Brazilian Portuguese, and Telugu
- Update all Python dependencies (#1392 #1248)

### Development stuff

- Update db versions used in CI to match Debian Trixie (#1392)
- Migrate from setup.cfg to pyproject.toml (#1243)
- Document [repository rules](https://ihatemoney.readthedocs.io/en/latest/contributing.html#repository-rules) (#1253)
- Replace the black linter by ruff
- Replace virtualenv and pip by uv
- Remove tox

## 6.1.5 (2024-03-19)

- Fix README and changelog not being displayed on PyPI
- Fix ability to change project settings when project has existing currency (#1292)
- Update translations for Dutch and German


## 6.1.4 (2023-12-14)

- Fix missing markdown include in manifest (#1274)
- Update translations for Chinese, Turkish, Czech, Spanish (Latin America), Swedish


## 6.1.3 (2023-11-23)

- Revert update to flask and werkzeug 2.3 because of a regression (see #1272)


## 6.1.2 (2023-11-19)

- Fix password generation command line crash (#1242)
- Update to flask and werkzeug 2.3 (#1244)


## 6.1.1 (2023-10-04)

### Currency conversion API workarounds

We are using an external API for currency conversion.  This API recently
started requiring an API key, and this broke I Hate Money in many ways.

This release adds a set of workarounds for this issue.  This should restore
basic functionality such as adding bills.  However, we had to disable
some operations to prevent crashing:

- Setting or changing the default currency on an existing project is no longer possible.
  However, setting a project to "No currency" is still possible.
- Adding or editing a bill with a currency that differs from the default currency
  of the project is no longer possible

[Longer-term solutions are being discussed](https://github.com/spiral-project/ihatemoney/issues/1232).
If you are using currencies in your projects, your input is welcome.

### Added

- Simplifies adding a bill with keyboard only (#1221)
- Add details of bills in history (#1223)
- Remember last "For whom?" field when adding a new bill (#1222)
- Speed up unit tests (#1214)
- Update translations for Spanish, Russian, Kannada, Swedish, Polish, German, and Italian

### Fixed
- Fix remembering the last selected payer when switching project (#1224)


## 6.1.0 (2023-07-29)

### Added
- Add RSS feed for each project (#1158)
- Security: require private code to edit a project settings (#1204)

### Fixed
- Fix 404 page crash (#1201)


## 6.0.1 (2023-07-22)

### Added
- Add support for `APPLICATION_ROOT` in Docker container (#1189)
- Improve docker-compose example: admin password and volume for database (#1169)

### Fixed
- Fix docker-compose example quoting (#1164)
- Fix crash when using existing sessions (migrate them to dict) (#1194)
- Add newly created projects to the list of projects (#1193)


## 6.0.0 (2023-07-13)

### Breaking changes
- Drop Python 3.6 support
- Add Python 3.11 support

The minimum supported version is now Python 3.7, and the project is
tested with up to Python 3.11

### Added
- Enable new languages: Catalan, Czech, Spanish, Persian, Hebrew, Hungarian, Kannada, Serbian, Telugu, Thai
- Build ARM64 and ARMv7 Docker image (#1141)
- Allow bills with an amount of zero (#1133)
- Add confirmation for expense deletion (#1096)
- Display a QR code when inviting people (#1000)
- Add a cancel button when editing a bill for better UX (#1013)

### Fixed
- Fix project deletion in the dashboard (#1094)
- Fix duplicate project name in dropdown list (#1082)
- Fix captcha validation, it should be case insensitive on both side (#1061)
- Fix CSRF on logout (#1040)
- Fix XSS when inviting people by email (#1044)

### Changed
- Use a better quality favicon (#1102)
- Use Flask-Limiter to implement rate limiting (#1054)

## 5.2.0 (2022-04-07)

### Added

- Make docker image production-ready: support PostgreSQL, allow customizing port, PUID, PGID (#919)
- List supported currencies in API under api/currencies (#961)
- Allow to import bills in CSV format, compatible with Cospend (#951)
  Note that there is a [known issue with this new feature](https://github.com/spiral-project/ihatemoney/issues/980)

### New settings

- Add [SHOW_ADMIN_EMAIL](https://ihatemoney.readthedocs.io/en/latest/configuration.html#show-admin-email)
  setting (#965)

### Changed settings

- [MAIL_DEFAULT_SENDER](https://ihatemoney.readthedocs.io/en/latest/configuration.html#mail-default-sender)
  is now a string instead of a tuple.  The old syntax is still accepted but support will be dropped on
  the next major release (#1007)

### Fixed

- Fix support for project IDs with uppercase characters (#925, #934)
- Purge project history on deletion (#989)
- Prevent large integer inputs to avoid crash (#994)
- [Performance] Get weight sum along with bills to scale (#949)
- Do not require a captcha when using the API (#931)
- Fix default "legal link" value in docker (#950)
- Fix showcase images in case of subdir installation (#974)
- Check that chosen language is in the supported list (#971)

### Changed

- User interface fixes, especially for mobile devices (#901, #904, #905, #929, #943, #944, #945, #991)
- Always display topmost buttons in the list of bills: new bill button & pagination (#956)
- Display monthly statistics for the range of months where the project was active (#885)
- Hide "each" amount when there's only one recipient (#1008)
- Display admin email in error message for password reminder (#965)
- Send an email when the project is created via the API (#938)
- Add compatibility with Python 3.10 (#921)
- Support WTForms 3 (#916)

## 5.1.1 (2021-10-26)

-   No actual change, fixup release because 5.1.0 did not upload to pypi

## 5.1.0 (2021-10-26)

### Added

-   Add the option to display a "legal link" at the bottom of pages (#883)

### New settings

-   Add [LEGAL_LINK](https://ihatemoney.readthedocs.io/en/latest/configuration.html#legal-link)
    setting (#883)

### Changed

-   Improve performance of balance and statistics computation (#890)
-   Reduce the resolution of showcase pictures by 50% (#880)
-   Improve pagination style in the list of bills (#873)

## 5.0.1 (2021-10-20)

-   Include images in the package archives (#872)

## 5.0.0 (2021-10-19)

### Breaking changes

-   Include project code into project authentication token. This
    invalidates all existing API tokens and invitation links from
    previous versions (#802 #843)
-   Drop support for Python 2 (#483)
-   Drop support for Python 3.5 (#571)
-   Drop support for MySQL (#743)
-   Require MariaDB version 10.3.2 or above (#632)
-   Enable session cookie security by default (#845)
-   Change token path authentication to /{project}/join/{token} (#843)

The minimum supported version is now Python 3.6, and the project is
tested with up to Python 3.9

See [upgrade instructions](https://ihatemoney.readthedocs.io/en/latest/upgrade.html)
to make sure the upgrade goes smoothly.

### Security

-   Add CSRF validation on destructive actions (#796)
-   Ask for private code to delete project or project history (#796)
-   Add headers to mitigate Clickjacking, XSS, and other attacks:
    [X-Frame-Options]{.title-ref}, [X-XSS-Protection]{.title-ref},
    [X-Content-Type-Options]{.title-ref},
    [Content-Security-Policy]{.title-ref}, [Referrer-Policy]{.title-ref}
    (#845)
-   Add URL validation to external link to prevent XSS (#846)

### Added

-   Allow to import previously exported json data (#518)
-   Add new optional field "external link" in bill form (#429)
-   Add optional currencies to project and bills (#541, #864)
-   Add new statistics showing monthly expenses (#526)
-   Add pagination to the list of bills (#480)
-   Add sorting, pagination, and searching to the admin dashboard (#538)
-   Add Project History page that records all changes (#553)
-   Add token-based authentication to the API (#504)
-   Add illustrations as a showcase, currently only for French (#544)
-   Add a page for downloading mobile application (#688)
-   Add optional support for a simple CAPTCHA (#844)
-   Add translations for Greek, Esperanto, Italian, Japanese, Portuguese
    and Swedish
-   Publish an [official docker
    image](https://hub.docker.com/r/ihatemoney/ihatemoney)

### New settings

-   Add
    [ENABLE_CAPTCHA](https://ihatemoney.readthedocs.io/en/latest/configuration.html#enable-captcha)
    setting (#844)
-   Use and document
    [SESSION_COOKIE_SECURE](https://ihatemoney.readthedocs.io/en/latest/configuration.html#session-cookie-secure)
    setting (#845)
-   Use and document
    [BABEL_DEFAULT_TIMEZONE](https://ihatemoney.readthedocs.io/en/latest/configuration.html#babel-default-timezone)
    setting (#590)

### Changed

-   Use the external debts lib to solve settlements (#476)
-   Remove balance column in statistics view (#323)
-   Make language choice persistent (#547)
-   Localize date strings in the current language (#590)
-   Differenciate "flash alerts" notifications (#594)
-   Display "flash messages" persistently instead of making them
    disappear (#856)
-   Improve menu bar spacing, put history and settings in a submenu
    (#739)
-   Change Dockerfile to install python dependencies at build time
    (#793)
-   Updating project settings doesn\'t require to enter or update
    project code (#774)
-   Bump dependencies: WTForms (#768) jinja2 (#753) itsdangerous (#756)
    flask (#755 #757 #764)
-   Remove requirements files in favor of setup.cfg pinning (#558)
-   Make language choice persistent (#547)
-   Flash messages must be dimissed manually (#856)
-   Increased the font size of the logo (#828)

### Fixed

-   Improve input of email addresses when inviting people to join a
    project (#133)
-   Fix order of participants in the statistics page (#608)
-   Clarify project edition form: private code is not required (#774)
-   Fix Python dependency contraints to be less strict
-   Improve documentation (#781 #819 #821)
-   Fix datepicker that was displayed twice on some browsers (#221)
-   Members weight are now rounded to 2 decimal (#838)

### Documentation

-   Reorganize "Contributing" documentation to be more accessible to
    new contributors
-   Improve documentation regarding database migrations (#569)
-   Added a page about [the security
    model](https://ihatemoney.readthedocs.io/en/latest/security.html)
    (#858)

## 4.1.5 (2020-07-26)

This release fixes a [serious security
issue](https://github.com/spiral-project/ihatemoney/security/advisories/GHSA-67j9-c52g-w2q9).

All users are encouraged to upgrade.

### Fixed

-   Fix unauthorized access and modification of project data
    (CVE-2020-15120) (#663)

### Changed

-   Change mobile icon link (#598)
-   Improve French translation of email templates (#593)

### Added

-   Add translations for Portuguese (Brazil), Tamil, Hindi

## 4.1.4 (2020-06-07)

This is a bugfix-only release. It is almost certainly the last release
to support Python 2: you should upgrade to Python 3!

### Fixed

-   Fix failed installation because dependencies were not being pinned
    (#540, #545, #558)
-   backend: Trim usernames to remove leading or trailing spaces. This
    avoids a situation where different names can be visually identical
    (#367)
-   backend: Fix API to forbid project creation when the
    [ALLOW_PUBLIC_PROJECT_CREATION]{.title-ref} setting is set to false
    (#496)
-   backend: Fix crash when a localized email template is missing (#592)
-   backend: Fix language code parsing (#589)
-   backend: Improve error handling when sending emails (#595)
-   UI: Fix datepicker that was being displayed twice on some browsers
    (#221)
-   UI: Fix "Submit and add a new one" button that had no effect when
    adding a bill (#498)
-   UI: Prevent bill cancellation when cancelling autocomplete (#506)
-   UI: Fix responsive width of homepage on small screns (#549)
-   UI: Fix color of the "Add a member" button (#499)
-   UI: Fix missing HTML tag (#583)
-   UI: Fix a small typo in the french project-reminder email (#486)
-   UI: Fix typo on message displayed when adding a member (#575)
-   UI: Fix incorrect tool-tip message about the private code (#623)
-   UI : Fix bug on tool-tip message (#635)

### Added

-   Add translations for German, Spanish (latin-america), Norwegian
    (bokmål), Indonesian, Polish, Russian, Chinese, Turkish, Ukrainian
-   Update translations for all languages

## 4.1.3 (2019-09-18)

### Fixed

-   Fix packaging. Previous (4.1) release wasn\'t pip-installable on all
    systems.
-   Fix readme and requirements.txt to upload to PyPI.

### Changed

-   Display password reminder message on a new page rather than on a
    flash message (#455, #469)

## 4.1 (2019-09-08)

### Added

-   Add a `compress_assets` target in the makefile to compress PNG
    (#459)
-   Document how to use systemd (#435)
-   Add support for python 3.7
-   Add links to documentation, mobile app and git repository in the
    footer (#445)
-   Use weblate to handle translations
-   Add dutch translation
-   Add project switcher on login page if already logged (#445)

### Changed

-   Documentation has been cleaned and reorganised.
-   Display a placeholder when no entries are present in the bill list.
    (#457)
-   Disable the "add bill" action until members are present (#457)
-   Improve invitations UX (#451)
-   In the bills list, display the "added on" column as a tooltip
    (#443)
-   Updated bootstrap to latest stable (#440)
-   Improved "project already exists" message (#442)
-   Improve usability specially for small screen (#441)
-   Replace export forms by links (#450)
-   Rework homepage design (#445)
-   Docker now downloads IHM from PyPI or the reference git repo (#446)
-   Arrange navbar items by functions (#445)

## 4.0 (2019-01-24)

### Added

-   Add CORS headers in the API (#407)
-   Document database migrations (#390)
-   Allow basic math operations in amount field (#413)
-   Add bill.creation_date field (#327)
-   Document PostgreSQL configuration (#415)

### Fixed

-   Do not allow negative weights on users (#366)
-   Fix docker image (#398)
-   minor documentation changes

### Changed

-   Update API project list (#405)

## 3.0 (2018-11-25)

### Fixed

-   Fix broken install with pip ≥ 10 (#340)
-   Fix the generation of the supervisord template (#309)
-   Fix Apache conf template (#359)
-   Regenerate translations and improve fr translations (#338)
-   Fix the validation of the hashed password (#310)
-   Fix infinite loop that happened when accessing / (#358)
-   Fix email validation when sending invites
-   Fix double-click when deleting a bill (#349)
-   Fix error escaping (#388)
-   Fix form error on already existing participant (#370)
-   Fix documentation for create bills via api (#391)
-   Fix docker ADMIN_PASSWORD configuration (#384)
-   Fix docker bug where conf is duplicated at each run (#392)
-   Fix cffi installation in Dockerfile (#364)

### Added

-   Document MySQL setup (#357)
-   Add a favicon.ico (#381)
-   Document external mail server configuration (#278)
-   Improve settings documentation styling (#251)
-   Add a ihatemoney delete-project command to delete a project (#375)
-   Add nice 404 error pages (#379)

### Changed

-   Enhance translation tooling (#360)
-   Improve Makefile (#387)
-   Sort members alphabetically in the new bill form. (#374)
-   Underline actions links on hover (#377)

### Removed

-   Remove Sentry, as it\'s not used anymore on prod. (#380)

## 2.1 (2018-02-16)

### Changed

-   Use flask-restful instead of deprecated flask-rest for the REST API
    (#315)
-   Make sidebar scrollable. Usefull for large groups (#316)

### Fixed

-   Fix the "IOError" crash when running [ihatemoney
    generate-config]{.title-ref} (#308)
-   Made the left-hand sidebar scrollable (#318)
-   Fix and enhanche Docker support (#320, #321)

### Added

-   Statistics API (#343)
-   Allow to disable/enable member via API (#301)
-   Enable basic Apache auth passthrough for API (#303)

## 2.0 (2017-12-27)

### Breaking changes

-   `ADMIN_PASSWORD` is now stored hashed. The
    `ihatemoney generate_password_hash` command can now be used to
    generate a proper password HASH (#236)
-   Turn the WSGI file into a python module, renamed from
    budget/ihatemoney.wsgi to ihatemoney/wsgi.py. Please update your
    Apache/Gunicorn configuration! (#218)
-   Admin privileges are now required to access the dashboard (#262)
-   [password]{.title-ref} field has been removed from project API GET
    views (#289)

### Changed

-   Logged admin can see any project (#262)
-   Simpler and safer authentication logic (#270)
-   Use token based auth to reset passwords (#269)
-   Better install doc (#275)
-   Use token based auth in invitation e-mails (#280)
-   Use hashed passwords for projects (#286)

### Added

-   `ihatemoney generate-config` to give working examples of config
    files (#275)
-   Statistics tab (#257)
-   Python3.6 support (#259)
-   ALLOW_PUBLIC_PROJECT_CREATION setting (#262)
-   Projects can be edited/deleted from the dashboard (#262)
-   ACTIVATE_ADMIN_DASHBOARD setting (#262)
-   Link to the dashboard in the navigation bar (#262)
-   Dockerfile
-   Documentation explaining the upgrade process

### Fixed

-   Fix [PUT api/project/:code/members/:id]{.title-ref} API endpoint
    (#295)
-   Fix member name uniqueness validation on API (#299)

### Removed

-   Remove unused option in the setup script

## 1.0 (2017-06-20)

### Added

-   Apache WSGI Support (#191)
-   Brush up the Makefile (#207, #201)
-   Externalize the settings from source folder (#193)
-   Makefile: Add new rule to compile translations (#207)
-   Project creation can be restricted to admin (#210)
-   More responsive layout (#213)

### Changed

-   Some README enhancements
-   Move tests to budget.tests (#205)
-   The demo project can be disabled (#209)

### Fixed

-   Fix sphinx integration (#208)

## 0.9 (2017-04-04)

-   First release of the project.
