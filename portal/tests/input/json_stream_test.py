import unittest
import time

from  portal.input.json_stream import JsonEventHandler, JsonEventParser


PERFORMANCE_TEST = b'{ "header": "12345", "body": 12345.15 }{ "header": "12345", "body": 1234e+5 }{ "header": "12345", "body": -12345 }{ "header": "12345", "body": null }{ "header": "12345", "body": false }{ "header": "12345", "body": true }'
FLAT_OBJECT_MULTIPLE_TYPES = b'{ "header": "12345", "body": 12345.15 }{ "header": "12345", "body": 1234e+5 }{ "header": "12345", "body": -12345 }{ "header": "12345", "body": null }{ "header": "12345", "body": false }{ "header": "12345", "body": true }'
NESTED_OBJECTS = b'{ "header": "12345", "auth": { "token": "yb907n834gyb9708234tvgy9h780", "time": 123878921748 }, "body": "test" }{ "header": "12345", "auth": { "token": "yb907n834gyb9708234tvgy9h780", "time": 123878921748 }, "body": "test" }'
NESTED_ARRAYS = b'["test", 12345, 12345.01, -12345, 12345e+5, 12345E+4, 12345e-4, 12345E-1, [ "test" ]]'
COMPLEX_NESTING = b'{"authentication": { "uid": "65c45346-436c-4f1d-8a02-7230fd570760", "token": "569e0670-e798-4e34-be65-23dbcfa81b73" }, "body": ["testing", { "key": "a", "value": 12345 }]}{"authentication": { "uid": "65c45346-436c-4f1d-8a02-7230fd570760", "token": "569e0670-e798-4e34-be65-23dbcfa81b73" }, "body": ["testing", { "key": "a", "value": 12345 }]}'

class EventValidator(JsonEventHandler):

    def __init__(self, test, expectations=dict()):
        self.test = test
        self.calls = dict()
        self.expectations = expectations

    def _called(self, call, value=None):
        times_called = self.calls.get(call)
        if times_called is None:
            times_called = 1
        else:
            times_called += 1
        self.calls[call] = times_called

    def assert_expectations(self):
        output = ''
        for call in self.expectations:
            times_called = self.calls.get(call, 0)
            expected = self.expectations.get(call, 0)
            if times_called != expected:
                    output += (
                            '{} called an unexpected amount of times. '
                            'Expected: {} - Actual: {}\n'
                        ).format(call, expected, times_called)
        if len(output) > 0:
            self.test.fail(output)

    def message_end(self):
        self._called('message_end')

    def begin_object(self):
        self._called('begin_object')

    def end_object(self):
        self._called('end_object')

    def begin_array(self):
        self._called('begin_array')

    def end_array(self):
        self._called('end_array')

    def fieldname(self, fieldname):
        self._called('fieldname', fieldname)

    def string_value(self, value):
        self._called('string_value', value)

    def number_value(self, value):
        self._called('number_value', value)

    def boolean_value(self, value):
        self._called('boolean_value', value)

    def null_value(self):
        self._called('null_value')


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

    def test_read_flat_object_multiple_types(self):
        validator = EventValidator(self, {
            'message_end': 6,
            'begin_object': 6,
            'end_object': 6,
            'begin_array': 0,
            'end_array':  0,
            'fieldname': 12,
            'string_value': 6,
            'number_value': 3,
            'boolean_value': 2,
            'null_value': 1
        })
        processor = JsonEventParser(validator)
        processor.read(FLAT_OBJECT_MULTIPLE_TYPES)
        validator.assert_expectations()

    def test_read_nested_objects(self):
        validator = EventValidator(self, {
            'message_end': 2,
            'begin_object': 4,
            'end_object': 4,
            'begin_array': 0,
            'end_array':  0,
            'fieldname': 10,
            'string_value': 6,
            'number_value': 2,
            'boolean_value': 0,
            'null_value': 0
        })
        processor = JsonEventParser(validator)
        processor.read(NESTED_OBJECTS)
        validator.assert_expectations()

    def test_read_nested_arrays(self):
        validator = EventValidator(self, {
            'message_end': 1,
            'begin_object': 0,
            'end_object': 0,
            'begin_array': 2,
            'end_array':  2,
            'fieldname': 0,
            'string_value': 2,
            'number_value': 7,
            'boolean_value': 0,
            'null_value': 0
        })
        processor = JsonEventParser(validator)
        processor.read(NESTED_ARRAYS)
        validator.assert_expectations()

    def test_read_complex_nesting(self):
        validator = EventValidator(self, {
            'message_end': 2,
            'begin_object': 6,
            'end_object': 6,
            'begin_array': 2,
            'end_array':  2,
            'fieldname': 12,
            'string_value': 8,
            'number_value': 2,
            'boolean_value': 0,
            'null_value': 0
        })
        processor = JsonEventParser(validator)
        processor.read(COMPLEX_NESTING)
        validator.assert_expectations()


def performance(duration=10, print_output=True):
    data = COMPLEX_NESTING
    processor = JsonEventParser(JsonEventHandler())
    runs = 0
    then = time.time()
    while time.time() - then < duration:
        processor.read(data)
        runs += 1
    if print_output:
        length_in_bytes = len(data)
        print((
                'Ran {} times in {} seconds for {} runs per second. '
                'With a message length of {} bytes, this equals {} MB/sec'
            ).format(
                runs,
                duration,
                runs / float(duration),
                length_in_bytes,
                (length_in_bytes * runs / 1024 / 1024)))


if __name__ == '__main__1':
    unittest.main()


if __name__ == '__main__':
    print('Executing warmup')
    performance(10, False)
    print('Executing performance test')
    performance(5)

    print('Profiling...')
    import cProfile
    cProfile.run('performance(5)')
