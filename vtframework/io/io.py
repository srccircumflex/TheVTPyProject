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

from __future__ import annotations

import sys
from abc import ABC
from threading import Thread, Condition, Lock
from time import sleep, monotonic, monotonic_ns
from multiprocessing import Pipe
from multiprocessing.connection import Connection
from multiprocessing.context import reduction as _reduction
from typing import TextIO, Callable, Type, Iterator, AnyStr, Iterable

from vtframework.iodata.c1ctrl import ManualESC, isFinal
from vtframework.iosys.vtermios import mod_nonblock, mod_nonecho, ModItem, ModItemsHandle, ModDummy
from vtframework.iodata.chars import Char
from vtframework.iodata.keys import Key
from vtframework.iodata.replies import Reply
from vtframework.iodata.mouse import Mouse
from vtframework.iodata.esccontainer import EscSegment
from vtframework.iosys.vtiinterpreter import MainInterpreter

_ForkingPickler = _reduction.ForkingPickler

if sys.platform == "win32":
    from msvcrt import kbhit as _kbhit
else:
    from select import select as _select

    def _kbhit() -> bool:
        return _select([sys.stdin.buffer], [], [], 0)[0] != list()


def kbhit() -> bool:
    """:return: whether stdin is waiting to be read."""
    return _kbhit()


def getch(block: bool = False, interpreter: MainInterpreter = MainInterpreter()
          ) -> Char | Key | Mouse | Reply | EscSegment:
    """
    Read an input from stdin and complete sequential inputs (UTF8 sequence / escape sequences).
    Block until an input can be read if `block` is ``True``, otherwise return :class:`Char`\\ ('') if nothing can be
    read.
    """
    if not block and not kbhit():
        _cr = Char('')
    else:
        _cr = interpreter.gen(lambda: sys.stdin.buffer.read(1))
    return _cr


def flushio() -> None:
    """Flush stdin and stdout."""
    sys.stdin.flush()
    sys.stdout.flush()


def out(*__s: str, sep: str = '', end: str = '', flush: bool = False) -> None:
    """Write to stdout."""
    sys.stdout.write(str().join([i + sep for i in __s]) + end)
    if flush:
        sys.stdout.flush()


class _Pipe:
    """
    Handle for a simplex pipe.

    Compared to the original, some parameter and value verifications are skipped.
    """

    in_pipe: Connection
    out_pipe: Connection

    def __init__(self):
        self.out_pipe, self.in_pipe = Pipe(False)

    def send_bytes(self, __b: bytes) -> None:
        self.in_pipe._check_closed()
        self.in_pipe._check_writable()
        self.in_pipe._send_bytes(memoryview(__b))

    def recv_bytes(self) -> bytes:
        self.out_pipe._check_closed()
        self.out_pipe._check_readable()
        if (buf := self.out_pipe._recv_bytes(None)) is None:
            self.out_pipe._bad_message_length()
        return buf.getvalue()

    def send(self, __o: object) -> None:
        self.send_bytes(_ForkingPickler.dumps(__o))

    def recv(self):
        self.out_pipe._check_closed()
        self.out_pipe._check_readable()
        buf = self.out_pipe._recv_bytes()
        return _ForkingPickler.loads(buf.getbuffer())

    def poll(self) -> bool:
        return self.out_pipe.poll()


