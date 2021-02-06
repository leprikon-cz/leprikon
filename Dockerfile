########
# base #
########

FROM ubuntu:focal AS base

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
    locales \
    python3-pip \
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
    python3-dev \
    libpython3.7
RUN pip install poetry wheel
COPY poetry.lock pyproject.toml ./
RUN poetry export -f requirements.txt --without-hashes \
  | pip wheel --wheel-dir=/app/dist -r /dev/stdin
COPY README.rst /app/README.rst
COPY leprikon /app/leprikon
RUN poetry build --format wheel


#########
# final #
#########

FROM base AS final

LABEL name="Leprikón"
LABEL maintainer="Jakub Dorňák <jakub.dornak@misli.cz>"

RUN apt-get -y --no-install-recommends install \
    libmysqlclient21 \
    libpython3.8 \
    mariadb-client \
    nginx \
    postgresql-client \
    sqlite3 \
    supervisor

COPY --from=build /app/dist /app/dist

RUN pip install --no-deps /app/dist/*

COPY . /src

RUN cp -a /src/translations/* /usr/local/lib/python3.8/dist-packages/ \
 && cp -a /src/conf /src/bin /src/startup ./ \
 && rm -r /src \
 && mkdir -p data/ipython htdocs/media htdocs/static run \
 && leprikon collectstatic --no-input \
 && rm data/db.sqlite3 \
 && chown www-data:www-data data htdocs/media run

VOLUME /app/data /app/htdocs/media

CMD ["/app/bin/run-supervisord"]
