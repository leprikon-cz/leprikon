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

# optionally see the logs (press CTRL+c to stop)
sudo docker-compose logs -f leprikon

# once the initial migration is finished (may take few minutes),
# you should be able to open http://127.0.0.1:8000/ in your favorite browser.

# when finished stop the appliaction containers
sudo docker-compose down
```

Update requirements
-------------------

Since `pyproject.toml` is changed with each release bump, docker build cache gets
invalidated and requirements would be downloaded and installed even if the actual
requirements remain unchanged. To address this we use `requirements.txt`, which
only changes when requirements are updated. Use following command to regenerate
`requirements.txt` whenever poetry requirements are updated:

```shell
poetry export -f requirements.txt --output requirements.txt
```
