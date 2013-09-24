from portal.log import get_logger

from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer

from portal.input.syslog import Parser, SyslogMessageHandler


_LOG = get_logger(__name__)


class TornadoConnection(object):

    def __init__(self, reader, stream, address):
        self.reader = reader
        self.stream = stream
        self.address = address

        # Set our callbacks
        self.stream.set_close_callback(self._on_close)
        self.stream.read_until_close(
            callback=self._on_stream,
            streaming_callback=self._on_stream)

    def _on_stream(self, data):
        try:
            self.reader.read(data)
        except Exception as ex:
            _LOG.exception(ex)

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


class SyslogServer(TornadoTcpServer):

    def __init__(self, address, msg_delegate, ssl_options=None):
        super(SyslogServer, self).__init__(address, ssl_options)
        self.msg_delegate = msg_delegate

    def handle_stream(self, stream, address):
        TornadoConnection(Parser(self.msg_delegate), stream, address)


def start_io():
    IOLoop.instance().start()


def stop_io():
    IOLoop.instance().stop()
