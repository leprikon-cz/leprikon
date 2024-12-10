#!/bin/bash

set -e

poetry update && poetry export -f requirements.txt > requirements.txt

read -p "Commit changes? (yes) " COMMIT

if [ "$COMMIT" = "" ] || [ "$COMMIT" = "yes" ]; then
    git add poetry.lock requirements.txt
    git commit -m "Update requirements"
fi
