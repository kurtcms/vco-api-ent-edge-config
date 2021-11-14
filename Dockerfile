# syntax=docker/dockerfile:1
FROM python:3.7

# Install cron
RUN apt-get update && apt-get -y install cron

# Change working directory to /app
WORKDIR /app

COPY requirements.txt ./
COPY vco_client.py vco_main.py ./
COPY vco-ent-edge-config.py ./
COPY .env ./
COPY crontab /etc/cron.d/crontab

RUN pip3 install -r requirements.txt
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab
