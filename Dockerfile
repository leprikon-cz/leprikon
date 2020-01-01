FROM ubuntu:bionic

LABEL name="Leprikón"
LABEL maintainer="Jakub Dorňák <jakub.dornak@misli.cz>"

ENV IPYTHONDIR=/app/data/ipython
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/
COPY patch /app/patch

# install requirements and generate czech locale
RUN apt-get update \
 && apt-get -y upgrade \
 && apt-get -y --no-install-recommends install \
    build-essential \
    gcc \
    git \
    libicu-dev \
    libmysqlclient-dev \
    libssl-dev \
    python3-dev \
    locales \
    libmysqlclient20 \
    libpython3.6 \
    mariadb-client \
    memcached \
    nginx \
    postgresql-client \
    python3-pip \
    python3-setuptools \
    sqlite3 \
    supervisor \
 && pip3 install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && rm requirements.txt \
 && patch /usr/local/lib/python3.6/dist-packages/cmsplugin_filer_folder/cms_plugins.py patch/cmsplugin_filer_folder-cms_plugins.patch \
 && rm -r patch \
 && apt-get -y purge \
    build-essential \
    gcc \
    git \
    libicu-dev \
    libmysqlclient-dev \
    libssl-dev \
    python3-dev \
 && apt-get -y autoremove \
 && apt-get -y clean \
 && ln -s /usr/bin/python3 /usr/local/bin/python \
 && echo cs_CZ.UTF-8 UTF-8 > /etc/locale.gen && locale-gen
ENV LC_ALL cs_CZ.UTF-8

# install leprikon
COPY . /src
RUN pip install --no-cache-dir --no-deps /src \
 && cp -a /src/translations/* /usr/local/lib/python3.6/dist-packages/ \
 && cp -a /src/conf /src/bin /src/startup ./ \
 && rm -r /src \
 && mkdir -p data/ipython htdocs/media htdocs/static run \
 && leprikon collectstatic --no-input \
 && rm data/db.sqlite3 \
 && chown www-data:www-data data htdocs/media run

VOLUME /app/data /app/htdocs/media

CMD ["/app/bin/run-supervisord"]
