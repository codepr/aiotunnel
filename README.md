Aiotunnel
=========

[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)

Yet another HTTP tunnel, supports two modes; a direct one which open a local port on the host
machine and redirect all TCP data to the remote side of the tunnel, which actually connect to the
desired URL. A second one which require the client part to be run on the target system we want to
expose, the server side on a (arguably) public machine (e.g. an AWS EC2) which expose a port to
communicate to our target system through HTTP.


## Quickstart

Let's suppose we have a machine located at `10.5.0.240` that we want to expose SSH access and a
server on which we have free access located at `10.5.0.10`; we really don't know if port 22 on
`10.5.0.240` is already exposed or if the IP address will change, we actually don't care because
once set the server address, it will retrieve all incoming commands via HTTP GET requests to the our
known server.

So just run the `tunneld` on the server at `10.5.0.10` (you probably'll want to daemonize it through
NOHUP or by creating a systemd service) in reverse mode:

```sh
doe@10.5.0.10:~$ python aiotunnel.py server -r
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

On the target machine at `10.5.0.240` run the client bound to the service we want to expose (SSH in
this case but could be anything):

```sh
doe@10.5.0.240:~$ python aiotunnel.py client --server-addr 10.5.0.10 --server-port 8080 -A localhost -p 22 -r
[2018-10-14 22:20:45,806] Opening a connection with 127.0.0.1:22 and 0.0.0.0:8888 over HTTP
[2018-10-14 22:20:45,831] 0.0.0.0:8888 over HTTP to http://10.5.0.10:8080/aiotunnel
[2018-10-14 22:20:45,832] Obtained a client id: aeb7cfc6-3de3-4bc1-b769-b81641d496eb
```

Now we're ready to open an SSH session to `10.5.0.10` even in the case of a closed 22 port or a
different IP address.

```sh
doe@10.5.0.15:~$ ssh doe@10.5.0.10 -p 8888

Welcome to Linux 4.19.0-1-MANJARO
Last login: Thu Feb 11 17:28:20 2016
doe@10.5.0.240:~$
```

A more common approach is to use the tunnel without `-r`/`--reverse` flag. In this case we actually
have the port 22 exposed on the target system, but our network do not permit traffic over SSH. In
this case we use a known server as a proxy to demand the actual SSH connection to him, while we
communicate with him by using HTTP requests:

- `POST` to establish the connection
- `PUT` to send data
- `GET` to read responses
- `DELETE` to close the connection

So on our known server located at `10.5.0.10` we start a `tunneld` process

```sh
doe@10.5.0.10:~$ python aiotunnel.py server
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

On the network-constrainted machine we start a `tunnel` instance

```sh
doe@10.5.0.5:~$ python aiotunnel.py -A 10.0.5.240 -P 22
[2018-10-15 00:58:41,744] Opening local port 8888 and 10.0.5.240:22 over HTTP
```
And we're good to go.

It's possible to use the `Dockerfile` to build an image and run it in a container, default start
with a command `python aiotunnel.py server -r`, easily overridable.

```sh
doe@10.5.0.240:~$ docker build -t aiotunnel /path/to/aiotunnel
doe@10.5.0.240:~$ docker run --rm --network host aiotunnel python aiotunnel.py client --server-addr 10.5.0.10 --server-port 8080 -A localhost -p 22 -r
```

## Installation

Clone the repository and install it locally or play with it using `python -i` or `ipython`.

```
$ git clone https://github.com/codepr/aiotunnel.git
$ cd aiotunnel
$ pip install .
```

or, to skip cloning part

```
$ pip install git+https://github.com/codepr/aiotunnel.git@master#egg=aiotunnel
```

## Changelog

See the [CHANGES](CHANGES.md) file.
