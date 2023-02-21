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
from typing import Callable, Iterable, Literal, Type, Union, Any

from vtframework.iodata.esccontainer import EscSegment
from vtframework.iodata.c1ctrl import (
    FsFpnF,
    Fe,
    CSI,
    SS3,
    DCS,
    OSC,
    APP,
    UnknownESC,
)
from vtframework.iodata.c1ctrl import (
    isEscape27,
    isFsFpnFIntro,
    isFinal,
)
from vtframework.iodata.keys import (
    Key,
    Ctrl,
    FKey,
    NavKey,
    Meta,
    KeyPad,
    DelIns,
    EscEsc,
    ModKey,
)
from vtframework.iodata.mouse import Mouse
from vtframework.iodata.replies import (
    Reply,
    InvalidReplyError,
    ReplyCKS,
    ReplyCP,
    ReplyWindow,
    ReplyTIC,
    ReplyTID,
    ReplyDA,
    ReplyDECPM,
    ReplyOSColor,
)
from vtframework.iodata.chars import (
    Char,
    ASCII,
    UTF8,
    Space,
    Pasted,
)

_ESC_KEYS = {
    b'A': NavKey(NavKey.K.A_UP),  # (HP) (VT52)
    b'B': NavKey(NavKey.K.A_DOWN),  # (HP) (VT52)
    b'C': NavKey(NavKey.K.A_RIGHT),  # (HP) (VT52)
    b'D': NavKey(NavKey.K.A_LEFT),  # (HP) (VT52)
    b'F': NavKey(NavKey.K.C_END),  # (HP)
    b'J': DelIns(DelIns.K.HPClear),  # (HP)
    # b'P': DelIns(DelIns.K.DELETE),          # (HP)     # [ conflict with DCS ]
    # b'P': KeyPad(KeyPad.K.PF1),      # (VT52)   # [ conflict with DCS ]
    b'Q': DelIns(DelIns.K.INSERT),  # (HP)
    # b'Q': KeyPad(KeyPad.K.PF2),      # (VT52)
    b'R': KeyPad(KeyPad.K.PF3),  # (VT52)
    # b'S': KeyPad(KeyPad.K.PF4),      # (VT52)
    b'S': NavKey(NavKey.K.P_DOWN),  # (HP)
    b'T': NavKey(NavKey.K.P_UP),  # (HP)
    b'h': NavKey(NavKey.K.C_HOME),  # (HP)
}
_ESC_KEYS2 = {
    b'? ': Space(' '),  # (VT52)
    b'?I': Space('\t'),  # (VT52)
    b'?M': Space('\n'),  # (VT52)
    b'?j': KeyPad('*'),  # (VT52)
    b'?k': KeyPad('+'),  # (VT52)
    b'?l': KeyPad(','),  # (VT52)
    b'?m': KeyPad('-'),  # (VT52)
    b'?n': KeyPad('.'),  # (VT52)
    b'?o': KeyPad('/'),  # (VT52)
    b'?p': KeyPad(0),  # (VT52)
    b'?q': KeyPad(1),  # (VT52)
    b'?r': KeyPad(2),  # (VT52)
    b'?s': KeyPad(3),  # (VT52)
    b'?t': KeyPad(4),  # (VT52)
    b'?u': KeyPad(5),  # (VT52)
    b'?v': KeyPad(6),  # (VT52)
    b'?w': KeyPad(7),  # (VT52)
    b'?x': KeyPad(8),  # (VT52)
    b'?y': KeyPad(9),  # (VT52)
    b'?X': KeyPad('='),  # (VT52)
}
_SS3_KEYS = {
    b' ': Space(' '),  # (VT220) (PC)
    b'I': Space('\t'),  # (VT220) (PC)
    b'M': Space('\n'),  # (VT220) (PC)
    b'j': KeyPad('*'),  # (VT220) (PC)
    b'k': KeyPad('+'),  # (VT220) (PC)
    b'l': KeyPad(','),  # (VT220) (PC)
    b'm': KeyPad('-'),  # (VT220) (PC)
    b'n': KeyPad('.'),  # (VT220)
    b'o': KeyPad('/'),  # (VT220) (PC)
    b'p': KeyPad(0),  # (VT220)
    b'q': KeyPad(1),  # (VT220)
    b'r': KeyPad(2),  # (VT220)
    b's': KeyPad(3),  # (VT220)
    b't': KeyPad(4),  # (VT220)
    b'u': KeyPad(5),  # (VT220)
    b'v': KeyPad(6),  # (VT220)
    b'w': KeyPad(7),  # (VT220)
    b'x': KeyPad(8),  # (VT220)
    b'y': KeyPad(9),  # (VT220)
    b'X': KeyPad('='),  # (VT220)
}
_Fe = {
    # b'D': FeSeqs(b'D'),  # [ conflict with Key LEFT ]
    b'E': Fe('E'),
    # b'F': FeSeqs('F'),  # [ conflict with Key END ]
    b'H': Fe('H'),
    b'M': Fe('M'),
    b'V': Fe('V'),
    b'W': Fe('W'),
    b'Z': Fe('Z'),
    b'\\': Fe('\\')
}
_FsFpnF = {
    b'n': FsFpnF('n'),
    b'o': FsFpnF('o'),
    b'|': FsFpnF('|'),
    b'}': FsFpnF('}'),
    b'~': FsFpnF('~'),
    b'6': FsFpnF('6'),
    b'9': FsFpnF('9'),
    b'7': FsFpnF('7'),
    b'8': FsFpnF('8'),
    b'=': FsFpnF('='),
    b'>': FsFpnF('>'),
    b'c': FsFpnF('c'),
    b'l': FsFpnF('l'),
    b'm': FsFpnF('m'),
}


