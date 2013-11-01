import zmq

import simplejson as json

from portal.log import get_logger
from portal.input.syslog import SyslogMessageHandler


_LOG = get_logger(__name__)


class ZeroMQCaster(object):

    def __init__(self, bind_host_tuple):
        self.context = zmq.Context()
        self.socket_type = zmq.PUSH
        self.sock = self.context.socket(self.socket_type)
        self.sock.bind('tcp://{0}:{1}'.format(*bind_host_tuple))

    def cast(self, msg):
        try:
            self.sock.send(msg)
        except Exception as ex:
            _LOG.exception(ex)

    def close(self):
        self.sock.close()


class SyslogToZeroMQHandler(SyslogMessageHandler):

    def __init__(self, zmq_caster):
        self.msg = bytearray()
        self.msg_head = None
        self.caster = zmq_caster

    def on_msg_head(self, msg_head):
        self.msg_head = msg_head

    def on_msg_part(self, msg_part):
        self.msg.extend(msg_part)

    def on_msg_complete(self, msg_length):
        syslog_msg = self.msg_head.as_dict()
        syslog_msg['msg'] = self.msg.decode('utf-8')
        syslog_msg['msg_length'] = msg_length

        self.caster.cast(json.dumps(syslog_msg))
