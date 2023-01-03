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
from typing import Literal
from typing import Iterable, Callable

from .esccontainer import EscSegment

try:
    from ..io.io import InputSuper
    __4doc1 = InputSuper
    from ..iosys.vtiinterpreter import MainInterpreter
    __4doc2 = MainInterpreter
except ImportError:
    pass


# [i] Escape character representations:
#
# octal = 0o033 | "\\033"
# hexadecimal = 0x1b | "\\x1b"
# unicode = \\u001b
# decimal = 27
# e = \\e
# ctrl_key = ^[
# powershell = $([char]27)
# powershell_e = `e


class NoneSeqs(str):
    """Type for incorrect sequences. (eq. ``str()``)"""
    def __bool__(self) -> bool:
        return False


NONE_SEQS = NoneSeqs()


class FsFpnF(EscSegment):
    """
    Fs | Fp | nF Escape Sequence

    Tell the Terminal to send C1 control characters as:
        - [S7C1T]   ESC SP F : 7-Bit sequences  <nF>
        - [S8C1T]   ESC SP G : 8-Bit sequences  <nF>
        VT200 always accept 8-Bit sequences except when configured for VT100
    Set ANSI conformance level to:
        - ESC SP L : level 1  <nF>
        - ESC SP M : level 2  <nF>
        - ESC SP N : level 3  <nF>
    DEC Screen:
        - [DECDHL] ESC # 3 : double-height line, top half (VT100)  <nF>
        - [DECDHL] ESC # 4 : double-height line, bottom half (VT100)  <nF>
        - [DECSWL] ESC # 5 : single-width line (VT100)  <nF>
        - [DECDWL] ESC # 6 : double-width line (VT100)  <nF>
        - [DECALN] ESC # 8 : Screen Alignment Test (VT100)  <nF>
    Select Character Set:
        - ESC % @  : Default (ISO 8859-1)  <nF>
        - ESC % G  : UTF-8  <nF>
        - ESC ( Param : Designate G0 Character Set (VT100)  <nF>
        - ESC ) Param : Designate G1 Character Set (VT100)  <nF>
        - ESC * Param : Designate G2 Character Set (VT220)  <nF>
        - ESC + Param : Designate G3 Character Set (VT220)  <nF>
        - ESC - Param : Designate G1 Character Set (VT300)  <nF>
        - ESC . Param : Designate G2 Character Set (VT300)  <nF>
        - ESC / Param : Designate G3 Character Set (VT300)  <nF>
        - [LS2] ESC n : Invoke the G2 Character Set as GL  <Fs>
        - [LS3] ESC o : Invoke the G3 Character Set as GL  <Fs>
        - [LS3R] ESC | : Invoke the G3 Character Set as GR  <Fs>
        - [LS2R] ESC } : Invoke the G2 Character Set as GR  <Fs>
        - [LS1R] ESC ~ : Invoke the G1 Character Set as GR (VT100)  <Fs>

    Index:
        - [DECBI] ESC 6 : Back Index (VT420)  <Fp>
        - [DECFI] ESC 9 : Forward Index (VT420)  <Fp>
    Cursor:
        - [DECSC] ESC 7 : Save Cursor (VT100)  <Fp>  **[i] Windows / UNIX compatible**
        - [DECRC] ESC 8 : Restore Cursor (VT100)  <Fp>  **[i] Windows / UNIX compatible**
    Keypad:
        - [DECKPAM] ESC = : Application Keypad  <Fp>  **[i] Windows / UNIX compatible**
        - [DECKPNM] ESC > : Normal Keypad (VT100)  <Fp>  **[i] Windows / UNIX compatible**

    - [RIS] ESC c : Full SGRReset (VT100)  <Fs>

    - ESC l : Memory Lock. Lock mamory above the cursor. (HP)  <Fs>
    - ESC m : Memory Unlock (HP)  <Fs>

    ****

    # Resources:
     ; `xterm/Controls-beginning-with-ESC`_
     ; `wikipedia/ANSI_escape_code/Fs_Escape_sequences`_
     ; `wikipedia/ANSI_escape_code/Fp_Escape_sequences`_
     ; `wikipedia/ANSI_escape_code/nF_Escape_sequences`_
     ; `microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`_
     ; `microsoft/console-virtual-terminal-sequences/mode-changes`_

    .. _`xterm/Controls-beginning-with-ESC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Controls-beginning-with-ESC
    .. _`wikipedia/ANSI_escape_code/Fs_Escape_sequences`: https://en.wikipedia.org/wiki/ANSI_escape_code#Fs_Escape_sequences
    .. _`wikipedia/ANSI_escape_code/Fp_Escape_sequences`: https://en.wikipedia.org/wiki/ANSI_escape_code#Fp_Escape_sequences
    .. _`wikipedia/ANSI_escape_code/nF_Escape_sequences`: https://en.wikipedia.org/wiki/ANSI_escape_code#nF_Escape_sequences
    .. _`microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#simple-cursor-positioning
    .. _`microsoft/console-virtual-terminal-sequences/mode-changes`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#mode-changes
    """

    @classmethod
    def new_FsFpnF(cls, __c: str) -> FsFpnF | NoneSeqs:
        """Create a new :class:`FsFpnF` type from the sequence `__c` (must be the escape-sequence without ESC prefix).
        Check the sequence before if the structure fits and return :class:`NoneSeqs` in case of no match."""
        if not isFsFpnF(__c):
            return NONE_SEQS
        return cls.new_esc(__c)

    def __new__(cls, __c: str) -> FsFpnF:
        """Create a new :class:`FsFpnF` type from the sequence `__c` (must be the escape-sequence without ESC prefix)."""
        return cls.new_esc(__c)


