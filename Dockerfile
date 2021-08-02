# syntax=docker/dockerfile:1
FROM python:3.7

# Install cron
RUN apt-get update && apt-get -y install cron

# Create a Docker volume to store the Python script outputs on
# the Docker host under /var/lib/docker/volumes/<volume-name>/_data
# Run the 'docker volume prune' command to delete all unused volumes
VOLUME /app
WORKDIR /app

COPY requirements.txt requirements.txt
COPY client.py client.py
COPY vco-ent-edge-config.py vco-ent-edge-config.py
COPY .env .env
COPY crontab /etc/cron.d/crontab

RUN pip3 install -r requirements.txt
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

# Cron in foreground as the entry point for the container
ENTRYPOINT cron -f
