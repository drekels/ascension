import logging


logging.getLogger(__name__).addHandler(logging.NullHandler())


VERSION = (0, 1, 1, 0)


def get_version():
    return ".".join([str(x) for x in VERSION])
