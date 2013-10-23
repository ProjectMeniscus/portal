import signal
import simplejson as json

import portal.config as config

from portal.log import get_logger, get_log_manager
from portal.server import SyslogServer, start_io, stop_io
from portal.input.syslog import SyslogMessageHandler


_LOG = get_logger(__name__)


def stop(signum, frame):
    _LOG.debug('Stop called at frame:\n{}'.format(frame))
    stop_io()


class MessageHandler(SyslogMessageHandler):

    def __init__(self):
        self.msg = bytearray()
        self.msg_head = None
        self.msg_count = 0

    def on_msg_head(self, message_head):
        self.msg_count += 1
        self.msg_head = message_head

    def on_msg_part(self, message_part):
        self.msg.extend(message_part)

    def on_msg_complete(self, message_length):
        message_dict = self.msg_head.as_dict()
        message_dict['message_length'] = str(message_length)
        message_dict['message'] = str(self.msg)
        _LOG.debug('Message: {}'.format(json.dumps(message_dict)))
        self.msg_head = None
        del self.msg[:]


if __name__ == '__main__':
    try:
        config = config.load_config()

        logging_manager = get_log_manager()
        logging_manager.configure(config)

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
            MessageHandler(),
            ssl_options)
        syslog_server.start()

        # Take over SIGTERM and SIGINT
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        # Start I/O
        start_io()
    except Exception as ex:
        _LOG.exception(ex)

