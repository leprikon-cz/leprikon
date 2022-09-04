########
# base #
########

FROM ubuntu:22.04 AS base

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV IPYTHONDIR=/app/data/ipython
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED 1
ENV TZ=Europe/Prague

# install requirements and generate czech locale
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get -y --no-install-recommends install \
  libmysqlclient21 \
  libpython3.10 \
  locales \
  mariadb-client \
  nginx \
  patch \
  postgresql-client \
  python3-pip \
  sqlite3 \
  supervisor \
  tzdata \
  && pip3 install --no-cache-dir --upgrade pip \
  && ln -s /usr/bin/python3 /usr/local/bin/python \
  && echo cs_CZ.UTF-8 UTF-8 > /etc/locale.gen && locale-gen
ENV LC_ALL cs_CZ.UTF-8


#########
# build #
#########

FROM base AS build

RUN apt-get -y --no-install-recommends install \
  build-essential \
  gcc \
  git \
  libicu-dev \
  libmysqlclient-dev \
  libssl-dev \
  pkg-config \
  python3-dev
RUN pip install poetry wheel
COPY poetry.lock pyproject.toml ./
RUN poetry export -o requirements.txt --without-hashes \
  && pip wheel --wheel-dir=/app/dist -r requirements.txt
COPY README.rst /app/README.rst
COPY leprikon /app/leprikon
RUN poetry build --format wheel


#########
# final #
#########

FROM base AS final

LABEL name="Leprikón"
LABEL maintainer="Jakub Dorňák <jakub.dornak@misli.cz>"

COPY --from=build /app/dist /app/dist

RUN pip install --no-deps /app/dist/*

COPY bin /app/bin
COPY conf /app/conf
COPY patch /app/patch
COPY startup /app/startup
COPY translations /app/translations

RUN cp -a /app/translations/* /usr/local/lib/python3.10/dist-packages/ \
  && patch /usr/local/lib/python3.10/dist-packages/cmsplugin_filer_folder/cms_plugins.py patch/cmsplugin_filer_folder-cms_plugins.patch \
  && mkdir -p data/ipython htdocs/media htdocs/static run \
  && leprikon collectstatic --no-input \
  && rm data/db.sqlite3 \
  && chown www-data:www-data data htdocs/media run

VOLUME /app/data /app/htdocs/media

CMD ["/app/bin/run-supervisord"]
