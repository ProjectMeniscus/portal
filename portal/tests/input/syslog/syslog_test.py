import unittest
import time

from portal.input.syslog import (
    SyslogMessageHandler, Parser, ParsingError
)


BAD_OCTET_COUNT = (
    b'2A <46>1 - tohru - 6611 - - start')

TOO_LONG_OCTET_COUNT = (
    b'9345395891038650918340698109386510938 <46>1 - tohru - 6611 - - start')

SHORT_OCTET_COUNT = (
    b'28 <46>1 - tohru - 6611 - - start')

ACTUAL_MESSAGE = (
    b'158 <46>1 2013-04-02T14:12:04.873490-05:00 tohru rsyslogd - - - '
    b'[origin software="rsyslogd" swVersion="7.2.5" x-pid="12662" x-info='
    b'"http://www.rsyslog.com"] start')

HAPPY_PATH_MESSAGE = bytearray(
    b'259 <46>1 2012-12-11T15:48:23.217459-06:00 tohru ' +
    b'rsyslogd 6611 12512 [origin_1 software="rsyslogd" ' +
    b'swVersion="7.2.2" x-pid="12297" ' +
    b'x-info="http://www.rsyslog.com"]' +
    b'[origin_2 software="rsyslogd" swVersion="7.2.2" ' +
    b'x-pid="12297" x-info="http://www.rsyslog.com"] ' +
    b'start')

MISSING_FIELDS = bytearray(
    b'217 <46>1 - tohru ' +
    b'- 6611 - [origin_1 software="rsyslogd" ' +
    b'swVersion="7.2.2" x-pid="12297" ' +
    b'x-info="http://www.rsyslog.com"]' +
    b'[origin_2 software="rsyslogd" swVersion="7.2.2" ' +
    b'x-pid="12297" x-info="http://www.rsyslog.com"] ' +
    b'start')

NO_STRUCTURED_DATA = bytearray(
    b'30 <46>1 - tohru - 6611 - - start')


def chunk_message(data, parser, chunk_size=10):
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
        self.msg = bytearray()
        self.msg_head = None
        self.complete = False
        self.caught_exception = None

    @property
    def called(self):
        return self.times_called > 0

    def call_received(self):
        self.times_called += 1

    def on_msg_head(self, msg_head):
        self.msg_head = msg_head
        self.call_received()

    def on_msg_part(self, msg_part):
        self.msg.extend(msg_part)

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

    def test_bad_octet_count(self):
        validator = MessageValidator(self)
        parser = Parser(validator)

        with self.assertRaises(ParsingError):
            parser.read(BAD_OCTET_COUNT)

    def test_too_long_octet_count(self):
        validator = MessageValidator(self)
        parser = Parser(validator)

        with self.assertRaises(ParsingError):
            parser.read(TOO_LONG_OCTET_COUNT)

    def test_short_octet_count(self):
        validator = MessageValidator(self)
        parser = Parser(validator)

        with self.assertRaises(ParsingError):
            parser.read(SHORT_OCTET_COUNT)

    def test_read_actual_message(self):
        validator = ActualValidator(self)
        parser = Parser(validator)

        parser.read(ACTUAL_MESSAGE)
        self.assertTrue(validator.called)
        validator.validate()

    def test_read_message_head(self):
        validator = HappyPathValidator(self)
        parser = Parser(validator)

        chunk_message(HAPPY_PATH_MESSAGE, parser)
        self.assertTrue(validator.called)
        validator.validate()

    def test_read_message_with_missing_fields(self):
        validator = MissingFieldsValidator(self)
        parser = Parser(validator)

        chunk_message(MISSING_FIELDS, parser)
        self.assertTrue(validator.called)
        validator.validate()

    def test_read_message_with_no_sd(self):
        validator = MissingSDValidator(self)
        parser = Parser(validator)

        chunk_message(NO_STRUCTURED_DATA, parser)
        self.assertTrue(validator.called)
        validator.validate()

    def test_read_messages_back_to_back(self):
        validator = ActualValidator(self)
        parser = Parser(validator)

        chunk_message(ACTUAL_MESSAGE, parser)
        chunk_message(ACTUAL_MESSAGE, parser)
        chunk_message(ACTUAL_MESSAGE, parser)
        chunk_message(ACTUAL_MESSAGE, parser)
        self.assertEqual(4, validator.times_called)


def performance(duration=10, print_output=True):
    validator = MessageValidator(None)
    parser = Parser(validator)
    runs = 0
    then = time.time()
    while time.time() - then < duration:
        parser.read(HAPPY_PATH_MESSAGE)
        runs += 1
    if print_output:
        print('Ran {} times in {} seconds for {} runs per second.'.format(
            runs,
            duration,
            runs / float(duration)))


if __name__ == '__main__1':
    unittest.main()

if __name__ == '__main__':
    print('Executing performance test')
    performance(4)
