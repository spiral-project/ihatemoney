FROM python:3.6-alpine

RUN mkdir /ihatemoney &&\
    mkdir -p /etc/ihatemoney &&\
    pip install --no-cache-dir gunicorn pymysql

WORKDIR /ihatemoney
COPY . .
ARG INSTALL_FROM_PYPI="False"
RUN if [ "$INSTALL_FROM_PYPI" = True ]; then\
    pip install --no-cache-dir ihatemoney ; else\
    pip install --no-cache-dir -e . ; \
    fi

ENV DEBUG="False" \
    SQLALCHEMY_DATABASE_URI="sqlite:////database/ihatemoney.db" \
    SQLALCHEMY_TRACK_MODIFICATIONS="False" \
    SECRET_KEY="tralala" \
    MAIL_DEFAULT_SENDER="('Budget manager', 'budget@notmyidea.org')" \
    MAIL_SERVER="localhost" \
    MAIL_PORT=25 \
    MAIL_USE_TLS=False \
    MAIL_USE_SSL=False \
    MAIL_USERNAME=None \
    MAIL_PASSWORD=None \
    ACTIVATE_DEMO_PROJECT="True" \
    ADMIN_PASSWORD="" \
    ALLOW_PUBLIC_PROJECT_CREATION="True" \
    ACTIVATE_ADMIN_DASHBOARD="False"

VOLUME /database
EXPOSE 8000
ENTRYPOINT ["/ihatemoney/conf/confandrun.sh"]
