Aiotunnel
=========

Yet another HTTP tunnel, supports two modes; a direct one which open a local port on the host
machine and redirect all TCP data to the remote side of the tunnel, which actually connect to the
desired URL. A second one which require the client part to be run on the target system we want to
expose, the server side on a (arguably) public machine (e.g. an AWS EC2) which expose a port to
communicate to our target system through HTTP.
