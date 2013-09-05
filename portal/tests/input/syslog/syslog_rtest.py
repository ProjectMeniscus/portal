import unittest

from portal.input.syslog import (
    SyslogMessageHandler, Parser, ParsingError
)


SIMPLE_MESSAGE = (
    b'158 <46>1 2013-04-02T14:12:04.873490-05:00 tohru rsyslogd - - - '
    b'[origin software="rsyslogd" swVersion="7.2.5" x-pid="12662" x-info='
    b'"http://www.rsyslog.com"] start')

SD_MESSAGE = (
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
        self.complete = False
        self.caught_exception = None

    def clear(self):
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

    def on_msg_part(self, msg_part):
        self.msg += msg_part

    def on_msg_complete(self):
        self.complete = True

    def validate(self):
        self.test.assertTrue(
            self.complete,
            'A syslog message must be completed in order to be valid.')

        self._validate(
            self.test,
            self.caught_exception,
            self.msg_head,
            self.msg)

    def _validate(self, test, caught_exception, msg_head, msg):
        raise NotImplementedError

    def validate_sd_msg(self):
        self.test.assertEqual('142', self.msg_head.priority)
        self.test.assertEqual('1', self.msg_head.version)
        self.test.assertEqual('2013-07-12T14:17:00.134003+00:00',
                              self.msg_head.timestamp)
        self.test.assertEqual('tohru', self.msg_head.hostname)
        self.test.assertEqual('apache', self.msg_head.appname)
        self.test.assertEqual('-', self.msg_head.processid)
        self.test.assertEqual('-', self.msg_head.messageid)
        self.test.assertEqual(1, len(self.msg_head.sd))
        self.test.assertTrue('meniscus' in self.msg_head.sd)
        self.test.assertTrue('token' in self.msg_head.sd['meniscus'])
        self.test.assertEqual('4c5e9071-6791-4023-859c-aa39077582d0',
                              self.msg_head.sd['meniscus']['token'])
        self.test.assertTrue('tenant' in self.msg_head.sd['meniscus'])
        self.test.assertEqual('95feffb0',
                              self.msg_head.sd['meniscus']['tenant'])
        self.test.assertEqual(('127.0.0.1 - - [12/Jul/2013:19:40:58 +0000] '
                               '"GET /test.html HTTP/1.1" 404 466 "-" '
                               '"curl/7.29.0"'), self.msg)

    def validate_simple_msg(self):
        self.test.assertEqual('46', self.msg_head.priority)
        self.test.assertEqual('1', self.msg_head.version)
        self.test.assertEqual('2013-04-02T14:12:04.873490-05:00',
                              self.msg_head.timestamp)
        self.test.assertEqual('tohru', self.msg_head.hostname)
        self.test.assertEqual('rsyslogd', self.msg_head.appname)
        self.test.assertEqual('-', self.msg_head.processid)
        self.test.assertEqual('-', self.msg_head.messageid)
        self.test.assertEqual(0, len(self.msg_head.sd))
        self.test.assertEqual(('[origin software="rsyslogd" swVersion="7.2.5" '
                               'x-pid="12662" x-info="http://www.rsyslog.com"]'
                               ' start'), self.msg)


class WhenParsingSyslog(unittest.TestCase):

    def test_read_actual_message(self):
        validator = MessageValidator(self)
        parser = Parser(validator)

        try:
            chunk_message(SD_MESSAGE, parser)
            self.assertTrue(validator.called)
            validator.validate_sd_msg()

            # Clear the validator for the next run
            validator.clear()

            chunk_message(SIMPLE_MESSAGE, parser)
            #self.assertTrue(validator.called)
            validator.validate_simple_msg()
        except ParsingError as err:
            print(err.msg)
            print(err.cause)
            self.fail('Exception caught: {}'.format(err))


if __name__ == '__main__':
    unittest.main()
