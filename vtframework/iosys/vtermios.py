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

from typing import Literal, TextIO, Callable, Any
from sys import platform, stdout, stdin
import atexit

from vtframework.iodata.keys import Ctrl, DelIns


if platform != "win32":
    import termios

    STDIN_STREAM: TextIO = stdin
    STDIN_FILENO: int = stdin.fileno()
    STDOUT_STREAM: TextIO = stdout
    STDOUT_FILENO: int = stdout.fileno()

    INAPPROPRIATE_DEVICE_VALUE: int = 25

    # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html


    def __get_handle(fileno: int) -> int:
        return fileno


    def __get_flags(handle: int) -> list[int, int, int, int, int, int, list[bytes]] | int:
        try:
            return termios.tcgetattr(handle)
        except Exception as e:
            raise EnvironmentError(*e.args)


    def __enable_flags(handle: int, flags: list[int, int, int, int, int, int, list[bytes]] | int, when: int = termios.TCSANOW
                       ) -> None:
        try:
            termios.tcsetattr(handle, when, flags)
        except Exception as e:
            raise EnvironmentError(*e.args)

    
    def __get_flag(flags: list[int, int, int, int, int, int, list[bytes]] | int,
                   on: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']
                   ) -> int:
        if on[-1] in 'CQS\\':
            flg = flags[-1][{'C': termios.VINTR, 'Q': termios.VSTART, 'S': termios.VSTOP, '\\': termios.VQUIT}[on[-1]]]
            try:
                return ord(flg)
            except TypeError:
                return flg
        else:
            return flags[{'in': 0, 'out': 1, 'ctrl': 2, 'local': 3}[on]]
        
    
    def __set_cc(__chr: int | Ctrl | DelIns | bytes | None, flags: list[int, int, int, int, int, int, list[bytes]] | int,
                 on: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']
                 ) -> list[int, int, int, int, int, int, list[bytes]] | int:
        if not __chr:
            __chr = 0
        elif isinstance(__chr, DelIns):
            __chr = 127
        elif isinstance(__chr, Ctrl):
            __chr = Ctrl.MOD
        flags[-1][{'C': termios.VINTR, 'Q': termios.VSTART, 'S': termios.VSTOP, '\\': termios.VQUIT}[on[-1]]] = __chr
        return flags


    def __add_flag(__add: int, flags: list[int, int, int, int, int, int, list[bytes]] | int,
                   on: Literal['in', 'out', 'ctrl', 'local']
                   ) -> list[int, int, int, int, int, int, list[bytes]] | int:
        flags[{'in': 0, 'out': 1, 'ctrl': 2, 'local': 3}[on]] |= __add
        return flags


    def __sub_flag(__rm: int, flags: list[int, int, int, int, int, int, list[bytes]] | int,
                   on: Literal['in', 'out', 'ctrl', 'local']
                   ) -> list[int, int, int, int, int, int, list[bytes]] | int:
        flags[{'in': 0, 'out': 1, 'ctrl': 2, 'local': 3}[on]] &= ~__rm
        return flags


    def __is_set(__val: int | Ctrl | DelIns | bytes | None, flags: list[int, int, int, int, int, int, list[bytes]] | int,
                 on: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']
                 ) -> bool:
        if on[-1] in 'CQS\\':
            if not __val:
                __val = 0
            elif isinstance(__val, DelIns):
                __val = 127
            elif isinstance(__val, Ctrl):
                __val = Ctrl.MOD
            elif isinstance(__val, bytes):
                __val = ord(__val)
            return __get_flag(flags, on) == __val
        else:
            return (flag := __get_flag(flags, on)) == (flag | __val)


    def check_build(__build: int = ...) -> None:
        return


    def add_flag(fileno: int,
                 mod_value: int | Ctrl | DelIns | bytes | None,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'],
                 mod_when: int = termios.TCSANOW,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem:
        mod = ModItem(fileno, mod_value, mod_targ, mod_when, reset_atexit=reset_atexit, note=note)
        mod.add_flag()
        return mod


    def sub_flag(fileno: int,
                 mod_value: int,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local'],
                 mod_when: int = termios.TCSANOW,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem:
        mod = ModItem(fileno, mod_value, mod_targ, mod_when, reset_atexit=reset_atexit, note=note)
        mod.sub_flag()
        return mod


    def request(fileno: int,
                mod_value: int | Ctrl | DelIns | bytes | None,
                mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...) -> bool:
        return __is_set(mod_value, __get_flags(__get_handle(fileno)), mod_targ)


    def mod_ansiin() -> ModDummy | ModItem:
        return ModDummy()


    def mod_ansiout() -> ModDummy | ModItem:
        return ModDummy()


    def mod_nonecho() -> ModItem:
        try:
            return sub_flag(STDIN_FILENO, termios.ECHO, 'local', note='ECHO')
        except RecursionError as r:
            mi = ModItem.from_recursion(r)
            mi.sub_flag()
            return mi


    def mod_nonblock() -> ModItemsHandle | ModItem:
        try:
            return sub_flag(STDIN_FILENO, termios.ICANON, 'local', note='ICANON')
        except RecursionError as r:
            mi = ModItem.from_recursion(r)
            mi.sub_flag()
            return mi


    def mod_nonprocess() -> ModItemsHandle | ModItem:
        try:
            isig = sub_flag(STDIN_FILENO, termios.ISIG, 'local', note='ISIG')
        except RecursionError as r:
            isig = ModItem.from_recursion(r)
            isig.sub_flag()
        try:
            ixon = sub_flag(STDIN_FILENO, termios.IXON, 'in', note='IXON')
        except RecursionError as r:
            ixon = ModItem.from_recursion(r)
            ixon.sub_flag()
        return ModItemsHandle(isig, ixon)


    def mod_nonimpldef() -> ModItemsHandle | ModDummy:
        try:
            out = sub_flag(STDOUT_FILENO, termios.OPOST, 'out', note='OPOST')
        except RecursionError as r:
            out = ModItem.from_recursion(r)
            out.sub_flag()
        try:
            in_ = sub_flag(STDIN_FILENO, termios.IEXTEN, 'in', note='IEXTEN')
        except RecursionError as r:
            in_ = ModItem.from_recursion(r)
            in_.sub_flag()
        return ModItemsHandle(in_, out)


else:
    import ctypes
    from ctypes import wintypes
    from sys import getwindowsversion

    KERNEL32 = ctypes.windll.kernel32

    STDIN_STREAM: TextIO = stdin
    STDIN_FILENO: int = -10
    STDOUT_STREAM: TextIO = stdout
    STDOUT_FILENO: int = -11

    INAPPROPRIATE_DEVICE_VALUE: int = 6
    INVALID_HANDLE_VALUE: int = -1

    # https://docs.microsoft.com/en-us/windows/console/setconsolemode
    # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h

    # input flags
    CMD_ENABLE_PROCESSED_INPUT: int = 0x0001
    CMD_ENABLE_LINE_INPUT: int = 0x0002
    CMD_ENABLE_ECHO_INPUT: int = 0x0004
    CMD_ENABLE_WINDOW_INPUT: int = 0x0008
    CMD_ENABLE_MOUSE_INPUT: int = 0x0010
    CMD_ENABLE_INSERT_MODE: int = 0x0020
    CMD_ENABLE_QUICK_EDIT_MODE: int = 0x0040
    CMD_ENABLE_EXTENDED_FLAGS: int = 0x0080
    CMD_ENABLE_AUTO_POSITION: int = 0x0100
    CMD_ENABLE_VIRTUAL_TERMINAL_INPUT: int = 0x0200

    # output flags
    CMD_ENABLE_PROCESSED_OUTPUT: int = 0x0001
    CMD_ENABLE_WRAP_AT_EOL_OUTPUT: int = 0x0002
    CMD_ENABLE_VIRTUAL_TERMINAL_PROCESSING: int = 0x0004
    CMD_DISABLE_NEWLINE_AUTO_RETURN: int = 0x0008
    CMD_ENABLE_LVB_GRID_WORLDWIDE: int = 0x0010

    # https://docs.microsoft.com/en-us/windows/wsl/release-notes#build-16257
    ENABLE_VIRTUAL_TERMINAL_BUILD_REQUIRED: int = 16257


    def __get_handle(fileno: int) -> int:
        if (handle := KERNEL32.GetStdHandle(fileno)) == INVALID_HANDLE_VALUE:
            raise EnvironmentError(KERNEL32.GetLastError(), 'KERNEL32.GetStdHandle returned INVALID_HANDLE_VALUE')
        return handle


    def __get_flags(handle: int) -> list[int, int, int, int, int, int, list[bytes]] | int:
        out = wintypes.DWORD()
        if not KERNEL32.GetConsoleMode(handle, ctypes.byref(out)):
            raise EnvironmentError(KERNEL32.GetLastError(), 'KERNEL32.GetConsoleMode failed')
        return out.value


    def __enable_flags(handle: int, flags: list[int, int, int, int, int, int, list[bytes]] | int, when: int = ...
                       ) -> None:
        if not KERNEL32.SetConsoleMode(handle, flags):
            raise EnvironmentError(KERNEL32.GetLastError(), 'KERNEL32.SetConsoleMode failed')


    def __get_flag(flags: list[int, int, int, int, int, int, list[bytes]] | int,
                   on: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...
                   ) -> int:
        return flags


    def __set_cc(__chr: int | Ctrl | DelIns | bytes | None = ...,
                 flags: list[int, int, int, int, int, int, list[bytes]] | int = ...,
                 on: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...
                 ) -> list[int, int, int, int, int, int, list[bytes]] | int:
        return flags


    def __add_flag(__add: int, flags: list[int, int, int, int, int, int, list[bytes]] | int,
                   on: Literal['in', 'out', 'ctrl', 'local'] = ...
                   ) -> list[int, int, int, int, int, int, list[bytes]] | int:
        return flags | __add


    def __sub_flag(__rm: int, flags: list[int, int, int, int, int, int, list[bytes]] | int,
                   on: Literal['in', 'out', 'ctrl', 'local'] = ...
                   ) -> list[int, int, int, int, int, int, list[bytes]] | int:
        return flags & ~__rm


    def __is_set(__val: int | Ctrl | DelIns | bytes | None, flags: list[int, int, int, int, int, int, list[bytes]] | int,
                 on: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...
                 ) -> bool:
        return flags == (flags | __val)


    def check_build(__build: int) -> None:
        if (build := getwindowsversion().build) < __build:
            raise EnvironmentError(None, 'Build verification failed', build)


    def add_flag(fileno: int,
                 mod_value: int | Ctrl | DelIns | bytes | None,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...,
                 mod_when: int = ...,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem:
        mod = ModItem(fileno, mod_value, mod_targ, mod_when, reset_atexit=reset_atexit, note=note)
        mod.add_flag()
        return mod


    def sub_flag(fileno: int,
                 mod_value: int,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local'] = ...,
                 mod_when: int = ...,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem:
        mod = ModItem(fileno, mod_value, mod_targ, mod_when, reset_atexit=reset_atexit, note=note)
        mod.sub_flag()
        return mod


    def request(fileno: int,
                mod_value: int | Ctrl | DelIns | bytes | None,
                mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...) -> bool:
        return __is_set(mod_value, __get_flags(__get_handle(fileno)), mod_targ)


    def mod_ansiin() -> ModDummy | ModItem:
        check_build(ENABLE_VIRTUAL_TERMINAL_BUILD_REQUIRED)
        try:
            return add_flag(STDIN_FILENO, CMD_ENABLE_VIRTUAL_TERMINAL_INPUT, note='ENABLE_VIRTUAL_TERMINAL_INPUT')
        except RecursionError as r:
            mi = ModItem.from_recursion(r)
            mi.add_flag()
            return mi


    def mod_ansiout() -> ModDummy | ModItem:
        check_build(ENABLE_VIRTUAL_TERMINAL_BUILD_REQUIRED)
        try:
            return add_flag(STDOUT_FILENO, CMD_ENABLE_VIRTUAL_TERMINAL_PROCESSING, note='ENABLE_VIRTUAL_TERMINAL_PROCESSING')
        except RecursionError as r:
            mi = ModItem.from_recursion(r)
            mi.add_flag()
            return mi


    def mod_nonecho() -> ModItem:
        try:
            mi_echo = sub_flag(STDIN_FILENO, CMD_ENABLE_ECHO_INPUT, note='ENABLE_ECHO_INPUT')
            return mi_echo
        except RecursionError as r:
            mi = ModItem.from_recursion(r)
            mi.sub_flag()
            return mi


    def mod_nonblock() -> ModItemsHandle | ModItem:
        mi_echo = mod_nonecho()
        try:
            return ModItemsHandle(mi_echo, sub_flag(STDIN_FILENO, CMD_ENABLE_LINE_INPUT, note='ENABLE_LINE_INPUT'))
        except RecursionError as r:
            mi_block = ModItem.from_recursion(r)
            mi_block.sub_flag()
            return ModItemsHandle(mi_echo, mi_block)


    def mod_nonprocess() -> ModItemsHandle | ModItem:
        try:
            return sub_flag(STDIN_FILENO, CMD_ENABLE_PROCESSED_INPUT, note='ENABLE_PROCESSED_INPUT')
        except RecursionError as r:
            mi = ModItem.from_recursion(r)
            mi.sub_flag()
            return mi


    def mod_nonimpldef() -> ModItemsHandle:
        try:
            mi_ext = add_flag(STDIN_FILENO, CMD_ENABLE_EXTENDED_FLAGS, note='CMD_ENABLE_EXTENDED_FLAGS')
        except RecursionError as r:
            mi_ext = ModItem.from_recursion(r)
            mi_ext.sub_flag()
        try:
            mi_qui = sub_flag(STDIN_FILENO, CMD_ENABLE_QUICK_EDIT_MODE, note='CMD_ENABLE_QUICK_EDIT_MODE')
        except RecursionError as r:
            mi_qui = ModItem.from_recursion(r)
            mi_qui.sub_flag()
        return ModItemsHandle(mi_ext, mi_qui)


    def regedit_permanent_virtual_terminal_level_syscommand(value: Literal[0, 1]) -> str:
        return f'REG ADD HKCU\CONSOLE /f /v VirtualTerminalLevel /t REG_DWORD /d {value}'


_get_handle = __get_handle
_get_flags = __get_flags
_enable_flags = __enable_flags
_get_flag = __get_flag
_set_cc = __set_cc
_add_flag = __add_flag
_sub_flag = __sub_flag
_is_set = __is_set


class InappropriateDeviceHandler:
    action: Callable[[Exception], Any]
    other_action: Callable[[Exception], Any]

    @staticmethod
    def _raise(exc: Exception):
        raise EnvironmentError(*exc.args).with_traceback(exc.__traceback__)

    def __init__(self,
                 action: Callable[[Exception], Any] = _raise,
                 other_action: Callable[[Exception], Any] = _raise):
        self.action = action
        self.other_action = other_action

    @staticmethod
    def is_inappropriatedeverr(exc: Exception) -> bool:
        return (val := exc.args) and val[0] == INAPPROPRIATE_DEVICE_VALUE

    def handle(self, exc: Exception) -> Any:
        if self.is_inappropriatedeverr(exc):
            return self.action(exc)
        else:
            return self.other_action(exc)

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> Any:
        if exc_val:
            return self.handle(exc_val)


__ModItemsCache__: list[ModItem] = list()

__ORIGIN_FLAGS__: dict[int, list[int, int, int, int, int, int, list[bytes]] | int] = dict()


class ModItem:
    fileno: int
    mod_value: int
    mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']
    mod_when: int
    reset_atexit: bool
    _before_reset_atexit: tuple[Callable[[], Any]]
    note: Any
    origin_state: bool
    _set_: Callable[[], None]
    _rm_: Callable[[], None]
    _hash: int

    def __init__(self,
                 fileno: int,
                 mod_value: int | Ctrl | DelIns | bytes | None,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...,
                 mod_when: int = ...,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None):

        self.fileno = fileno
        self.mod_value = mod_value
        self.mod_targ = mod_targ
        self.mod_when = mod_when

        handle = _get_handle(fileno)
        origin_flags = _get_flags(handle)

        if isinstance(mod_targ, str) and mod_targ[-1] in 'CQS\\':
            if not mod_value:
                mod_value = 0
            elif isinstance(mod_value, Ctrl):
                mod_value = mod_value.MOD
            elif isinstance(mod_value, DelIns):
                mod_value = 127
            else:
                mod_value = ord(mod_value)

            origin_val = _get_flag(origin_flags, mod_targ)

            def _set() -> None:
                _enable_flags(handle,
                              _set_cc(mod_value, _get_flags(handle), mod_targ),
                              mod_when)

            def _rm() -> None:
                _enable_flags(handle,
                              _set_cc(origin_val, _get_flags(handle), mod_targ),
                              mod_when)
        else:

            def _set() -> None:
                _enable_flags(handle,
                              _add_flag(mod_value, _get_flags(handle), mod_targ),
                              mod_when)

            def _rm() -> None:
                _enable_flags(handle,
                              _sub_flag(mod_value, _get_flags(handle), mod_targ),
                              mod_when)

        self._set_, self._rm_ = _set, _rm

        self._hash = hash((fileno, mod_value, mod_targ))
        self.note = note

        try:
            raise RecursionError('Modification already available @ index: ', __ModItemsCache__.index(self))
        except ValueError:
            __ModItemsCache__.append(self)

        self.reset_atexit = reset_atexit
        atexit.register(self._reset_atexit)
        self._before_reset_atexit = tuple()

        self.origin_state = request(fileno, mod_value, mod_targ)

        __ORIGIN_FLAGS__.setdefault(fileno, origin_flags)

    @staticmethod
    def from_recursion(e: RecursionError) -> ModItem:
        return __ModItemsCache__[e.args[1]]

    @classmethod
    def instance(cls,
                 fileno: int,
                 mod_value: int | Ctrl | DelIns | bytes | None,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'] = ...,
                 mod_when: int = ...,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem:
        try:
            return cls(fileno, mod_value, mod_targ, mod_when, reset_atexit=reset_atexit, note=note)
        except RecursionError as e:
            return __ModItemsCache__[e.args[1]]

    def origin(self) -> bool | int:
        return self.origin_state

    def request(self) -> bool:
        return request(self.fileno, self.mod_value, self.mod_targ)

    def sub_flag(self) -> None:
        self._rm_()

    def add_flag(self) -> None:
        self._set_()

    def reset(self) -> None:
        if self.origin_state:
            self.add_flag()
        else:
            self.sub_flag()

    def purge(self) -> None:
        atexit.unregister(self._reset_atexit)
        self._exit()
        __ModItemsCache__.remove(self)

    def _exit(self) -> None:
        for f in reversed(self._before_reset_atexit):
            f()
        self.reset()

    def _reset_atexit(self) -> None:
        if self.reset_atexit:
            self._exit()

    def add_before_reset_atexit(self, func: Callable[[], Any]) -> None:
        self._before_reset_atexit += (func,)

    def __int__(self) -> int:
        return self.mod_value

    def __eq__(self, other: ModItem) -> bool:
        return self.__hash__() == other.__hash__()

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__} {repr(self.note)} " \
               f"({self.fileno} {self.mod_value} {self.mod_targ} {self.origin_state})>"


class ModItemsHandle(tuple[ModItem]):

    def __new__(cls, *args: ModItem) -> ModItemsHandle:
        return tuple.__new__(cls, args)

    def origin(self) -> tuple[bool, ...]:
        return tuple(itm.origin() for itm in self)

    def request(self) -> tuple[bool, ...]:
        return tuple(itm.request() for itm in self)

    def sub_flag(self) -> None:
        for itm in reversed(self):
            itm.rmflag()

    def add_flag(self) -> None:
        for itm in self:
            itm.add_flag()

    def reset(self) -> None:
        for itm in reversed(self):
            itm.reset()

    def purge(self) -> None:
        for itm in reversed(self):
            itm.purge()


class ModDummy:

    def __call__(self, *args, **kwargs) -> ModDummy:
        return self

    def __getattr__(self, *args, **kwargs) -> ModDummy:
        return self

    def __getattribute__(self, *args, **kwargs) -> ModDummy:
        return self

    def __getitem__(self, *args, **kwargs) -> ModDummy:
        return self

    def __iter__(self) -> ModDummy:
        return self

    def __next__(self) -> None:
        raise StopIteration

    def __len__(self) -> int:
        return 0

    def __bool__(self) -> bool:
        return False


def cache_purge() -> None:
    for itm in __ModItemsCache__.copy():
        itm.purge()