class Fe(EscSegment):
    r"""
    Fe (7-Bit) Escape Sequence

    - [IND]   ESC D (0x84): Index
    - [NEL]   ESC E (0x85): Next Line
    - [---]   ESC F (0x86): To the lower left corner
    - [HTS]   ESC H (0x88): Horizontal Tab Set  **[i] Windows / UNIX compatible**
    - [RI]    ESC M (0x8d): Reverse Index  **[i] Windows / UNIX compatible**
    - [SS2]   ESC N (0x8e): Single Shift Select of G2 Character Set (VT220) (Chr)
    - [SS3]   ESC O (0x8f): Single Shift Select of G3 Character Set (VT220) (Chr)
    - [DCS]   ESC P (0x90): Device Control String (Seq - t)
    - [SPA]   ESC V (0x96): Start of Protected Area
    - [EPA]   ESC W (0x97): End of Protected Area
    - [SOS]   ESC X (0x98): Start of String (Seq - t) (`APP`)
    - [DECID] ESC Z (0x9a): Terminal ID Request
    - [CSI]   ESC [ (0x9b): Control Sequence Introducer (Seq)
    - [ST]    ESC \\ (0x9c): String Terminator (t)
    - [OSC]   ESC ] (0x9d): Operating System Command (Seq - t)
    - [PM]    ESC ^ (0x9e): Private Message (Seq - t) (`APP`)
    - [APC]   ESC _ (0x9f): Application Program Command (Seq - t) (`APP`)

    Derivatives:
        - :class:`CSI`
        - :class:`SS3`
        - :class:`DCS`
        - :class:`OSC`
        - :class:`APP`

    ****

    # Resources:
     ; `xterm/C1-8-Bit-Control-Characters`_
     ; `wikipedia/ANSI_escape_code/Fe_Escape_sequences`_
     ; `microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`_
     ; `microsoft/console-virtual-terminal-sequences/tabs`_

    .. _`xterm/C1-8-Bit-Control-Characters`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-C1-%5F8-Bit%5F-Control-Characters
    .. _`wikipedia/ANSI_escape_code/Fe_Escape_sequences`: https://en.wikipedia.org/wiki/ANSI_escape_code#Fe_Escape_sequences
    .. _`microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#simple-cursor-positioning
    .. _`microsoft/console-virtual-terminal-sequences/tabs`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#tabs
    """

    @classmethod
    def new_Fe(cls, __c: str) -> Fe | NoneSeqs:
        """Create a new :class:`Fe` type from the sequence `__c` (must be the escape-sequence without ESC prefix).
        Check the sequence before if the structure fits and return :class:`NoneSeqs` in case of no match."""
        if not isFeIntro(__c, False):
            return NONE_SEQS
        return cls.new_esc(__c)

    def __new__(cls, __c: str) -> Fe:
        """Create a new :class:`Fe` type from the sequence `__c` (must be the escape-sequence without ESC prefix)."""
        return cls.new_esc(__c)


