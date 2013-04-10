import socket
import signal
import weakref
import errno
import logging
import pyev
import json

from portal import PersistentProcess
from portal.env import get_logger
from portal.input.rfc5424 import SyslogParser, SyslogMessageHandler


_LOG = get_logger('portal.server')

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)
STOPSIGNALS = (signal.SIGINT, signal.SIGTERM)

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
#        if self.msg_count % 100000 == 0:
        message_dict = self.msg_head.as_dict()
        message_dict['message'] = (self.msg + last_message_part).decode('utf-8')
        _LOG.debug('Message: {}'.format(json.dumps(message_dict)))
        self.msg_head = None
        self.msg = b''


class SocketINetAddress(object):

    def __init__(self, address, port):
        self.address = address
        self.port = port

    def repr(self):
        return '{}:{}'.format(self.address, self.port)


class Connection(object):

    def __init__(self, loop, reader, sock, address):
        self.reader = reader
        self.address = address
        self.sock = sock
        self.watcher = pyev.Io(self.sock, pyev.EV_READ, loop, self.on_io)
        self.watcher.start()

    def start(self, loop):
        self.watcher = pyev.Io(self.sock, pyev.EV_READ, loop, self.on_io)

    def set_interest(self, events):
        self.watcher.stop()
        self.watcher.set(self.sock, events)
        self.watcher.start()

    def on_io(self, watcher, revents):
        if revents & pyev.EV_READ:
            try:
                buffered_read = self.sock.recv(1024)
                if buffered_read:
                    self.reader.read(buffered_read)
                else:
                    self.close()
                    _LOG.info('Connection closed by peer {}'.format(
                        self.address))
            except socket.error as err:
                if err.args[0] not in NONBLOCKING:
                    self.close()
                    _LOG.error("Error reading from {}".format(self.address))

    def close(self):
        self.sock.close()
        self.watcher.stop()
        self.watcher = None
        _LOG.debug("{0}: closed".format(self))


class Server(object):

    def __init__(self, address):
        self.loop = pyev.default_loop()
        self.conns = weakref.WeakValueDictionary()
        self.watchers = list()
        self.address = address
        self._build_sock(address)

    def _build_sock(self, address):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(address)
        self.sock.setblocking(0)
        self.watchers.append(
            pyev.Io(self.sock, pyev.EV_READ, self.loop, self.on_read))

    def start(self):
        # Open the socket for accepting connections
        self.sock.listen(socket.SOMAXCONN)
        _LOG.debug("{0}: started on {0.address}".format(self))
        # Register for unix signals for stopping
        for signal in STOPSIGNALS:
            self.watchers.append(
                pyev.Signal(signal, self.loop, self.on_stop_signal))
        # Start all watchers
        for watcher in self.watchers:
            watcher.start()
        # Kickoff libev - Note, this takes over process flow
        self.loop.start()

    def stop(self):
        # Halt libev
        self.loop.stop(pyev.EVBREAK_ALL)
        # Close the server socket
        self.sock.close()
        # Kill libev watchers
        while self.watchers:
            self.watchers.pop().stop()
        # Close lingering connections
        for conn in self.conns.values():
            conn.close()
        _LOG.debug("{0}: stopped on {0.address}".format(self))

    def on_stop_signal(self, watcher, revents):
        _LOG.info('Signaled to stop...')
        self.stop()

    def on_read(self, watcher, revents):
        while True:
            try:
                sock, address = self.sock.accept()
                sock.setblocking(0)
                self.conns[address] = Connection(self.loop, self.new_reader(), sock, address)
                _LOG.debug('Accepted connection from: {}'.format(address))
            except socket.error as err:
                if err.args[0] not in NONBLOCKING:
                    _LOG.exception(err)
                    self.stop()
                break

    def new_reader(self):
        raise NotImplementedError()


class SyslogServer(Server):

    def __init__(self, address):
        super(SyslogServer, self).__init__(address)

    def new_reader(self):
        return SyslogParser(MessageHandler())


if __name__ == "__main__":
    server = SyslogServer(("127.0.0.1", 5140))
    server.start()
