from typing import Any, Callable, Literal, TextIO, overload
from vtframework.iodata.keys import Ctrl, DelIns

STDIN_STREAM: TextIO
STDIN_FILENO: int
STDOUT_STREAM: TextIO
STDOUT_FILENO: int
INAPPROPRIATE_DEVICE_VALUE: int


def __get_handle(fileno: int) -> int:
    """
    Return the handle for a stream by `fileno`.

    - @ **UNIX** :
        `fileno` :
            fileno from ``sys.stdin`` | ``sys.stdout`` | ``sys.stderr``

        ``return:`` fileno (int)

    - @ **Windows**:
        `fileno` :
            ``-10`` (stdin) | ``-11`` (stdout) | ``-12`` (stderr)

        ``return:`` handle (int)

        ``raise EnvironmentError:`` when GetStdHandle has returned -1
    """
@overload
def __get_flags(handle: int) -> int: ...
@overload
def __get_flags(handle: int) -> list[int, int, int, int, int, int, list[bytes]]:
    """
    Return the current values of the emulator.

    `handle` : handle from ``__get_handle``.

    - @ **UNIX** :
        ``return:`` [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]

        ``raise EnvironmentError:`` when termios raises an error. (gets the same args)

    - @ **Windows**:
        ``return:`` console mode.

        ``raise EnvironmentError:`` if GetConsoleMode returns False, value from GetLastError is in args[0].
    """
@overload
def __enable_flags(handle: int, flags: int) -> None: ...
@overload
def __enable_flags(handle: int, flags: list[int, int, int, int, int, int, list[bytes]], when: int) -> None:
    """
    Set the values of the emulator.

    `handle` : handle from ``__get_handle``.

    `flags` : values from ``__get_flags``.

    - @ **UNIX** :
        `when` :
            Default value is ``termios.TCSANOW``.

        ``raise EnvironmentError(termios error args):`` when termios raises an error.

    - @ **Windows**:
        ``raise EnvironmentError:`` if `SetConsoleMode` returns False, value from `GetLastError` is in args[0].
    """