class StdinAdapter(Thread, TextIO):
    """
    An adapter for ``sys.stdin``. This allows a more precise query about whether characters can be read from the stream
    (unlike select.select/msvcrt.kbhit, which in fact only consider a keystroke). This allows more dynamic processing
    of sequential input (escape sequences). Starts itself as daemon thread and reads from the original stdin while
    ``self.keepalive`` is ``True`` and puts the read characters into a pipe.
    **Is assigned to sys.stdin and overwrites kbhit.**

    **[ i ]** :class:`InputSuper` expects that ``sys.stdin`` has been adapted that way.

    The emulator is modified accordingly (nonblock & nonecho) for usage if the parameter `mod` is set to ``True``
    (default). The value ``reset_atexit`` in the :class:`ModItem`'s is ``True`` by default to reset the modifications
    to the emulator when exiting the Python interpreter.

    When ``adapter.stop`` or ``adapter.exit`` is executed, the loop in the thread is terminated after the next read
    from the original stdin; ``sys.stdin`` and ``kbhit`` is reset after the full read from the adapter; this requires
    the execution of ``adapter.get`` until an ``EOFError`` is raised!. Immediate abort of the reading process from the
    original stdin is not possible. **Note** that executing ``adapter.exit`` or leaving the contextmanager (``with``)
    also resets the emulator's modifications (if the parameter `mod` was set to ``True``), which can cause stdin to
    block the reading process until the next newline. The context manager also stops the thread as described below when
    exiting.

    :raises RecursionError: if sys.stdin is already adapted.
    """

    class _Buffer(TextIO, ABC):
        stdin_adapter: StdinAdapter

        def __init__(self, stdin_adapter: StdinAdapter):
            self.stdin_adapter = stdin_adapter

        def fileno(self) -> int:
            """_stdin_.buffer.fileno()"""
            return StdinAdapter._stdin_.buffer.fileno()

        def flush(self) -> None:
            """_stdin_.buffer.flush()"""
            StdinAdapter._stdin_.buffer.flush()

        def isatty(self) -> bool:
            """_stdin_.buffer.isatty()"""
            return StdinAdapter._stdin_.buffer.isatty()

        def read(self, n: int) -> bytes:
            """stdin_adapter.get()"""
            return bytes().join(self.stdin_adapter.get() for _ in range(n))

        def readable(self) -> bool:
            """``True``"""
            return True

        def writable(self) -> bool:
            """``False``"""
            return False

    class _Semaphore:

        _cond: Condition
        _value: int

        def __init__(self):
            self._cond = Condition(Lock())
            self._value = 0

        def _add(self) -> None:
            with self._cond:
                self._value += 1
                self._cond.notify()

        def _sub(self):
            with self._cond:
                while self._value == 0:
                    self._cond.wait(None)
                else:
                    self._value -= 1

        def _wait(self, timeout: float):
            rc = False
            endtime = None
            with self._cond:
                while self._value == 0:
                    if endtime is None:
                        endtime = monotonic() + timeout
                    else:
                        timeout = endtime - monotonic()
                        if timeout <= 0:
                            break
                    self._cond.wait(timeout)
                else:
                    rc = True
            return rc

        def value(self) -> int:
            """number of bytes in the pipe"""
            return self._value

        def poll(self) -> poll:
            """whether bytes in the pipe"""
            return bool(self._value)

    modblock: ModItem | ModItemsHandle | ModDummy
    modecho: ModItem | ModDummy

    _stdin_: TextIO[str] = sys.stdin
    _pipe: _Pipe
    keepalive: bool
    __semaphore__: _Semaphore
    _buffer: _Buffer

    def __init__(self, mod: bool = True):
        if isinstance(sys.stdin, StdinAdapter):
            raise RecursionError('sys.stdin is already adapted')
        Thread.__init__(self, daemon=True)
        self.__semaphore__ = self._Semaphore()
        self._pipe = _Pipe()
        self._buffer = self._Buffer(self)

        if mod:
            self.modblock = mod_nonblock()
            self.modecho = mod_nonecho()
        else:
            self.modblock = ModDummy()
            self.modecho = ModDummy()

        self.start()

    @property
    def buffer(self) -> _Buffer:
        return self._buffer

    def run(self) -> None:
        """
        Read continuously from stdin while ``self.keepalive`` is ``True`` and put the read characters into a pipe.
        Block in the reading process until a character can be read.
        """
        while self.keepalive:
            self._pipe.send_bytes(self._stdin_.buffer.read(1))
            self.__semaphore__._add()

    def kbhit(self) -> bool:
        """:return: Whether a character is in the pipe or in stdin to get."""
        return self.__semaphore__.poll() or _kbhit() or self._pipe.poll()

    def _get(self, block: bool = True) -> bytes:
        """:raise EOFError: stopped and empty (see exit / stop)"""
        if block or self.kbhit():
            try:
                return self._pipe.recv_bytes()
            finally:
                self.__semaphore__._sub()
        else:
            return b''

    def get(self, block: bool = True) -> bytes:
        """
        Get a character from the buffer pipe of the adapter, `block` until a character is present or return ``b''``
        immediately if none is present.

        :raise EOFError: The adapter has been marked for termination and the buffer is empty
          (``sys.stdin`` and ``kbhit`` being reset).
        """
        return self._get(block)

    def stop(self) -> None:
        """
        Stop the thread loop after the next read from stdin (blocks).
        Reset ``sys.stdin`` and ``kbhit`` after everything has been read from the buffer of the adapter;
        this requires the execution of ``adapter.get`` until an ``EOFError`` is raised!
        """
        if self.keepalive:
            self.keepalive = False

            def _finget(block: bool = True) -> bytes:
                if self.__semaphore__.poll() or self._pipe.poll():
                    try:
                        return self._pipe.recv_bytes()
                    finally:
                        self.__semaphore__._sub()
                elif self.is_alive():
                    if block:
                        try:
                            return self._pipe.recv_bytes()
                        finally:
                            self.__semaphore__._sub()
                    else:
                        return b''
                else:
                    global kbhit
                    kbhit = _kbhit
                    sys.stdin = self._stdin_
                    raise EOFError

            global kbhit
            self.get = _finget
            kbhit = lambda: True

    def start(self) -> None:
        """[Re-]Start the thread loop and overwrite ``sys.stdin`` and ``kbhit``."""
        global kbhit
        kbhit = self.kbhit
        sys.stdin = self
        self.keepalive = True
        self.get = self._get
        super().start()

    def exit(self):
        """
        [ Reset the emulator modifications and ] stop the thread loop after the next read from stdin (blocks).
        **Note** that if `mod` was set to ``True`` the read process of stdin is blocked not only until the next
        character but until the next line break. Reset ``sys.stdin`` and ``kbhit`` after everything has been read
        from the buffer of the adapter; this requires the execution of ``adapter.get`` until an ``EOFError`` is raised!
        """
        self.stop()
        self.modblock.reset()
        self.modecho.reset()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()

    def fileno(self) -> int:
        """_stdin_.fileno()"""
        return self._stdin_.fileno()

    def flush(self) -> None:
        """_stdin_.flush()"""
        self._stdin_.flush()

    def isatty(self) -> bool:
        """_stdin_.isatty()"""
        return self._stdin_.isatty()

    def read(self, n: int) -> str:
        """adapter.get()"""
        return bytes().join(self.get() for _ in range(n)).decode()

    def readable(self) -> bool:
        """``True``"""
        return True

    def writable(self) -> bool:
        """``False``"""
        return False

    def clear(self) -> None:
        """drain the adapter buffer pipe"""
        while self.kbhit():
            self.get(False)

    @property
    def mode(self) -> str:
        return "r"

    @property
    def name(self) -> str:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    @property
    def closed(self) -> bool:
        raise NotImplementedError

    def readline(self, __limit: int = ...) -> AnyStr:
        raise NotImplementedError

    def readlines(self, __hint: int = ...) -> list[AnyStr]:
        raise NotImplementedError

    def seek(self, __offset: int, __whence: int = ...) -> int:
        raise NotImplementedError

    def seekable(self) -> bool:
        raise NotImplementedError

    def tell(self) -> int:
        raise NotImplementedError

    def truncate(self, __size: int | None = ...) -> int:
        raise NotImplementedError

    def write(self, __s: AnyStr) -> int:
        raise NotImplementedError

    def writelines(self, __lines: Iterable[AnyStr]) -> None:
        raise NotImplementedError

    def __next__(self) -> AnyStr:
        raise NotImplementedError

    def __iter__(self) -> Iterator[AnyStr]:
        raise NotImplementedError


