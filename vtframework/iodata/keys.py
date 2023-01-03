# MIT License
#
# Copyright (c) 2022 Adrian F. Hoefflin [srccircumflex]
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
from typing import Literal, NamedTuple, Union, Iterable, Type
from sys import platform
from re import search

_MOD_COLLECTION: dict[int, tuple[int, ...]] = {
    2: (2, 4, 6, 8, 10, 12, 14, 16),
    3: (3, 4, 7, 8, 11, 12, 15, 16),
    5: (5, 6, 7, 8, 13, 14, 15, 16),
    9: (9, 10, 11, 12, 13, 14, 15, 16),
}


class _MOD(int):

    def __and__(self, other: _MOD):
        return _MOD(self + other - 1)

    def __contains__(self, item: Literal[2, 3, 5, 9] | _MOD):
        return self in _MOD_COLLECTION[item]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"


class _MODI(NamedTuple):
    """Key modifier values.

    Supports the ``&`` operator to represent combined keystrokes.

    ``SHIFT = 2 ALT = 3 CTRL = 5 META = 9``"""
    SHIFT: _MOD = _MOD(2)
    ALT: _MOD = _MOD(3)
    CTRL: _MOD = _MOD(5)
    META: _MOD = _MOD(9)


class _NoneMODI(NamedTuple):
    """
    Modifiers not supported.

    [Nothing here]
    """


class _NoneKEYS(NamedTuple):
    """
    No key values.

    [Nothing here]
    """


class _NavKeyKEYS(NamedTuple):
    """
    - ``A_*`` : Arrow keys
    - ``C_*`` : Cursor Navigation
    - ``P_*`` : Page
    - ``SHIFT_TAB`` : Shift-Tab
    ``A_RIGHT = 1 A_LEFT = -1 A_UP = -2 A_DOWN = 2 C_HOME = -3
    C_END = 3 C_BEGIN = -4 P_DOWN = 6 P_UP = -6 SHIFT_TAB = 9``
    """
    A_RIGHT: int = 1
    A_LEFT: int = -1
    A_UP: int = -2
    A_DOWN: int = 2
    C_HOME: int = -3
    C_END: int = 3
    C_BEGIN: int = -4
    P_DOWN: int = 6
    P_UP: int = -6
    SHIFT_TAB: int = 9


class _KeyPadKEYS(NamedTuple):
    """Keypad function keys.

    ``PF1 = -1 PF2 = -2 PF3 = -3 PF4 = -4``"""
    PF1: int = -1
    PF2: int = -2
    PF3: int = -3
    PF4: int = -4


class _DelInsKEYS(NamedTuple):
    """``INSERT = 1 BACKSPACE = 0 DELETE = -1 HPClear = -11``"""
    INSERT: int = 1
    BACKSPACE: int = 0
    DELETE: int = -1
    HPClear: int = -11


class _KeysValues(NamedTuple):
    """Collection of keys values."""
    NavKey: _NavKeyKEYS = _NavKeyKEYS()
    KeyPad: _KeyPadKEYS = _KeyPadKEYS()
    DelIns: _DelInsKEYS = _DelInsKEYS()


KEY_VALUES = _KeysValues()
MOD_VALUES = _MODI()

NONE_MOD = _NoneMODI()
NONE_KEY = _NoneKEYS()


