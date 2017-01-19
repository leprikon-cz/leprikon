Leprikón
==============

Leprikón je informační systém pro střediska volného času,
domy dětí a mládeže a podobné organizace.
[www.leprikon.cz](https://www.leprikon.cz/)

[![Build Status](https://travis-ci.org/leprikon-cz/leprikon.svg?branch=master)](https://travis-ci.org/leprikon-cz/leprikon)

Instalace
---------

Vytvoření a aktivace virtuálního prostředí:
```shell
virtualenv env
. env/bin/activate
```

Instalace Leprikónu včetně závislostí:
```shell
pip install https://github.com/leprikon-cz/leprikon/archive/master.zip
```

Vytvoření projektu:
```shell
django-admin startproject myddm --template=https://github.com/leprikon-cz/project_template/archive/master.zip
cd myddm
chmod +x manage.py
```

Inicializace databáze:
```shell
./manage.py migrate
```

Vytvoření uživatele:
```shell
./manage.py createsuperuser
```

Vytvoření uživatele:
```shell
./manage.py runserver
```

