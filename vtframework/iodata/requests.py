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

from vtframework.iodata.c1ctrl import CSI, OSC

try:
    from vtframework.iodata import replies
    __4doc1 = replies
except ImportError:
    pass


class RequestDevice:
    """
    Device requests.

    *For more information about the reply, see the documentation of the methods and the corresponding reply classes:*
    :class:`replies.ReplyDA` :class:`replies.ReplyTIC` :class:`replies.ReplyTID` :class:`replies.ReplyCKS`.

    - [DA primary]   CSI 0 c     (.termattr_DA)  **[i] Windows / UNIX compatible**
    - [DA secondary] CSI > 0 c   (.termid_TIC)
    - [DA tertiary]  CSI = 0 c   (.termuid_TID)
    - [DECCKSR]      CSI ? 63 n  (.checksum_CKS)

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/query-state`_
     ; `xterm/CSI/Primary-DA`_
     ; `xterm/CSI/Secondary-DA`_
     ; `xterm/CSI/Tertiary-DA`_
     ; `xterm/CSI/DSR-DEC`_

    .. _`microsoft/console-virtual-terminal-sequences/query-state`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#query-state
    .. _`xterm/CSI/Primary-DA`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps-c.1CA3
    .. _`xterm/CSI/Secondary-DA`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-gt-Ps-c.1DAB
    .. _`xterm/CSI/Tertiary-DA`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3D-Ps-c.1D0D
    .. _`xterm/CSI/DSR-DEC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3F-Ps-n.1D1A
    """

    @staticmethod
    def termattr_DA() -> CSI:
        """
        Request terminal attributes (Primary DA):
            - CSI 0 c
            -> CSI ? value c  (:class:`replies.ReplyDA`)

        Term: VT100
        """
        return CSI('0c')

    @staticmethod
    def termid_TIC() -> CSI:
        """
        Request terminal id code (Secondary DA):
            - CSI > 0 c
            -> CSI > term ; firmware ; keyboard_option c  (:class:`replies.ReplyTIC`)

        Term: VT220 (VT100 at xterm)
        """
        return CSI('>0c')

    @staticmethod
    def termuid_TID() -> CSI:
        """
        Request terminal unit id (Tertiary DA):
            - CSI = 0 c
            -> DCS ! | side=hex term_id0=hex term_id1=hex term_id2=hex ST  (:class:`replies.ReplyTID`)

        Term: VT400
        """
        return CSI('=0c')

    @staticmethod
    def checksum_CKS(ID: int = None) -> CSI:
        """
        Report memory checksum (DECCKSR):
            - CSI ? 63 n
            - CSI ? 63 ; id n
            -> DCS id ! ~ x=hexd x=hexd x=hexd x=hexd ST  (:class:`replies.ReplyCKS`)
        """
        if ID is not None:
            return CSI(f'?63;{ID}n')
        return CSI('?63n')


class RequestGeo:
    """
    Geometry requests.

    *For more information about the reply, see the documentation of the methods and the corresponding reply classes:*
    :class:`replies.ReplyCP` :class:`replies.ReplyWindow`.

    - [CPR]      CSI 6 n                           (.cursorpos_CP)  **[i] Windows / UNIX compatible**
    - [DECXCPR]  CSI ? 6 n                         (.cursorpos_CP)
    - [XTWINOPS] CSI { 14 | 15 | 16 | 18 | 19 } t  (.window)

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/query-state`_
     ; `xterm/CSI/DSR`_
     ; `xterm/CSI/DSR-DEC`_
     ; `xterm/CSI/XTWINOPS`_

    .. _`microsoft/console-virtual-terminal-sequences/query-state`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#query-state
    .. _`xterm/CSI/DSR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps-n.1CAE
    .. _`xterm/CSI/DSR-DEC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3F-Ps-n.1D1A
    .. _`xterm/CSI/XTWINOPS`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps%3BPs%3BPs-t.1EB0
    """

    @staticmethod
    def cursorpos_CP(CPR: bool = True) -> CSI:
        """
        Device Status Report (DSR):

            Report Cursor Position (CPR): (default)
                - CSI 6 n  **[i] Windows / UNIX compatible**
                -> CSI row ; column R  (:class:`replies.ReplyCP`)

        [DEC-specific] Device Status Report (DSR):

            Report Cursor Position (DECXCPR):
                - CSI ? 6 n
                -> CSI ? row ; column ; page R  (:class:`replies.ReplyCP`)
        """
        return CSI(('' if CPR else '?'), '6n')

    @staticmethod
    def window(param: Literal[14, 18, 15, 19, 16]) -> CSI:
        """
        Extended window options (XTWINOPS), controls may be disabled by the allowWindowOps resource.

        - CSI 14 t  : Report textarea size in pixels (xterm)
            -> CSI 4 ; y ; x t
        - CSI 18 t  : Report textarea size in characters
            -> CSI 8 ; y ; x t
        - CSI 15 t  : Report screen size in pixels
            -> CSI 5 ; y ; x t
        - CSI 19 t  : Report screen size in characters
            -> CSI 9 ; y ; x t
        - CSI 16 t  : Report character cell size in pixels (xterm)
            -> CSI 6 ; y ; x t

        Reply: :class:`replies.ReplyWindow`
        """
        return CSI(f'{param}t')


