########
# base #
########

FROM ubuntu:24.04 AS base

WORKDIR /app

ENV BASE_DIR=/app
ENV DEBIAN_FRONTEND=noninteractive
ENV IPYTHONDIR=/app/data/ipython
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED 1
ENV TZ=Europe/Prague

# install requirements and generate czech locale
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get -y --no-install-recommends install \
  git \
  libicu74 \
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
  libicu-dev \
  libmysqlclient-dev \
  libssl-dev \
  pkg-config \
  python3-dev
RUN pip install --break-system-packages poetry wheel
RUN virtualenv /venv
ENV VIRTUAL_ENV=/venv
COPY requirements.txt ./
RUN /venv/bin/pip install -r requirements.txt
# TODO: remove following line
RUN /venv/bin/pip install git+https://github.com/leprikon-cz/cmsplugin-filer.git@leprikon
COPY poetry.lock pyproject.toml ./
RUN poetry install --only main --no-root
COPY README.rst /app/README.rst
COPY leprikon /app/leprikon
RUN poetry install --only-root


#########
# final #
#########

FROM base AS final

LABEL name="Leprikón"
LABEL maintainer="Jakub Dorňák <jakub.dornak@misli.cz>"

COPY --from=build /venv /venv
COPY --from=build /app/leprikon /app/leprikon
ENV VIRTUAL_ENV=/venv
ENV PATH=/venv/bin:$PATH

COPY bin /app/bin
COPY conf /app/conf
COPY startup /app/startup
COPY translations /app/translations

RUN cp -a /app/translations/* /venv/lib/python3.12/site-packages/ \
  && mkdir -p data/ipython htdocs/media htdocs/static run \
  && leprikon collectstatic --no-input \
  && rm data/db.sqlite3 \
  && chown www-data:www-data data htdocs/media run

VOLUME /app/data /app/htdocs/media

CMD ["/app/bin/run-supervisord"]
