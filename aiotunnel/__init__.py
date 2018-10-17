# BSD 3-Clause License
#
# Copyright (c) 2018, Andrea Giacomo Baldan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import json
import logging

__version__ = '1.1.0'

CONFIG = {
    'logpath': './',
    'logformat': '[%(asctime)s] %(name)s - %(message)s',
    'loglevel': 'WARNING',
    'verbose': False,
    'server': {
        'host': '127.0.0.1',
        'port': 8080,
        'certfile': None,
        'keyfile': None,
        'reverse': False
    },
    'client': {
        'host': '127.0.0.1',
        'port': 8888,
        'target_host': None,
        'target_port': None,
        'server_host': '127.0.0.1',
        'server_port': 8080
    }
}


def read_configuration(filepath):
    global CONFIG
    CONFIG = json.load(filepath)


def set_config_key(key, value):
    global CONFIG
    if isinstance(value, dict):
        CONFIG[key].update(value)
    else:
        CONFIG[key] = value


LOGLEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR
}


def setup_logging():
    DEFAULT_LOGPATH = os.getenv('LOGPATH', CONFIG['logpath'])
    DEFAULT_FORMAT = os.getenv('LOG_FORMAT', CONFIG['logformat'])
    LOGLEVEL = os.getenv('LOGLEVEL', CONFIG['loglevel'])
    # create module logger
    logger = logging.getLogger('aiotunnel')
    logger.setLevel(LOGLEVEL_MAP[LOGLEVEL])

    # create file handler which logs even debug messages
    fh = logging.FileHandler(os.path.join(DEFAULT_LOGPATH, 'aiotunnel.log'))
    fh.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(LOGLEVEL_MAP[LOGLEVEL])

    # create formatter and add it to the handlers
    formatter = logging.Formatter(DEFAULT_FORMAT)
    ch_formatter = logging.Formatter('[%(asctime)s] %(message)s')
    ch.setFormatter(ch_formatter)
    fh.setFormatter(formatter)

    # Add stream handler to the logger
    logger.addHandler(ch)
    logger.addHandler(fh)