class _FKeyInterpreter:
    KEY_CHR_N1 = {
        b'O': b'A'
              b'B'
              b'C'
              b'D'
              b'F'
              b'H'
              b'P'
              b'Q'
              b'R'
              b'S',
        b'[':
            b'A'
            b'B'
            b'C'
            b'D'
            b'E'
            b'F'
            b'G'
            b'H'
            b'I'
            b'L'
            b'P'
            b'Q'
            # b'R'  # [ conflict with CPR / DECXCPR if modified ]
            b'S'
            b'Z'
            b'z'
            b'~'
    }
    KEY_TILz = {  # CSI
        b'11': lambda _mod=0: FKey(1, _mod),  # <~ (PC)>
        b'12': lambda _mod=0: FKey(2, _mod),  # <~ (PC)>
        b'13': lambda _mod=0: FKey(3, _mod),  # <~ (PC)>
        b'14': lambda _mod=0: FKey(4, _mod),  # <~ (PC)>
        b'15': lambda _mod=0: FKey(5, _mod),  # <~ (PC)>
        b'17': lambda _mod=0: FKey(6, _mod),  # <~ (PC)>
        b'18': lambda _mod=0: FKey(7, _mod),  # <~ (PC)>
        b'19': lambda _mod=0: FKey(8, _mod),  # <~ (PC)>
        b'20': lambda _mod=0: FKey(9, _mod),  # <~ (PC)>
        b'21': lambda _mod=0: FKey(10, _mod),  # <~ (PC)>
        b'23': lambda _mod=0: FKey(11, _mod),  # <~ (PC)>
        b'24': lambda _mod=0: FKey(12, _mod),  # <~ (PC)>
        b'25': lambda _mod=0: FKey(13, _mod),  # <~ (VT220)>
        b'26': lambda _mod=0: FKey(14, _mod),  # <~ (VT220)>
        b'28': lambda _mod=0: FKey(15, _mod),  # <~ (VT220)>
        b'29': lambda _mod=0: FKey(16, _mod),  # <~ (VT220)>
        b'31': lambda _mod=0: FKey(17, _mod),  # <~ (VT220)>
        b'32': lambda _mod=0: FKey(18, _mod),  # <~ (VT220)>
        b'33': lambda _mod=0: FKey(19, _mod),  # <~ (VT220)>
        b'34': lambda _mod=0: FKey(20, _mod),  # <~ (VT220)>
        b'6': lambda _mod=0: NavKey(NavKey.K.P_DOWN, _mod),  # <~ (DEC) (VT220)>
        b'5': lambda _mod=0: NavKey(NavKey.K.P_UP, _mod),  # <~ (DEC) (VT220)>
        b'3': lambda _mod=0: DelIns(DelIns.K.DELETE, _mod),  # <~ (PC) (VT220)> <z (SUN)>
        b'2': lambda _mod=0: DelIns(DelIns.K.INSERT, _mod),  # <~ (PC) (VT220)> <z (SUN)>
        b'1': lambda _mod=0: NavKey(NavKey.K.C_HOME, _mod),  # <~ (VT220)> <z (SUN)>
        b'4': lambda _mod=0: NavKey(NavKey.K.C_END, _mod),  # <~ (VT220)> <z (SUN)>
        b'214': lambda _mod=0: NavKey(NavKey.K.C_HOME, _mod),  # <z (SUN)>
        b'220': lambda _mod=0: NavKey(NavKey.K.C_END, _mod),  # <z (SUN)>
        b'218': lambda _mod=0: NavKey(NavKey.K.C_BEGIN, _mod),  # <z (SUN)>
        b'222': lambda _mod=0: NavKey(NavKey.K.P_DOWN, _mod),  # <z (SUN)>
        b'216': lambda _mod=0: NavKey(NavKey.K.P_UP, _mod),  # <z (SUN)>
        b'196': lambda _mod=0: FKey(15, _mod),  # <z (SUN)>
        b'197': lambda _mod=0: FKey(16, _mod),  # <z (SUN)>
    }  # ~ | z
    KEY_CAP = {  # CSI | SS3
        0x50: lambda _mod=0: FKey(1, _mod),  # P <SS3 (PC)>    # [ in conflict with KeyPad.K_PF1 (VT220) (PC) ]
        0x51: lambda _mod=0: FKey(2, _mod),  # Q <SS3 (PC)>    # [ in conflict with KeyPad.K_PF1 (VT220) (PC) ]
        0x52: lambda _mod=0: FKey(3, _mod),  # R <SS3 (PC)>    # [ in conflict with KeyPad.K_PF1 (VT220) (PC) ]
        0x53: lambda _mod=0: FKey(4, _mod),  # S <SS3 (PC)>    # [ in conflict with KeyPad.K_PF1 (VT220) (PC) ]
        0x41: lambda _mod=0: NavKey(NavKey.K.A_UP, _mod),  # A <CSI (PC) (SCO)><SS3 (PC) (DEC) (SUN)>
        0x42: lambda _mod=0: NavKey(NavKey.K.A_DOWN, _mod),  # B <CSI (PC) (SCO)><SS3 (PC) (DEC) (SUN)>
        0x43: lambda _mod=0: NavKey(NavKey.K.A_RIGHT, _mod),  # C <CSI (PC) (SCO)><SS3 (PC) (DEC) (SUN)>
        0x44: lambda _mod=0: NavKey(NavKey.K.A_LEFT, _mod),  # D <CSI (PC) (SCO)><SS3 (PC) (DEC) (SUN)>
        0x48: lambda _mod=0: NavKey(NavKey.K.C_HOME, _mod),  # H <CSI (PC) (SCO)><SS3 (PC)>
        0x46: lambda _mod=0: NavKey(NavKey.K.C_END, _mod),  # F <CSI (PC) (SCO)><SS3 (PC)>
        0x45: lambda _mod=0: NavKey(NavKey.K.C_BEGIN, _mod),  # E <CSI (SCO)>
        0x47: lambda _mod=0: NavKey(NavKey.K.P_DOWN, _mod),  # G <CSI (SCO)>
        0x49: lambda _mod=0: NavKey(NavKey.K.P_UP, _mod),  # I <CSI (SCO)>
        0x4c: lambda _mod=0: DelIns(DelIns.K.INSERT, _mod),  # L <CSI (SCO)>
        0x5a: lambda _mod=2: NavKey(NavKey.K.SHIFT_TAB, _mod),  # Z
    }

    @staticmethod
    def get(_seqs: bytes, _introducer: bytes):
        try:
            if _seqs[-1] not in _FKeyInterpreter.KEY_CHR_N1[_introducer]:
                return False
            if _seqs[-2:].startswith(b"'"):  # DECDC
                return False
            values = _seqs[:-1].split(b';')
            if len(values) not in range(1, 4):
                return False
            if len(values) == 3:
                if values[0] != b'27':
                    return False
                return ModKey(int(values[2]), int(values[1]))
            if _seqs[-1] in (0x7a, 0x7e):  # z ~
                if len(values) == 2:
                    return _FKeyInterpreter.KEY_TILz[values[0]](int(values[1]))
                return _FKeyInterpreter.KEY_TILz[values[0]]()
            if len(values) == 2:
                return _FKeyInterpreter.KEY_CAP[_seqs[-1]](int(values[1]))
            if len(_seqs) != 1:
                return False
            return _FKeyInterpreter.KEY_CAP[_seqs[-1]]()
        except (ValueError, KeyError):
            return False