class CSI(Fe):
    """Control Sequence Introducer (0x9b) ``ESC [ ...``"""

    @classmethod
    def new_csi(cls, *params: str, string: str = '', outro: str = '') -> CSI:
        """Create a new :class:`CSI` type from the sequence parameters `params`.
        The fields `string` and `outro` are optional and will be processed according to :class:`EscSegment`."""
        return cls.new_esc('[', *params, string=string, outro=outro)

    def __new__(cls, *params: str, string: str = '', outro: str = '') -> CSI:
        """Create a new :class:`CSI` type from the sequence parameters `params`.
        The fields `string` and `outro` are optional and will be processed according to :class:`EscSegment`."""
        return cls.new_esc('[', *params, string=string, outro=outro)


class SS3(Fe):
    """Single Shift Select of G3 Character Set (VT220) (0x8f) ``ESC O ...``"""

    @classmethod
    def new_ss3(cls, *params: str, string: str = '', outro: str = '') -> SS3:
        """Create a new :class:`SS3` type from the sequence parameters `params`.
        The fields `string` and `outro` are optional and will be processed according to :class:`EscSegment`."""
        return cls.new_esc('O', *params, string=string, outro=outro)

    def __new__(cls, *params: str, string: str = '', outro: str = '') -> SS3:
        """Create a new :class:`SS3` type from the sequence parameters `params`.
        The fields `string` and `outro` are optional and will be processed according to :class:`EscSegment`."""
        return cls.new_esc('O', *params, string=string, outro=outro)


class DCS(Fe):
    """Device Control String (0x90) ``ESC P ...`` (terminated by ``ESC \\`` String Terminator (0x9c))"""

    @classmethod
    def new_dcs(cls, *params: str, esc_string: str = '') -> DCS:
        """Create a new :class:`DCS` type from the sequence parameters `params` and the escape-string `esc_string`."""
        return cls.new_pur(cls.new_raw('P', *params), esc_string, cls.new_raw('\\'))

    def __new__(cls, *params: str, esc_string: str = '') -> DCS:
        """Create a new :class:`DCS` type from the sequence parameters `params` and the escape-string `esc_string`."""
        return cls.new_pur(cls.new_raw('P', *params), esc_string, cls.new_raw('\\'))


class OSC(Fe):
    """Operating System Command (0x9d) ``ESC ] ...`` (terminated by ``ESC \\`` String Terminator (0x9c))"""

    @classmethod
    def new_osc(cls, *params: str, esc_string: str = '') -> OSC:
        """Create a new :class:`OSC` type from the sequence parameters `params` and the escape-string `esc_string`."""
        return cls.new_pur(cls.new_raw(']', *params), esc_string, cls.new_raw('\\'))

    def __new__(cls, *params: str, esc_string: str = '') -> OSC:
        """Create a new :class:`OSC` type from the sequence parameters `params` and the escape-string `esc_string`."""
        return cls.new_pur(cls.new_raw(']', *params), esc_string, cls.new_raw('\\'))


class APP(Fe):
    """
    Application defined Sequences  (terminated by ``ESC \\`` String Terminator (0x9c))
        - [SOS] ESC ``X`` Start of String (0x98)
        - [PM ] ESC ``^`` Private Message (0x9e)
        - [APC] ESC ``_`` Application Program Command (0x9f)
    """

    @classmethod
    def new_app(cls, __i: Literal['X', '^', '_'], *params: str, esc_string: str = '') -> APP | NoneSeqs:
        """Create a new :class:`APP` type from the intro character `__i`,
        the sequence parameters `params` and the escape-string `esc_string`.
        Check the sequence before if the structure fits and return :class:`NoneSeqs` in case of no match."""
        if __i not in ('X', '^', '_'):
            return NONE_SEQS
        return cls.new_pur(cls.new_raw(__i, *params), esc_string, cls.new_raw('\\'))

    def __new__(cls, __i: Literal['X', '^', '_'], *params: str, esc_string: str = '') -> APP:
        """Create a new :class:`APP` type from the intro character `__i`,
        the sequence parameters `params` and the escape-string `esc_string`."""
        return cls.new_pur(cls.new_raw(__i, *params), esc_string, cls.new_raw('\\'))


