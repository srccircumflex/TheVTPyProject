# MIT License
#
# Copyright (c) 2023 Adrian F. Hoefflin [srccircumflex]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#


from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
from queue import Queue
from time import localtime, strftime, sleep
from atexit import register
from sys import argv


def receiver(_ip: str, _port: int):
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.bind((_ip, _port))
        sock.listen(1)
        print(strftime("[%H:%M:%S]", localtime()), "-Receiver started- @ %s:%s" % (_ip, _port))
        try:
            while True:
                con, _ = sock.accept()
                while True:
                    if not (dat := con.recv(1024)):
                        break
                    print(dat.decode(errors='replace'), end='')
                    sleep(.002)
        except KeyboardInterrupt:
            exit('')


class Stream(Thread):
    def __init__(self, _ip: str, _port: int):
        Thread.__init__(self, daemon=True)
        self.q = Queue()
        self.con = (_ip, _port)
        self.start()

    def run(self) -> None:
        with socket(AF_INET, SOCK_STREAM) as sock:
            try:
                sock.connect(self.con)
                while True:
                    sock.sendall(self.q.get().encode())
            except ConnectionRefusedError:
                return

    def write(self, dat):
        self.q.put(dat)


_lock = False
_timeout = 15


def _exit_lock():
    i = 0
    while _lock:
        sleep(.1)
        i += 1
        if i == _timeout:
            raise TimeoutError('debugger: exit_lock')


debug_stream: Stream


def debug_o(*__o):
    global _lock
    _lock = True
    try:
        print(strftime("[%H:%M:%S]", localtime()), *__o, file=debug_stream)
    finally:
        _lock = False


def debug_stream_o(*__o, debug_stream_: Stream):
    global _lock
    _lock = True
    try:
        print(strftime("[%H:%M:%S]", localtime()), *__o, file=debug_stream_)
    finally:
        _lock = False


IP = "127.1.2.4"
PORT = 50000


if __name__ == "__main__":
    if argv[1:]:
        receiver(argv[1], int(argv[2]))
    else:
        receiver(IP, PORT)
else:
    register(_exit_lock)
    debug_stream = Stream(IP, PORT)
    debug_o('[×××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××]')