class Key:
    """
    The base class for keys.

    Derivatives:
        - :class:`NavKey`
        - :class:`FKey`
        - :class:`ModKey`
        - :class:`KeyPad`
        - :class:`DelIns`
        - :class:`EscEsc`
        - :class:`Meta`
        - :class:`Ctrl`
    """
    KEY: int
    MOD: _MOD
    K: _NoneKEYS = NONE_KEY
    M: _MODI = MOD_VALUES

    @property
    def __vtdtid__(self):
        return 2

    @__vtdtid__.setter
    def __vtdtid__(self, v):
        raise AttributeError("__vtdtid__ is not settable")

    @__vtdtid__.deleter
    def __vtdtid__(self):
        raise AttributeError("__vtdtid__ is not deletable")

    __slots__ = ('KEY', 'MOD')

    def __init__(self, key: int | bytes | str = None, mod: int | None = 0):
        """Create a reference object over the parent class."""
        self.KEY = key
        self.MOD = self._mod(mod)

    @staticmethod
    def _mod(mod: int | tuple | None) -> _MOD | None:
        if mod is None:
            return None
        if isinstance(mod, int):
            return _MOD(mod)
        _mod = mod[0]
        for i in range(1, len(mod)):
            _mod += mod[i] - 1
        return _MOD(_mod)

    def __contains__(
            self,
            item:
            Union[
                int,  # key value
                tuple[int, ...],  # comparison of combined keys
                None  # skip comparison
            ]
    ) -> bool:
        """Return whether the modification matches. Multiple keystrokes are queried via a tuple. 
        Values should be chosen from `self.M`."""
        return self.MOD is None or item is None or self.MOD == self._mod(item)

    def __eq__(self, other: Key) -> bool:
        """Return whether `other` is the same kind of instance and
        the defined parameters of the reference object correlate with those of the `other` one."""
        if not isinstance(self, other.__class__):
            return False
        return (self.KEY is None or other.KEY is None or self.KEY == other.KEY) and self.MOD in other

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {repr(self.KEY)} {repr(self.MOD)}>"

    def __hash__(self) -> int:
        return hash(self.__repr__())

    def __int__(self) -> int:
        return self.KEY

    def __iter__(self) -> Iterable:
        return self.KEY, self.MOD

    @staticmethod
    def eval(x: str) -> Key:
        """Create a :class:`Key` instance from a representative sting of a :class:`Key` instance.

        :raise ValueError(exception): on errors with the original exception as argument."""
        try:
            key: Key = eval((m := search("(?<=<)\\w+", x)).group() + '()')
            key.KEY = eval(search("(?<= )(['\"].['\"]|\\S+)", x[m.end():]).group())
            key.MOD = eval(search("\\S+(?=>$)", x).group())
            return key
        except Exception as e:
            raise ValueError(e)


class NavKey(Key):
    """

    ---Navigational Key Object---
    
    Arrow keys, pos1, end, page up/down, shift-tab.

    Shift-tab is a special case, an ``<NavKey(key=NavKey.K.SHIFT_TAB, mod=NavKey.M.SHIFT)>`` is always created for
    this key combination.
    The keys `pos1` and `end` are usually interpreted with the values from `NavKey.K.C_HOME` and `NavKey.K.C_END`.

    Values:

    - `KEY`: int
        Values for comparison in `K`:
            ``A_RIGHT = 1
            A_LEFT = -1
            A_UP = -2
            A_DOWN = 2
            C_HOME = -3
            C_END = 3
            C_BEGIN = -4
            P_DOWN = 6
            P_UP = -6
            SHIFT_TAB = 9``
    - `MOD`: int
        Values for comparison in `M`:
            ``SHIFT = 2
            ALT = 3
            CTRL = 5
            META = 9``
        Comparisons:
            - ``NavKey.M.SHIFT  in  NavKey(key)``
            - ``(NavKey.M.SHIFT, NavKey.M.CTRL)  in  NavKey(key)``  `(Combined modifications)`
            - ``NavKey.M.SHIFT & NavKey.M.CTRL  in  NavKey(key)``  `(Combined modifications)`

    ****
            
    # Resources:
     ; `xterm/PC-Style-Function-Keys`_
     ; ff.

    .. _`xterm/PC-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-PC-Style-Function-Keys
    
    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    :param key: Should be selected from `NavKey.K`.
      If `key` is None the comparison ``NavKey(None) == NavKey(Any)`` always returns True if the modification is True.
    :param mod: The modification to be compared.
     Should be selected from `NavKey.M`. The `&` operator can be used between the mods to represent combinations
     ( e.g. ``NavKey(1, NavKey.M.SHIFT & NavKey.M.CTRL)`` ). If mod is 0, no modification is explicitly expected.
     If mod is None, the comparison is always True.
    """

    K: _NavKeyKEYS = KEY_VALUES.NavKey

    def __init__(self, key: int = None, mod: int | None = 0):
        Key.__init__(self, key, mod)


class ModKey(Key):
    """

    ---Modify Other Keys Object---

    Values:
        
    - `KEY`: int
        ASCII value [+ 128]
    - `MOD`: int
        Values for comparison in `M`:
            ``SHIFT = 2
            ALT = 3
            CTRL = 5
            META = 9``
        Comparisons:
            - ``ModKey.M.SHIFT  in  ModKey(key)``
            - ``(ModKey.M.SHIFT, ModKey.M.CTRL)  in  ModKey(key)``  `(Combined modifications)`
            - ``ModKey.M.SHIFT & ModKey.M.CTRL  in  ModKey(key)``  `(Combined modifications)`

    ## untested ##

    ****

    # Resources:
     ; `xterm/Alt-and-Meta-Keys`_

    .. _`xterm/Alt-and-Meta-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Alt-and-Meta-Keys
    """

    def __init__(self, key: int = None, mod: int | None = 0):
        Key.__init__(self, key, mod)