class UnknownESC(EscSegment):
    """
    Type for unknown escape sequence, generated by :class:`MainInterpreter`.
    """

    def __new__(cls, seqs: str) -> UnknownESC:
        return cls.new_esc(seqs)


class ManualESC(EscSegment):
    """
    Type for manually entered escape sequence (see :class:`InputSuper`).
    """

    def __new__(cls, seqs: str) -> ManualESC:
        return cls.new_esc(seqs)


def isEscape27(__c: bytes | str) -> bool:
    """Return whether `__c` is the escape character."""
    try:
        return 27 == ord(__c)
    except TypeError:
        return False


FsFpnFStruc: dict[str, tuple[str, ...]] = {
    ' ': ('F', 'G', 'L', 'M', 'N'),
    '#': ('3', '4', '5', '6', '8'),
    '%': ('@', 'G'),
    '()*+': (
        'A', '', 'C', '5', 'H', '7', 'K', 'Q', '9', 'R', 'f', 'y', 'Z', '4', '">', '%2', '%6', '%=',
        '=', '`', 'E', '6', '0', '<', '>', '"4', '"?', '%0', '%5', '&4', '%3', '&5'),
    '-./': ('A', '', 'F', 'H', 'L', 'M'),
    '6789=>clmno|}~': ('',)
}


def isFsFpnF(seqs: str, _intro_only: bool = False) -> bool:
    """Check if `seqs` is a Fs, Fp, or nF sequence.
    The escape character must not be prepended.
    Check only the intro character if `_intro_only` is True."""
    for _intro, _seqs in FsFpnFStruc.items():
        if seqs[:1] in _intro:
            if _intro_only:
                return True
            if seqs[1:] in _seqs:
                return True
            else:
                return False
    return False


def isFsFpnFIntro(seqs: str, has_esc: bool = True) -> bool:
    """Check if the intro character in `seqs` is a Fs, Fp, or nF sequence intro character.
    Check for a prefixed escape character if `has_esc` is True."""
    if isEscape27(seqs[:1]):
        seqs = seqs[1:]
    elif has_esc:
        return False
    return isFsFpnF(seqs, _intro_only=True)


def isFsFpnFSeqs(seqs: str, has_esc: bool = True) -> bool:
    """Check if `seqs` is a Fs, Fp, or nF sequence.
    Check for a prefixed escape character if `has_esc` is True."""
    if isEscape27(seqs[:1]):
        seqs = seqs[1:]
    elif has_esc:
        return False
    return isFsFpnF(seqs)


def isFinal(char: str | bytes, finals: Iterable[int | tuple[int, int]]) -> bool:
    """Return whether the Unicode code point of `char` is in `finals`.
    Values in `finals` are explicitly specified as integers or as ranges
    ( ``tuple(incl. start, incl. end)`` )."""
    x = ord(char)
    for i in finals:
        if isinstance(i, tuple):
            if i[0] <= x <= i[1]:
                return True
        elif x == i:
            return True


FeStruc: dict[str, Callable[[str], bool] | None] = {
    'DEFHMVWZ': None,
    'NO': lambda other: isFinal(other[-1:], ((0x40, 0x7e), 0x20)),
    '[': lambda other: isFinal(other[-1:], ((0x40, 0x7e),)),
    'PX]\\^_': lambda other: isEscape27(other[-2:-1]) and other[-1:] == '\\'
}


def isFe(seqs: str, _intro_only: bool = False) -> bool:
    """Check if `seqs` is a Fe sequence. The escape character must not be prepended.
    Check only the intro character if `_intro_only` is True."""
    for _intro, _seqs in FeStruc.items():
        if seqs[:1] in _intro:
            if _intro_only or _seqs is None:
                return True
            if _seqs(seqs):
                return True
            else:
                return False
    return False


def isFeIntro(seqs: str, has_esc: bool = True) -> bool:
    """Check if the intro character in `seqs` is a Fe sequence intro character.
    Check for a prefixed escape character if `has_esc` is True."""
    if isEscape27(seqs[:1]):
        seqs = seqs[1:]
    elif has_esc:
        return False
    return isFe(seqs, True)


def isFeSeqs(seqs: str, has_esc: bool = True) -> bool:
    """Check if `seqs` is a Fe sequence. Check for a prefixed escape character if `has_esc` is True."""
    if isEscape27(seqs[:1]):
        seqs = seqs[1:]
    elif has_esc:
        return False
    return isFe(seqs)
