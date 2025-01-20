#!/usr/bin/python3 -u

import sys, os, getopt, select, time, logging, re
from prometheus_client import start_http_server, Counter, disable_created_metrics

PORT = 9112
EVENT_LOOP_SLEEP = 0.002
DEFAULT_FIFO_PATH = '/run/prometheus-client-apache-sites.stdin'

request_counter = Counter('apache_sites_requests', 'Number of requests processed', ['namespace', 'host', 'status_code'])
bytes_received_counter = Counter('apache_sites_bytes_received', 'Bytes received', ['namespace', 'host'])
bytes_sent_counter = Counter('apache_sites_bytes_sent', 'Bytes sent', ['namespace', 'host'])

def usage():
    print('Usage: ' + sys.argv[0] + ' [options]')
    print('')
    print('  -s, --service                Run the client as a (web) service.')
    print('  -f, --fifo PATH              FIFO socket path (defaults to /run/prometheus-client-apache-sites.stdin).')

def run_service(fifo_path):
    print("Starting service..")

    if not os.path.exists(fifo_path):
        raise Exception('Socket path does not exist: %s' % (fifo_path))

    # Expose prometheus metrics endpoint
    print("Starting server on port %d" % (PORT))
    disable_created_metrics()
    start_http_server(PORT)

    fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)

    # More info on performance: https://www.geeksforgeeks.org/python-os-mkfifo-method/
    with open(fd, 'r', buffering=1) as fifo:
        # Handle FIFO input
        print("Waiting for FIFO data..")

        while True:
            select.select([fifo], [], [fifo])
            process_log(fifo.readline().strip())
            time.sleep(EVENT_LOOP_SLEEP)

def process_log(input):
    sanitized_input = input.strip()

    # Do not handle empty input
    if sanitized_input == '':
        return

    regex = r'^(?P<namespace>.+) \| (?P<host>.+) \| "[A-Z]+ (?P<path>.+) (?P<protocol>HTTP\/\d\.\d)" (?P<status>\d{3}) (?P<bytes_received>\d+) (?P<bytes_sent>\d+)$'

    for line in sanitized_input.splitlines():
        regex_match = re.match(regex, line)

        if regex_match:
            values = regex_match.groupdict()
            status_code = values['status'][0:1] + 'xx'

            request_counter.labels(namespace=values['namespace'], host=values['host'], status_code=status_code).inc()
            bytes_received_counter.labels(namespace=values['namespace'], host=values['host']).inc(int(values['bytes_received']))
            bytes_sent_counter.labels(namespace=values['namespace'], host=values['host']).inc(int(values['bytes_sent']))


try:
    # Define the options and get them.
    options = getopt.getopt(sys.argv[1:], 'f:sph', ['fifo', 'service', 'help'])
    options = dict(options[0])

    action = ''
    fifo_path = DEFAULT_FIFO_PATH

    if '-f' in options:
        fifo_path = options['-f']
    if '--fifo' in options:
        fifo_path = options['--fifo']
    if '-s' in options or '--service' in options:
        action = 'service'
    if '-h' in options or '--help' in options:
        usage()
        sys.exit(0)

    if action == '':
        raise Exception('Please supply an action (--service).')

    if action == 'service':
        run_service(fifo_path)

except KeyboardInterrupt:
    sys.stdout.flush()
    pass

except Exception as e:
    sys.stderr.write(str(e) + '\n')
    sys.exit(1)