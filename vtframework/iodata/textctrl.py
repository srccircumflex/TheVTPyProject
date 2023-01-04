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

from typing import Literal

from vtframework.iodata.c1ctrl import FsFpnF, CSI


class Erase:
    """
    VT100:
        - [ED] CSI 0 J  (.display_below)  **[i] Windows / UNIX compatible**
        - [ED] CSI 1 J  (.display_above)  **[i] Windows / UNIX compatible**
        - [ED] CSI 2 J  (.display)  **[i] Windows / UNIX compatible**
        - [ED] CSI 3 J  (.display_lines)  **[i] Windows / UNIX compatible**
        - [EL] CSI 0 K  (.line_right)  **[i] Windows / UNIX compatible**
        - [EL] CSI 1 K  (.line_left)  **[i] Windows / UNIX compatible**
        - [EL] CSI 2 K  (.line)  **[i] Windows / UNIX compatible**
        - [RIS] ESC c   (.terminal)

        Term: VT100

    VT220: (selective erase)
        - [DECSED] CSI ? 0 J  (.display_below) (default)
        - [DECSED] CSI ? 1 J  (.display_above)
        - [DECSED] CSI ? 2 J  (.display)
        - [DECSED] CSI ? 3 J  (.display_lines)
        - [DECSEL] CSI ? 0 K  (.line_right)
        - [DECSEL] CSI ? 1 K  (.line_left)
        - [DECSEL] CSI ? 2 K  (.line)
        - [DECSTR] CSI ! p    (.terminal)  **[i] Windows / UNIX compatible**

        Term: VT220

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/text-modification`_
     ; `microsoft/console-virtual-terminal-sequences/soft-reset`_
     ; `xterm/CSI`_
    
    .. _`microsoft/console-virtual-terminal-sequences/text-modification`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-modification
    .. _`microsoft/console-virtual-terminal-sequences/soft-reset`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#soft-reset
    .. _`xterm/CSI`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Functions-using-CSI-%5F-ordered-by-the-final-character%5Fs%5F
    """

    @staticmethod
    def display_below(vt100: bool = True) -> CSI:
        """
        - CSI 0 J (VT100)
        - CSI ? 0 J
        """
        return CSI(('?' if not vt100 else ''), '0J')

    @staticmethod
    def display_above(vt100: bool = True) -> CSI:
        """
        - CSI 1 J (VT100)
        - CSI ? 1 J
        """
        return CSI(('?' if not vt100 else ''), '1J')

    @staticmethod
    def display(vt100: bool = True) -> CSI:
        """
        - CSI 2 J (VT100)
        - CSI ? 2 J
        """
        return CSI(('?' if not vt100 else ''), '2J')

    @staticmethod
    def display_lines(vt100: bool = True) -> CSI:
        """
        Term: xterm

        - CSI 3 J (VT100)
        - CSI ? 3 J
        """
        return CSI(('?' if not vt100 else ''), '3J')

    @staticmethod
    def line_right(vt100: bool = True) -> CSI:
        """
        - CSI 0 K (VT100)
        - CSI ? 0 K
        """
        return CSI(('?' if not vt100 else ''), '0K')

    @staticmethod
    def line_left(vt100: bool = True) -> CSI:
        """
        - CSI 1 K (VT100)
        - CSI ? 1 K
        """
        return CSI(('?' if not vt100 else ''), '1K')

    @staticmethod
    def line(vt100: bool = True) -> CSI:
        """
        - CSI 2 K (VT100)
        - CSI ? 2 K
        """
        return CSI(('?' if not vt100 else ''), '2K')

    @staticmethod
    def terminal(vt100: bool = True) -> FsFpnF | CSI:
        """
        - ESC c (VT100)
        - CSI ! p
        """
        if vt100:
            return FsFpnF('c')
        else:
            return CSI('!p')


