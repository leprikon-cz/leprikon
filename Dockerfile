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
RUN pip install --no-cache-dir uwsgi 'Django<1.11' ipython python-memcached

# install leprikon
COPY dist/leprikon.tar.gz /app/
RUN pip install --no-cache-dir /app/leprikon.tar.gz && rm /app/leprikon.tar.gz

# copy files
COPY manage.py run-nginx run-uwsgi /app/
COPY conf /app/conf
COPY var /app/var

# run this command at the end of any dockerfile based on this one
RUN ./manage.py collectstatic --link --no-input

# ensure that /app/var is writable
RUN chown www-data -R /app/var

CMD ["/usr/bin/supervisord", "-c", "/app/conf/supervisord.conf"]
