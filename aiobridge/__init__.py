import os
import logging

DEFAULT_FORMAT = os.getenv('LOG_FORMAT', '%(name)s - %(message)s')

LOGLEVEL = os.getenv('LOGLEVEL', 'INFO')

LOGLEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR
}

# create module logger
logger = logging.getLogger('aiobridge')
logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
fh = logging.FileHandler('aiobridge.log')
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(LOGLEVEL_MAP[LOGLEVEL])

# create formatter and add it to the handlers
formatter = logging.Formatter(DEFAULT_FORMAT)
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# Add stream handler to the logger
logger.addHandler(ch)
logger.addHandler(fh)