class _ReplyInterpreter:

    class CSIReplies:
        introducer = b'['

        DA_CP_DECPM_param0 = 63  # ?
        DA_fin = 99  # c
        CP_fin = 82  # R
        DECPM_fin = b'$y'

        TIC_param0 = 62  # >
        TIC_fin = 99  # c

        WinReply_fin = 116  # t

    class DCSReplies:
        introducer = b'P'

        CKS_param_hint = b'!~'

        TID_param1 = 33  # !

    class OSCReplies:
        introducer = b']'

    @staticmethod
    def get(_seqs: bytes, _introducer: bytes):

        try:
            if _introducer == _ReplyInterpreter.CSIReplies.introducer:
                __seqs = EscSegment.new_raw('[', _seqs.decode())
                if _seqs[0] == _ReplyInterpreter.CSIReplies.DA_CP_DECPM_param0:
                    if _seqs[-1] == _ReplyInterpreter.CSIReplies.DA_fin:
                        return ReplyDA(__seqs)
                    if _seqs[-1] == _ReplyInterpreter.CSIReplies.CP_fin:
                        return ReplyCP(__seqs)
                    if _seqs[-2:] == _ReplyInterpreter.CSIReplies.DECPM_fin:
                        return ReplyDECPM(__seqs)
                elif _seqs[0] == _ReplyInterpreter.CSIReplies.TIC_param0:
                    if _seqs[-1] == _ReplyInterpreter.CSIReplies.TIC_fin:
                        return ReplyTIC(__seqs)
                elif _seqs[-1] == _ReplyInterpreter.CSIReplies.CP_fin:
                    return ReplyCP(__seqs)
                elif _seqs[-1] == _ReplyInterpreter.CSIReplies.WinReply_fin:
                    return ReplyWindow(__seqs)
            elif _introducer == _ReplyInterpreter.DCSReplies.introducer:
                __seqs = EscSegment.new_raw(_seqs.decode())
                if _ReplyInterpreter.DCSReplies.CKS_param_hint in _seqs:
                    return ReplyCKS(__seqs)
                elif _seqs[1] == _ReplyInterpreter.DCSReplies.TID_param1:
                    return ReplyTID(__seqs)
            elif _introducer == _ReplyInterpreter.OSCReplies.introducer:
                __seqs = EscSegment.new_raw(']', _seqs.decode())
                return ReplyOSColor(__seqs)
        except InvalidReplyError:
            return False


class _BaseInterpreter:
    """
    The base class of interpreters.

    Derivatives and structure:

    :class:`MainInterpreter` ->
        - :class:`BaseInterpreterFinalST`
            - :class:`DevCtrlStrInterpreter`
            - :class:`OSCmdInterpreter`
            - :class:`AppInterpreter`
        - :class:`SingeShiftInterpreter`
            - :class:`SingeShift3Interpreter`
        - :class:`CtrlSeqsInterpreter`
        - :class:`MouseInterpreter`
        - :class:`FsFpnFInterpreter`
        - :class:`Utf8Interpreter`
        - :class:`BrPasteMInterpreter`
    """
    finals: Iterable[int | tuple[int, int]] = ((0x30, 0x7e), 0x20)  # 0–9:;<=>?@A–Z[\]^_`a–z{|}~ SP

    _introducer: bytes
    _buffer: bytes
    _b: bytes
    buffer: bytes
    target: Callable[[bytes], Key | Char | EscSegment]

    bound: Callable[[_BaseInterpreter, bytes], Any]
    bound_final: Callable[[_BaseInterpreter, bytes], Any]

    @property
    def buffer(self) -> bytes:
        return self._introducer + self._buffer

    @buffer.setter
    def buffer(self, val: bytes) -> None:
        self._buffer = val

    def __init__(self, _t: Callable[[bytes], Key | Char | EscSegment]):
        self.target = _t
        self.bound = self.bound_final = lambda *_: None

    def __call__(self, _b: bytes, _i: bytes) -> _BaseInterpreter:
        self._buffer = self._b = _b
        self._introducer = _i
        return self

    def bind_to_char(self, __f: Callable[[_BaseInterpreter, bytes], Any]) -> _BaseInterpreter:
        self.bound = __f
        return self

    def bind_to_fin(self, __f: Callable[[_BaseInterpreter, bytes], Any]) -> _BaseInterpreter:
        self.bound_final = __f
        return self

    def bind(self, to_char: Callable[[_BaseInterpreter, bytes], Any], to_fin: Callable[[_BaseInterpreter, bytes], Any]
             ) -> _BaseInterpreter:
        return self.bind_to_char(to_char).bind_to_fin(to_fin)

    def _reset(self) -> None:
        self._buffer = self._b

    def _fin(self, __o, _fchar: bytes):
        self.bound_final(self, _fchar)
        if not __o:
            __o = UnknownESC(self._buffer.decode())
        self._reset()
        return __o

    def __lshift__(self, _char: bytes) -> Union[_BaseInterpreter, EscSegment, Key, Char, Reply]:
        self._buffer += _char
        if isFinal(_char, self.finals):
            return self._fin(self.target(self._buffer), _char)
        self.bound(self, _char)
        return self


class _FinalCount(int):
    def __init__(self, _count: int):
        self._count = _count

    def __eq__(self, item: int):
        self._count -= 1
        return not self._count


class Utf8Interpreter(_BaseInterpreter):
    """:class:`UTF8`-Sequence Interpreter"""

    def __init__(self):
        _BaseInterpreter.__init__(self, None)
        
    def __call__(self, _startbyte: bytes, _t: Callable[[bytes], UTF8 | Meta] = lambda b: UTF8(b.decode())) -> Utf8Interpreter:
        super().__call__(_startbyte, b'')
        self.target = _t
        for n, r in enumerate((((0xc2, 0xdf),), ((0xe0, 0xef),), ((0xf0, 0xf4),)), 1):
            if isFinal(_startbyte, r):
                self.finals = (_FinalCount(n),)
                break
        return self


