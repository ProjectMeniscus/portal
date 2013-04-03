import time
import signal
import socket

MESSAGE = (
    b'158 <46>1 2013-04-02T14:12:04.873490-05:00 tohru rsyslogd - - - '
    b'[origin software="rsyslogd" swVersion="7.2.5" x-pid="12662" x-info='
    b'"http://www.rsyslog.com"] start')

continue_sending = True


def exit_run():
    continue_sending = False


def run(sock):
    sent = 0
    then = time.time()
    try:
        while continue_sending and time.time() - then < 10:
            sock.sendall(MESSAGE)
            sent += 1
    except Exception as ex:
        print(ex)
    finally:
        sock.close()
    print(('Sent {} messages in 10 seconds at a rate of {} mps for a '
          'total of {} MB').format(
            sent, sent / 10, (sent * 158 / 1024 / 1024)))


signal.signal(signal.SIGINT, exit_run)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 5140))
run(sock)
