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
from typing import NamedTuple, overload, Literal, Type, Generator, Any
from re import sub, search

from vtframework.iodata import decpm


class InvalidReplyError(ValueError):
    """Raised if the reply is invalid"""
    def __init__(self, rep, seq, exp):
        ValueError.__init__(self, rep.__class__.__name__, seq, exp)


class Reply:
    """
    The base class for replies.

    Derivatives:
        - :class:`ReplyDA`
        - :class:`ReplyTID`
        - :class:`ReplyTIC`
        - :class:`ReplyCP`
        - :class:`ReplyCKS`
        - :class:`ReplyDECPM`
        - :class:`ReplyWindow`
        - :class:`ReplyOSColor`
    """
    SEQS: None | str
    REPLY_VALUES: None | NamedTuple

    @property
    def __vtdtid__(self):
        return 4

    @__vtdtid__.setter
    def __vtdtid__(self, v):
        raise AttributeError("__vtdtid__ is not settable")

    @__vtdtid__.deleter
    def __vtdtid__(self):
        raise AttributeError("__vtdtid__ is not deletable")

    __slots__ = ('SEQS', 'REPLY_VALUES')

    def __init__(self, *args, **kwargs):
        self.SEQS = None
        self.REPLY_VALUES = None

    def __eq__(self, other: Reply) -> bool:
        if not isinstance(self, other.__class__):
            return False
        return self.REPLY_VALUES is None or self.REPLY_VALUES == other.REPLY_VALUES

    def __contains__(self, name: str) -> bool:
        return getattr(self.REPLY_VALUES, name.upper().replace(' ', '_'), None) is not None

    def __getitem__(self, name: str) -> Any:
        return getattr(self.REPLY_VALUES, name.upper().replace(' ', '_'))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({repr(self.SEQS)}, " + sub('(\\w+\\(|\\)$)', '', repr(self.REPLY_VALUES)) + ")>"

    def __hash__(self) -> int:
        return hash(f"{self.__class__.__name__}{self.REPLY_VALUES}")

    def __str__(self) -> str:
        """:raise TypeError: SEQS of reference objects are None"""
        return self.SEQS

    def __iter__(self) -> Generator[tuple[str, Any]]:
        """
        :return: Generator[<(key, value) pair>]
        :raise AttributeError: REPLY_VALUES of the parent class are None
        """
        return ((k, self.__getitem__(k)) for k in self.REPLY_VALUES.__annotations__)

    @staticmethod
    def eval(x: str) -> Reply:
        """Create a :class:`Reply` instance from a representative sting of a :class:`Reply` instance.

        :raise ValueError(exception): on errors with the original exception as argument."""
        try:
            return eval(x[1:-1])
        except Exception as e:
            raise ValueError(e)


