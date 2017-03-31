FROM python:2

MAINTAINER Jakub Dorňák <jakub.dornak@misli.com>
LABEL name=Leprikón

ENV PYTHONUNBUFFERED 1

# install and generate czech locale
RUN apt-get update && apt-get install locales -y && echo cs_CZ.UTF-8 UTF-8 > /etc/locale.gen && locale-gen

# install leprikon
RUN pip install --no-cache-dir uwsgi 'Django<1.10' ipython leprikon python-memcached

# install recommended set of cms plugins
RUN pip install --no-cache-dir cmsplugin-filer djangocms-column djangocms-link djangocms-style djangocms-snippet djangocms-googlemap djangocms-video

# install packages that will be required by future versions of leprikon
RUN pip install --no-cache-dir social-auth-app-django django-verified-email-field raven

ADD app/ /app/

RUN chown www-data -R /app/var

WORKDIR /app

CMD ./run
