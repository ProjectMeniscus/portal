import unittest
import time

from portal.input.syslog import (
    SyslogMessageHandler, Parser, ParsingError
)


ACTUAL_MESSAGE = (
    b'158 <46>1 2013-04-02T14:12:04.873490-05:00 tohru rsyslogd - - - '
    b'[origin software="rsyslogd" swVersion="7.2.5" x-pid="12662" x-info='
    b'"http://www.rsyslog.com"] start')


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

    def message_head(self, msg_head):
        self.msg_head = msg_head
        self.call_received()

    def message_part(self, msg_part):
        self.msg += msg_part

    def message_complete(self, msg_part):
        self.msg += msg_part

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
        test.assertEqual('46', msg_head.priority)
        test.assertEqual('1', msg_head.version)
        test.assertEqual('2013-04-02T14:12:04.873490-05:00',
                         msg_head.timestamp)
        test.assertEqual('tohru', msg_head.hostname)
        test.assertEqual('rsyslogd', msg_head.appname)
        test.assertEqual('-', msg_head.processid)
        test.assertEqual('-', msg_head.messageid)
        test.assertEqual(0, len(msg_head.sd))


class HappyPathValidator(MessageValidator):

    def _validate(self, test, caught_exception, msg_head, msg):
        test.assertEqual('46', msg_head.priority)
        test.assertEqual('1', msg_head.version)
        test.assertEqual('2012-12-11T15:48:23.217459-06:00',
                         msg_head.timestamp)
        test.assertEqual('tohru', msg_head.hostname)
        test.assertEqual('rsyslogd', msg_head.appname)
        test.assertEqual('6611', msg_head.processid)
        test.assertEqual('12512', msg_head.messageid)
        test.assertEqual(2, len(msg_head.sd))

        # Unicode and python 2.x makes John cry
        expected_sd = {
            unicode('origin_1'): {
                unicode('software'): b'rsyslogd',
                unicode('swVersion'): b'7.2.2',
                unicode('x-pid'): b'12297',
                unicode('x-info'): b'http://www.rsyslog.com'
            },
            unicode('origin_2'): {
                unicode('software'): b'rsyslogd',
                unicode('swVersion'): b'7.2.2',
                unicode('x-pid'): b'12297',
                unicode('x-info'): b'http://www.rsyslog.com'
            }
        }

        test.assertEqual(expected_sd, msg_head.sd)


class MissingFieldsValidator(MessageValidator):

    def _validate(self, test, caught_exception, msg_head, msg):
        test.assertEqual('46', msg_head.priority)
        test.assertEqual('1', msg_head.version)
        test.assertEqual('-', msg_head.timestamp)
        test.assertEqual('tohru', msg_head.hostname)
        test.assertEqual('-', msg_head.appname)
        test.assertEqual('6611', msg_head.processid)
        test.assertEqual('-', msg_head.messageid)
        test.assertEqual(2, len(msg_head.sd))


class MissingSDValidator(MessageValidator):

    def _validate(self, test, caught_exception, msg_head, msg):
        test.assertEqual('46', msg_head.priority)
        test.assertEqual('1', msg_head.version)
        test.assertEqual('-', msg_head.timestamp)
        test.assertEqual('tohru', msg_head.hostname)
        test.assertEqual('-', msg_head.appname)
        test.assertEqual('6611', msg_head.processid)
        test.assertEqual('-', msg_head.messageid)
        test.assertEqual(0, len(msg_head.sd))


class WhenParsingSyslog(unittest.TestCase):

    def test_read_actual_message(self):
        validator = ActualValidator(self)
        parser = Parser(validator)

        parser.read(ACTUAL_MESSAGE)
        self.assertTrue(validator.called)
        validator.validate()


if __name__ == '__main__':
    unittest.main()