class MouseInterpreter(_BaseInterpreter):
    """
    Interpreter for :class:`Mouse` actions. Sub-interpreter of :class:`CtrlSeqsInterpreter`.


    Activated by one of:  (:class:`DECPrivateMode`)
        - [CSI ? 9 h]
        - [CSI ? 1000 h]
        - [CSI ? 1002 h]
        - [CSI ? 1003 h]

    Modified by one of:  (:class:`DECPrivateMode`)
        - [CSI ? 1005 h]
        - [CSI ? 1006 h]
    """
    _BUTTONS = (
        (0, 4, 8, 16, 12, 20, 24, 28),
        (1, 5, 9, 17, 13, 21, 25, 29),
        (2, 6, 10, 18, 14, 22, 26, 30),
        (3, 7, 11, 19, 15, 23, 27, 31),
        (32, 36, 40, 48, 44, 52, 56, 60),
        (33, 37, 41, 49, 45, 53, 57, 61),
        (34, 38, 42, 50, 46, 54, 58, 62),
        (35, 39, 43, 51, 47, 55, 59, 63),
        (64, 68, 72, 80, 76, 84, 88, 92),
        (65, 69, 73, 81, 77, 85, 89, 93)
    )
    button: int | None
    x: int | tuple | None
    y: int | tuple | None

    def __init__(self):
        _BaseInterpreter.__init__(self, None)

    def __call__(self, _mode: bytes) -> MouseInterpreter:
        self._introducer = self._buffer = self._b = b''
        self._introducer = b'[' + _mode
        self.finals, self.interpret = {
            b'M': ((_FinalCount(3),), self.interpret_M),
            b't': ((_FinalCount(2),), self.interpret_t),
            b'T': ((_FinalCount(6),), self.interpret_T),
            b'<': ((0x6d, 0x4d), self.interpret_SGR)  # mM
        }[_mode]
        self.button = None
        self.y = None
        self.x = None
        return self

    def _final(self, _chr: bytes):
        if isFinal(_chr, self.finals):
            self.bound_final(self, _chr)
            for buttons in self._BUTTONS:
                if self.button in buttons:
                    mod = self.button - buttons[0]
                    return Mouse(buttons[0], mod, self.x, self.y)
            return Mouse(self.button, -1, self.x, self.y)
        self.bound(self, _chr)
        return self

    def interpret_t(self, _char: bytes):
        self.button = Mouse.B.L_PRESS
        if self.y is None:
            self.y = ord(_char) - 32
        elif self.x is None:
            self.x = ord(_char) - 32
        return self._final(_char)

    def interpret_T(self, _char: bytes):
        self.button = Mouse.B.L_MOVE
        if self.y is None:
            self.y = ord(_char) - 32
        elif self.x is None:
            self.x = ord(_char) - 32
        elif isinstance(self.y, int):
            self.y = (self.y, ord(_char) - 32)
        elif isinstance(self.x, int):
            self.x = (self.x, ord(_char) - 32)
        elif len(self.y) == 2:
            self.y += (ord(_char) - 32,)
        elif len(self.x) == 2:
            self.x += (ord(_char) - 32,)
        return self._final(_char)

    def interpret_M(self, _char: bytes):
        if self.button is None:
            self.button = ord(_char) - 32
        elif self.x is None:
            self.x = ord(_char) - 32
        elif self.y is None:
            self.y = ord(_char) - 32
        return self._final(_char)

    def interpret_SGR(self, _char: bytes):
        if self.button is None:
            if _char == b';':
                self.button = int(self._buffer)
                self._reset()
            else:
                self._buffer += _char
        elif self.x is None:
            if _char == b';':
                self.x = int(self._buffer)
                self._reset()
            else:
                self._buffer += _char
        elif self.y is None:
            if _char in b'mM':
                self.y = int(self._buffer)
                self._reset()
                if _char == b'm':
                    self.button = 3
            else:
                self._buffer += _char
        return self._final(_char)

    def __lshift__(self, _char: bytes) -> Union[MouseInterpreter, Mouse]:
        return self.interpret(_char)


class BrPasteMInterpreter(_BaseInterpreter):
    """
    Interpreter for bracketed :class:`Pasted` mode sequences beginning with ``"ESC [ 200 ~"``
    and terminated by ``"ESC [ 201 ~"``.

    Sub-interpreter of :class:`CtrlSeqsInterpreter`.

    Activated by:  (:class:`DECPrivateMode`)
        - [CSI ? 2004 h]
    """

    def __init__(self):
        _BaseInterpreter.__init__(self, lambda b: Pasted(b.decode()))
        self.finals = (0x7e,)  # ~
        
    def __call__(self) -> BrPasteMInterpreter:
        super().__call__(b'', b'[200~')
        return self

    def __lshift__(self, _char: bytes) -> Union[BrPasteMInterpreter, Pasted]:
        self._buffer += _char
        if isFinal(_char, self.finals):
            if isEscape27(self._buffer[-6:-5]) and self._buffer.endswith(b'[201~'):
                return self._fin(self.target(self._buffer[:-6]), b'[201~')
        self.bound(self, _char)
        return self


class CtrlSeqsInterpreter(_BaseInterpreter):
    """
    Interpreter for control sequences beginning with ``"["`` (:class:`CSI`).

    Most keystrokes and all mouse actions are represented by them.
    Mouse actions are forwarded to :class:`MouseInterpreter`.
    Bracketed paste forwarded to :class:`BrPasteMInterpreter`.
    """

    MouseInterpreter: MouseInterpreter
    BrPasteMInterpreter: BrPasteMInterpreter

    def __init__(self, mouseinterpreter: MouseInterpreter, brpasteminterpreter: BrPasteMInterpreter):
        _BaseInterpreter.__init__(self, lambda b: CSI(b.decode()))
        self.finals = ((0x40, 0x7e),)  # @A–Z[\]^_`a–z{|}~
        self._MOUSE = b'MtT<'
        super().__call__(b'', b'[')
        self.MouseInterpreter = mouseinterpreter
        self.BrPasteMInterpreter = brpasteminterpreter

    def __lshift__(self, _char: bytes
                   ) -> Union[CtrlSeqsInterpreter, MouseInterpreter, BrPasteMInterpreter, Key, Reply, CSI, UnknownESC]:
        if not self._buffer and _char in self._MOUSE:
            self.bound(self, _char)
            return self.MouseInterpreter.__call__(_char)
        self._buffer += _char
        if isFinal(_char, self.finals):
            if self._buffer == b'200~':
                self._reset()
                return self.BrPasteMInterpreter.__call__()
            if fkey := _FKeyInterpreter.get(self._buffer, b'['):
                return self._fin(fkey, _char)
            if rep := _ReplyInterpreter.get(self._buffer, b'['):
                return self._fin(rep, _char)
            return self._fin(self.target(self._buffer), _char)
        self.bound(self, _char)
        return self