class KeyPad(Key):
    """

    ---Keypad Object---

    Values:

    - `KEY`: int | str = ``'+' '-' '*' '/' '=' '.' ',' -1(PF1) -2(PF2) -3(PF3) -4(PF4) 0-9(N)``
    - `MOD`: int = 0

    ## untested ##

    ****

    # Resources:
     ; `xterm/PC-Style-Function-Keys`_
     ; `xterm/VT220-Style-Function-Keys`_
     ; `xterm/VT52-Style-Function-Keys`_
     
    .. _`xterm/PC-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-PC-Style-Function-Keys
    .. _`xterm/VT220-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-VT220-Style-Function-Keys
    .. _`xterm/VT52-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-VT52-Style-Function-Keys
    """
    M: _NoneMODI = NONE_MOD
    K: _KeyPadKEYS = KEY_VALUES.KeyPad

    KEY: int | str

    def __init__(self, key: int | str = None):
        Key.__init__(self, key, 0)


class DelIns(Key):
    """

    ---Delete/Insert Key Object---
    
    Delete, Insert and Backspace.

    Values:

    - `KEY`: int
        Values for comparison in `K`:
            ``INSERT = 1
            BACKSPACE = 0
            DELETE = -1
            HPClear = -11``
    - `MOD`: int
        Values for comparison in `M`:
            ``SHIFT = 2
            ALT = 3
            CTRL = 5
            META = 9``
        Comparisons:
            - ``DelIns.M.SHIFT  in  DelIns(key)``
            - ``(DelIns.M.SHIFT, DelIns.M.CTRL)  in  DelIns(key)``  `(Combined modifications)`
            - ``DelIns.M.SHIFT & DelIns.M.CTRL  in  DelIns(key)``  `(Combined modifications)`

    ****

    # Resources:
     ; `xterm/PC-Style-Function-Keys`_
     ; ff.

    .. _`xterm/PC-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-PC-Style-Function-Keys

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.
    
    :param key: Should be selected from `DelIns.K`.
      If `key` is None the comparison ``DelIns(None) == DelIns(Any)`` always returns True if the modification matches.
    :param mod: The modification to be compared.
     Should be selected from `DelIns.M`. The `&` operator can be used between the mods to represent combinations
     ( e.g. ``DelIns(1, DelIns.M.SHIFT & DelIns.M.CTRL)`` ). If mod is 0, no modification is explicitly expected.
     If mod is None, the comparison is always True.
    """

    K: _DelInsKEYS = KEY_VALUES.DelIns

    def __init__(self, key: int = None, mod: int | None = 0):
        Key.__init__(self, key, mod)


class FKey(Key):
    """

    ---Function Key Object---

    Values:

    - `KEY`: int = Key number (1-20)
    - `MOD`: int
        Values for comparison in `M`:
            ``SHIFT = 2
            ALT = 3
            CTRL = 5
            META = 9``
        Comparisons:
            - ``FKey.M.SHIFT  in  FKey(key)``
            - ``(FKey.M.SHIFT, FKey.M.CTRL)  in  FKey(key)``  `(Combined modifications)`
            - ``FKey.M.SHIFT & FKey.M.CTRL  in  FKey(key)``  `(Combined modifications)`

    ****

    # Resources:
     ; `xterm/PC-Style-Function-Keys`_
     ; ff.

    .. _`xterm/PC-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-PC-Style-Function-Keys

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    :param key: If `key` is None the comparison ``FKey(None) == FKey(Any)`` always returns True if the modification is
     True.
    :param mod: The modification to be compared.
     Should be selected from `FKey.M`. The `&` operator can be used between the mods to represent combinations
     ( e.g. ``FKey(1, FKey.M.SHIFT & FKey.M.CTRL)`` ). If mod is 0, no modification is explicitly expected.
     If mod is None, the comparison is always True.
    """

    def __init__(self, key: int = None, mod: int | None = 0):
        Key.__init__(self, key, mod)


