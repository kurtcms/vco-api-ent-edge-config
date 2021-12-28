# VMware VeloCloud SD-WAN Orchestrator API: Automated Edge Configuration Backup

This Python app is containerised with [Docker Compose](https://docs.docker.com/compose/) for a modular and cloud native deployment that fits in any microservice architecture.

It does the following:

1. Call the [VMware VeloCloud Orchestrator (VCO) API](#reference) to download a copy of the config stack for all of the SD-WAN Edges in the enterprise network;
2. Export the config stacks as separate JSON files on a `Docker volume` that is mounted in the same directory of the `docker-compose.yml` file on the Docker host, or in the same directory of the Python script if it is run as a standalone service, in a number of nested directories by the date and time of the API call; and
3. Repeat the process every 15 minutes on the hour and at :15, :30 and :45 past for an automated Edge config backup.

<img src="https://kurtcms.org/git/vco-api-ent-edge-config/vco-api-ent-edge-config-screenshot.png" width="550">

## Table of Content

- [Getting Started](#getting-started)
  - [Git Clone](#git-clone)
  - [Environment Variable](#environment-variables)
  - [Crontab](#crontab)
  - [Docker Container](#docker-container)
	  - [Docker Compose](#docker-compose)
	  - [Build and Run](#build-and-run)
  - [Standalone Python Script](#standalone-python-script)
    - [Dependencies](#dependencies)
    - [Cron](#cron)
- [Config Stack in JSON](#config-stack-in-json)
- [Reference](#reference)

## Getting Started

Get started in three simple steps:

1. [Download](#git-clone) a copy of the app;
2. Create the [environment variables](#environment-variables) for the VCO authentication and modify the [crontab](#crontab) if needed;
3. [Docker Compose](#docker-compose) or [build and run](#build-and-run) the image manually to start the app, or alternatively run the Python script as a standalone service.

### Git Clone

Download a copy of the app with `git clone`
```shell
$ git clone https://github.com/kurtcms/vco-api-ent-edge-config /app/
```

### Environment Variables


The app expects the hostname, the API token or the username and password for the VCO, as environment variables in a `.env` file in the same directory.

Should both the API token, and the username and password, for the VCO be present, the app will always use the API token.

Be sure to create the `.env` file.

```shell
$ nano /app/vco-api-ent-edge-config/.env
```

And define the credentials accordingly.

```
VCO_HOSTNAME = 'vco.managed-sdwan.com/'

# Either the API token
VCO_TOKEN = '(redacted)'

# Or the username and password
VCO_USERNAME = 'kurtcms@gmail.com'
VCO_PASSWORD = '(redacted)'
```

### Crontab

By default the app is scheduled with [cron](https://linux.die.net/man/8/cron) to pull a copy of the config stack for all the SD-WAN Edges in the enterprise network every 15 minutes, with `stdout` and `stderr` redirected to the main process for `Docker logs`.  

Modify the `crontab` if a different schedule is required.

```shell
$ nano /app/vco-api-ent-edge-config/crontab
```

### Docker Container

Packaged as a container, the app is a standalone, executable package that may be run on Docker Engine. Be sure to have [Docker](https://docs.docker.com/engine/install/) installed.

#### Docker Compose

With Docker Compose, the app may be provisioned with a single command. Be sure to have [Docker Compose](https://docs.docker.com/compose/install/) installed.

```shell
$ docker-compose up -d
```

Stopping the container is as simple as a single command.

```shell
$ docker-compose down
```

#### Build and Run

Otherwise the Docker image can also be built manually.

```shell
$ docker build -t vco_api_ent_edge_config /app/vco-api-ent-edge-config/
```

Run the image with Docker once it is ready.  

```shell
$ docker run -it --rm --name vco_api_ent_edge_config vco_api_ent_edge_config
```

### Standalone Python Script

Alternatively the `vco_api_ent_edge_config.py` script may be deployed as a standalone service.

#### Dependencies

In which case be sure to install the following required libraries for the `vco_api_main.py`:

1. [Requests](https://github.com/psf/requests)
2. [Python-dotenv](https://github.com/theskumar/python-dotenv)
3. [NumPy](https://github.com/numpy/numpy)
4. [pandas](https://github.com/pandas-dev/pandas)

```shell
$ pip3 install requests python-dotenv numpy pandas
```

#### Cron

The script may then be executed with a task scheduler such as [cron](https://linux.die.net/man/8/cron) that runs it once every 15 minutes for example.

```shell
$ (crontab -l; echo "*/15 * * * * /usr/bin/python3 /app/vco-api-ent-edge-config/vco_api_ent_edge_config.py") | crontab -
```

## Config Stack in JSON

The config stacks for all the Edges in the enterprise network will be downloaded and saved as separate JSON files on a `Docker volume` that is mounted in the same directory of the `docker-compose.yml` file on the Docker host. If the Python script is run as a standalone service, the JSON files will be in the same directory of the script instead.

In any case, the JSON files are stored under a directory by the enterpriseName, and nested in a number of subdirectories named respectively by the year, the month and the day, and finally by the full date and time of the API call to ease access.

```
.
└── enterpriseName/
    └── Year/
        └── Month/
            └── Date/
                └── YYYY-MM-DD-HH-MM-SS/
                    ├── edgeName1.json
                    ├── edgeName2.json
                    ├── edgeName3.json
                    └── edgeName4.json
```

## Reference

- [VMware SD-WAN Orchestrator API v1 Release 4.0.1](https://code.vmware.com/apis/1045/velocloud-sdwan-vco-api)