class FsFpnFInterpreter(_BaseInterpreter):
    """Interpreter for the less complex Fs-, Fp- and nF- Escape Sequences (:class:`FsFpnF`)."""

    def __init__(self):
        _BaseInterpreter.__init__(self, lambda b: FsFpnF(b.decode()))
        self.finals = ((0x30, 0x7e),)  # 0–9:;<=>?@A–Z[\]^_`a–z{|}~
        
    def __call__(self, _b) -> FsFpnFInterpreter:
        super().__call__(_b, _b)
        return self

    def __lshift__(self, _char: bytes) -> Union[FsFpnFInterpreter, FsFpnF, UnknownESC]:
        self._buffer += _char
        if isFinal(_char, self.finals):
            if __FsFpnF := self.target(self._buffer):
                return self._fin(__FsFpnF, _char)
            return self._fin(UnknownESC(self._buffer.decode()), _char)
        self.bound(self, _char)
        return self


class SingeShiftInterpreter(_BaseInterpreter):
    """
    Base class for interpreters of single-shift sequences beginning with
    ``"N"`` (SS2) and ``"O"`` (:class:`SS3`). This is only used for SS2 and creates a :class:`Fe` sequence.

    Derivatives:
        - :class:`SingeShift3Interpreter`
    """

    def __init__(self, _t):
        _BaseInterpreter.__init__(self, _t)
        self.finals = ((0x40, 0x7e), 0x20)  # @A–Z[\]^_`a–z{|}~ SP
        self.__call__(b'N', b'')


class SingeShift3Interpreter(SingeShiftInterpreter):
    """
    Interpreter for single-shift select G3 sequences starting with ``"O"`` (:class:`SS3`).

    Used less frequently for the representation of keystrokes.
    But mostly for the unmodified representation of F1 to F4 or arrow keys.
    """

    def __init__(self):
        SingeShiftInterpreter.__init__(self, lambda b: SS3(b.decode()))
        self.__call__(b'', b'O')

    def __lshift__(self, _char: bytes) -> Union[SingeShift3Interpreter, Key, SS3, UnknownESC]:
        self._buffer += _char
        if isFinal(_char, self.finals):
            if key := _SS3_KEYS.get(self._buffer):
                return self._fin(key, _char)
            if fkey := _FKeyInterpreter.get(self._buffer, b'O'):
                return self._fin(fkey, _char)
            return self._fin(self.target(self._buffer), _char)
        self.bound(self, _char)
        return self


class BaseInterpreterFinalST(_BaseInterpreter):
    """
    Base interpreter for escape sequences starting with ``"P"`` (:class:`DCS`), ``"X"`` (SOS (:class:`APP`)),
    ``"]"`` (:class:`OSC`), ``"^"`` (PM (:class:`APP`)) or ``"_"`` (APC (:class:`APP`)) and terminated by a string
    terminator ``"ESC \\"`` (ST).

    Derivatives:
        - :class:`DevCtrlStrInterpreter`  (DCS)
        - :class:`OSCmdInterpreter`  (OSC)
        - :class:`AppInterpreter`  (SOS, PM, APC)
    """

    class _Final(int):
        def __init__(self):
            self._esc_match = False

        def __eq__(self, item: int):
            if self._esc_match:
                self._esc_match = False
                if item == 0x5c:
                    return True
                return False
            if item == 27:
                self._esc_match = True

    def __init__(self, _t):
        _BaseInterpreter.__init__(self, _t)
        self.finals = (self._Final(),)


class DevCtrlStrInterpreter(BaseInterpreterFinalST):
    """
    Interpreter for Device-Control-String sequences beginning with ``"P"`` (:class:`DCS`) and terminated by
    ``"ESC \\"`` (ST). Are used for some replies.
    """

    def __init__(self):
        BaseInterpreterFinalST.__init__(self, lambda b: DCS(esc_string=b[:-2].decode()))
        self.__call__(b'', b'P')

    def __lshift__(self, _char: bytes) -> Union[DevCtrlStrInterpreter, Reply, DCS, UnknownESC]:
        self._buffer += _char
        if isFinal(_char, self.finals):
            if rep := _ReplyInterpreter.get(self._buffer, b'P'):
                return self._fin(rep, _char)
            return self._fin(self.target(self._buffer), _char)
        self.bound(self, _char)
        return self


class OSCmdInterpreter(BaseInterpreterFinalST):
    """
    Interpreter for Operating-System-Command sequences beginning with ``"]"`` (:class:`OSC`) and terminated by
    ``"ESC \\"`` (ST). Used for OSC-replies.
    """

    def __init__(self):
        BaseInterpreterFinalST.__init__(self, lambda b: OSC(esc_string=b[:-2].decode()))
        self.__call__(b'', b']')

    def __lshift__(self, _char: bytes) -> Union[OSCmdInterpreter, OSC, UnknownESC]:
        self._buffer += _char
        if isFinal(_char, self.finals):
            if rep := _ReplyInterpreter.get(self._buffer, b']'):
                return self._fin(rep, _char)
            return self._fin(self.target(self._buffer), _char)
        self.bound(self, _char)
        return self


class AppInterpreter(BaseInterpreterFinalST):
    """
    Interpreter for :class:`APP`-lication defined sequences beginning with
        - ``"X"`` (SOS)
        - ``"^"`` (PM)
        - ``"_"`` (APC)
    and terminated by ``"ESC \\"`` (ST).
    """

    def __init__(self, _i: Literal[b'X', b'^', b'_']):
        BaseInterpreterFinalST.__init__(self, lambda b: APP(_i.decode(), esc_string=b[1:-2].decode()))
        self.__call__(b'', _i)

    def __lshift__(self, _char: bytes) -> Union[AppInterpreter, APP, UnknownESC]:
        self._buffer += _char
        if isFinal(_char, self.finals):
            return self._fin(self.target(self._buffer), _char)
        self.bound(self, _char)
        return self


