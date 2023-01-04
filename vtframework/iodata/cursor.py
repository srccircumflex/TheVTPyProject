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

try:
    from vtframework.iodata import decpm
    __4doc1 = decpm
except ImportError:
    pass

from vtframework.iodata.c1ctrl import FsFpnF, Fe, CSI
from vtframework.iosys.gates import __STYLE_GATE__


class CursorSave:
    """
    Fp: (default)
        Save and restore cursor

        - [DECSC] ESC 7  (.save)  **[i] Windows / UNIX compatible**
        - [DECRC] ESC 8  (.restore)  **[i] Windows / UNIX compatible**

        Term: VT100

    CSI: (available only when DECLRMM is disabled: CSI ? 69 l (:class:`decpm.DECPrivateMode`))
        Save and restore cursor

        - [SCOSC] CSI s  (.save)  **[i] Windows / UNIX compatible**
        - [SCORC] CSI u  (.restore)  **[i] Windows / UNIX compatible**

        Term: VT100

    ****

    ****

    # Resources:
     ; `xterm/Controls-beginning-with-ESC`_
     ; `xterm/CSI`_
     ; `microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`_
     ; `microsoft/console-virtual-terminal-sequences/cursor-positioning`_

    .. _`xterm/Controls-beginning-with-ESC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Controls-beginning-with-ESC
    .. _`xterm/CSI`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Functions-using-CSI-%5F-ordered-by-the-final-character%5Fs%5F
    .. _`microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#simple-cursor-positioning
    .. _`microsoft/console-virtual-terminal-sequences/cursor-positioning`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#cursor-positioning
    """

    @staticmethod
    def save(Fp_: bool = True) -> FsFpnF | CSI:
        """:return: ESC 7  |  CSI s"""
        if Fp_:
            return FsFpnF('7')
        else:
            return CSI('s')

    @staticmethod
    def restore(Fp_: bool = True) -> FsFpnF | CSI:
        """:return: ESC 8  |  CSI u"""
        if Fp_:
            return FsFpnF('8')
        else:
            return CSI('u')


class CursorStyle:
    """
    Set Cursor Style (DECSCUSR).

    - CSI 0 SP q  (.blinking_block)
    - CSI 1 SP q  (.default)
    - CSI 2 SP q  (.steady_block)
    - CSI 3 SP q  (.blinking_underline)
    - CSI 4 SP q  (.steady_underline)
    - CSI 5 SP q  (.blinking_bar)
    - CSI 6 SP q  (.steady_bar)

    Term: VT520

    ****

    ****

    # Resources:
     ; `xterm/CSI/DECSCUSR`_

    .. _`xterm/CSI/DECSCUSR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps-SP-q.1D81
    """

    @staticmethod
    @__STYLE_GATE__(CSI.new_nul)
    def blinking_block() -> CSI:
        """:return: CSI 0 SP q"""
        return CSI('0 q')

    @staticmethod
    @__STYLE_GATE__(CSI.new_nul)
    def default() -> CSI:
        """:return: CSI 1 SP q"""
        return CSI('1 q')

    @staticmethod
    @__STYLE_GATE__(CSI.new_nul)
    def steady_block() -> CSI:
        """:return: CSI 2 SP q"""
        return CSI('2 q')

    @staticmethod
    @__STYLE_GATE__(CSI.new_nul)
    def blinking_underline() -> CSI:
        """:return: CSI 3 SP q"""
        return CSI('3 q')

    @staticmethod
    @__STYLE_GATE__(CSI.new_nul)
    def steady_underline() -> CSI:
        """:return: CSI 4 SP q"""
        return CSI('4 q')

    @staticmethod
    @__STYLE_GATE__(CSI.new_nul)
    def blinking_bar() -> CSI:
        """
        Term: xterm

        :return: CSI 5 SP q
        """
        return CSI('5 q')

    @staticmethod
    @__STYLE_GATE__(CSI.new_nul)
    def steady_bar() -> CSI:
        """
        Term: xterm

        :return: CSI 6 SP q
        """
        return CSI('6 q')


