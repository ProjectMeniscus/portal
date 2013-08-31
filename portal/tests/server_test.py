import simplejson as json

from multiprocessing import Process

from portal.env import get_logger
from portal.server import start_io, SyslogServer, JsonStreamServer
from portal.input.syslog import SyslogMessageHandler
from portal.input.jsonstream import JsonMessageHandler


_LOG = get_logger('portal.tests.server_test')


class JsonHandler(JsonMessageHandler):

    def __init__(self):
        self.msg_count = 0

    def header(self, key, value):
        #_LOG.debug('Header: {} = {}'.format(key, value))
        pass

    def body(self, body):
        #_LOG.debug('Message body: {}'.format(body))
        self.msg_count += 1
        if self.msg_count % 10000 == 0:
            _LOG.debug('Processed {} messages.'.format(self.msg_count))


class MessageHandler(SyslogMessageHandler):

    def __init__(self):
        self.msg = b''
        self.msg_head = None
        self.msg_count = 0

    def message_head(self, message_head):
        self.msg_count += 1
        self.msg_head = message_head

    def message_part(self, message_part):
        self.msg += message_part

    def message_complete(self, last_message_part):
        message_dict = self.msg_head.as_dict()
        message_dict['message'] = (
            self.msg + last_message_part).decode('utf-8')
        _LOG.debug('Message: {}'.format(json.dumps(message_dict)))
        self.msg_head = None
        self.msg = b''


if __name__ == "__main__":
    syslog_server = SyslogServer(("127.0.0.1", 5140), MessageHandler())
    json_server = JsonStreamServer(("127.0.0.1", 9001), JsonHandler())
    syslog_server.start()
    json_server.start()
    start_io()