class _CodeNumPredefinedValue(tuple):

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    def __add__(self, other) -> _CodeNumPredefinedValue:
        return self.__class__(*self, *other)


class _CodeNumProperty(Iterable):

    _VALS: tuple[int | tuple[int, int]] | _CodeNumPredefinedValue

    def __iter__(self):
        for i in self._VALS:
            yield i

    def set(self, *args: int | tuple[int, int] | _CodeNumPredefinedValue):
        vals = list()
        for arg in args:
            if isinstance(arg, _CodeNumPredefinedValue):
                vals.extend(arg)
            else:
                vals.append(arg)
        self._VALS = tuple(vals)


class _ProtectedIntroducers(_CodeNumProperty):

    Fe_REPLIES = _CodeNumPredefinedValue(0x4f, 0x50, 0x5b, 0x5d)  # O P [ ]  (SS3, DCS, CSI, OSC)
    Fe_App = _CodeNumPredefinedValue(0x58, 0x5e, 0x5f)
    Fe_Seqs = _CodeNumPredefinedValue(0x44, 0x45, 0x46, 0x48, (0x4d, 0x50), 0x56, 0x57, 0x58, 0x5a, (0x5b, 0x5f))
    Fs_Seqs = _CodeNumPredefinedValue(0x63, (0x6d, 0x6f), 0x7c, 0x7d, 0x7e)
    Fp_Seqs = _CodeNumPredefinedValue((0x36, 0x39), 0x3d, 0x3e)
    nF_Seqs = _CodeNumPredefinedValue(0x20, 0x23, 0x25, (0x28, 0x2b), 0x2d, 0x2e, 0x2f)
    VT52_Keys = _CodeNumPredefinedValue((0x41, 0x44), 0x52)
    VT52_KeyPad = _CodeNumPredefinedValue(0x3f, )
    HP_Keys = _CodeNumPredefinedValue((0x41, 0x44), 0x4a, 0x46, 0x51, 0x53, 0x54, 0x68)
    NONE = _CodeNumPredefinedValue()
    _VALS: tuple[int | tuple[int, int]] = Fe_REPLIES

    def set(self, *args: int | tuple[int, int] | _CodeNumPredefinedValue):
        """
        Escaping sequences starting with these characters are further
        interpreted as escaping sequences and not as pressing ``Alt/Meta+Key`` (:class:`Meta`).

        The default value of ``(0x4f, 0x50, 0x5b, 0x5d)`` corresponds to
        ``("O" (SS3), "P" (DCS), "[" (CSI), "]" (OSC))``,
        these are regular response sequences or sequences of the keyboard or mouse.

        Can be set via `PROTECTED_INTRODUCERS.set()`. Collection of predefined values:
        ``Fe_REPLIES,
        Fe_App,
        Fe_Seqs,
        Fs_Seqs,
        Fp_Seqs,
        nF_Seqs,
        VT52_Keys,
        VT52_KeyPad,
        HP_Keys,
        NONE``

        :param args: Ranges can be defined via a tuple (start, inclusive end).
        """
        super().set(*args)


class _AcceptedMetaKeys(_CodeNumProperty):

    ASCII_CTRL = _CodeNumPredefinedValue((0x00, 0x1f), )
    ASCII = _CodeNumPredefinedValue((0x20, 0x7e), )
    DELETE = _CodeNumPredefinedValue(0x7f, )
    UTF8 = _CodeNumPredefinedValue(0xc2, 0xf4)
    NONE = _CodeNumPredefinedValue()
    _VALS: tuple[int | tuple[int, int]] = ((0x00, 0x7f), (0xc2, 0xf4))  # NUL - DEL, UTF8

    def set(self, *args: int | tuple[int, int] | _CodeNumPredefinedValue):
        """
        These characters are considered to be enabled for ``Alt/Meta+Key`` interpretation (:class:`Meta`).

        The default values of ``((0x00, 0x7f), (0xc2, 0xf4))`` span the range of
        ASCII Control Characters, ASCII Printable Characters,
        ASCII Delete and the start bytes of UTF8 sequences -- so all.

        Can be set via ``ACCEPTED_META_KEYS.set()``. Collection of predefined values:
        ``ASCII_CTRL,
        ASCII,
        DELETE,
        UTF8,
        NONE``

        :param args: Ranges can be defined via a tuple (start, inclusive end).
        """
        super().set(*args)


class _SpaceTargets(_CodeNumProperty):

    TAB = _CodeNumPredefinedValue(0x09, )
    LINEFEED = _CodeNumPredefinedValue(0x0a, )
    RETURN = _CodeNumPredefinedValue(0x0d, )
    SPACE = _CodeNumPredefinedValue(0x20, )
    ENTER = LINEFEED + RETURN
    ANY = ENTER + SPACE + TAB
    NONE = _CodeNumPredefinedValue()
    _VALS: tuple[int | tuple[int, int]] = (0x20,)

    def set(self, *args: int | tuple[int, int] | _CodeNumPredefinedValue):
        """
        Create ``Tab``, ``Return``, ``Linefeed`` or ``Space`` as :class:`Space` instead of :class:`Ctrl`.

        Can be set via ``SPACE_TARGETS.set()``. Collection of predefined values:
        ``TAB,
        LINEFEED,
        RETURN,
        SPACE,
        ENTER(LINEFEED and RETURN),
        ANY,
        NONE``

        Default:
            - ``Space`` -> `Space`
            - ``Tab``, ``Return``, ``Linefeed`` -> `Ctrl`

        :param args: Ranges can be defined via a tuple (start, inclusive end).
        """
        super().set(*args)


