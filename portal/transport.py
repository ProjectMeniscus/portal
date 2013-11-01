"""
The transport module defines the classes that serve as the transport layer for
Portal when sending parsed syslog messages downstream.
"""

import simplejson as json
import zmq

from portal.log import get_logger
from portal.input.syslog import SyslogMessageHandler


_LOG = get_logger(__name__)


class ZeroMQCaster(object):
    """
    ZeroMQCaster allows for messages to be sent downstream by pushing
    messages over a zmq socket to downstream clients.  If multiple clients
    connect to this PUSH socket the messages will be load balanced evenly
    across the clients.
    """

    def __init__(self, bind_host_tuple):
        """
        Creates an instance of the ZeroMQCaster.  A zmq PUSH socket is
        created and is bound to the specified host:port.

        :param bind_host_tuple: (host, port), for example ('127.0.0.1', '5000')
        """
        self.context = zmq.Context()
        self.socket_type = zmq.PUSH
        self.sock = self.context.socket(self.socket_type)
        self.sock.bind('tcp://{0}:{1}'.format(*bind_host_tuple))

    def cast(self, msg):
        """
        Sends a message over the zmq PUSH socket
        """
        try:
            self.sock.send(msg)
        except Exception as ex:
            _LOG.exception(ex)

    def close(self):
        """
        Close the zmq socket
        """
        self.sock.close()


class SyslogToZeroMQHandler(SyslogMessageHandler):
    """
    SyslogToZeroMQHandler provides callback methods for the Syslog Parser.
    It builds a dictionary of a parsed syslog message and then sends the
    message downstream using ZeroMQ.
    """

    def __init__(self, zmq_caster):
        """
        Initializes the handler msg, and msg_head.

        :param zmq_caster: An instance of ZeroMQCaster class
        """
        self.msg = bytearray()
        self.msg_head = None
        self.caster = zmq_caster

    def on_msg_head(self, msg_head):
        """
        Callback method for the parser when the full syslog message head
        is received.

        :param msg_head: An instance of the SyslogMessageHead class
        """
        self.msg_head = msg_head

    def on_msg_part(self, msg_part):
        """
        Callback method for the parser that builds the message as
        parts are received

        :param msg_part: An str representing a piece or all of a syslog message
        """
        self.msg.extend(msg_part)

    def on_msg_complete(self, msg_length):
        """
        Callback method for the parser when a complete syslog message
        has been received.  It assembles the final message and sends
        downstream over ZeroMQ.

        :param msg_length: The byte count of the syslog message received
        """
        syslog_msg = self.msg_head.as_dict()
        syslog_msg['msg'] = self.msg.decode('utf-8')
        syslog_msg['msg_length'] = msg_length

        self.caster.cast(json.dumps(syslog_msg))


class ZeroMQReceiver(object):
    """
    ZeroMQReceiver allows for messages to be received by pulling
    messages over a zmq socket from an upstream host.  This client may
    connect to multiple upstream hosts.
    """

    def __init__(self, connect_host_tuples):
        """
        Creates an instance of the ZeroMQReceiver.  A zmq PULL socket is
        created and is connected to all specified host:port.

        :param connect_host_tuples: [(host, port), (host, port)],
        for example [('127.0.0.1', '5000'), ('127.0.0.1', '5001')]
        """
        self.connect_host_tuples = connect_host_tuples
        self.context = zmq.Context()
        self.socket_type = zmq.PULL
        self.sock = self.context.socket(self.socket_type)

        for host_tuple in self.connect_host_tuples:
            self.sock.connect("tcp://{}:{}".format(*host_tuple))

    def get(self):
        """
        Read a message form the zmq socket and return
        """
        return self.sock.recv()

    def close(self):
        """
        Close the zmq socket
        """
        self.sock.close()
