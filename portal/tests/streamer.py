import time
import signal
import socket

MESSAGE = (
    b'158 <46>1 2013-04-02T14:12:04.873490-05:00 tohru rsyslogd - - - '
    b'[origin software="rsyslogd" swVersion="7.2.5" x-pid="12662" x-info='
    b'"http://www.rsyslog.com"] start')

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
    try:
        while continue_sending and time.time() - then < TEST_DURATION:
            sock.sendall(MESSAGE)
            sent += 1
    except Exception as ex:
        print(ex)
    finally:
        sock.close()
    megs_sent = sent * 158 / 1024 / 1024
    print(OUTPUT.format(
        sent,
        TEST_DURATION,
        sent / TEST_DURATION,
        megs_sent,
        megs_sent / TEST_DURATION))


signal.signal(signal.SIGINT, exit_run)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 5140))
run(sock)
