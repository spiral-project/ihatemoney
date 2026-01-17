FROM python:3.11-alpine

ENV PORT="8000" \
    # Keeps Python from generating .pyc files in the container
    PYTHONDONTWRITEBYTECODE=1 \
    # Turns off buffering for easier container logging
    PYTHONUNBUFFERED=1

# ihatemoney configuration
ENV DEBUG="False" \
    ACTIVATE_ADMIN_DASHBOARD="False" \
    ACTIVATE_DEMO_PROJECT="True" \
    ADMIN_PASSWORD="" \
    ALLOW_PUBLIC_PROJECT_CREATION="True" \
    BABEL_DEFAULT_TIMEZONE="UTC" \
    GREENLET_TEST_CPP="no" \
    MAIL_DEFAULT_SENDER="Budget manager <admin@example.com>" \
    MAIL_PASSWORD="" \
    MAIL_PORT="25" \
    MAIL_SERVER="localhost" \
    MAIL_USE_SSL="False" \
    MAIL_USE_TLS="False" \
    MAIL_USERNAME="" \
    SECRET_KEY="tralala" \
    SESSION_COOKIE_SECURE="True" \
    SHOW_ADMIN_EMAIL="True" \
    SQLALCHEMY_DATABASE_URI="sqlite:////database/ihatemoney.db" \
    SQLALCHEMY_TRACK_MODIFICATIONS="False" \
    APPLICATION_ROOT="/" \
    ENABLE_CAPTCHA="False" \
    LEGAL_LINK=""

ADD . /src

RUN echo "**** install build dependencies ****" &&\
    apk add --no-cache --virtual=build-dependencies \
    gcc \
    musl-dev \
    postgresql-dev &&\
    echo "**** install runtime packages ****" && \
    apk add --no-cache \
    shadow \
    postgresql-libs && \
    echo "**** create runtime folder ****" && \
    mkdir -p /etc/ihatemoney &&\
    echo "**** install pip packages ****" && \
    pip install --no-cache-dir \
    gunicorn && \
    pip install --no-cache-dir -e /src[database] && \
    echo "**** create user abc:abc ****" && \
    useradd -u 1000 -U -d /src abc && \
    echo "**** cleanup ****" && \
    apk del --purge build-dependencies &&\
    rm -rf \
    /tmp/*

VOLUME /database
EXPOSE ${PORT}
ENTRYPOINT ["/src/conf/entrypoint.sh"]
