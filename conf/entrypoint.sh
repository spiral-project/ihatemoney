#!/bin/sh

# Fail the whole script on the first failure.
set -e

cat <<EOF > /etc/ihatemoney/ihatemoney.cfg
DEBUG = $DEBUG
SQLALCHEMY_DATABASE_URI = "$SQLALCHEMY_DATABASE_URI"
SQLACHEMY_DEBUG = DEBUG
SQLALCHEMY_TRACK_MODIFICATIONS = $SQLALCHEMY_TRACK_MODIFICATIONS
SECRET_KEY = "$SECRET_KEY"
MAIL_SERVER = "$MAIL_SERVER"
MAIL_PORT = $MAIL_PORT
MAIL_USE_TLS = $MAIL_USE_TLS
MAIL_USE_SSL = $MAIL_USE_SSL
MAIL_USERNAME = "$MAIL_USERNAME"
MAIL_PASSWORD = "$MAIL_PASSWORD"
MAIL_DEFAULT_SENDER = "$MAIL_DEFAULT_SENDER"
ACTIVATE_DEMO_PROJECT = $ACTIVATE_DEMO_PROJECT
ADMIN_PASSWORD = '$ADMIN_PASSWORD'
ALLOW_PUBLIC_PROJECT_CREATION = $ALLOW_PUBLIC_PROJECT_CREATION
ACTIVATE_ADMIN_DASHBOARD = $ACTIVATE_ADMIN_DASHBOARD
EOF

if [ ! -z "$NIGHTLY" ]; then
    # Clone or update repository into /ihatemoney.
    if [ ! -d /ihatemoney/.git ]; then
        echo "Cloning..."
        git clone --depth 1 https://github.com/spiral-project/ihatemoney /ihatemoney
        echo "Done cloning."
    else
        cd /ihatemoney
        echo "Updating..."
        git pull || echo "Couldn't update; maybe Github is unreachable?"
        echo "Done updating."
    fi
    pip install --no-cache-dir -e /ihatemoney
else
    # Get the latest release from PyPy.
    pip install --no-cache-dir --upgrade ihatemoney
fi

# Start gunicorn without forking
exec gunicorn ihatemoney.wsgi:application \
     -b 0.0.0.0:8000 \
     --log-syslog \
     "$@"
