import zmq
import simplejson as json

from portal.log import get_logger


_LOG = get_logger(__name__)


class ZeroMQReciever(object):

    def __init__(self, connect_host_tuples):
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.PULL)

        for host_tuple in connect_host_tuples:
            self.sock.connect("tcp://{}:{}".format(*host_tuple))

    def get(self):
        return self.sock.recv()
