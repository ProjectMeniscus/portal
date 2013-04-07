import unittest
import time

from  portal.output.json_stream import JsonEventHandler


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

    def test_read(self):
        pass


def performance(duration=10, print_output=True):
    validator = MessageValidator(None)
    parser = SyslogParser(validator)
    runs = 0
    then = time.time()
    while time.time() - then < duration:
        chunk_message('test', parser, 4)
        runs += 1
    if print_output:
        print('Ran {} times in {} seconds for {} runs per second.'.format(
            runs,
            duration,
            runs / float(duration)))


if __name__ == '__main__':
    print('Executing warmup')
    performance(10, False)
    print('Executing performance test')
    performance(5)

    print('Profiling...')
    import cProfile
    cProfile.run('performance(5)')
