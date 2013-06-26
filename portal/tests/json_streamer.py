import time
import signal
import socket
import copy

from portal.output.json import ObjectJsonWriter

HEADERS = {
    'authentication': {
        'token': '569e0670-e798-4e34-be65-23dbcfa81b73',
        'uid': '65c45346-436c-4f1d-8a02-7230fd570760'
    }
}

BODY = {
    'contents': [
        'testing',
        {
            'key': 'a',
            'value': '12345'
        }
    ]
}

TEST_DURATION = 10
OUTPUT = str('Sent {} messages in {} seconds at a rate of {} messages/sec '
             'for a total of {} MB at {} MB/sec')

# Global to catch SIGINT
continue_sending = True


def exit_run():
    continue_sending = False


def run(sock):
    sent = 0
    then = time.time()
    writer = ObjectJsonWriter()
    try:
        while continue_sending and time.time() - then < TEST_DURATION:
            writer.write(HEADERS, BODY, sock)
            sent += 1
    except Exception as ex:
        print(ex)
    finally:
        sock.close()
    megs_sent = sent * 270 / 1024 / 1024
    print(OUTPUT.format(
        sent,
        TEST_DURATION,
        sent / TEST_DURATION,
        megs_sent,
        megs_sent / TEST_DURATION))


signal.signal(signal.SIGINT, exit_run)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 9001))
run(sock)