class TextModification:
    """
    Character positioning

    - [HPR] CSI n=1 a  (.chr_pos_rel)
    - [HPA] CSI n=1 `  (.chr_pos_abs)
    - [ICH] CSI n=1 @  (.ins_chr)  **[i] Windows / UNIX compatible**
    - [DCH] CSI n=1 P  (.del_chr)  **[i] Windows / UNIX compatible**
    - [ECH] CSI n=1 X  (.erase_chr)  **[i] Windows / UNIX compatible**
    - [IL] CSI n=1 L   (.ins_ln)  **[i] Windows / UNIX compatible**
    - [DL] CSI n=1 M   (.del_ln)  **[i] Windows / UNIX compatible**

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/text-modification`_
     ; `xterm/CSI`_
    
    .. _`microsoft/console-virtual-terminal-sequences/text-modification`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-modification
    .. _`xterm/CSI`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Functions-using-CSI-%5F-ordered-by-the-final-character%5Fs%5F
    """

    @staticmethod
    def chr_pos_rel(n: int = 1) -> CSI:
        """
        Character to position n -- relative (HPR).

        :return: CSI { n } a
        """
        return CSI(f'{n}a')

    @staticmethod
    def chr_pos_abs(n: int = 1) -> CSI:
        """
        Character to position n -- absolute (HPA).

        :return: CSI { n } `
        """
        return CSI(f'{n}`')

    @staticmethod
    def ins_chr(n: int = 1) -> CSI:
        """
        Insert n blank characters (ICH).

        :return: CSI { n } @
        """
        return CSI(f'{n}@')

    @staticmethod
    def del_chr(n: int = 1) -> CSI:
        """
        Delete n characters (DCH).

        :return: CSI { n } P
        """
        return CSI(f'{n}P')

    @staticmethod
    def erase_chr(n: int = 1) -> CSI:
        """
        Erase n characters (ECH).

        :return: CSI { n } X
        """
        return CSI(f'{n}X')

    @staticmethod
    def ins_ln(n: int = 1) -> CSI:
        """
        Insert n lines (IL).

        :return: CSI { n } L
        """
        return CSI(f'{n}L')

    @staticmethod
    def del_ln(n: int = 1) -> CSI:
        """
        Delete n lines (DL).

        :return: CSI { n } M
        """
        return CSI(f'{n}M')


