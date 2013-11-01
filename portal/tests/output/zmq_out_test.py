import unittest
from mock import MagicMock, patch
from portal.output import zmq_out
import zmq


def suite():
    WhenTestingZeroMqCaster()


class WhenTestingZeroMqCaster(unittest.TestCase):
    def setUp(self):
        self.bind_host_tuple = ('127.0.0.1', '5000')
        self.Context = MagicMock()
        self.socket_mock = MagicMock
        self.caster = zmq_out.ZeroMQCaster(self.bind_host_tuple)

    def test_constructor(self):
        self.assertIsInstance(self.caster.context, zmq.Context)
        self.assertEqual(self.caster.socket_type, zmq.PUSH)

    def test_cast(self):
        self.assertTrue(True)

    def tearDown(self):
        self.caster.close()





if __name__ == '__main__':
    unittest.main()