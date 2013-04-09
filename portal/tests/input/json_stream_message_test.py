import unittest
import time

from pprint import pprint

from  portal.input.json_stream import JsonEventHandler, JsonEventParser
from  portal.input.json_stream_message import JsonMessageAssembler, JsonMessageHandler


COMPLEX_NESTING = b'{"authentication": { "uid": "65c45346-436c-4f1d-8a02-7230fd570760", "token": "569e0670-e798-4e34-be65-23dbcfa81b73" }, "body": ["testing", { "key": "a", "value": 12345 }]}{"authentication": { "uid": "65c45346-436c-4f1d-8a02-7230fd570760", "token": "569e0670-e798-4e34-be65-23dbcfa81b73" }, "body": ["testing", { "key": "a", "value": 12345 }]}'
MESSAGE_DICT = {
    'authentication': {
        'token': '569e0670-e798-4e34-be65-23dbcfa81b73',
        'uid': '65c45346-436c-4f1d-8a02-7230fd570760'
    },
    'fake': False,
    'body': [
        'testing',
        {
            'key': 'a',
            'value': '12345'
        }
    ]
}


class EventValidator(JsonMessageHandler):

    MESSAGE_FORMAT = 'Message message element "{}" not found in message.\n'

    def __init__(self, test, expectations):
        self.test = test
        self.expectations = expectations

    def header(self, key, value):
        expected = self.expectations.get(key)
        self.test.assertTrue(expected)
        self.test.assertEqual(expected, value)

    def body(self, body):
        self.test.assertEqual(self.expectations.get('body'), body)


def chunk_message(data, parser, chunk_size=10, limit=-1):
    if limit <= 0:
        limit = len(data)
    index = 0
    while index < limit:
        next_index = index + chunk_size
        end_index = next_index if next_index < limit else limit
        parser.read(data[index:end_index])
        index = end_index


class WhenParsingJson(unittest.TestCase):

    def test_read_complex_nesting(self):
        validator = EventValidator(self, MESSAGE_DICT)
        processor = JsonEventParser(JsonMessageAssembler(validator))
        processor.read(COMPLEX_NESTING)


if __name__ == '__main__':
    unittest.main()