class CharSet:
    """
    Select character set:  (.select)

    ESC ...
        - % @  : Default (ISO 8859-1)
        - % G  : UTF-8

    ****

    Designate character set:  (.designate\\*)

    ESC ...
        - (   : Designate G0 Character Set (VT100)  **[i] Windows / UNIX compatible**
        - )   : Designate G1 Character Set (VT100)
        - \\* : Designate G2 Character Set (VT220)
        - \\+ : Designate G3 Character Set (VT220)
        Parameters:
            - A   : UK (VT100)
            - B   : USASCII (VT100)  **[i] Windows / UNIX compatible**
            - C   : Finnish (VT200)
            - H   : Swedish (VT200)
            - K   : German (VT200)
            - Q   : French Canadian (VT200)
            - R   : French (VT200)
            - y   : Italian (VT200)
            - Z   : Spanish (VT200)
            - 4   : Dutch (VT200)
            - " > : Greek (VT500)
            - % 2 : Turkish (VT500)
            - % 6 : Portuguese (VT300)
            - % = : Hebrew (VT500)
            - =   : Swiss (VT200)
            - E   : Norwegian (VT200)
            - 0   : DEC Special Characters and Line Drawing (VT100)  **[i] Windows / UNIX compatible**
            - <   : DEC Supplemental (VT200)
            - >   : DEC Technical (VT300)
            - " 4 : DEC Hebrew (VT500)
            - " ? : DEC Greek (VT500)
            - % 0 : DEC Turkish (VT500)
            - % 5 : DEC Supplemental Graphics (VT300)
            - & 4 : DEC Cyrillic (VT500)
            - % 3 : SCS NRCS (VT500)
            - & 5 : DEC Russian (VT500)

    ****

    Designate character set (VT >= 300):  (.designate*)

    ESC ...
        - \\-  : Designate G1 Character Set (VT300)
        - .    : Designate G2 Character Set (VT300)
        - /    : Designate G3 Character Set (VT300)
        Parameters:
            - A  : ISO Latin-1 Supplemental (VT300)
            - B  : ISO Latin-2 Supplemental (VT500)
            - F  : ISO Greek Supplemental (VT500)
            - H  : ISO Hebrew Supplemental (VT500)
            - L  : ISO Latin-Cyrillic (VT500)
            - M  : ISO Latin-5 Supplemental (VT500)

    ****

    Invoke character set: (.invoke)

    ESC ...
        - [LS2]  n  : Invoke the G2 Character Set as GL
        - [LS3]  o  : Invoke the G3 Character Set as GL
        - [LS3R] |  : Invoke the G3 Character Set as GR
        - [LS2R] }  : Invoke the G2 Character Set as GR
        - [LS1R] ~  : Invoke the G1 Character Set as GR (VT100)

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/designate-character-set`_
     ; `xterm/Controls-beginning-with-ESC`_

    .. _`microsoft/console-virtual-terminal-sequences/designate-character-set`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#designate-character-set
    .. _`xterm/Controls-beginning-with-ESC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Controls-beginning-with-ESC
    """

    @staticmethod
    def invoke(param: Literal['n', 'o', '|', '}', '~']) -> FsFpnF:
        """:return: ESC { param }"""
        return FsFpnF(param)

    @staticmethod
    def select(utf8: bool = False) -> FsFpnF:
        """
        :param utf8: return `ESC %G`(UTF-8) if True, else `ESC %@`(default)

        :return: ESC { %G | %@ }
        """
        if utf8:
            return FsFpnF('%G')
        else:
            return FsFpnF('%@')

    @staticmethod
    def designateG0_VT100(
            param: Literal[
                'A', 'B', 'C', 'H', 'K', 'Q', 'R', 'y', 'Z', '4', '">', '%2', '%6',
                '%=', '=', 'E', '0', '<', '>', '"4', '"?', '%0', '%5', '&4', '%3', '&5'
            ]
    ) -> FsFpnF:
        """:return: ESC ( { param }"""
        return FsFpnF(f"({param}")

    @staticmethod
    def designateG1_VT100(
            param: Literal[
                'A', 'B', 'C', 'H', 'K', 'Q', 'R', 'y', 'Z', '4', '">', '%2', '%6',
                '%=', '=', 'E', '0', '<', '>', '"4', '"?', '%0', '%5', '&4', '%3', '&5'
            ]
    ) -> FsFpnF:
        """:return: ESC ) { param }"""
        return FsFpnF(f"){param}")

    @staticmethod
    def designateG2_VT220(
            param: Literal[
                'A', 'B', 'C', 'H', 'K', 'Q', 'R', 'y', 'Z', '4', '">', '%2', '%6',
                '%=', '=', 'E', '0', '<', '>', '"4', '"?', '%0', '%5', '&4', '%3', '&5'
            ]
    ) -> FsFpnF:
        """:return: ESC * { param }"""
        return FsFpnF(f"*{param}")

    @staticmethod
    def designateG3_VT220(
            param: Literal[
                'A', 'B', 'C', 'H', 'K', 'Q', 'R', 'y', 'Z', '4', '">', '%2', '%6',
                '%=', '=', 'E', '0', '<', '>', '"4', '"?', '%0', '%5', '&4', '%3', '&5'
            ]
    ) -> FsFpnF:
        """:return: ESC + { param }"""
        return FsFpnF(f"+{param}")

    @staticmethod
    def designateG1_VT300(
            param: Literal[
                'A', 'B', 'F', 'H', 'L', 'M'
            ]
    ) -> FsFpnF:
        """:return: ESC - { param }"""
        return FsFpnF(f"-{param}")

    @staticmethod
    def designateG2_VT300(
            param: Literal[
                'A', 'B', 'F', 'H', 'L', 'M'
            ]
    ) -> FsFpnF:
        """:return: ESC . { param }"""
        return FsFpnF(f".{param}")

    @staticmethod
    def designateG3_VT300(
            param: Literal[
                'A', 'B', 'F', 'H', 'L', 'M'
            ]
    ) -> FsFpnF:
        r""":return: ESC \ { param }"""
        return FsFpnF(f"\\{param}")
