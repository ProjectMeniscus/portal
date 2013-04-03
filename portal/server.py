import socket
import signal
import weakref
import errno
import logging
import pyev
import json

from portal.env import get_logger
from portal.input.rfc5424 import SyslogParser, SyslogMessageHandler

_LOG = get_logger('portal.server')

STOPSIGNALS = (signal.SIGINT, signal.SIGTERM)
NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)


class MessageHandler(SyslogMessageHandler):

    def __init__(self):
        self.msg_count = 0

    def on_message_head(self, message_head):
        self.msg_count += 1
        if self.msg_count % 100000 == 0:
            _LOG.debug('Messages processed: {}'.format(self.msg_count))

    def on_message_part(self, message_part):
        pass


class Connection(object):

    def __init__(self, sock, address, loop):
        self.parser = SyslogParser(MessageHandler())
        self.sock = sock
        self.address = address
        self.sock.setblocking(0)
        self.watcher = pyev.Io(self.sock, pyev.EV_READ, loop, self.io_cb)
        self.watcher.start()
        _LOG.debug("{0}: ready".format(self))

    def reset(self, events):
        self.watcher.stop()
        self.watcher.set(self.sock, events)
        self.watcher.start()

    def handle_error(self, msg, level=logging.ERROR, exc_info=True):
        _LOG.log(level, "{0}: {1} --> closing".format(self, msg),
                    exc_info=exc_info)
        self.close()

    def handle_read(self):
        try:
            buf = self.sock.recv(1024)
        except socket.error as err:
            if err.args[0] not in NONBLOCKING:
                self.handle_error("error reading from {0}".format(self.sock))

        if buf:
            self.parser.read(buf)
        else:
            self.handle_error("connection closed by peer", logging.DEBUG, False)

    def io_cb(self, watcher, revents):
        if revents & pyev.EV_READ:
            self.handle_read()

    def close(self):
        self.sock.close()
        self.watcher.stop()
        self.watcher = None
        _LOG.debug("{0}: closed".format(self))


class Server(object):

    def __init__(self, address):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(address)
        self.sock.setblocking(0)
        self.address = self.sock.getsockname()
        self.loop = pyev.default_loop()
        self.watchers = [pyev.Signal(sig, self.loop, self.signal_cb)
                         for sig in STOPSIGNALS]
        self.watchers.append(pyev.Io(self.sock, pyev.EV_READ, self.loop,
                                     self.io_cb))
        self.conns = weakref.WeakValueDictionary()

    def handle_error(self, msg, level=logging.ERROR, exc_info=True):
        _LOG.log(level, "{0}: {1} --> stopping".format(self, msg),
                    exc_info=exc_info)
        self.stop()

    def signal_cb(self, watcher, revents):
        self.stop()

    def io_cb(self, watcher, revents):
        try:
            while True:
                try:
                    sock, address = self.sock.accept()
                    _LOG.debug('Accepted connection from: {}'.format(address))
                except socket.error as err:
                    if err.args[0] in NONBLOCKING:
                        break
                    else:
                        raise
                else:
                    self.conns[address] = Connection(sock, address, self.loop)
        except Exception:
            self.handle_error("error accepting a connection")

    def start(self):
        self.sock.listen(socket.SOMAXCONN)
        for watcher in self.watchers:
            watcher.start()
        _LOG.debug("{0}: started on {0.address}".format(self))
        self.loop.start()

    def stop(self):
        self.loop.stop(pyev.EVBREAK_ALL)
        self.sock.close()
        while self.watchers:
            self.watchers.pop().stop()
        for conn in self.conns.values():
            conn.close()
        _LOG.debug("{0}: stopped".format(self))


if __name__ == "__main__":
    server = Server(("127.0.0.1", 5140))
    server.start()