class SpamHandle:
    """
    A handler (callable) for repeated input.

    Applied inside ``run`` in ``Input`` and executed with the input object and the pipe.

    Inside ``__call__``, an input is discarded if it was made within `spamtime`, it is equal to the previous input,
    and the counter is equal to `spammax`.

    If pipe is empty when called, the query is skipped, the item is placed in the pipe, and the handler is reset;
    even if a spam condition is false.

    The corresponding methods (``in_spamtime`` and ``else_``) are swapped out of ``__call__``,
    for targeted modification in inheritances.

    :param spammax: The maximum number of identical entries that will be entered with the spam cadence.
    :param spamtime: Defines the spam cadence in seconds.
    """

    prev_char: Char | Key | Mouse | Reply | EscSegment | ManualESC | None
    spammax: int
    count: int
    time: int
    spamtime: int

    def __init__(self, spammax: int = 0, spamtime: float = .4):
        self.prev_char = None
        self.spammax = spammax
        self.count = 0
        self.spamtime = int(spamtime * 1_000_000_000)
        self.time = monotonic_ns()

    def __call__(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC, pipe: _Pipe) -> bool:
        t = monotonic_ns()
        try:
            if not pipe.poll():
                return self.else_(char, pipe)
            elif t - self.time < self.spamtime:
                if self.prev_char == char:
                    return self.in_spamtime(char, pipe)
                else:
                    return self.else_(char, pipe)
            else:
                return self.else_(char, pipe)
        finally:
            self.time = t

    def send(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC, pipe: _Pipe) -> bool:
        return self.__call__(char, pipe)

    def else_(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC, pipe: _Pipe) -> bool:
        """Executed when the `pipe` is empty, the input is not in spam time or the current item is
        different from the previous one."""
        self.reset(char)
        pipe.send(char)
        return True

    def in_spamtime(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC, pipe: _Pipe) -> bool:
        """Executed when the input is in the spam time and the current item is equal to the previous one."""
        if self.count != self.spammax:
            self.count += 1
            pipe.send(char)
            return True
        else:
            return False

    def reset(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC) -> None:
        self.prev_char = char
        self.count = 0


