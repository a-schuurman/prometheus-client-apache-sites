# Prometheus Client for Apache Sites
A simple light-weight solution to keep track of Apache request throughput, bandwidth and response statuses on a
site/domain level. 

## Why create another Prometheus client for Apache?
Yet another prometheus client for gathering statistics of Apache2, what is so different? The goal was simple for me, I
needed a way to gather basic statistics of sites running through Apache without a lot of many (infra) dependencies,
having little/none disk activity and the ability to have realtime statistics.

The answer? Write Apache logs to a named pipe (FIFO), have a service actively reading/parsing these logs and update
in-memory metrics exposed on `/metrics` endpoint.

## Features
Such a simple solution has little features, but is powerful in its simplicity:

### Prometheus Counters
- Bytes sent
- Bytes received
- Requests

### Prometheus Labels
- Namespace (a custom way to group sites/domains)
- Request host
- Status code (Only for request metrics)

## How to install
_Note: This guide is created for Debian, sorry for all other distro users!_

### Copy handler

```sh
mkdir -p /opt/prometheus-client-apache-sites/
```

Put the copy the `handler.py` within the folder `/opt/prometheus-client-apache-sites/` and set the permissions:

```sh
chmod +x /opt/prometheus-client-apache-sites/handler.py
```

### Install pip dependencies
```sh
pip install prometheus-client
```

### Install Systemd service
Copy the files in the systemd folder of this repository into `/lib/systemd/system` and let systemd refresh its
configuration by running:

```sh
systemctl daemon-reload
```

### Now start the service:
```shell
systemctl start prometheus-client-apache-sites
```

### Configure virtual hosts

First of all, let's understand the logging format used by this solution:

**Format:**
```
<namespace> | <host> | "<method> <path> <protocol>" <status_code> <bytes_received> <bytes_sent>
```

**Example:**
```
mydomain.com | sub.mydomain.com | "GET / HTTP/1.1" 200 153 7621
```

To make sure logs are picked up and handled by the Prometheus client, simply write the logs to the named pipe by adding
the following Apache configuration file to your desired virtual hosts:

```
LogFormat "%v | %{Host}i | \"%r\" %>s %I %O" prometheus
CustomLog "/run/prometheus-client-apache-sites.stdin" prometheus
```

### Connect to Prometheus
Now it's for the nice part, add this service as target to your Prometheus server. By default, this service runs on port
`9112`. Make sure to add some firewall rules to protect it from the outside world ;-)

### Known issues/caveats
- Make sure the Systemd service is running and keeps reading, otherwise Apache logs a lot of errors on the SIGPIPE for named pipe.