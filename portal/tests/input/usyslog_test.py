import unittest
import time

from  portal.input.usyslog import SyslogMessageHandler, Parser


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
    b'216 <46>1 - tohru ' +
    b'- 6611 - [origin_1 software="rsyslogd" ' +
    b'swVersion="7.2.2" x-pid="12297" ' +
    b'x-info="http://www.rsyslog.com"]' +
    b'[origin_2 software="rsyslogd" swVersion="7.2.2" ' +
    b'x-pid="12297" x-info="http://www.rsyslog.com"] ' +
    b'start')

NO_STRUCTURED_DATA = bytearray(
    b'30 <46>1 - tohru - 6611 - - start')


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
        self.called = False
        self.times_called = 0


class ActualValidator(MessageValidator):

    def message_head(self, msg_head):
        self.called = True
        self.times_called += 1
        self.test.assertEqual('46', msg_head.priority)
        self.test.assertEqual('1', msg_head.version)
        self.test.assertEqual('2013-04-02T14:12:04.873490-05:00',
            msg_head.timestamp)
        self.test.assertEqual('tohru', msg_head.hostname)
        self.test.assertEqual('rsyslogd', msg_head.appname)
        self.test.assertEqual('-', msg_head.processid)
        self.test.assertEqual('-', msg_head.messageid)
        self.test.assertEqual(0, len(msg_head.sd))


class HappyPathValidator(MessageValidator):

    def message_head(self, msg_head):
        self.called = True
        self.times_called += 1
        self.test.assertEqual('46', msg_head.priority)
        self.test.assertEqual('1', msg_head.version)
        self.test.assertEqual('2012-12-11T15:48:23.217459-06:00',
            msg_head.timestamp)
        self.test.assertEqual('tohru', msg_head.hostname)
        self.test.assertEqual('rsyslogd', msg_head.appname)
        self.test.assertEqual('6611', msg_head.processid)
        self.test.assertEqual('12512', msg_head.messageid)
        self.test.assertEqual(2, len(msg_head.sd))


class MissingFieldsValidator(MessageValidator):

    def message_head(self, msg_head):
        self.called = True
        self.times_called += 1
        self.test.assertEqual('46', msg_head.priority)
        self.test.assertEqual('1', msg_head.version)
        self.test.assertEqual('-', msg_head.timestamp)
        self.test.assertEqual('tohru', msg_head.hostname)
        self.test.assertEqual('-', msg_head.appname)
        self.test.assertEqual('6611', msg_head.processid)
        self.test.assertEqual('-', msg_head.messageid)
        self.test.assertEqual(2, len(msg_head.sd))



class MissingSDValidator(MessageValidator):

    def message_head(self, msg_head):
        self.called = True
        self.times_called += 1
        self.test.assertEqual('46', msg_head.priority)
        self.test.assertEqual('1', msg_head.version)
        self.test.assertEqual('-', msg_head.timestamp)
        self.test.assertEqual('tohru', msg_head.hostname)
        self.test.assertEqual('-', msg_head.appname)
        self.test.assertEqual('6611', msg_head.processid)
        self.test.assertEqual('-', msg_head.messageid)
        self.test.assertEqual(0, len(msg_head.sd))


class WhenParsingSyslog(unittest.TestCase):

    def test_read_actual_message(self):
        validator = ActualValidator(self)
        parser = Parser(validator)

        parser.read(ACTUAL_MESSAGE)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        self.assertTrue(validator.called)

    def test_read_message_head(self):
        validator = HappyPathValidator(self)
        parser = Parser(validator)

        chunk_message(HAPPY_PATH_MESSAGE, parser)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        self.assertTrue(validator.called)

    def test_read_message_with_missing_fields(self):
        validator = MissingFieldsValidator(self)
        parser = Parser(validator)

        chunk_message(MISSING_FIELDS, parser)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        self.assertTrue(validator.called)

    def test_read_message_with_no_sd(self):
        validator = MissingSDValidator(self)
        parser = Parser(validator)

        chunk_message(NO_STRUCTURED_DATA, parser)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        self.assertTrue(validator.called)

    def test_read_messages_back_to_back(self):
        validator = ActualValidator(self)
        parser = Parser(validator)

        chunk_message(ACTUAL_MESSAGE, parser)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        chunk_message(ACTUAL_MESSAGE, parser)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        chunk_message(ACTUAL_MESSAGE, parser)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        chunk_message(ACTUAL_MESSAGE, parser)
        self.assertEqual(0, parser.cparser._lexer().remaining())
        self.assertEqual(4, validator.times_called)


def performance(duration=10, print_output=True):
    validator = MessageValidator(None)
    parser = Parser(validator)
    runs = 0
    then = time.time()
    while time.time() - then < duration:
        chunk_message(HAPPY_PATH_MESSAGE, parser, 263)
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
    performance(5)

    print('Profiling...')
    import cProfile
    cProfile.run('performance(5)')
