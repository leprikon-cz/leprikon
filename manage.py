#!/bin/bash

if ! which leprikon &> /dev/null; then
    if ! test -e env/bin/activate; then
        virtualenv env
    fi
    . env/bin/activate
    if ! which leprikon &> /dev/null; then
        pip install -r requirements.txt
    fi
fi

if [ -n "$1" ]; then
    export DEBUG="${DEBUG:-TEMPLATE}"
else
    # bash-completion
    export DEBUG=""
fi

export PYTHONPATH=.
#export SITE_MODULE=leprikon

exec leprikon "$@"