class MainInterpreter(_BaseInterpreter):
    """
    This is the main interpreter object, all other interpreter types in the module are used by this one.

    The input types of the framework are created character by character by this object.
    The interpretation starts with the first call of the interpreter's ``__call__`` method, depending on whether the
    character is completed at the call, an input type or a subinterpreter is returned.
    Subinterpreters obtain the following characters through ``__lshift__`` until the sequential input is completed and
    an input type is returned. The query whether the return value is a complete input type is made by ``isdone()``.

    >>> sequence = interpreter(char)
    >>> while not interpreter.isdone(sequence):
    >>>     sequence <<= char
        
    The complete generation of final objects can be done via ``gen``.

    The class provides a close interface to the processed characters through methods with ``bind_`` prefix.

    Since the combined input with Alt/Meta prefixes the character with an escape character, the way in which an escape
    sequence is to be interpreted can be determined by the ``ACCEPTED_META_KEYS`` and ``PROTECTED_INTRODUCERS``
    attributes.

    ``PROTECTED_INTRODUCERS`` defines code numbers of introductory characters to be interpreted as escape sequence.
    By default, the values ``(0x4f, 0x50, 0x5b, 0x5d)`` = ``("O" (SS3), "P" (DCS), "[" (CSI), "]" (OSC))``
    are used, these are the components of the control characters for the regular response sequences and the inputs of
    the mouse or function keys of the keyboard.
    Inside the attribute is a collection of predefined values, and it can be modified via
    ``PROTECTED_INTRODUCERS.set()``.

    ``ACCEPTED_META_KEYS`` defines code numbers of characters that are accepted as :class:`Meta`\ types.
    By default, all characters (which are not picked up by ``PROTECTED_INTRODUCERS``) are accepted.
    Inside the attribute is a collection of predefined values, and it can be modified via
    ``ACCEPTED_META_KEYS.set()``.

    Whether ``Tab``, ``Return``, ``Linefeed`` or ``Space`` is to be created as :class:`Space` or :class:`Ctrl` can
    be determined via ``SPACE_TARGETS``. By default, only ``Space`` is created as Space.
    Inside the attribute is a collection of predefined values, and it can be modified via
    ``SPACE_TARGETS.set()``.

    ****

    ****

    # Recources:
     ; `xterm/CSI`_ ff.
     ; `xterm/OSC`_ ff.
     ; `xterm/Special-Keyboard-Keys`_ ff.
     ; `microsoft/console-virtual-terminal-sequences/input-sequences`_

    .. _`xterm/CSI`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Functions-using-CSI-%5f-ordered-by-the-final-character%5fs%5f
    .. _`xterm/OSC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Operating-System-Commands
    .. _`xterm/Special-Keyboard-Keys`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Special-Keyboard-Keys
    .. _`microsoft/console-virtual-terminal-sequences/input-sequences`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#input-sequences
    """

    _Esc_Interpreters: dict[bytes,
                            SingeShiftInterpreter
                            | DevCtrlStrInterpreter
                            | AppInterpreter
                            | OSCmdInterpreter
                            | CtrlSeqsInterpreter
                            | SingeShift3Interpreter]
    _UTF8_Interpreter: Utf8Interpreter
    _FsFpnF_Interpreter: FsFpnFInterpreter

    PROTECTED_INTRODUCERS: _ProtectedIntroducers

    ACCEPTED_META_KEYS: _AcceptedMetaKeys

    SPACE_TARGETS: _SpaceTargets

    bound_esc: Callable[[], Any]
    bound_esc_intro: Callable[[bytes], Any]

    esc_sequences: bool

    def __init__(self, esc_sequences: bool = True):
        _BaseInterpreter.__init__(self, None)
        super().__call__(b'', b'')
        self.esc_sequences = esc_sequences
        self.PROTECTED_INTRODUCERS = _ProtectedIntroducers()
        self.ACCEPTED_META_KEYS = _AcceptedMetaKeys()
        self.SPACE_TARGETS = _SpaceTargets()
        self._Esc_Interpreters = {b'N': SingeShiftInterpreter(lambda b: Fe(b.decode())),
                                  b'P': DevCtrlStrInterpreter(),
                                  b'X': AppInterpreter(b'X'),
                                  b']': OSCmdInterpreter(),
                                  b'^': AppInterpreter(b'^'),
                                  b'_': AppInterpreter(b'_'),
                                  b'[': CtrlSeqsInterpreter(MouseInterpreter(), BrPasteMInterpreter()),
                                  b'O': SingeShift3Interpreter()}
        self._UTF8_Interpreter = Utf8Interpreter()
        self._FsFpnF_Interpreter = FsFpnFInterpreter()
        self.bound_esc = self.bound_esc_intro = lambda *_: None

    def __call__(self, _in: bytes) -> Ctrl | ASCII | DelIns | Space | Utf8Interpreter | MainInterpreter:

        # EOT (Windows Ctrl+Z)
        if not _in:
            return Ctrl('Z')

        # ASCII
        if isFinal(_in, ((0x21, 0x7e),)):
            return ASCII(_in.decode())

        # Backspace, Ctrl+Backspace
        if isFinal(_in, (0x7f, 0x08)):
            return DelIns(DelIns.K.BACKSPACE, (DelIns.M.CTRL if ord(_in) == 0x08 else 0))

        # Tab Linefeed Return Space  (0x09, 0x0a, 0x0d, 0x20)
        if isFinal(_in, self.SPACE_TARGETS):
            return Space(_in.decode())

        # Utf8 start byte
        if isFinal(_in, ((0xc2, 0xf4),)):
            utfi = self._UTF8_Interpreter.__call__(_in)
            utfi.bound(utfi, _in)
            return utfi

        # ESC
        if self.esc_sequences:
            if isFinal(_in, (0x1b,)):
                self.bound_esc()
                return self

        # ASCII control
        if isFinal(_in, ((0x00, 0x20),)):
            return Ctrl(_in)

    @staticmethod
    def isdone(__o) -> bool:
        """Return whether the object is a completed sequence."""
        return not isinstance(__o, _BaseInterpreter)

    def gen(self, _in: Callable[[], bytes]) -> EscSegment | Key | Mouse | Reply | Char:
        """Generate a complete sequence from the return values of `_in`."""
        seq = self(_in())
        while not self.isdone(seq):
            seq <<= _in()
        return seq

    @staticmethod
    def _getunknown(seqs: bytes):
        try:
            return _ESC_KEYS2[seqs]
        except KeyError:
            return UnknownESC(seqs.decode())

    def __lshift__(self, _introducer: bytes) -> _BaseInterpreter | EscSegment | Key | Char | Reply:

        self.bound_esc_intro(_introducer)

        if isFinal(_introducer, (0x1b,)):
            return EscEsc()

        if not isFinal(_introducer, self.PROTECTED_INTRODUCERS):

            if isFinal(_introducer, self.ACCEPTED_META_KEYS):

                # Alt+Backspace, Alt+Ctrl+Backspace
                if isFinal(_introducer, (0x7f, 0x08)):
                    if ord(_introducer) == 0x08:
                        return DelIns(DelIns.K.BACKSPACE, DelIns.M.CTRL & DelIns.M.ALT)
                    return DelIns(DelIns.K.BACKSPACE, DelIns.M.ALT)

                # Utf8 start byte
                if isFinal(_introducer, ((0xc2, 0xf4),)):
                    return self._UTF8_Interpreter.__call__(_introducer, lambda _b: Meta(_b.decode()))

                return Meta(_introducer)

        try:
            return _FsFpnF[_introducer]
        except KeyError:
            pass
        try:
            return _Fe[_introducer]
        except KeyError:
            pass
        try:
            return _ESC_KEYS[_introducer]
        except KeyError:
            pass

        if isFsFpnFIntro(_introducer.decode(), False):
            return self._FsFpnF_Interpreter.__call__(_introducer)

        return self._Esc_Interpreters.get(_introducer, _BaseInterpreter(self._getunknown).__call__(_introducer, b''))

    def bind_esc(self, __f: Callable[[], Any] = lambda *_: None) -> None:
        """Bind the execution of function `__f` to the occurrence of an introductory escape character."""
        self.bound_esc = __f

    def bind_intro(self, __f: Callable[[bytes], Any] = lambda *_: None) -> None:
        """
        Bind the execution of function `__f` to the introductory character of an escape sequence after the escape
        character. The function gets the character when it is executed.
        The introductory character after escape, is also known as the second component part of the control character,
        a sequence could be finalized by this.
        """
        self.bound_esc_intro = __f

    def bind_to_interpreter(self, interpreter: Type[Utf8Interpreter
                                                    | FsFpnFInterpreter
                                                    | SingeShiftInterpreter
                                                    | BaseInterpreterFinalST
                                                    | DevCtrlStrInterpreter
                                                    | AppInterpreter
                                                    | OSCmdInterpreter
                                                    | CtrlSeqsInterpreter
                                                    | SingeShift3Interpreter
                                                    | BrPasteMInterpreter
                                                    | MouseInterpreter] | Literal['any'],
                            to_char: Literal['param', 'p', 'final', 'f', 'any'],
                            __f: Callable[[_BaseInterpreter, bytes], Any] = lambda *_: None) -> None:
        """
        Bind within the sequence `interpreter` type, to the parameter characters and/or to the final character,
        the execution of function `__f`.

        The `interpreter` is defined as a type and passed to ``isinstance()`` to determine the target.
        Note the hierarchy of interpreter classes for this:

        - :class:`BaseInterpreterFinalST`
            - :class:`DevCtrlStrInterpreter`
            - :class:`OSCmdInterpreter`
            - :class:`AppInterpreter`
        - :class:`SingeShiftInterpreter`
            - :class:`SingeShift3Interpreter`
        - :class:`CtrlSeqsInterpreter`
        - :class:`MouseInterpreter`
        - :class:`FsFpnFInterpreter`
        - :class:`Utf8Interpreter`
        - :class:`BrPasteMInterpreter`

        For binding to all types, ``"any"`` can be specified.

        The character type `to_char` can be specified as ``"param"`` or ``"final"``; or as ``"any"`` for both types.

        The function `__f` receives at execution the active interpreter object and the character as parameterization.
        """
        if interpreter == Utf8Interpreter:
            if to_char == 'p':
                self._UTF8_Interpreter.bind_to_char(__f)
            elif to_char == 'f':
                self._UTF8_Interpreter.bind_to_fin(__f)
            else:
                self._UTF8_Interpreter.bind(__f, __f)
        elif interpreter == FsFpnFInterpreter:
            if to_char == 'p':
                self._FsFpnF_Interpreter.bind_to_char(__f)
            elif to_char == 'f':
                self._FsFpnF_Interpreter.bind_to_fin(__f)
            else:
                self._FsFpnF_Interpreter.bind(__f, __f)
        elif interpreter == BrPasteMInterpreter:
            if to_char == 'p':
                self._Esc_Interpreters[b'['].BrPasteMInterpreter.bind_to_char(__f)
            elif to_char == 'f':
                self._Esc_Interpreters[b'['].BrPasteMInterpreter.bind_to_fin(__f)
            else:
                self._Esc_Interpreters[b'['].BrPasteMInterpreter.bind(__f, __f)
        elif interpreter == MouseInterpreter:
            if to_char == 'p':
                self._Esc_Interpreters[b'['].MouseInterpreter.bind_to_char(__f)
            elif to_char == 'f':
                self._Esc_Interpreters[b'['].MouseInterpreter.bind_to_fin(__f)
            else:
                self._Esc_Interpreters[b'['].MouseInterpreter.bind(__f, __f)
        else:
            if interpreter == 'any':
                interpreter = object
                if to_char == 'p':
                    self._UTF8_Interpreter.bind_to_char(__f)
                    self._FsFpnF_Interpreter.bind_to_char(__f)
                    self._Esc_Interpreters[b'['].BrPasteMInterpreter.bind_to_char(__f)
                    self._Esc_Interpreters[b'['].MouseInterpreter.bind_to_char(__f)
                elif to_char == 'f':
                    self._UTF8_Interpreter.bind_to_fin(__f)
                    self._FsFpnF_Interpreter.bind_to_fin(__f)
                    self._Esc_Interpreters[b'['].BrPasteMInterpreter.bind_to_fin(__f)
                    self._Esc_Interpreters[b'['].MouseInterpreter.bind_to_fin(__f)
                else:
                    self._UTF8_Interpreter.bind(__f, __f)
                    self._FsFpnF_Interpreter.bind(__f, __f)
                    self._Esc_Interpreters[b'['].BrPasteMInterpreter.bind(__f, __f)
                    self._Esc_Interpreters[b'['].MouseInterpreter.bind(__f, __f)
            if to_char == 'p':
                def bind(_inter: _BaseInterpreter):
                    _inter.bind_to_char(__f)
            elif to_char == 'f':
                def bind(_inter: _BaseInterpreter):
                    _inter.bind_to_fin(__f)
            else:
                def bind(_inter: _BaseInterpreter):
                    _inter.bind_to_char(__f)
                    _inter.bind_to_fin(__f)
            for inter in self._Esc_Interpreters.values():
                if isinstance(inter, interpreter):
                    bind(inter)