class SpamHandleNicer(SpamHandle):
    """Derived from :class:`SpamHandle`, modified in such a way that the repeated input of the defined types with
    the spam cadence is always discarded, except the pipe is empty."""

    _nice: tuple[Type[Char | Key | Mouse | Reply | EscSegment | ManualESC]]

    def __init__(self, *must_nice: Type[Char | Key | Mouse | Reply | EscSegment | ManualESC],
                 spammax: int = 0, spamtime: float = .4):
        SpamHandle.__init__(self, spammax, spamtime)
        self._nice = must_nice

    def in_spamtime(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC, pipe: _Pipe) -> bool:
        if not isinstance(char, self._nice):
            return super().in_spamtime(char, pipe)
        else:
            return False


class SpamHandleRestrictive(SpamHandle):
    """Derived from :class:`SpamHandle`, modified in such a way that the input of the defined types requires an
    empty pipe."""

    _excl: tuple[Type[Char | Key | Mouse | Reply | EscSegment | ManualESC]]

    def __init__(self, *exclusive: Type[Char | Key | Mouse | Reply | EscSegment | ManualESC],
                 spammax: int = 0, spamtime: float = .4):
        SpamHandle.__init__(self, spammax, spamtime)
        self._excl = exclusive

    def __call__(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC, pipe: _Pipe) -> bool:
        t = monotonic_ns()
        try:
            if not pipe.poll():
                return self.else_(char, pipe)
            elif not isinstance(char, self._excl):
                if t - self.time < self.spamtime:
                    if self.prev_char == char:
                        return self.in_spamtime(char, pipe)
                return self.else_(char, pipe)
            else:
                return False
        finally:
            self.time = t


class SpamHandleOne(SpamHandle):
    """Derived from :class:`SpamHandle`, modified in such a way that all input is discarded except when
    the pipe is empty."""

    def __call__(self, char: Char | Key | Mouse | Reply | EscSegment | ManualESC, pipe: _Pipe) -> bool:
        if not pipe.poll():
            pipe.send(char)
            return True
        else:
            return False


