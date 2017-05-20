FROM python:2

MAINTAINER Jakub Dorňák <jakub.dornak@misli.com>
LABEL name=Leprikón

ENV PYTHONUNBUFFERED 1

WORKDIR /app

# install requirements and generate czech locale
RUN apt-get update \
 && apt-get -y upgrade \
 && apt-get -y install locales supervisor nginx memcached \
 && apt-get -y autoremove \
 && apt-get -y clean \
 && echo cs_CZ.UTF-8 UTF-8 > /etc/locale.gen && locale-gen

# install required packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir uwsgi -r requirements.txt \
 && rm requirements.txt

# install leprikon
COPY . /src
RUN pip install --no-cache-dir /src \
 && cp -a /src/conf /src/manage.py /src/run-nginx /src/run-uwsgi ./ \
 && rm -r /src \
 && mkdir -p var/data var/htdocs/media var/htdocs/static var/run \
 && ./manage.py collectstatic --link --no-input \
 && chown www-data -R var

CMD ["/usr/bin/supervisord", "-c", "/app/conf/supervisord.conf"]
