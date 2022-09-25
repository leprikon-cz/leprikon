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

# if your instance is exposed to the internet and dns record pointed to your IP you can uncomment line LEPRIKON_DOMAIN and change to your desired domain.
# then Lets Encrypt certificate will be automatically generated for your domain
# if you want to use reverse proxy or only for testing then leave as is

# start the application containers
# (you need docker-compose installed and docker service running)
sudo docker-compose up -d

# optionally see the logs (press CTRL+c to stop)
sudo docker-compose logs -f leprikon

# once the initial migration is finished (may take few minutes),
# you should be able to open http://127.0.0.1:8000/ in your favorite browser.

# when finished stop the appliaction containers
sudo docker-compose down
```
