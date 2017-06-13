Leprikón
========

Leprikón is web information system for leisure centres and other educational organizations.

`www.leprikon.cz <https://www.leprikon.cz/>`__

`Docker image <https://hub.docker.com/r/leprikon/leprikon/>`__


Installation with pip
---------------------

.. code:: shell

    # create and enter an empty directory of your choice
    mkdir leprikon && cd leprikon

    # create and activate virtual environment
    virtualenv env
    . env/bin/activate

    # install leprikon with all the requirements
    pip install leprikon

    # create database
    leprikon migrate

    # create admin user
    leprikon createsuperuser

    # run development server
    ./manage.py runserver
