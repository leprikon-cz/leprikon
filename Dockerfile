FROM python:2

MAINTAINER Jakub Dorňák <jakub.dornak@misli.com>
LABEL name=Leprikón

ENV PYTHONUNBUFFERED 1

# install and generate czech locale
RUN apt-get update && apt-get install locales -y && echo cs_CZ.UTF-8 UTF-8 > /etc/locale.gen && locale-gen

# install required packages
RUN pip install --no-cache-dir uwsgi 'Django<1.11' ipython python-memcached

# install leprikon
COPY . /src
RUN pip install --no-cache-dir -e /src

COPY manage.py run /app/
COPY var /app/var/
RUN chown www-data -R /app/var

WORKDIR /app

# run this command at the end of any dockerfile based on this one
RUN ./manage.py collectstatic --link --no-input

CMD ./run
