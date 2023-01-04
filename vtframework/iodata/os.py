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

from typing import Literal, overload

from vtframework.iodata.esccontainer import EscContainer
from vtframework.iodata.c1ctrl import FsFpnF, CSI, OSC
from vtframework.iodata.sgr import _getrgb, _getname
from vtframework.iosys.gates import __STYLE_GATE__


class CtrlByteConversion:
    """
    Tell the Terminal to send C1 control characters as:
        - [S8C1T]   ESC SP G : 8-Bit sequences (default)
        - [S7C1T]   ESC SP F : 7-Bit sequences
        VT200 always accept 8-Bit sequences except when configured for VT100

    ****

    ****

    # Resources:
     ; `xterm/Controls-beginning-with-ESC`_

    .. _`xterm/Controls-beginning-with-ESC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Controls-beginning-with-ESC
    """

    @staticmethod
    def conversion(_8bit: bool = True) -> FsFpnF:
        """
        :param _8bit: return `ESC SP G`(8-Bit/default) if True, else `ESC SP F`(7-Bit)

        :return: ESC SP { G | F }
        """
        if _8bit:
            return FsFpnF(' G')
        else:
            return FsFpnF(' F')


class WindowManipulation:
    """
    Extended window options (XTWINOPS), extended by xterm.
    This controls may be disabled by the allowWindowOps resource.

    -         CSI 8 ; y ; x t    (.resize)
    - [DECSLPP]  CSI >=24 t         (.resizeln)

    Window Title

    -  OSC 0 ; string ST  (.change_ico_n_title)  **[i] Windows / UNIX compatible**
    -  OSC 2 ; string ST  (.change_title)  **[i] Windows / UNIX compatible**

    ****

    ****

    # Resources:
     ; `xterm/CSI/XTWINOPS`_
     ; `microsoft/console-virtual-terminal-sequences/window-title`_

    .. _`xterm/CSI/XTWINOPS`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Ps%3BPs%3BPs-t.1EB0
    .. _`microsoft/console-virtual-terminal-sequences/window-title`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#window-title
    """

    @staticmethod
    def resize(x: int = 80, y: int = 24) -> CSI:
        """
        Resize the textarea in characters.

        :return: CSI 8 ; { y } ; { x } t
        """
        return CSI(f'8;{y};{x}t')

    @staticmethod
    def resizeln(n: int = 24) -> CSI:
        """
        Resize to n lines (DECSLPP).
        [ ! ] 24 is the minimum

        Term: VT340, VT420, xterm

        :return: CSI { n } t
        """
        assert n >= 24, f"24 is the minimum: `{n=}'"
        return CSI(f'{n}t')

    @staticmethod
    def change_ico_n_title(string: str) -> OSC:
        """
        Change icon name and window title to string.

        :return: OSC 0 ; { string } ST
        """
        return OSC('0;', esc_string=string)

    @staticmethod
    def change_title(string: str) -> OSC:
        """
        Change window title to string.

        :return: OSC 2 ; { string } ST
        """
        return OSC('2;', esc_string=string)