class Input(Thread):
    """
    This class provides methods to read from stdin. The :class:`MainInterpreter` is accessible via ``__interpreter__``.
    Can be started as a daemon thread to pipe the input in the background during a loop.

    Manual entry of escape sequences will cause blocking until it is
    completed correctly (may cause errors if the sequence is informal).

    The emulator is modified accordingly (nonblock & nonecho) for usage if the parameter `mod` is set to ``True``
    (default). The value ``reset_atexit`` in the :class:`ModItem`'s is ``True`` by default to reset the modifications
    to the emulator when exiting the Python interpreter.

    Can be used as a contextmanager/suit (``with``): [ resets the emulator modifications (`mod`) and ] stops the thread 
    loop on exit. **Note** that if `thread_block` is ``True``, the reading process in the thread blocks even after 
    exiting until the next character; in combination with `mod` it blocks even until the next line break!

    Spam handlers works most reactively in combination with `thread_block`.
    For more information see the :class:`SpamHandle`, :class:`SpamHandleNicer`, :class:`SpamHandleRestrictive`
    and :class:`SpamHandleOne`.

    :param thread_smoothness: specifies the time value for how many seconds to wait in a thread iteration.
    :param thread_block: enables blocked reading of stdin in the thread (thread_smoothness is ignored in this case).
    :param thread_spam: optional handler for repeated inputs.
    :param mod: modifies the emulator accordingly if is True (nonblock and nonecho).
    """

    _pipe: _Pipe
    modblock: ModItem | ModItemsHandle | ModDummy
    modecho: ModItem | ModDummy
    t_smoothness: float
    t_block: bool
    t_spam: SpamHandle | Callable
    t_keepalive: bool
    __interpreter__: MainInterpreter

    def __init__(self, thread_smoothness: float | bool = .03, thread_block: bool = False,
                 thread_spam: SpamHandle | None = SpamHandle(),
                 mod: bool = True):
        Thread.__init__(self, daemon=True)
        self._pipe = _Pipe()
        if mod:
            self.modblock = mod_nonblock()
            self.modecho = mod_nonecho()
        else:
            self.modblock = ModDummy()
            self.modecho = ModDummy()
        self.t_smoothness = float(thread_smoothness)
        self.t_block = thread_block
        self.t_spam = thread_spam or (lambda c, p: not p.send(c))
        self.t_keepalive = True
        self.__interpreter__ = MainInterpreter()

    @staticmethod
    def kbhit() -> bool:
        """:return: whether stdin [ adapter ] is waiting to be read."""
        return kbhit()

    def getch(self, block: bool = False) -> Char | Key | Mouse | Reply | EscSegment:
        """
        Read an input from stdin and complete sequential inputs (UTF8 sequence / escape sequences).
        Block until an input can be read if `block` is True, otherwise return :class:`Char`\\ ('') if nothing can be
        read.
        """
        return getch(block, self.__interpreter__)

    def read(
            self, get: bool = True, block: bool = True, smoothness: float = .0, flush_io: bool = False
    ) -> Char | Key | Mouse | Reply | EscSegment | None:
        """
        Flush stdin and stdout if `flush_io` is True. Then wait `smoothness` seconds before reading from stdin
        (`block` is forwarded to ``self.getch``). Return the read object if `get` is ``True``, otherwise put it in the
        pipe.
        """
        if flush_io:
            flushio()
        sleep(smoothness)
        if _cr := self.getch(block=block):
            if get:
                return _cr
            else:
                self._pipe.send(_cr)
        elif get:
            return Char('')

    def pipe_get(
            self, block: bool = False
    ) -> Char | Key | Mouse | Reply | EscSegment:
        """
        Read an object from the pipe. Block until an object can be read if `block` is ``True``,
        otherwise return :class:`Char`\\ ('') if nothing can be read.
        """
        if not block and not self._pipe.poll():
            return Char('')
        return self._pipe.recv()

    def send(self, block: bool = False) -> bool:
        """
        Read with or without `block`\\ ing and put the object in the pipe.

        :return: Whether the input is putted to the pipe (see SpamHandlers).
        """
        if block:
            return self.t_spam(self.getch(block=True), self._pipe)
        elif _cr := self.getch(block=False):
            return self.t_spam(_cr, self._pipe)
        else:
            return False

    def run(self) -> None:
        """
        Read with or without blocking (``self.t_block``) while ``self.t_keepalive`` is ``True`` and put the
        objects in the pipe. Wait ``self.t_smoothness`` seconds in an iteration if ``self.t_block`` is ``False``.
        """
        if self.t_block:
            while self.t_keepalive:
                self.t_spam(self.getch(block=True), self._pipe)
        elif self.t_smoothness:
            while self.t_keepalive:
                sleep(self.t_smoothness)
                if _cr := self.getch(block=False):
                    self.t_spam(_cr, self._pipe)
        else:
            while self.t_keepalive:
                if _cr := self.getch(block=False):
                    self.t_spam(_cr, self._pipe)

    def stop(self) -> None:
        """Stop the thread loop in ``self.run``."""
        self.t_keepalive = False

    def start(self, *, daemon: bool = True) -> None:
        """[Re-]Start the thread."""
        self.t_keepalive = True
        self.daemon = daemon
        super().start()

    def exit(self) -> None:
        """[ Reset the emulator modifications ] and stop the thread loop."""
        self.stop()
        self.modblock.reset()
        self.modecho.reset()

    def __enter__(self) -> Input:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.exit()


