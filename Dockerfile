FROM python:3.10-alpine

ENV PORT="8000"

# ihatemoney configuration
ENV DEBUG="False" \
    ACTIVATE_ADMIN_DASHBOARD="False" \
    ACTIVATE_DEMO_PROJECT="True" \
    ADMIN_PASSWORD="" \
    ALLOW_PUBLIC_PROJECT_CREATION="True" \
    BABEL_DEFAULT_TIMEZONE="UTC" \
    GREENLET_TEST_CPP="no" \
    MAIL_DEFAULT_SENDER="('Budget manager', 'budget@notmyidea.org')" \
    MAIL_PASSWORD="" \
    MAIL_PORT="25" \
    MAIL_SERVER="localhost" \
    MAIL_USE_SSL="False" \
    MAIL_USE_TLS="False" \
    MAIL_USERNAME="" \
    SECRET_KEY="tralala" \
    SESSION_COOKIE_SECURE="True" \
    SQLALCHEMY_DATABASE_URI="sqlite:////database/ihatemoney.db" \
    SQLALCHEMY_TRACK_MODIFICATIONS="False" \
    ENABLE_CAPTCHA="False" \
    LEGAL_LINK="False"

ADD . /src

RUN echo "**** install runtime packages ****" && \
    apk add --no-cache \
    shadow && \
    echo "**** create runtime folder ****" && \
    mkdir -p /etc/ihatemoney &&\
    echo "**** install pip packages ****" && \
    pip install --no-cache-dir gunicorn pymysql && \
    pip install --no-cache-dir -e /src && \
    echo "**** create user abc:abc ****" && \
    useradd -u 1000 -U -d /src abc && \
    echo "**** cleanup ****" && \
    rm -rf \
    /tmp/*

VOLUME /database
EXPOSE ${PORT}
ENTRYPOINT ["/src/conf/entrypoint.sh"]
