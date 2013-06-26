from .env import get_logger

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.tcpserver import TCPServer

from portal.input.usyslog import Parser, SyslogMessageHandler
from portal.input.jsonep import JsonEventParser
from portal.input.jsonstream import JsonMessageAssembler


_LOG = get_logger(__name__)


class TornadoConnection(object):

    def __init__(self, reader, stream, address):
        self.reader = reader
        self.stream = stream
        self.address = address

        # Set our callbacks
        self.stream.set_close_callback(self._on_close)
        self.stream.read_until_close(
            callback=self._on_read,
            streaming_callback=self._on_stream)

    def _on_stream(self, data):
        self.reader.read(data)

    def _on_read(self, data):
        pass

    def _on_close(self):
        pass


class TornadoTcpServer(TCPServer):

    def __init__(self, address, ssl_options=None):
        super(TornadoTcpServer, self).__init__(ssl_options=ssl_options)
        self.address = address

    def start(self):
        self.bind(self.address[1], self.address[0])
        super(TornadoTcpServer, self).start()
        _LOG.info('TCP server ready!')


class JsonStreamServer(TornadoTcpServer):

    def __init__(self, address, msg_delegate, ssl_options=None):
        super(JsonStreamServer, self).__init__(address, ssl_options)
        self.msg_delegate = msg_delegate

    def handle_stream(self, stream, address):
        reader = JsonEventParser(JsonMessageAssembler(self.msg_delegate))
        TornadoConnection(reader, stream, address)


class SyslogServer(TornadoTcpServer):

    def __init__(self, address, msg_delegate, ssl_options=None):
        super(SyslogServer, self).__init__(address, ssl_options)
        self.msg_delegate = msg_delegate

    def handle_stream(self, stream, address):
        TornadoConnection(Parser(self.msg_delegate), stream, address)


def start_io():
    IOLoop.instance().start()