class CursorNavigate:
    """
    Cursor navigation.

    - [CUU] CSI n=1 A        (.up)  **[i] Windows / UNIX compatible**
    - [CUD] CSI n=1 B        (.down)  **[i] Windows / UNIX compatible**
    - [CUF] CSI n=1 C        (.forward)  **[i] Windows / UNIX compatible**
    - [CUB] CSI n=1 D        (.back)  **[i] Windows / UNIX compatible**
    - [CNL] CSI n=1 E        (.nextline)  **[i] Windows / UNIX compatible**
    - [CPL] CSI n=1 F        (.preline)  **[i] Windows / UNIX compatible**
    - [CHA] CSI n=1 G        (.column)  **[i] Windows / UNIX compatible**
    - [CUP] CSI y=1 ; x=1 H  (.position)  **[i] Windows / UNIX compatible**
    - [HTS] ESC H            (.tab_stop_set)  **[i] Windows / UNIX compatible**
    - [TBC] CSI 0 g          (.tab_column_clear)  **[i] Windows / UNIX compatible**
    - [TBC] CSI 3 g          (.tab_all_clear)  **[i] Windows / UNIX compatible**
    - [CHT] CSI n=1 I        (.tab_forward)  **[i] Windows / UNIX compatible**
    - [CBT] CSI n=1 Z        (.tab_back)  **[i] Windows / UNIX compatible**
    - [VPA] CSI n=1 d        (.line_absolute)  **[i] Windows / UNIX compatible**
    - [VPR] CSI n=1 e        (.line_relative)  **[i] Windows / UNIX compatible**
    - [HVP] CSI y=1 ; x=1 f  (.positionf)  **[i] Windows / UNIX compatible**
    - [RI] ESC M             (.reverse_index)  **[i] Windows / UNIX compatible**
    - [IND] ESC D            (.next_index)

    ****

    ****

    # Resources:
     ; `xterm/C1-8-Bit-Control-Characters`_
     ; `xterm/CSI`_
     ; `microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`_
     ; `microsoft/console-virtual-terminal-sequences/cursor-positioning`_
     ; `microsoft/console-virtual-terminal-sequences/tabs`_

    .. _`xterm/C1-8-Bit-Control-Characters`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-C1-%5F8-Bit%5F-Control-Characters
    .. _`xterm/CSI`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Functions-using-CSI-%5F-ordered-by-the-final-character%5Fs%5F
    .. _`microsoft/console-virtual-terminal-sequences/simple-cursor-positioning`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#simple-cursor-positioning
    .. _`microsoft/console-virtual-terminal-sequences/cursor-positioning`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#cursor-positioning
    .. _`microsoft/console-virtual-terminal-sequences/tabs`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#tabs
    """

    @staticmethod
    def up(n: int = 1) -> CSI:
        """:return: CSI { n } A"""
        return CSI(f'{n}A')

    @staticmethod
    def down(n: int = 1) -> CSI:
        """:return: CSI { n } B"""
        return CSI(f'{n}B')

    @staticmethod
    def forward(n: int = 1) -> CSI:
        """:return: CSI { n } C"""
        return CSI(f'{n}C')

    @staticmethod
    def back(n: int = 1) -> CSI:
        """:return: CSI { n } D"""
        return CSI(f'{n}D')

    @staticmethod
    def nextline(n: int = 1) -> CSI:
        """
        to next line n (CNL).

        :return: CSI { n } E
        """
        return CSI(f'{n}E')

    @staticmethod
    def preline(n: int = 1) -> CSI:
        """
        to preceding line n (CPL).

        :return: CSI { n } F
        """
        return CSI(f'{n}F')

    @staticmethod
    def column(n: int = 1) -> CSI:
        """
        to character position n -- absolute (CHA).

        :return: CSI { n } G
        """
        return CSI(f'{n}G')

    @staticmethod
    def position(x: int = 1, y: int = 1) -> CSI:
        """
        to x/y-position (CUP).

        :return: CSI { y } ; { x } H
        """
        return CSI(f'{y};{x}H')

    @staticmethod
    def tab_stop_set() -> Fe:
        """
        Set a tab stop in the current column (HTS).

        :return: ESC H
        """
        return Fe('H')

    @staticmethod
    def tab_column_clear() -> CSI:
        """
        Clear the tab stop in the current column, if there is one (TBC).

        :return: CSI 0 g
        """
        return CSI('0g')

    @staticmethod
    def tab_all_clear() -> CSI:
        """
        Clear all tab stops (TBC).

        :return: CSI 3 g
        """
        return CSI('3g')

    @staticmethod
    def tab_forward(n: int = 1) -> CSI:
        """
        n forwards tabulation (CHT).

        :return: CSI { n } I
        """
        return CSI(f'{n}I')

    @staticmethod
    def tab_back(n: int = 1) -> CSI:
        """
        n backwards tabulation (CBT).

        :return: CSI { n } Z
        """
        return CSI(f'{n}Z')

    @staticmethod
    def line_absolute(n: int = 1) -> CSI:
        """
        to line position n -- absolute (VPA).

        :return: CSI { n } d
        """
        return CSI(f'{n}d')

    @staticmethod
    def line_relative(n: int = 1) -> CSI:
        """
        to line position n -- relative (VPR).

        :return: CSI { n } e
        """
        return CSI(f'{n}e')

    @staticmethod
    def positionf(x: int = 1, y: int = 1) -> CSI:
        """
        to x/y-position (HVP).

        :return: CSI { y } ; { x } f
        """
        return CSI(f'{y};{x}f')

    @staticmethod
    def reverse_index() -> Fe:
        """
        Reverse Index (RI) 0x8d.

        :return: ESC M
        """
        return Fe('M')

    @staticmethod
    def next_index() -> Fe:
        """
        Index (IND) 0x84.

        :return: ESC D
        """
        return Fe('D')


class Scroll:
    """
    Scrolling

    - [SU] CSI n=1 S             (.up)  **[i] Windows / UNIX compatible**
    - [SD] CSI n=1 T             (.down)  **[i] Windows / UNIX compatible**
    - [DECSTBM] CSI n=0 ; n=0 r  (.set_region)  **[i] Windows / UNIX compatible**
    Term:
        - SU / SD: VT420
        - DECSTBM: VT100

    ****

    ****

    # Resources:
     ; `xterm/CSI`_
     ; `microsoft/console-virtual-terminal-sequences/viewport-positioning`_
     ; `microsoft/console-virtual-terminal-sequences/scrolling-margins`_

    .. _`xterm/CSI`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Functions-using-CSI-%5F-ordered-by-the-final-character%5Fs%5F
    .. _`microsoft/console-virtual-terminal-sequences/viewport-positioning`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#viewport-positioning
    .. _`microsoft/console-virtual-terminal-sequences/scrolling-margins`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#scrolling-margins
    """

    @staticmethod
    def up(n: int = 1) -> CSI:
        """:return: CSI { n } S"""
        return CSI(f'{n}S')

    @staticmethod
    def down(n: int = 1) -> CSI:
        """:return: CSI { n } T"""
        return CSI(f'{n}T')

    @staticmethod
    def set_region(top: int = 0, bottom: int = 0) -> CSI:
        """
        Set scrolling region (default 0/0 eq. full window).

        :return: CSI { top } ; { bottom } r
        """
        return CSI(f'{top};{bottom}r')
