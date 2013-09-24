import zmq
import simplejson as json

from portal.log import get_logger


_LOG = get_logger(__name__)


class ZeroMQReciever(object):

    def __init__(self, connect_host_tuple):
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.PULL)
        self.sock.connect("tcp://{}:{}".format(*connect_host_tuple))

    def get(self):
        try:
            return self.sock.recv()
        except Exception as ex:
            _LOG.exception(ex)


zmq_sock = ZeroMQReciever(('127.0.0.1', 5000))

read = 0
msg = ''

while msg is not None:
    msg = zmq_sock.get()
    msg_dict = json.loads(msg)
    read += 1
    if read % 10000 == 0:
        print('Got {} messages'.format(read))