class InputSuper(Input):
    r"""
    Derived from :class:`Input`, modified in such a way that the manual input of escape sequences is recognized
    and supervised. Creates :class:`ManualESC`\ (intro=sequence) from manually entered escape sequences.
    Requires ``sys.stdin`` and ``io.kbhit`` to be modified via :class:`StdinAdapter`.

        >>> StdinAdapter()
        >>> [with] [var = ] InputSuper(...

    The emulator modification can be handled via the adapter instead of the input class. Therefore, the
    contextmanager/suit function is assiged to :class:`StdinAdapter`. On exit, the ``exit`` method of StdinAdapter
    is executed, and the own thread is then terminated by the raised ``EOFError``.

    Additional parameters:
        `manual_esc_tt` (typing time): sets the time allowed between keystrokes.
         (Note: if the parameter is ``0``, pressing esc will create ``<ManualESC(intro="\x1b")> == ManualESC()``
         immediately.

        `manual_esc_interpreter`: use the interpreters also for manually entered escape sequences.

        `manual_esc_finals`: defines the final characters with which to end an escape sequence.
         (Is by default the operating system independent input of Enter or ESC).
    """
    me_finals: tuple[int | tuple[int, int]]
    me_tt = float
    _me_inter: Callable
    _adapter: StdinAdapter

    adapter_processing_tolerance: float = 0.002

    def __init__(self,
                 thread_smoothness: float | bool = .03, thread_block: bool = False,
                 thread_spam: SpamHandle | None = SpamHandle(),
                 manual_esc_tt: float = .8,
                 manual_esc_interpreter: bool = False,
                 manual_esc_finals: tuple[int | tuple[int, int], ...] | None = (0xa, 0xd, 0x1b),  # \n \r ESC
                 ):
        if not isinstance(sys.stdin, StdinAdapter):
            raise EnvironmentError('sys.stdin is not adapted -- initialize io.StdinAdapter')
        self._adapter = sys.stdin
        Input.__init__(self, thread_smoothness, thread_block, thread_spam, mod=False)

        self.me_finals = manual_esc_finals or ()
        self.me_tt = manual_esc_tt

        if manual_esc_interpreter:
            def me_interpreter(inter):
                sys.stdin: StdinAdapter
                try:
                    while True:
                        if self.kbhit():
                            inter <<= sys.stdin.get()
                        elif sys.stdin.__semaphore__._wait(self.me_tt):
                            inter <<= sys.stdin.get()
                        else:
                            _seq = inter.buffer
                            inter._reset()
                            return ManualESC(_seq.decode())
                        if self.__interpreter__.isdone(inter):
                            return inter
                        elif inter._buffer and isFinal(inter._buffer[-1:], self.me_finals):
                            _seq = inter.buffer
                            inter._reset()
                            return ManualESC(_seq.decode())
                except:
                    _seq = inter.buffer
                    inter._reset()
                    return ManualESC(_seq.decode())
        else:
            def me_interpreter(inter):
                sys.stdin: StdinAdapter
                seq = inter.buffer
                inter._reset()
                while True:
                    if self.kbhit():
                        seq += sys.stdin.get()
                    elif sys.stdin.__semaphore__._wait(self.me_tt):
                        seq += sys.stdin.get()
                    else:
                        return ManualESC(seq.decode())
                    if seq and isFinal(seq[-1:], self.me_finals):
                        return ManualESC(seq.decode())

        self._me_inter = me_interpreter

    def run(self) -> None:
        """
        Read with or without blocking (``self.t_block``) while ``self.t_keepalive`` is ``True`` and put the
        objects in the pipe. Wait ``self.t_smoothness`` seconds in an iteration if ``self.t_block`` is ``False``.

        Recognize and supervise manual input of esc.
        """
        try:
            super().run()
        except EOFError:
            self.t_keepalive = False

    def getch(self, block: bool = False) -> Char | Key | Mouse | Reply | EscSegment | ManualESC:
        """
        Get a character from the stdin adapter, complete sequential input (UTF8 sequence / escape sequences)
        but recognize and supervise manual input of esc. Block until an input can be read if block is ``True``,
        otherwise return :class:`Char`\\ ('') if nothing can be read.

        :raise AttributeError: sys.stdin was reset to the origin.
        :raise EOFError: StdinAdapter was marked to finish and is empty.
        """
        sys.stdin: StdinAdapter
        if not block and not self.kbhit():
            return Char('')
        seq = self.__interpreter__(sys.stdin.get())
        while True:
            if self.__interpreter__.isdone(seq):
                return seq
            elif self.kbhit():
                seq <<= sys.stdin.get()
            elif sys.stdin.__semaphore__._wait(self.adapter_processing_tolerance):
                seq <<= sys.stdin.get()
            else:
                return self._me_inter(seq)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._adapter.exit()
