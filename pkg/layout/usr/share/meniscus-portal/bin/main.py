import signal

import portal.config as config

from portal.log import get_logger, get_log_manager
from portal.server import SyslogServer, start_io, stop_io
from portal.transport import SyslogToZeroMQHandler, ZeroMQCaster


def stop(signum, frame):
    _LOG.debug('Stop called at frame:\n{}'.format(frame))
    stop_io()


config = config.load_config()

logging_manager = get_log_manager()
logging_manager.configure(config)

_LOG = get_logger(__name__)


if __name__ == '__main__':
    # Set up the zmq message caster
    caster = ZeroMQCaster(config.core.zmq_bind_host)

    ssl_options = None

    cert_file = config.ssl.cert_file
    key_file = config.ssl.key_file

    if None not in (cert_file, key_file):
        ssl_options = dict()
        ssl_options['certfile'] = cert_file
        ssl_options['keyfile'] = key_file

        _LOG.debug('SSL enabled: {}'.format(ssl_options))

    # Set up the syslog server
    syslog_server = SyslogServer(
        config.core.syslog_bind_host,
        SyslogToZeroMQHandler(caster),
        ssl_options)
    syslog_server.start()

    # Take over SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    # Start I/O
    start_io()

