import unittest
import time

from portal.input.syslog import (
    SyslogMessageHandler, Parser, ParsingError
)


SIMPLE_MESSAGE = (
    b'158 <46>1 2013-04-02T14:12:04.873490-05:00 tohru rsyslogd - - - '
    b'[origin software="rsyslogd" swVersion="7.2.5" x-pid="12662" x-info='
    b'"http://www.rsyslog.com"] start')

ACTUAL_MESSAGE = (
    b'225 <142>1 2013-07-12T14:17:00.134003+00:00 tohru apache - - '
    b'[meniscus token="4c5e9071-6791-4023-859c-aa39077582d0" '
    b'tenant="95feffb0"] 127.0.0.1 - - [12/Jul/2013:19:40:58 +0000]'
    b' "GET /test.html HTTP/1.1" 404 466 "-" "curl/7.29.0"')


def chunk_message(data, parser, chunk_size=10, limit=-1):
    if limit <= 0:
        limit = len(data)
    index = 0
    while index < limit:
        next_index = index + chunk_size
        end_index = next_index if next_index < limit else limit
        parser.read(data[index:end_index])
        index = end_index


class MessageValidator(SyslogMessageHandler):

    def __init__(self, test):
        self.test = test
        self.times_called = 0
        self.msg = ''
        self.msg_head = None
        self.caught_exception = None

    @property
    def called(self):
        return self.times_called > 0

    def call_received(self):
        self.times_called += 1

    def exception(self, ex):
        self.caught_exception = ex
        self.call_received()

    def on_msg_head(self, msg_head):
        self.msg_head = msg_head
        self.call_received()
        print '\n**************msg_head******************\n'

    def on_msg_part(self, msg_part):
        self.msg += msg_part

    def on_msg_complete(self):
        pass

    def validate(self):
        self._validate(
            self.test,
            self.caught_exception,
            self.msg_head,
            self.msg)

    def _validate(self, test, caught_exception, msg_head, msg):
        raise NotImplementedError


class ActualValidator(MessageValidator):

    def _validate(self, test, caught_exception, msg_head, msg):
        test.assertEqual('142', msg_head.priority)
        test.assertEqual('1', msg_head.version)
        test.assertEqual('2013-07-12T14:17:00.134003+00:00',
                         msg_head.timestamp)
        test.assertEqual('tohru', msg_head.hostname)
        test.assertEqual('apache', msg_head.appname)
        test.assertEqual('-', msg_head.processid)
        test.assertEqual('-', msg_head.messageid)
        test.assertEqual(1, len(msg_head.sd))
        test.assertTrue('meniscus' in msg_head.sd)
        test.assertTrue('token' in msg_head.sd['meniscus'])
        test.assertEqual('4c5e9071-6791-4023-859c-aa39077582d0',
                         msg_head.sd['meniscus']['token'])
        test.assertTrue('tenant' in msg_head.sd['meniscus'])
        test.assertEqual('95feffb0', msg_head.sd['meniscus']['tenant'])
        test.assertEqual(('127.0.0.1 - - [12/Jul/2013:19:40:58 +0000] '
                          '"GET /test.html HTTP/1.1" 404 466 "-" '
                          '"curl/7.29.0"'), msg)


class WhenParsingSyslog(unittest.TestCase):

    def test_read_actual_message(self):
        validator = ActualValidator(self)
        parser = Parser(validator)
        parser.read(ACTUAL_MESSAGE)
        self.assertTrue(validator.called)
        validator.validate()
        #parser.reset()
        parser.read(SIMPLE_MESSAGE)
        #print validator.msg_head.as_dict()


if __name__ == '__main__':
    unittest.main()

