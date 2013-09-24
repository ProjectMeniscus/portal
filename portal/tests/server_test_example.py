import simplejson as json

from multiprocessing import Process

from portal.log import get_logger
from portal.server import start_io, SyslogServer
from portal.input.syslog import SyslogMessageHandler


_LOG = get_logger('portal.tests.server_test')


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

    def on_msg_complete(self):
        message_dict = self.msg_head.as_dict()
        message_dict['message'] = str(self.msg)
        _LOG.debug('Message: {}'.format(json.dumps(message_dict)))
        self.msg_head = None
        del self.msg[:]


if __name__ == "__main__":
    syslog_server = SyslogServer(("127.0.0.1", 5140), MessageHandler())
    syslog_server.start()
    start_io()
