import unittest

import simplejson
from mock import MagicMock, patch
from portal import transport
from portal.input.syslog.usyslog import SyslogMessageHead


class WhenTestingZeroMqCaster(unittest.TestCase):

    def setUp(self):
        self.host = '127.0.0.1'
        self.port = '5000'
        self.bind_host_tuple = (self.host, self.port)
        self.msg = '{"key": "value"}'
        self.zmq_mock = MagicMock()
        self.zmq_mock.PUSH = transport.zmq.PUSH

        #set up the mock of the socket object
        self.socket_mock = MagicMock()
        #create a mock for the zmq context object
        self.context_mock = MagicMock()
        #have the mock context object return the mock socket
        # when the context.socket() method is called
        self.context_mock.socket.return_value = self.socket_mock
        #have the mock zmq module return the mocked context object
        # when the Context() constructor is called
        self.zmq_mock.Context.return_value = self.context_mock
        #create the caster while patching zmq with the above mock objects
        with patch('portal.transport.zmq', self.zmq_mock):
            self.caster = transport.ZeroMQCaster(self.bind_host_tuple)

    def test_constructor(self):
        self.assertEqual(self.caster.socket_type, transport.zmq.PUSH)
        self.context_mock.socket.assert_called_once_with(transport.zmq.PUSH)
        self.socket_mock.bind.assert_called_once_with(
            'tcp://{0}:{1}'.format(self.host, self.port))

    def test_cast(self):
        self.caster.cast(self.msg)
        self.socket_mock.send.assert_called_once_with(self.msg)

    def test_close(self):
        self.caster.close()
        self.socket_mock.close.assert_called_once()


class WhenTestingSyslogToZeroMQHandler(unittest.TestCase):

    def setUp(self):
        self.caster = MagicMock()
        self.handler = transport.SyslogToZeroMQHandler(self.caster)
        self.msg_head = SyslogMessageHead()
        self.msg_part_1 = "Part 1 "
        self.msg_part_2 = "Part 2 "
        self.msg_part_3 = "Part 3 "
        self.test_message = self.msg_part_1 + self.msg_part_2 + self.msg_part_3
        self.msg_length = 127
        self.final_message = self.msg_head.as_dict()
        self.final_message['msg'] = self.test_message
        self.final_message['msg_length'] = self.msg_length

    def test_constructor(self):
        self.assertIsInstance(self.handler.msg, bytearray)
        self.assertIsNone(self.handler.msg_head)
        self.assertEqual(self.handler.caster, self.caster)

    def test_on_msg_head(self):
        self.handler.on_msg_head(self.msg_head)
        self.assertEqual(self.handler.msg_head, self.msg_head)

    def test_on_msg_part(self):
        self.handler.on_msg_part(self.msg_part_1)
        self.assertEqual(
            self.handler.msg,
            bytearray(self.msg_part_1)
        )
        self.handler.on_msg_part(self.msg_part_2)
        self.assertEqual(
            self.handler.msg,
            bytearray(self.msg_part_1 + self.msg_part_2)
        )
        self.handler.on_msg_part(self.msg_part_3)
        self.assertEqual(
            self.handler.msg,
            bytearray(self.msg_part_1 + self.msg_part_2 + self.msg_part_3)
        )

    def test_on_msg_complete(self):
        self.handler.on_msg_head(self.msg_head)
        self.handler.on_msg_part(self.msg_part_1)
        self.handler.on_msg_part(self.msg_part_2)
        self.handler.on_msg_part(self.msg_part_3)
        self.handler.on_msg_complete(self.msg_length)
        self.caster.cast.assert_called_once_with(
            simplejson.dumps(self.final_message))


class WhenTestingZeroMqReceiver(unittest.TestCase):

    def setUp(self):
        self.host = '127.0.0.1'
        self.port = '5000'
        self.connect_host_tuple = (self.host, self.port)
        self.connect_host_tuples = [self.connect_host_tuple]
        self.zmq_mock = MagicMock()
        self.zmq_mock.PULL = transport.zmq.PULL

        #set up the mock of the socket object
        self.socket_mock = MagicMock()
        #create a mock for the zmq context object
        self.context_mock = MagicMock()
        #have the mock context object return the mock socket
        # when the context.socket() method is called
        self.context_mock.socket.return_value = self.socket_mock
        #have the mock zmq module return the mocked context object
        # when the Context() constructor is called
        self.zmq_mock.Context.return_value = self.context_mock
        #create the caster while patching zmq with the above mock objects
        with patch('portal.transport.zmq', self.zmq_mock):
            self.receiver = transport.ZeroMQReceiver(self.connect_host_tuples)

    def test_constructor(self):
        self.assertEqual(self.receiver.socket_type, transport.zmq.PULL)
        self.context_mock.socket.assert_called_once_with(transport.zmq.PULL)
        self.socket_mock.connect.assert_called_once_with(
            'tcp://{0}:{1}'.format(self.host, self.port))

    def test_get(self):
        self.receiver.get()
        self.socket_mock.recv.assert_called_once()

    def test_close(self):
        self.receiver.close()
        self.socket_mock.close.assert_called_once()


class WhenIntegrationTestingTransport(unittest.TestCase):

    def setUp(self):
        self.host = '127.0.0.1'
        self.port = '5000'
        self.host_tuple = (self.host, self.port)
        self.connect_host_tuples = [self.host_tuple]

        self.msg_head = SyslogMessageHead()
        self.test_message = "test_message"
        self.msg_length = 127
        self.final_message = self.msg_head.as_dict()
        self.final_message['msg'] = self.test_message
        self.final_message['msg_length'] = self.msg_length
        self.final_message_json = simplejson.dumps(self.final_message)

    def test_message_transport_over_zmq(self):
        self.caster = transport.ZeroMQCaster(self.host_tuple)
        self.handler = transport.SyslogToZeroMQHandler(self.caster)
        self.receiver = transport.ZeroMQReceiver(self.connect_host_tuples)

        self.handler.on_msg_head(self.msg_head)
        self.handler.on_msg_part(self.test_message)
        self.handler.on_msg_complete(self.msg_length)

        rcvd_msg = self.receiver.get()
        self.assertEqual(rcvd_msg, self.final_message_json)

    def tearDown(self):
        self.caster.close()
        self.receiver.close()


if __name__ == '__main__':
    unittest.main()
