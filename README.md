Leprikón
========

Leprikón is web information system for leisure centres and other educational organizations.

[www.leprikon.cz](https://www.leprikon.cz/)


Installation with docker-compose
--------------------------------

```shell
# create and enter an empty directory of your choice
mkdir leprikon && cd leprikon

# download docker-compose configuration
wget https://raw.githubusercontent.com/leprikon-cz/leprikon/master/docker-compose.yml

# start the application containers
# (you need docker-compose installed and docker service running)
sudo docker-compose up -d

# fix the default charset of automaticaly created database
# (single long line)
sudo docker-compose exec leprikon bash -c "echo \"DROP DATABASE \$DATABASE_NAME; CREATE DATABASE \$DATABASE_NAME DEFAULT CHARACTER SET utf8 COLLATE utf8_czech_ci;\" | leprikon dbshell"

# create database schema
sudo docker-compose exec leprikon leprikon migrate

# create superuser account
sudo docker-compose exec leprikon leprikon createsuperuser

# open http://127.0.0.1:8000/admin/ in your favorite browser and login

# when finished stop the appliaction containers
sudo docker compose down
```