class EscEsc(Key):
    """

    ---ESC double---
    
    Will be interpreted when esc is pressed twice.
    (Also send via ``ctrl+alt/meta+3``, ``ctrl+alt/meta+[`` and ``ctrl+alt/meta+{`` (**UNIX**)
    (see :class:`Meta` and :class:`Ctrl`)).

    Values:

    - `KEY`: int = 2727
    - `MOD`: int = 2727
    
    ****

    This object is created by the vtiinterpreter and also serves as a reference object.
    """
    M: _NoneMODI = NONE_MOD
    KEY: int = 2727
    MOD: int = 2727

    def __init__(self):
        Key.__init__(self)
        self.KEY = self.MOD = 2727


class Ctrl(Key):
    r"""

    ---ASCII Control Character---
    
    Values:

    - `KEY`: str = character shifted by adding 64 (ASCII: ``@A-Z\\]^_```)
    - `MOD`: int = decimal character value (0 - 32)

    Basically, the alphabetic characters ( ``ctrl + [a-z_]`` ) -- except h, i, j, m -- are interpreted in combination with ctrl as
    `Ctrl(<upper character>)`.
    ( **[ ! ]** To avoid the terminal processing in advance, this must be modified beforehand).

    Platform dependent specifics are listed below.

    - @ **UNIX** :
        Default characters processed by the terminal
        (representative, also applies to combinations that send the same, see below):

            - ``ctrl + c`` : INTR
            - ``ctrl + q`` : IXON
            - ``ctrl + s`` : IXOFF
            - ``ctrl + z`` : SUSP
            - ``ctrl + \`` : QUIT

        Specifics:

            - ``ctrl + h`` = ctrl + backspace -> :class:`DelIns` (KEY=0, MOD=5)
            - ``ctrl + i`` = \\t -> :class:`Space` ("\\t") or :class:`Ctrl` ("I") (vtiinterpreter configuration)
            - ``ctrl + j`` = \\n | \\r -> :class:`Space` ("\\n") or :class:`Ctrl` ("J") (vtiinterpreter configuration)
            - ``ctrl + m`` = \\n | \\r -> :class:`Space` ("\\n") or :class:`Ctrl` ("M") (vtiinterpreter configuration)
            - ``ctrl + space`` -> :class:`Ctrl` ("@")
            - ``ctrl + @`` -> :class:`Ctrl` ("@")
            - ``ctrl + | (Or)`` -> :class:`Ctrl` ("\\")
            - ``ctrl + 2`` -> :class:`Ctrl` ("@")
            - ``ctrl + 3`` = ESC
            - ``ctrl + 4`` -> :class:`Ctrl` ("\\")
            - ``ctrl + 5`` -> :class:`Ctrl` ("]")
            - ``ctrl + 6`` -> :class:`Ctrl` ("^")
            - ``ctrl + 7`` -> :class:`Ctrl` ("_")
            - ``ctrl + 8`` = backspace -> :class:`DelIns` (KEY=0)
            - ``ctrl + /`` -> :class:`Ctrl` ("_")
            - ``ctrl + {`` = ESC
            - ``ctrl + [`` = ESC
            - ``ctrl + ]`` -> :class:`Ctrl` ("]")
            - ``ctrl + }`` -> :class:`Ctrl` ("]")
            - ``ctrl + ?`` = backspace -> :class:`DelIns` (KEY=0)
            - ``ctrl + \\`` -> :class:`Ctrl` ("\\")
            - ``ctrl + ~`` -> :class:`Ctrl` ("^")
            - ``ctrl + -`` -> :class:`Ctrl` ("_")
            - ``ctrl + _`` -> :class:`Ctrl` ("_")

        Depending on the vtiinterpreter configuration ``Tab``, ``Enter/Return`` and ``Space`` are interpreted as `Ctrl`.

            - ``Tab`` -> :class:`Ctrl` ("I")
            - ``Enter/Return`` -> :class:`Ctrl` ("J")
            - ``Space`` -> :class:`Ctrl` ("\`")

    - @ **Windows**:
        Default characters processed by the terminal
        (representative, also applies to combinations that send the same, see below):

            - ``ctrl + c`` : INTR

        Specifics:

            - ``ctrl + h`` = ctrl + backspace -> :class:`DelIns` (5)
            - ``ctrl + i`` = \\t -> :class:`Space` ("\\t") or :class:`Ctrl` ("I") (vtiinterpreter configuration)
            - ``ctrl + j`` = \\n | \\r -> :class:`Space` ("\\n") or :class:`Ctrl` ("J") (vtiinterpreter configuration)
            - ``ctrl + m`` = \\n | \\r -> :class:`Space` ("\\n") or :class:`Ctrl` ("M") (vtiinterpreter configuration)
            - ``ctrl + &`` -> :class:`Ctrl` ("^")
            - ``ctrl + 7`` -> :class:`Ctrl` ("_")
            - ``ctrl + /`` -> :class:`Ctrl` ("_")
            - ``ctrl + +`` -> :class:`Ctrl` ("]")
            - ``ctrl + #`` -> :class:`Ctrl` ("\\")
            - ``ctrl + _`` -> :class:`Ctrl` ("_")
            - ``break/pause`` -> :class:`Ctrl` ("Z")

        Depending on the vtiinterpreter configuration ``Tab``, ``Enter/Return`` and ``Space`` are interpreted as `Ctrl`.

            - ``Tab`` -> :class:`Ctrl` ("I")
            - ``Enter/Return`` -> :class:`Ctrl` ("M")
            - ``Space`` -> :class:`Ctrl` ("\`")

    ****

    # Resources:
     ; `xterm/PC-Style-Function-Keys`_
     ; ff.
     ; `wikipedia/UTF-8/Codepage_layout`_

    .. _`xterm/PC-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-PC-Style-Function-Keys
    .. _`wikipedia/UTF-8/Codepage_layout`: https://en.wikipedia.org/wiki/UTF-8#Codepage_layout

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    :param key: "tab", "enter", "space" are aliases for the corresponding key.
      If `key` is None the comparison ``Ctrl(None) == Ctrl(Any)`` always returns True.
    """
    M: _NoneMODI = NONE_MOD
    KEY: str

    def __init__(
            self,
            key: bytes | Literal["@", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O",
                                 "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "\\", "]", "^", "_",
                                 "`",
                                 "tab", "enter", "space"] = None
    ):
        if isinstance(key, bytes):
            Key.__init__(self, chr((_oc := ord(key)) + 64), _oc)
        elif isinstance(key, str):
            if k := {
                "t": "I",
                "e": ("M" if platform == "win32" else "J"),
                "s": "`"
            }.get(key[0]):
                key = k
            Key.__init__(self, key, ord(key) - 64)
        else:
            Key.__init__(self, None, None)