class ReplyDA(Reply):
    """
    [DA1] Primary Device Attributes

    `ReplyDA['VT']`: int | str
        Current operating VT level. Known classes codes are converted into levels.

        Known classes:
            - 1 = 100
            - 1 ; 0 = 101
            - 4 = 132
            - 6 = 102
            - 7 = 131
            - 12 = 125
            - 62 = 220
            - 63 = 320
            - 64 = 420

        If the level is not found, `ReplyDA['VT']` is the unconverted class code (str)
        if the value is greater than 64 (level 4 terminal); otherwise `ReplyDA['VT']` is not set.

    `ReplyDA['PARAMS']`: tuple[int, ...]
        Device attributes.

        Attributes for levels less than 220:
            - 0 = no options
            - 2 = advanced video options
            - 6 = advanced video and graphics

        Attributes for levels greater/equal than 220:
            - 0 = no options
            - 1 = 132-columns
            - 2 = Printer
            - 3 = ReGIS graphics
            - 4 = Sixel graphics
            - 6 = selective erase
            - 7 = soft character set
            - 8 = user-defined keys
            - 9 = national replacement charachter set
            - 15 = technical characters
            - 16 = locator port
            - 17 = terminal state interrogation
            - 18 = user windows
            - 21 = horizontal scrolling
            - 22 = ANSI color
            - 28 = rectangular editing
            - 29 = ANSI text locator
            - 42 = CHARSET_ISO_LATIN2
            - 45 = soft key map
            - 46 = ASCII emulation

    ****

    # Resources:
     ; `vt100.net/DA1`_
     ; `xterm/CSI/Primary-DA`_

    .. _`vt100.net/DA1`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps-c.1CA3
    .. _`xterm/CSI/Primary-DA`: https://vt100.net/docs/vt510-rm/DA1.html

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword VT:  int: known cases | str: unknown but the value of the class suggests a terminal with level >= 4 |
      tuple[int | str]: value contained
    :keyword PARAMS: int | tuple[int, ...]: expected values

    :raises InvalidReplyError:
    """

    class ReplyValues(NamedTuple):
        VT: int | str
        PARAMS: tuple[int, ...]
        # VT: int | tuple[int | str] | None
        # PARAMS: int | tuple | None

        def __eq__(self, other: ReplyDA.ReplyValues):
            if self.VT is not None:
                if isinstance(self.VT, tuple):
                    if other.VT not in self.VT:
                        return False
                elif self.VT != other.VT:
                    return False
            if self.PARAMS is not None:
                if isinstance(self.PARAMS, int):
                    if self.PARAMS not in other.PARAMS:
                        return False
                else:
                    for p in self.PARAMS:
                        if p not in other.PARAMS:
                            return False
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    class _VTClassToLevel:
        map: dict = {
            1: 100,  # or 101
            4: 132,
            6: 102,
            7: 131,
            12: 125,
            62: 220,
            63: 320,
            64: 420
        }

        def __getitem__(self, item: str):
            return self.map.get(int(item), (item if int(item) > 64 else None))

    VTClassToLevel = _VTClassToLevel()

    @overload
    def __init__(self, *, VT: Literal[100, 101, 132, 102, 131, 125, 220, 320, 420] | str | tuple[Literal[100, 101, 132, 102, 131, 125, 220, 320, 420] | str, ...] = None, PARAMS: Literal[0, 1, 2, 3, 4, 6, 7, 8, 9, 15, 16, 17, 18, 21, 22, 28, 29, 42, 45, 46] | tuple[Literal[0, 1, 2, 3, 4, 6, 7, 8, 9, 15, 16, 17, 18, 21, 22, 28, 29, 42, 45, 46], ...] = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyDA.ReplyValues = ReplyDA.ReplyValues._ref(_kwargs)
            return
        try:
            params = _seqs[3:-1].split(';')
            vt = self.VTClassToLevel[params.pop(0)]
            _params = list()
            for param in params:
                if param == '0':
                    if vt == 100:
                        vt = 101
                _params.append(int(param))
            self.REPLY_VALUES: ReplyDA.ReplyValues = self.ReplyValues(VT=vt, PARAMS=tuple(_params))
        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


class ReplyTID(Reply):
    """
    [DA3] Tertiary Device Attributes

    `ReplyTID['MANUFACTURING_SIDE']`: str[hex]
        Manufacturing side code

    `ReplyTID['TERMINAL_ID']`: str[hexhexhex]
        Unique terminal manufacturer identification

    ****

    # Resources:
     ; `vt100.net/DA3`_

    .. _`vt100.net/DA3`: https://vt100.net/docs/vt510-rm/DA3.html

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword MANUFACTURING_SIDE: str
    :keyword TERMINAL_ID: str

    :raises InvalidReplyError:
    """

    class ReplyValues(NamedTuple):
        MANUFACTURING_SIDE: str
        TERMINAL_ID: str
        # MANUFACTURING_SIDE: str | None
        # TERMINAL_ID: str | None

        def __eq__(self, other: ReplyTID.ReplyValues):
            if self.MANUFACTURING_SIDE is not None and other.MANUFACTURING_SIDE != self.MANUFACTURING_SIDE:
                return False
            if self.TERMINAL_ID is not None and other.TERMINAL_ID != self.TERMINAL_ID:
                return False
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    @overload
    def __init__(self, *, MANUFACTURING_SIDE: str = None, TERMINAL_ID: str = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyTID.ReplyValues = ReplyTID.ReplyValues._ref(_kwargs)
            return
        try:
            self.REPLY_VALUES: ReplyTID.ReplyValues = self.ReplyValues(MANUFACTURING_SIDE=_seqs[4:6], TERMINAL_ID=_seqs[6:-2])
            assert len(self.REPLY_VALUES.MANUFACTURING_SIDE) == 2
            assert len(self.REPLY_VALUES.TERMINAL_ID) == 6
        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


class ReplyTIC(Reply):
    """
    [DA2] Secondary Device Attributes

    `ReplyTIC['VT']`: int | str
        Terminal identification code. Known classes codes are converted into levels.

        Known classes:
            - 0 = 100
            - 1 = 220
            - 2 = 240 or 241 = 240
            - 18 = 330
            - 19 = 340
            - 24 = 320
            - 32 = 382
            - 41 = 420
            - 61 = 510
            - 64 = 520
            - 65 = 525

        If the level is not found, `ReplyTIC['VT']` is the unconverted class code (str)
        if the value is greater than 65 (level 5 terminal); otherwise `ReplyTIC['VT']` is not set.

    `ReplyTIC['FIRMWARE']`: int
        Firmware version

    `ReplyTIC['KEYBOARD']`: bool
        - True = PC Keyboard option
        - False = STD Keyboard

    ****

    # Resources:
     ; `vt100.net/DA2`_
     ; `xterm/CSI/Secondary-DA`_

    .. _`vt100.net/DA2`: https://vt100.net/docs/vt510-rm/DA2.html
    .. _`xterm/CSI/Secondary-DA`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-gt-Ps-c.1DAB

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword VT: int: known cases | str: unknown but the value of the class suggests a terminal with level >= 5 |
      tuple[int | str]: value contained
    :keyword FIRMWARE: int: explicit | tuple[int, ...]: contained
    :keyword KEYBOARD: bool

    :raises InvalidReplyError:
    """

    class ReplyValues(NamedTuple):
        VT: int | str
        FIRMWARE: int
        KEYBOARD: bool
        # VT: int | tuple[int | str] | None
        # FIRMWARE: int | tuple[int] | None
        # KEYBOARD: bool | None

        def __eq__(self, other: ReplyTIC.ReplyValues):
            for ref, otr in zip((self.VT, self.FIRMWARE), (other.VT, other.FIRMWARE)):
                if ref is not None:
                    if isinstance(ref, tuple):
                        if otr not in ref:
                            return False
                    elif ref != other:
                        return False
            if self.KEYBOARD is not None and other.KEYBOARD is not self.KEYBOARD:
                return False
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    class _VTClassToLevel:
        map: dict = {
            0: 100,
            1: 220,
            2: 240,  # or 241
            18: 330,
            19: 340,
            24: 320,
            32: 382,
            41: 420,
            61: 510,
            64: 520,
            65: 525
        }

        def __getitem__(self, item: str):
            return self.map.get(int(item), (item if int(item) > 65 else None))

    VTClassToLevel = _VTClassToLevel()

    @overload
    def __init__(self, *, VT: Literal[100, 220, 240, 330, 340, 320, 382, 420, 510, 520, 525] | str | tuple[Literal[100, 220, 240, 330, 340, 320, 382, 420, 510, 520, 525] | str, ...] = None, FIRMWARE: int | tuple[int, ...] = None, KEYBOARD: bool = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyTIC.ReplyValues = ReplyTIC.ReplyValues._ref(_kwargs)
            return
        try:
            params = _seqs[3:-1].split(';')
            self.REPLY_VALUES: ReplyTIC.ReplyValues = self.ReplyValues(
                VT=self.VTClassToLevel[params[0]], FIRMWARE=int(params[1]), KEYBOARD={'0': False, '1': True}[params[2]]
            )
        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


class ReplyCP(Reply):
    """
    [CPR] Cursor Position Report | [DECXCPR] Extended Cursor Position

    `ReplyCP['x']`: int
        Current column

    `ReplyCP['y']`: int
        Current line

    `ReplyCP['PAGE']`: int  (only set if the extended mode was used)
        Current page

    ****

    # Resources:
     ; `xterm/CSI/DSR/CPR`_
     ; `xterm/CSI/DSR-DEC/DECXCPR`_

    .. _`xterm/CSI/DSR/CPR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps-n%3APs-%3D-6.1E06
    .. _`xterm/CSI/DSR-DEC/DECXCPR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3F-Ps-n%3APs-%3D-6.1E72

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword x: int: explicit position | tuple[int, int]: position in range
    :keyword y: int: explicit position | tuple[int, int]: position in range
    :keyword PAGE: int

    :raises InvalidReplyError:
    """

    class ReplyValues(NamedTuple):
        PAGE: int
        x: int
        y: int
        # PAGE: int | tuple | None
        # x: int | tuple | None
        # y: int | tuple | None

        def __eq__(self, other: ReplyCP.ReplyValues):
            ref: tuple

            def comp():
                if isinstance(ref, tuple):
                    return ref[0] <= otr < ref[1]
                return otr == ref

            for ref, otr in zip((self.PAGE, self.x, self.y), (other.PAGE, other.x, other.y)):
                if ref is not None and not comp():
                    return False
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    @overload
    def __init__(self, *, PAGE: int | tuple[int, int] = None, x: int | tuple[int, int] = None, y: int | tuple[int, int] = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyCP.ReplyValues = ReplyCP.ReplyValues._ref(_kwargs)
            return
        try:
            page = None
            if _seqs[2] == "?":
                y, x, page = _seqs[3:-1].split(';')
                page = int(page)
            else:
                y, x = _seqs[2:-1].split(';')
            self.REPLY_VALUES: ReplyCP.ReplyValues = self.ReplyValues(PAGE=page, x=int(x), y=int(y))
        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


class ReplyCKS(Reply):
    """
    [DECCKSR] Memory Checksum Report

    `ReplyCKS['ID']`: int  (only set if defined at request)
        The id if one has been defined

    `ReplyCKS['CHECKSUM']`: str[hexdhexdhexdhexd]
        The checksum report of the current text macro definitions

    ****

    # Resources:
     ; `vt100.net/DECCKSR`_
     ; `xterm/CSI/DSR-DEC/DECCKSR`_

    .. _`vt100.net/DECCKSR`: https://vt100.net/docs/vt510-rm/DECCKSR.html
    .. _`xterm/CSI/DSR-DEC/DECCKSR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3F-Ps-n%3APs-%3D-6-3.1ED2

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword ID: int
    :keyword CHECKSUM: str

    :raises InvalidReplyError:
    """

    class ReplyValues(NamedTuple):
        ID: int
        CHECKSUM: str
        # ID: int | None
        # CHECKSUM: str | None

        def __eq__(self, other: ReplyCKS.ReplyValues):
            if self.ID is not None and other.ID != self.ID:
                return False
            if self.CHECKSUM is not None and other.CHECKSUM != self.CHECKSUM:
                return False
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    @overload
    def __init__(self, *, ID: int = None, CHECKSUM: str = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyCKS.ReplyValues = ReplyCKS.ReplyValues._ref(_kwargs)
            return
        try:
            id_ = None
            if _seqs[2] != "!":
                id_ = int(_seqs[2:].split('!')[0])
            self.REPLY_VALUES: ReplyCKS.ReplyValues = self.ReplyValues(ID=id_, CHECKSUM=_seqs[:-2].split('~')[-1])
        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


class ReplyDECPM(Reply):
    """
    [DECRQM] Request DEC Mode [DECRPM]

    `ReplyDECPM['MODE']`: int
        The queried DEC mode.

    `ReplyDECPM['VALUE']`: int
        The return value.

        - 0 = not recognized
        - 1 = set
        - 2 = reset
        - 3 = permanently set
        - 4 = permanently reset

    The return value is also stored in ``decpm.__ReplyCache__`` during interpretation,
    for a query via :class:`decpm.DECPrivateMode`.reply_cache(<mode>).

    ****

    # Resources:
     ; `vt100.net/DECRPM`_
     ; `xterm/CSI/DECRQM`_

    .. _`vt100.net/DECRPM`: https://vt100.net/docs/vt510-rm/DECRPM.html
    .. _`xterm/CSI/DECRQM`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps-%24-p.1D01

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword MODE: int
    :keyword VALUE: int: explicit value | tuple[int, ...]: value contained

    :raises InvalidReplyError:
    """

    class ReplyValues(NamedTuple):
        MODE: int
        VALUE: int
        # MODE: int | None
        # VALUE: int | tuple | None

        def __eq__(self, other: ReplyDECPM.ReplyValues):
            if self.MODE is not None and other.MODE != self.MODE:
                return False
            if self.VALUE is not None:
                if isinstance(self.VALUE, tuple):
                    return other.VALUE in self.VALUE
                return self.VALUE == other.VALUE
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    @overload
    def __init__(self, *, MODE: int = None, VALUE: Literal[0, 1, 2, 3, 4] | tuple[Literal[0, 1, 2, 3, 4], ...] = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyDECPM.ReplyValues = ReplyDECPM.ReplyValues._ref(_kwargs)
            return
        try:
            mode, val = _seqs[3:-2].split(';')
            self.REPLY_VALUES: ReplyDECPM.ReplyValues = self.ReplyValues(MODE=int(mode), VALUE=int(val))

            decpm.__ReplyCache__[self.REPLY_VALUES.MODE] = self.REPLY_VALUES.VALUE

        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


class ReplyWindow(Reply):
    """
    [XTWINOPS] Extended Window Options

    `ReplyWindow['MODE']`: int
        The mode used.

    `ReplyWindow['x']`: int
        x-axis value

    `ReplyWindow['y']`: int
        y-axis value

    ****

    # Resources:
     ; `xterm/CSI/Report xterm text area size`_

    .. _`xterm/CSI/Report xterm text area size`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps%3BPs%3BPs-t%3APs-%3D-1-4.2064

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword MODE: int
    :keyword x: int: explicit position | tuple[int, int]: position in range
    :keyword y: int: explicit position | tuple[int, int]: position in range

    :raises InvalidReplyError:
    """

    class ReplyValues(NamedTuple):
        MODE: int
        x: int
        y: int
        # MODE: int | None
        # x: int | tuple | None
        # y: int | tuple | None

        def __eq__(self, other: ReplyWindow.ReplyValues):
            ref: tuple

            def comp():
                if not isinstance(ref, tuple):
                    return otr == ref
                return ref[0] <= otr < ref[1]

            if self.MODE is not None and other.MODE != self.MODE:
                return False
            for ref, otr in zip((self.x, self.y), (other.x, other.y)):
                if ref is not None and not comp():
                    return False
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    @overload
    def __init__(self, *, MODE: int = None, x: int | tuple[int, int] = None, y: int | tuple[int, int] = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyWindow.ReplyValues = ReplyWindow.ReplyValues._ref(_kwargs)
            return
        try:
            mode, y, x = _seqs[2:-1].split(';')
            self.REPLY_VALUES: ReplyWindow.ReplyValues = self.ReplyValues(MODE=int(mode), x=int(x), y=int(y))
        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


class ReplyOSColor(Reply):
    """
    [OSC] Operating System Command Reply

    `ReplyOSColor['TARGET']`: int
        The index to which the value refers.
        
        - Palette colors:  (The real values of the palette colors are negated)
            - ``0`` | ``-8`` : black | bright black
            - ``-1`` | ``-9`` : red | bright red
            - ``-2`` | ``-10`` : green | bright green
            - ``-3`` | ``-11`` : yellow | bright yellow
            - ``-4`` | ``-12`` : blue | bright blue
            - ``-5`` | ``-13`` : magenta | bright magenta
            - ``-6`` | ``-14`` : cyan | bright cyan
            - ``-7`` | ``-15`` : white | bright white
            - ``-255 - 0``: remainder of the 256-color table
            
        - Environment colors:
            - ``10`` | ``15`` : foreground | Tektronix foreground
            - ``11`` | ``16`` : background | Tektronix background

        - Cursor colors:
            - ``12`` | ``18`` : standard | Tektronix cursor

        - Highlighting colors:
            - ``19`` : foreground
            - ``17`` : background

        - Pointer colors
            - ``13`` : foreground
            - ``14`` : background

    `ReplyOSColor['r']`: int
        red of the rgb value

    `ReplyOSColor['g']`: int
        green of the rgb value

    `ReplyOSColor['b']`: int
        blue of the rgb value

    ****

    # Resources:
     ; `xterm/OSC`_

    .. _`xterm/OSC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Operating-System-Commands

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    If a keyword is not specified, the comparison of this value is skipped and becomes True.

    :keyword TARGET: int: explicit | tuple[int, ...]: value contained
    :keyword R: int: explicit value | tuple[int, int]: value in range
    :keyword G: int: explicit value | tuple[int, int]: value in range
    :keyword B: int: explicit value | tuple[int, int]: value in range

    :raises InvalidReplyError:
    """
    class ReplyValues(NamedTuple):
        TARGET: int  # if <= 0 == rel
        R: int
        G: int
        B: int
        # TARGET: int | tuple | None
        # R: int | tuple | None
        # G: int | tuple | None
        # B: int | tuple | None

        def __eq__(self, other: ReplyOSColor.ReplyValues):
            ref: tuple

            def comp():
                if isinstance(ref, tuple):
                    return ref[0] <= otr < ref[1]
                return otr == ref

            if isinstance(self.TARGET, tuple) and other.TARGET not in self.TARGET:
                return False
            elif isinstance(self.TARGET, int) and other.TARGET != self.TARGET:
                return False
            for ref, otr in zip((self.R, self.G, self.B), (other.R, other.G, other.B)):
                if ref is not None and not comp():
                    return False
            return True

        @classmethod
        def _ref(cls, kwargs: dict):
            for kw in cls.__annotations__:
                kwargs.setdefault(kw, None)
            return cls(**kwargs)

    @overload
    def __init__(self, *, TARGET: int | tuple[int, ...] = None,
                 R: int | tuple[int, int] = None, G: int | tuple[int, int] = None, B: int | tuple[int, int] = None):
        ...

    def __init__(self, _seqs: str = None, **_kwargs):
        Reply.__init__(self)
        self.SEQS = _seqs
        if _seqs is None:
            self.REPLY_VALUES: ReplyOSColor.ReplyValues = ReplyOSColor.ReplyValues._ref(_kwargs)
            return
        try:
            params = _seqs[2:-2].split(';')
            r, g, b = params[-1][4:].split('/')
            r, g, b = int(r[:2], 16), int(g[:2], 16), int(b[:2], 16)
            if params[0] == "4":
                self.REPLY_VALUES: ReplyOSColor.ReplyValues = ReplyOSColor.ReplyValues(
                    TARGET=-int(params[1]), R=r, G=g, B=b)
            else:
                self.REPLY_VALUES: ReplyOSColor.ReplyValues = ReplyOSColor.ReplyValues(
                    TARGET=int(params[0]), R=r, G=g, B=b)
        except Exception as e:
            raise InvalidReplyError(self, _seqs, e)


def Eval(x: str) -> Reply | Type[Reply]:
    """Return a :class:`Reply` instance or type from a representative sting.

    :raise ValueError(exception): on errors with the original exception as argument."""
    try:
        if x.startswith('<class '):
            return eval(search("(?<=\\.)\\w+(?='>$)", x).group())
        else:
            return Reply.eval(x)
    except Exception as e:
        raise ValueError(e)