@overload
def __get_flag(flags: int) -> int: ...
@overload
def __get_flag(flags: list[int, int, int, int, int, int, list[bytes]], on: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']) -> int:
    """
    Get the termios flag value from index `on`,

    `flags` must be the attribute list of ``__get_flags`` and `on` defines the index over ``"in"``, ``"out"``,
    ``"ctrl"``, ``"local"`` or can be defined over ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``
    as the index of a control character.

    The function always returns the numeric value as an integer and is a **pseudo function under Windows**.
    """
@overload
def __set_cc() -> int: ...
@overload
def __set_cc(__chr: int | Ctrl | DelIns | bytes | None, flags: list[int, int, int, int, int, int, list[bytes]] | int, on: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']) -> list[int, int, int, int, int, int, list[bytes]]:
    """
    Assign `__chr` to the control characters in `flags` on index `on` and return the modified attribute list.
    This is an **pseudo function under Windows**.

    `__chr` can be specified by a character in the range ``00-7f`` as a numeric value or bytestring,
    also control characters can be expressed by a :class:`Ctrl` object and backspace by a :class:`DelIns` object.
    ``None`` is used to disable the index.

    `flags` must be the attribute list from ``__get_flags`` and the index is determined via `on` by
    ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``.
    """
@overload
def __add_flag(__add: int, flags: int) -> int: ...
@overload
def __add_flag(__add: int, flags: list[int, int, int, int, int, int, list[bytes]], on: Literal['in', 'out', 'ctrl', 'local']) -> list[int, int, int, int, int, int, list[bytes]]:
    """
    Add a constant and return the new configuration.

    `flags` : values from ``__get_flags``

    - @ **UNIX** :
        `__add` :
            The constant. Should be chosen from module ``termios``.

        `on` :
            Specify the flag index over ``"in"``, ``"out"``, ``"ctrl"`` or ``"local"``.

        # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html

    - @ **Windows**:
        `__add` :
            The constant. Should be chosen from this module. (``CMD_`` prefix)

        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h
    """
@overload
def __sub_flag(__rm: int, flags: int) -> int: ...
@overload
def __sub_flag(__rm: int, flags: list[int, int, int, int, int, int, list[bytes]], on: Literal['in', 'out', 'ctrl', 'local']) -> list[int, int, int, int, int, int, list[bytes]]:
    """
    Remove a constant and return the new configuration.

    `flags` : values from ``__get_flags``.

    - @ **UNIX** :
        `__rm` :
            The constant. Should be chosen from module ``termios``.

        `on` :
            Specify the flag index over ``"in"``, ``"out"``, ``"ctrl"`` or ``"local"``.

        # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html

    - @ **Windows**:
        `__rm` :
            The constant. Should be chosen from this module. (``CMD_`` prefix)

        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h
    """
@overload
def __is_set(__val: int, flags: int) -> bool: ...
@overload
def __is_set(__val: int | Ctrl | DelIns | bytes | None, flags: list[int, int, int, int, int, int, list[bytes]], on: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']) -> bool: ...
@overload
def __is_set(__val: int, flags: list[int, int, int, int, int, int, list[bytes]], on: Literal['in', 'out', 'ctrl', 'local']) -> bool:
    """
    Return whether the emulator flags contain the modification value.

    `flags` : values from ``__get_flags``.

    - @ **UNIX** :
        `__val` :
            Depending on `on`, a constant must be selected from the module ``termios`` or parameterized as a control
            character. If `on` is ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``, the corresponding index of
            the control character is queried and `__val` can be specified by a character in the range ``00-7f`` as a
            numeric value or bytestring, also control characters can be expressed by a :class:`Ctrl` object and backspace
            by a :class:`DelIns` object; if `__val` is ``None`` in this request, it is queried whether the index is
            deactivated.

        `on` :
            Specify the flag index over ``"in"``, ``"out"``, ``"ctrl"``, ``"local"``;
            ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``.

        # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html

    - @ **Windows**:
        `__val` :
            The constant. Should be chosen from this module. (``CMD_`` prefix)

        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h
    """
@overload
def check_build() -> None: ...
@overload
def check_build(__build: int) -> None:
    """
    - @ **UNIX** :
        Do nothing.

    - @ **Windows**:
        Check if the Windows build is greater than or equal to `__build` and ``raise EnvironmentError`` is not.
        Is automatically called by the functions ``mod_ansiin`` and ``mod_ansiout`` with the value
        ``ENABLE_VIRTUAL_TERMINAL_BUILD_REQUIRED``.

        # https://docs.microsoft.com/en-us/windows/wsl/release-notes#build-16257
    """
@overload
def add_flag(fileno: int, mod_value: int, *, reset_atexit: bool = True, note: Any = None) -> ModItem: ...
@overload
def add_flag(fileno: int, mod_value: int | Ctrl | DelIns | bytes | None, mod_targ: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'], mod_when: int = ..., *, reset_atexit: bool = True, note: Any = None) -> ModItem: ...
@overload
def add_flag(fileno: int, mod_value: int, mod_targ: Literal['in', 'out', 'ctrl', 'local'], mod_when: int = ..., *, reset_atexit: bool = True, note: Any = None) -> ModItem:
    """
    Modify the emulator parameterization and return a :class:`ModItem`.

    - @ **UNIX** :
        `fileno` :
            fileno from ``sys.stdin`` | ``sys.stdout`` | ``sys.stderr``

        `mod_value` :
            Depending on `mod_targ`, a constant must be selected from the module ``termios`` or
            parameterized as a new control character.
            If `mod_targ` is ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``, the corresponding index of the
            control characters is set to `mod_value`, these can be specified by a character in the range ``00-7f`` as a
            numeric value or bytestring, also control characters can be expressed by a :class:`Ctrl` object and
            backspace by a :class:`DelIns` object; if `mod_value` is ``None``, the index is disabled.

        `mod_targ` :
            Specify the flag index over ``"in"``, ``"out"``, ``"ctrl"``, ``"local"``;
            ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``.

        `when` :
            Default value is ``termios.TCSANOW``.

        # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html

    - @ **Windows**:
        `fileno` :
            ``-10`` (stdin) | ``-11`` (stdout) | ``-12`` (stderr)

        `mod_value` :
            The constant. Should be chosen from this module. (``CMD_`` prefix)

        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h

    `reset_atexit` : reset the modification when leaving the python interpreter.

    `note` : attach a note to the item.

    ``raise RecursionError:`` if an item of the same modification is already in ``__ModItemsCache__``. Decisive attributes: `fileno`, `mod_value`, `mod_targ`.

    ``raise EnvironmentError:`` an error occurred during the modification.
    """
@overload
def sub_flag(fileno: int, mod_value: int, *, reset_atexit: bool = True, note: Any = None) -> ModItem: ...
@overload
def sub_flag(fileno: int, mod_value: int, mod_targ: Literal['in', 'out', 'ctrl', 'local'], mod_when: int = ..., *, reset_atexit: bool = True, note: Any = None) -> ModItem:
    """
    Modify the emulator parameterization and return a :class:`ModItem`.

    - @ **UNIX** :
        `fileno` :
            fileno from ``sys.stdin`` | ``sys.stdout`` | ``sys.stderr``

        `mod_value` :
            The constant. Should be chosen from module ``termios``.

        `mod_targ` :
            Specify the flag index over ``"in"``, ``"out"``, ``"ctrl"`` or ``"local"``.

        `when` : 
            Default value is ``termios.TCSANOW``.

        # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html

    - @ **Windows**:
        `fileno` :  
            ``-10`` (stdin) | ``-11`` (stdout) | ``-12`` (stderr)

        `mod_value` :
            The constant. Should be chosen from this module. (``CMD_`` prefix)
        
        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h

    ``reset_atexit :`` reset the modification when leaving the python interpreter.

    ``note :`` attach a note to the item.

    ``raise RecursionError:`` if an item of the same modification is already in ``__ModItemsCache__``. Decisive attributes: `fileno`, `mod_value`, `mod_targ`.

    ``raise EnvironmentError:`` an error occurred during the modification.
    """
@overload
def request(fileno: int, mod_value: int) -> bool: ...
@overload
def request(fileno: int, mod_value: int | Ctrl | DelIns | bytes | None, mod_targ: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']) -> bool: ...
@overload
def request(fileno: int, mod_value: int, mod_targ: Literal['in', 'out', 'ctrl', 'local']) -> bool:
    """
    Return whether the emulator flags contain the modification value.

    - @ **UNIX** :
        `fileno` :
            fileno from ``sys.stdin`` | ``sys.stdout`` | ``sys.stderr``

        `mod_value` :
            Depending on `mod_targ`, a constant must be selected from the module ``termios`` or parameterized as a 
            control character. If `mod_targ` is ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``, 
            the corresponding index of the control character is queried and `mod_value` can be specified by a character 
            in the range ``00-7f`` as a numeric value or bytestring, also control characters can be expressed by a 
            :class:`Ctrl` object and backspace by a :class:`DelIns` object; if `mod_value` is ``None`` in this request, 
            it is queried whether the index is deactivated.

        `mod_targ` :
            Specify the flag index over ``"in"``, ``"out"``, ``"ctrl"``, ``"local"``;
            ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``.
        
        # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html

    - @ **Windows**:
        `fileno` :
            ``-10`` (stdin) | ``-11`` (stdout) | ``-12`` (stderr)

        `mod_value` :
            The constant. Should be chosen from this module. (``CMD_`` prefix)
            
        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h

    ``raise EnvironmentError:`` an error occurred during the request.
    """
def mod_ansiin() -> ModDummy | ModItem:
    """
    - @ **UNIX** :
        Do nothing and return :class:`ModDummy`.

    - @ **Windows**:
        Enable virtual terminal input (converts user input into ansi escape sequences).
        Return the :class:`ModItem` -- on recursion error from ``__ModItemsCache__``.

        ``raise EnvironmentError:`` an error occurred during the modification
    """
def mod_ansiout() -> ModDummy | ModItem:
    """
    - @ **UNIX** :
        Do nothing and return :class:`ModDummy`.

    - @ **Windows**:
        Enable virtual terminal processing (process output ansi escape sequences).
        Return the :class:`ModItem` -- on recursion error from ``__ModItemsCache__``.

        ``raise EnvironmentError:`` an error occurred during the modification.
    """
def mod_nonecho() -> ModItem:
    """
    Disable the echo on user input.
    Return the :class:`ModItem` -- on recursion error from ``__ModItemsCache__``.

    ``raise EnvironmentError:`` an error occurred during the modification.
    """
def mod_nonblock() -> ModItemsHandle | ModItem:
    """
    Enable non-blocked reading from stdin.

    - @ **UNIX** :
        Return the :class:`ModItem` -- on recursion error from ``__ModItemsCache__``.

    - @ **Windows**:
        The Windows cmd requires ``nonecho`` for this modification, so ``mod_nonecho`` is executed first.

        Return the :class:`ModItem`'s per constant as :class:`ModItemsHandle`\ (``CMD_ENABLE_ECHO_INPUT``,
        ``CMD_ENABLE_LINE_INPUT``) -- on recursion errors from ``__ModItemsCache__``.

    ``raise EnvironmentError:`` an error occurred during the modification.
    """
def mod_nonprocess() -> ModItemsHandle | ModItem:
    r"""
    Disable the processing of control characters by the terminal.

    - @ **UNIX** :
        Disabled keystrokes:
             - INTR (Ctrl-C) by ``termios.ISIG``
             - SUSP (Ctrl-Z) by ``termios.ISIG``
             - QUIT (Ctrl-\\) by ``termios.ISIG``
             - XON (Ctrl-Q) by ``termios.IXON``
             - XOFF (Ctrl-S) by ``termios.IXON``

        Return the :class:`ModItem`'s per constant as :class:`ModItemsHandle`\ (``ISIG``, ``IXON``) --
        on recursion errors from ``__ModItemsCache__``.

    - @ **Windows**:
        Disabled keystrokes:
             - INTR (Ctrl-C) by ``CMD_ENABLE_PROCESSED_INPUT``
             - "Select" (Shift-Arrow) by ``CMD_ENABLE_PROCESSED_INPUT``

        Return the :class:`ModItem` -- on recursion error from ``__ModItemsCache__``.

    ``raise EnvironmentError:`` an error occurred during the modification.
    """
def mod_nonimpldef() -> ModItemsHandle:
    """
    - @ **UNIX** :
        Disable implementation-defined input/output processing.

        Return the :class:`ModItem`'s per constant as :class:`ModItemsHandle`\ (``IEXTEN``, ``OPOST``) --
        on recursion errors from ``__ModItemsCache__``.

        ``raise EnvironmentError:`` an error occurred during the modification.

    - @ **Windows**:
        Disable the Quick Edit Mode of the cmd by enabling the Extended Flags and removing the Quick Edit Mode Bit.

        Return the :class:`ModItem`'s per constant as :class:`ModItemsHandle`\ (``CMD_ENABLE_EXTENDED_FLAGS``,
        ``CMD_ENABLE_QUICK_EDIT_MODE``) -- on recursion errors from ``__ModItemsCache__``.

        ``raise EnvironmentError:`` an error occurred during the modification.
    """


INVALID_HANDLE_VALUE: int

# https://docs.microsoft.com/en-us/windows/console/setconsolemode
# https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h

# input flags
CMD_ENABLE_PROCESSED_INPUT: int
CMD_ENABLE_LINE_INPUT: int
CMD_ENABLE_ECHO_INPUT: int
CMD_ENABLE_WINDOW_INPUT: int
CMD_ENABLE_MOUSE_INPUT: int
CMD_ENABLE_INSERT_MODE: int
CMD_ENABLE_QUICK_EDIT_MODE: int
CMD_ENABLE_EXTENDED_FLAGS: int
CMD_ENABLE_AUTO_POSITION: int
CMD_ENABLE_VIRTUAL_TERMINAL_INPUT: int

# output flags
CMD_ENABLE_PROCESSED_OUTPUT: int
CMD_ENABLE_WRAP_AT_EOL_OUTPUT: int
CMD_ENABLE_VIRTUAL_TERMINAL_PROCESSING: int
CMD_DISABLE_NEWLINE_AUTO_RETURN: int
CMD_ENABLE_LVB_GRID_WORLDWIDE: int

# https://docs.microsoft.com/en-us/windows/wsl/release-notes#build-16257
ENABLE_VIRTUAL_TERMINAL_BUILD_REQUIRED: int

def regedit_permanent_virtual_terminal_level_syscommand(value: Literal[0, 1]) -> str: ...

class InappropriateDeviceHandler:
    action: Callable[[Exception], Any]
    other_action: Callable[[Exception], Any]
    def __init__(self, action: Callable[[Exception], Any] = ..., other_action: Callable[[Exception], Any] = ...) -> None:
        """
        A contextmanager/suit for the modification functions. Primarily for debugging.
        Allows explicit handling of Inappropriate Device Errors
        (unusual error, raised e.g. when trying to modify the python shell in pycharm
        or also when working with pipes in the bash).

        Application example:
        
            The following block disables some escape sequences directly in the framework when an
            Inappropriate Device Error is raised.

            >>> with InappropriateDeviceHandler(
            >>>     action=lambda exp: (
            >>>         vtframework.iodata.sgr.__STYLE_GATE__.destroy(),
            >>>         vtframework.iodata.decpm.__DECPM_GATE__.destroy()
            >>>         )
            >>>     ):
            >>>     mod_[...]

        `action` will be executed when an Inappropriate Device Error (error number 6 under Windows, 25 under UNIX)
        is raised (default handling is raising).

        `other_action` is executed on all other errors.

        The functions receive the error as parameter and the return value is returned from ``__exit__``.
        """
    @staticmethod
    def is_inappropriatedeverr(exc: Exception) -> bool:
        """Return whether `exc` is an inappropriate device error."""
    def handle(self, exc: Exception) -> Any:
        """Perform the action for `exc`."""
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> Any: ...

__ModItemsCache__: list[ModItem]
__ORIGIN_FLAGS__: dict[int, list[int, int, int, int, int, int, list[bytes]] | int]

class ModItem:
    """
    An item to handling modifications on the emulator.

    - @ **UNIX** :
        `fileno` :
            fileno from ``sys.stdin`` | ``sys.stdout`` | ``sys.stderr``

        `mod_value` :
            Depending on `mod_targ`, a constant must be selected from the module ``termios`` or
            parameterized as a new control character.
            If `mod_targ` is ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``, the corresponding index of
            the control characters is the `mod_value` target, `mod_value` can then be specified by a character in
            the range ``00-7f`` as a numeric value or bytestring, also control characters can be expressed by a
            :class:`Ctrl` object and backspace by a :class:`DelIns` object; ``None`` is the value to disable the
            index.

        `mod_targ` :
            Specify the flag index over ``"in"``, ``"out"``, ``"ctrl"``, ``"local"``;
            ``"ctrl+C"``, ``"ctrl+Q"``, ``"ctrl+S"`` or ``"ctrl+\\"``.

        `when` :
            Default value is ``termios.TCSANOW``.

        # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html


    - @ **Windows**:
        `fileno` :
            ``-10`` (stdin) | ``-11`` (stdout) | ``-12`` (stderr)

        `mod_value` :
            The constant. Should be chosen from this module. (``CMD_`` prefix)

        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        # https://github.com/microsoft/win32metadata/blob/f86785bec72eef8aa9c9cf5a84fc6d446abe2db5/generation/WinSDK/RecompiledIdlHeaders/um/consoleapi.h

    ``reset_atexit :`` [ Execute addition functions, then ] reset the modification when leaving the python interpreter.

    ``note :`` attach a note to the item.

    ``raise RecursionError:`` if an item of the same modification is already in ``__ModItemsCache__``.
    Decisive attributes: `fileno`, `mod_value`, `mod_targ`.
    """

    fileno: int
    mod_value: int
    mod_targ: Literal['in', 'out', 'ctrl', 'local', 'ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\']
    mod_when: int
    reset_atexit: bool
    note: Any
    origin_state: bool

    @overload
    def __init__(self,
                 fileno: int,
                 mod_value: int,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> None: ...
    @overload
    def __init__(self,
                 fileno: int,
                 mod_value: int | Ctrl | DelIns | bytes | None,
                 mod_targ: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'],
                 mod_when: int,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> None: ...
    @overload
    def __init__(self,
                 fileno: int,
                 mod_value: int,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local'],
                 mod_when: int,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> None:
        ...

    @staticmethod
    def from_recursion(e: RecursionError) -> ModItem:
        """Return the item from the ``__ModItemsCache__`` by the error raised from init."""
    @classmethod
    @overload
    def instance(cls,
                 fileno: int,
                 mod_value: int,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem: ...
    @classmethod
    @overload
    def instance(cls,
                 fileno: int,
                 mod_value: int | Ctrl | DelIns | bytes | None,
                 mod_targ: Literal['ctrl+C', 'ctrl+Q', 'ctrl+S', 'ctrl+\\'],
                 mod_when: int,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem: ...
    @classmethod
    @overload
    def instance(cls,
                 fileno: int,
                 mod_value: int,
                 mod_targ: Literal['in', 'out', 'ctrl', 'local'],
                 mod_when: int,
                 *,
                 reset_atexit: bool = True,
                 note: Any = None) -> ModItem:
        """Try to create the item; on recursion error return the item from ``__ModItemsCache__``."""
    def origin(self) -> bool:
        """Whether the modification value was set in the emulator flags before modification."""
    def request(self) -> bool:
        """Whether the modification flag is currently set."""
    def sub_flag(self) -> None:
        """Remove the modification value from the emulator flags."""
    def add_flag(self) -> None:
        """Add the modification value to the emulator flags."""
    def reset(self) -> None:
        """Resets the modification value to the initialization state."""
    def purge(self) -> None:
        """Unregister the reset function at exit, execute the additional exit functions in lifo order then the `reset`
        method and remove the item from ``__ModItemsCache__``."""
    def add_before_reset_atexit(self, func: Callable[[], Any]) -> None:
        """Add a function to the additional exit functions, these will be executed in lifo order when exiting the
        interpreter, before resetting the modification. Or when the `purge` method is executed."""
    def __int__(self) -> int:
        """`mod_value`"""
    def __eq__(self, other: ModItem) -> bool:
        """``hash == hash``"""
    def __hash__(self) -> int:
        """Composed of `(fileno, mod_value, mod_targ)`"""

class ModItemsHandle(tuple[ModItem]):
    """A handler for modifications with multiple constants. Supports via iterations `reset` (lifo), `sub_flag` (lifo),
    `add_flag` (fifo), `origin` (fifo), `request` (fifo) and `purge` (lifo)."""
    def __new__(cls, *args: ModItem) -> ModItemsHandle: ...
    def origin(self) -> tuple[bool, ...]:
        """Whether the modification value was present in the emulator flags at initialization."""
    def request(self) -> tuple[bool, ...]:
        """Whether the modification flags are currently set."""
    def sub_flag(self) -> None:
        """Remove the modification value from the emulator flags."""
    def add_flag(self) -> None:
        """Add the modification value to the emulator flags."""
    def reset(self) -> None:
        """Resets the modification value to the initialization state."""
    def purge(self) -> None:
        """Unregister the reset function at exit, execute the additional exit functions in lifo order then the `reset`
        method and remove the item from ``__ModItemsCache__``."""

class ModDummy:
    """A pseudo object for modifications that are not applied depending on the operating system."""
    def __call__(self, *args, **kwargs) -> ModDummy: ...
    def __getattr__(self, *args, **kwargs) -> ModDummy: ...
    def __getattribute__(self, *args, **kwargs) -> ModDummy: ...
    def __getitem__(self, *args, **kwargs) -> ModDummy: ...
    def __iter__(self) -> ModDummy: ...
    def __next__(self) -> None: ...
    def __len__(self) -> int: ...
    def __bool__(self) -> bool:
        """``False``"""

def cache_purge() -> None:
    """Perform `purge` of each item in the ``__ModItemsCache__``, which will
    resets all modifications of them and clears the ``__ModItemsCache__``."""