class Meta(Key):
    r"""

    ---Meta/Alt Character---

    The largest range of alternative inputs. When an input is modified with Alt/Meta, `Meta(input)` is interpreted.
    Technically, the input is preceded by the escape character (``\x1b``), so a combination with :class:`Ctrl` is also
    always interpreted as `Meta`. (Example: ``ctrl+alt/meta+a -> Meta("\x01")``).
    This also means that if the combination with Ctrl sends the escape character, :class:`EscEsc` is automatically
    interpreted. Shifted characters are passed as such to `Meta`, thus the type is case sensitive
    ( ``alt/meta+a -> Meta("a")`` | ``alt/meta+shift+a -> Meta("A")`` ). Note: Control characters can NOT be shifted.

    Values:

    - `KEY`: str = character (UTF)
    - `MOD`: int = decimal character value

    ****

    # Resources:
     ; `xterm/PC-Style-Function-Keys`_
     ; ff.
     ; `xterm/Alt-and-Meta-Keys`_

    .. _`xterm/PC-Style-Function-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-PC-Style-Function-Keys
    .. _`xterm/Alt-and-Meta-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Alt-and-Meta-Keys

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.
    
    :param key: If `key` is None the comparison ``Meta(None) == Meta(Any)`` always returns True.
     The range of ASCII control characters - combined with Alt/Meta - can be assigned via `Ctrl(key)`
     ( e.g. ``Meta(Ctrl("A")) == Meta("\x01")`` ). Only consistent with alphabetic characters,
     for the `Ctrl` special cases, combinations may be ignored or interpreted uncommonly.
    """
    M: _NoneMODI = NONE_MOD

    KEY: str

    def __init__(self, key: bytes | str | Ctrl = None):
        if isinstance(key, str):
            Key.__init__(self, key, ord(key))
        elif isinstance(key, Ctrl):
            if key.MOD is None:
                raise ValueError('a wildcard cannot be used here')
            Key.__init__(self, chr(key.MOD), key.MOD)
        elif isinstance(key, bytes):
            Key.__init__(self, key.decode(), ord(key))
        else:
            Key.__init__(self, None, None)


def Eval(x: str) -> Key | Type[Key]:
    """Return a :class:`Key` instance or type from a representative sting.

    :raise ValueError(exception): on errors with the original exception as argument."""
    try:
        if x.startswith('<class '):
            return eval(search("(?<=\\.)\\w+(?='>$)", x).group())
        else:
            return Key.eval(x)
    except Exception as e:
        raise ValueError(e)
