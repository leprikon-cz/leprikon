FROM python:2

MAINTAINER Jakub Dorňák <jakub.dornak@misli.com>
LABEL name=Leprikón

ENV PYTHONUNBUFFERED 1

WORKDIR /app

# install requirements and generate czech locale
RUN curl https://nginx.org/keys/nginx_signing.key | apt-key add - \
 && echo deb http://nginx.org/packages/debian/ jessie nginx > /etc/apt/sources.list.d/nginx.list \
 && apt-get update \
 && apt-get -y upgrade \
 && apt-get -y install locales supervisor nginx memcached sqlite3 mysql-client postgresql-client \
 && apt-get -y autoremove \
 && apt-get -y clean \
 && echo cs_CZ.UTF-8 UTF-8 > /etc/locale.gen && locale-gen

# install required packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt

# install leprikon
COPY . /src
RUN pip install --no-cache-dir /src \
 && cp -a /src/conf /src/bin/run-nginx /src/bin/run-uwsgi ./ \
 && rm -r /src \
 && mkdir -p data htdocs/media htdocs/static run \
 && leprikon collectstatic --no-input \
 && chown www-data -R data htdocs/media run

CMD ["/usr/bin/supervisord", "-c", "/app/conf/supervisord.conf"]