class RequestDECPM:
    """
    DEC private mode requests.
    
    *For more information about the reply, see the documentation of the method and the corresponding reply class:*
    :class:`replies.ReplyDECPM`.

    - [DECRQM] CSI ? n=param $ p  (.privmode_DECPM)

    ****

    ****

    # Resources:
     ; `xterm/DECRQM`_

    .. _`xterm/DECRQM`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps-%24-p.1D01
    """

    @staticmethod
    def privmode_DECPM(mode: int) -> CSI:
        """
        Request DEC private mode (DECRQM):
            - CSI ? n=param $ p
            -> CSI ? n=param ; value $ y  (:class:`replies.ReplyDECPM`)

        Term: VT300
        """
        return CSI(f'?{mode}$p')


class RequestOSColor:
    """
    Color palette requests.

    *For more information about the reply, see the documentation of the methods and the corresponding reply class:*
    :class:`replies.ReplyOSColor`.

    - OSC 4 ; slot ; ? ST               (.rel)
    - OSC { 10 | 11 | 15 | 16 } ; ? ST  (.environment)
    - OSC { 12 | 18 } ; ? ST            (.cursor)
    - OSC { 17 | 18 } ; ? ST            (.highlight)
    - OSC { 13 | 14 } ; ? ST            (.pointer)

    ****

    ****

    # Resources:
     ; `xterm/OSC`_

    .. _`xterm/OSC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Operating-System-Commands
    """

    _color_nums = {
        'black': (0, 8),
        'red': (1, 9),
        'green': (2, 10),
        'yellow': (3, 11),
        'blue': (4, 12),
        'magenta': (5, 13),
        'cyan': (6, 14),
        'white': (7, 15)
    }

    @staticmethod
    def rel(color_slot: Literal['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'] | int,
            *, bright_version: bool = False) -> OSC:
        """
        Request color slot:
            - OSC 4 ; slot ; ? ST
            -> OSC 4 ; slot ; rgb:rrrr/gggg/bbbb ST  (:class:`replies.ReplyOSColor`)

        :param color_slot: 'black' | 'red' | 'green' | 'yellow' | 'blue' | 'magenta' | 'cyan' | 'white' | int:<remainder of the 256-table>
        :param bright_version: request the bright version (ignored if the slot is specified as integer)
        """
        if isinstance(color_slot, int):
            return OSC("4;", esc_string=f"{color_slot};?")
        else:
            color_n = RequestOSColor._color_nums[color_slot]
            if bright_version:
                return OSC("4;", esc_string=f"{color_n[1]};?")
            else:
                return OSC("4;", esc_string=f"{color_n[0]};?")

    @staticmethod
    def environment(*, fore: bool = False, Tektronix: bool = False) -> OSC:
        """
        Request the VT100 (default) | Tektronix text foreground or background (default) color.
            - OSC { 10 | 11 | 15 | 16 } ; ? ST
            -> OSC { 10 | 11 | 15 | 16 } ; rgb:rrrr/gggg/bbbb ST  (:class:`replies.ReplyOSColor`)

        :param fore: request the foreground, instead of the background
        :param Tektronix: request at Tektronix
        """
        if fore:
            return OSC("15;" if Tektronix else "10;", esc_string="?")
        else:
            return OSC("16;" if Tektronix else "11;", esc_string="?")

    @staticmethod
    def cursor(*, Tektronix: bool = False) -> OSC:
        """
        Request the VT100 (default) | Tektronix cursor color.
            - OSC { 12 | 18 } ; ? ST
            -> OSC { 12 | 18 } ; rgb:rrrr/gggg/bbbb ST  (:class:`replies.ReplyOSColor`)

        :param Tektronix: request at Tektronix
        """
        return OSC("18;" if Tektronix else "12;", esc_string="?")

    @staticmethod
    def highlight(*, fore: bool = False) -> OSC:
        """
        Request the highlight foreground or background (default) color.
            - OSC { 17 | 18 } ; ? ST
            -> OSC { 17 | 18 } ; rgb:rrrr/gggg/bbbb ST  (:class:`replies.ReplyOSColor`)

        :param fore: request the foreground, instead of the background
        """
        if fore:
            return OSC("19;", esc_string="?")
        else:
            return OSC("17;", esc_string="?")

    @staticmethod
    def pointer(*, fore: bool = False) -> OSC:
        """
        Request the pointer foreground or background (default) color.
            - OSC { 13 | 14 } ; ? ST
            -> OSC { 13 | 14 } ; rgb:rrrr/gggg/bbbb ST  (:class:`replies.ReplyOSColor`)

        :param fore: request the foreground, instead of the background
        """
        if fore:
            return OSC("13;", esc_string="?")
        else:
            return OSC("14;", esc_string="?")


