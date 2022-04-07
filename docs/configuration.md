(configuration)=
# Configuration

"ihatemoney" relies on a configuration file. If you run the
application for the first time, you will need to take a few moments to
configure the application properly.

The default values given here are those for the development mode. To
know defaults on your deployed instance, simply look at your
`ihatemoney.cfg` file.

"Production values" are the recommended values for use in production.

## Configuration files

By default, Ihatemoney loads its configuration from `/etc/ihatemoney/ihatemoney.cfg`.

If you need to load the configuration from a custom path, you can define
the `IHATEMONEY_SETTINGS_FILE_PATH` environment variable with the path
to the configuration file. For instance :

    export IHATEMONEY_SETTINGS_FILE_PATH="/path/to/your/conf/file.cfg"

The path should be absolute. A relative path will be interpreted as
being inside `/etc/ihatemoney/`.

## SQLALCHEMY_DATABASE_URI

Specifies the type of backend to use and its location. More information
on the format used can be found on [the SQLAlchemy
documentation](http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls).

-   **Default value:** `sqlite:///tmp/ihatemoney.db`
-   **Production value:** Set it to some path on your disk. Typically
    `sqlite:///home/ihatemoney/ihatemoney.db`. Do *not* store it under
    `/tmp` as this folder is cleared at each boot.

For example, if you're using MariaDB, use a configuration similar to
the following:

    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:pass@localhost/mydb'

If you're using PostgreSQL, your client must use utf8. Unfortunately,
PostgreSQL default is to use ASCII. Either change your client settings,
or specify the encoding by appending `?client_encoding=utf8` to the
connection string. This will look like:

    SQLALCHEMY_DATABASE_URI = 'postgresql://myuser:mypass@localhost/mydb?client_encoding=utf8'

## SECRET_KEY

The secret key used to encrypt cookies and generate secure tokens. They
are used to authenticate access to projects, both through the web
interface and through the API.

As such, you should never use a predictible secret key: an attacker with
the knowledge of the secret key could easily access any project and
bypass the private code verification.

-   **Production value:** `ihatemoney conf-example ihatemoney.cfg`
    sets it to something random, which should be good.

## SESSION_COOKIE_SECURE

A boolean that controls whether the session cookie will be marked
"secure". If this is the case, browsers will refuse to send the
session cookie over plain HTTP.

-   **Default value:** `True`
-   **Production value:** `True` if you run your service over HTTPS,
    `False` if you run your service over plain HTTP.

Note: this setting is actually interpreted by Flask, see the [Flask
documentation](https://flask.palletsprojects.com/en/2.0.x/config/#SESSION_COOKIE_SECURE)
for details.

## MAIL_DEFAULT_SENDER

An email address to use when sending emails.

-   **Default value:** `Budget manager <admin@example.com>`
-   **Production value:** Any valid email address.

## SHOW_ADMIN_EMAIL

A boolean that determines whether the admin email (`MAIL_DEFAULT_SENDER`) is
shown in error messages. This also needs `MAIL_DEFAULT_SENDER` to be set to a 
non default value to show it in the error messages.

-   **Default value:** `True`
-   **Production value:** Usually `True` unless you don't want the admin
    email to be shown for privacy reasons.

## ACTIVATE_DEMO_PROJECT

If set to `True`, a demo project will be available on the frontpage.

-   **Default value:** `True`
-   **Production value:** Usually, you will want to set it to `False`
    for a private instance.

## ADMIN_PASSWORD

Hashed password to access protected endpoints. If left empty, all
administrative tasks are disabled.

-   **Default value:** `""` (empty string)
-   **Production value:** To generate the proper password HASH, use
    `ihatemoney generate_password_hash` and copy the output into the
    value of *ADMIN_PASSWORD*.

## ALLOW_PUBLIC_PROJECT_CREATION

If set to `True`, everyone can create a project without entering the
admin password. If set to `False`, the password needs to be entered (and
as such, defined in the settings).

-   **Default value:** `True`.

## ACTIVATE_ADMIN_DASHBOARD

If set to `True`, the dashboard will become accessible
entering the admin password, if set to `True`, a non empty
ADMIN_PASSWORD needs to be set.

-   **Default value**: `False`

## APPLICATION_ROOT

If empty, ihatemoney will be served at domain root (e.g:
*http://domain.tld*), if set to `"somestring"`, it will be served from a
"folder" (e.g: *http://domain.tld/somestring*).

-   **Default value:** `""` (empty string)

## BABEL_DEFAULT_TIMEZONE

The timezone that will be used to convert date and time when displaying
them to the user (all times are always stored in UTC internally). If not
set, it will default to the timezone configured on the Operating System
of the server running ihatemoney, which may or may not be what you want.

-   **Default value:** *unset* (use the timezone of the server Operating
    System)
-   **Production value:** Set to the timezone of your expected users,
    with a format such as `"Europe/Paris"`. See [this list of TZ
    database names](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List)
    for a complete list.

Note: this setting is actually interpreted by Flask-Babel, see the
[Flask-Babel guide for formatting
dates](https://pythonhosted.org/Flask-Babel/#formatting-dates) for
details.

## ENABLE_CAPTCHA

It is possible to add a simple captcha in order to filter out spammer
bots on the form creation. In order to do so, you just have to set
`ENABLE_CAPTCHA = True`.

-   **Default value:** `False`
-   **Production value:** `True` is recommended to get spam-robots away.


## LEGAL_LINK

You may want to point to a special legal page, for instance to give
information about GDPR, or how you handle the data of your users.

If you want to do this, you can use the `LEGAL_LINK` setting. Set it to the
URL you want.

-   **Default value:** `""` (empty string)
-   **Production value:** The URL of your chosing.

## Configuring email sending

By default, Ihatemoney sends emails using a local SMTP server, but it's
possible to configure it to act differently, thanks to the great
[Flask-Mail
project](https://pythonhosted.org/flask-mail/#configuring-flask-mail)

-   **MAIL_SERVER** : default **'localhost'**
-   **MAIL_PORT** : default **25**
-   **MAIL_USE_TLS** : default **False**
-   **MAIL_USE_SSL** : default **False**
-   **MAIL_DEBUG** : default **app.debug**
-   **MAIL_USERNAME** : default **None**
-   **MAIL_PASSWORD** : default **None**
-   **DEFAULT_MAIL_SENDER** : default **None**