class OSColorControl:
    """
    Operating System Command (OSC)

    Set colors:
        - OSC 4 ; slot ; color ST               (.set_rel_color)  **[i] Windows / UNIX compatible**
        - OSC { 10 | 11 | 15 | 16 } ; color ST  (.set_environment_color)
        - OSC { 12 | 18 } ; color ST            (.set_cursor_color)
        - OSC { 17 | 18 } ; color ST            (.set_highlight_color)
        - OSC { 13 | 14 } ; color ST            (.set_pointer_color)

    Reset colors:
        - OSC 104 [ ; slot ] ST             (.reset_rel_color)
        - OSC { 110 | 111 | 115 | 116 } ST  (.reset_environment_color)
        - OSC { 112 | 118 } ST              (.reset_cursor_color)
        - OSC { 117 | 118 } ST              (.reset_highlight_color)
        - OSC { 113 | 114 } ST              (.reset_pointer_color)

    ****

    ****

    # Resources:
     ; `xterm/OSC`_
     ; `microsoft/console-virtual-terminal-sequences/screen-colors`_

    .. _`xterm/OSC`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Operating-System-Commands
    .. _`microsoft/console-virtual-terminal-sequences/screen-colors`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#screen-colors
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
    def _get_rgb(c: str | tuple[int, int, int]) -> str:
        if isinstance(c, str):
            if c[0] == '#':
                r = c[1:3]
                g = c[3:5]
                b = c[5:7]
            else:
                rgb = _getname(c)
                r = ("0%x" % rgb[1])[-2:]
                g = ("0%x" % rgb[2])[-2:]
                b = ("0%x" % rgb[3])[-2:]
        else:
            rgb = _getrgb(*c)
            r = ("0%x" % rgb[1])[-2:]
            g = ("0%x" % rgb[2])[-2:]
            b = ("0%x" % rgb[3])[-2:]
        return f"rgb:{r}/{g}/{b}"

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def set_rel_color(color_slot: Literal['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'] | int,
                      new_color: str | tuple[int, int, int], *, bright_version: bool = False) -> OSC:
        """
        Change color in slot to new color.

        :param color_slot: 'black' | 'red' | 'green' | 'yellow' | 'blue' | 'magenta' | 'cyan' | 'white' | int:<remainder of the 256-table>
        :param new_color: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :param bright_version: change the bright version (ignored if the slot is specified as integer)
        :return: OSC 4 ; { slot } ; { rgb } ST
        """
        rgb = OSColorControl._get_rgb(new_color)
        if isinstance(color_slot, int):
            rgb = f"{color_slot};{rgb}"
        else:
            color_n = OSColorControl._color_nums[color_slot]
            if bright_version:
                rgb = f"{color_n[1]};{rgb}"
            else:
                rgb = f"{color_n[0]};{rgb}"
        return OSC("4;", esc_string=rgb)

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def reset_rel_color(
            color_slot: Literal['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'] | int = None,
            *, bright_version: bool = False
    ) -> OSC:
        """
        Reset any color slot (default) | color slot.

        :param color_slot: OPTIONAL: 'black' | 'red' | 'green' | 'yellow' | 'blue' | 'magenta' | 'cyan' | 'white' | int:<remainder of the 256-table>
        :param bright_version: reset the bright version (ignored if the slot is specified as integer)
        :return: OSC 104 ; { slot } ST  |  OSC 104 ST
        """
        if color_slot is not None:
            if isinstance(color_slot, int):
                c = str(color_slot)
            else:
                color_n = OSColorControl._color_nums[color_slot]
                if bright_version:
                    c = str(color_n[1])
                else:
                    c = str(color_n[0])
            return OSC("104;", esc_string=c)
        else:
            return OSC("104", esc_string='')

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def set_environment_color(*, fore: str | tuple[int, int, int] = None, back: str | tuple[int, int, int] = None,
                              Tektronix: bool = False) -> OSC | EscContainer:
        """
        Change the VT100 (default) | Tektronix text foreground and/or background color.

        :param fore: OPTIONAL: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :param back: OPTIONAL: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :param Tektronix: change at Tektronix
        :return: OSC { 10 | 11 | 15 | 16 } ; { rgb } ST  [ OSC { 11 | 16 } ; { rgb } ST ]
        """
        if fore:
            if back:
                return OSC("15;" if Tektronix else "10;", esc_string=OSColorControl._get_rgb(fore)) + \
                       OSC("16;" if Tektronix else "11;", esc_string=OSColorControl._get_rgb(back))
            else:
                return OSC("15;" if Tektronix else "10;", esc_string=OSColorControl._get_rgb(fore))
        elif back:
            return OSC("16;" if Tektronix else "11;", esc_string=OSColorControl._get_rgb(back))
        else:
            return OSC(esc_string='')

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def reset_environment_color(*, fore: bool = False, back: bool = False,
                                Tektronix: bool = False) -> OSC | EscContainer:
        """
        Reset the VT100 (default) | Tektronix text foreground and(default)/or background color.

        :param fore: reset foreground if True
        :param back: reset background if True
        :param Tektronix: reset at Tektronix
        :return: OSC { 110 | 111 | 115 | 116 } ST  [ OSC { 111 | 116 } ST ]
        """
        if fore:
            if back:
                return OSC("115;" if Tektronix else "110;", esc_string='') + \
                       OSC("116;" if Tektronix else "111;", esc_string='')
            else:
                return OSC("115;" if Tektronix else "110;", esc_string='')
        elif back:
            return OSC("116;" if Tektronix else "111;", esc_string='')
        else:
            return OSC("115;" if Tektronix else "110;", esc_string='') + \
                   OSC("116;" if Tektronix else "111;", esc_string='')

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def set_cursor_color(new_color: str | tuple[int, int, int], *, Tektronix: bool = False) -> OSC:
        """
        Change the VT100 (default) | Tektronix cursor color.

        :param new_color: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :param Tektronix: change at Tektronix
        :return: OSC { 12 | 18 } ; { color } ST
        """
        return OSC("18;" if Tektronix else "12;", esc_string=OSColorControl._get_rgb(new_color))

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def reset_cursor_color(*, Tektronix: bool = False) -> OSC:
        """
        Reset the VT100 (default) | Tektronix cursor color.

        :param Tektronix: reset at Tektronix
        :return: OSC { 112 | 118 } ; { color } ST
        """
        return OSC("118;" if Tektronix else "112;", esc_string='')

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def set_highlight_color(*, fore: str | tuple[int, int, int] = None, back: str | tuple[int, int, int] = None
                            ) -> OSC | EscContainer:
        """
        Change the highlight foreground and/or background color.

        :param fore: OPTIONAL: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :param back: OPTIONAL: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :return: OSC { 17 | 18 } ; { color } ST
        """
        if fore:
            if back:
                return OSC("19;", esc_string=OSColorControl._get_rgb(fore)) + \
                       OSC("17;", esc_string=OSColorControl._get_rgb(back))
            else:
                return OSC("19;", esc_string=OSColorControl._get_rgb(fore))
        elif back:
            return OSC("17;", esc_string=OSColorControl._get_rgb(back))
        else:
            return OSC(esc_string='')

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def reset_highlight_color(*, fore: bool = False, back: bool = False) -> OSC | EscContainer:
        """
        Reset the highlight foreground and(default)/or background color.

        :param fore: reset foreground if True
        :param back: reset background if True
        :return: OSC { 117 | 118 } ST
        """
        if fore:
            if back:
                return OSC("119", esc_string='') + OSC("117", esc_string='')
            else:
                return OSC("119", esc_string='')
        elif back:
            return OSC("117", esc_string='')
        else:
            return OSC("119", esc_string='') + OSC("117", esc_string='')

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def set_pointer_color(*, fore: str | tuple[int, int, int] = None, back: str | tuple[int, int, int] = None
                          ) -> OSC | EscContainer:
        """
        Change the pointer foreground and/or background color.

        :param fore: OPTIONAL: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :param back: OPTIONAL: str(color name) | str(#rrggbb) | tuple(int(r), int(g), int(b))
        :return: OSC { 13 | 14 } ; { color } ST
        """
        if fore:
            if back:
                return OSC("13;", esc_string=OSColorControl._get_rgb(fore)) + \
                       OSC("14;", esc_string=OSColorControl._get_rgb(back))
            else:
                return OSC("13;", esc_string=OSColorControl._get_rgb(fore))
        elif back:
            return OSC("14;", esc_string=OSColorControl._get_rgb(back))
        else:
            return OSC(esc_string='')

    @staticmethod
    @__STYLE_GATE__(OSC.new_nul)
    def reset_pointer_color(*, fore: bool = False, back: bool = False) -> OSC | EscContainer:
        """
        Reset the pointer foreground and(default)/or background color.

        :param fore: reset foreground if True
        :param back: reset background if True
        :return: OSC { 113 | 114 } ST
        """
        if fore:
            if back:
                return OSC("113", esc_string='') + OSC("114", esc_string='')
            else:
                return OSC("113", esc_string='')
        elif back:
            return OSC("114", esc_string='')
        else:
            return OSC("113", esc_string='') + OSC("114", esc_string='')
