FROM python:3.7-alpine

ENV NIGHTLY="" \
    DEBUG="False" \
    SQLALCHEMY_DATABASE_URI="sqlite:////database/ihatemoney.db" \
    SQLALCHEMY_TRACK_MODIFICATIONS="False" \
    SECRET_KEY="tralala" \
    MAIL_DEFAULT_SENDER="('Budget manager', 'budget@notmyidea.org')" \
    MAIL_SERVER="localhost" \
    MAIL_PORT=25 \
    MAIL_USE_TLS=False \
    MAIL_USE_SSL=False \
    MAIL_USERNAME= \
    MAIL_PASSWORD= \
    ACTIVATE_DEMO_PROJECT="True" \
    ADMIN_PASSWORD="" \
    ALLOW_PUBLIC_PROJECT_CREATION="True" \
    ACTIVATE_ADMIN_DASHBOARD="False" \
    BABEL_DEFAULT_TIMEZONE="UTC" \
    GREENLET_TEST_CPP="no"

RUN apk update && apk add git gcc libc-dev libffi-dev openssl-dev wget &&\
    mkdir -p /etc/ihatemoney &&\
    pip install --no-cache-dir gunicorn pymysql;

COPY ./conf/entrypoint.sh /entrypoint.sh

VOLUME /database
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
