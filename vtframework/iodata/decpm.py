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

"""
- ``1`` :       Application Cursor Keys (DECCKM), VT100.
- ``2`` :       Designate USASCII for character sets G0-G3 (DECANM), VT100, and set VT100 mode.
- ``3`` :       132 Column Mode (DECCOLM), VT100.
- ``4`` :       Smooth (Slow) Scroll (DECSCLM), VT100.
- ``5`` :       Reverse Video (DECSCNM), VT100.
- ``6`` :       Origin Mode (DECOM), VT100.
- ``7`` :       Auto-Wrap Mode (DECAWM), VT100.
- ``8`` :       Auto-Repeat Keys (DECARM), VT100.
- ``9`` :       Send Mouse X & Y on button press. (X10 xterm mouse protocol)
- ``10`` :      Show toolbar (rxvt).
- ``12`` :      Start blinking cursor (AT&T 610).
- ``13`` :      Start blinking cursor (set only via resource or menu).
- ``14`` :      Enable XOR of blinking cursor control sequence and menu.
- ``18`` :      Print Form Feed (DECPFF), VT220.
- ``19`` :      Set print extent to full screen (DECPEX), VT220.
- ``25`` :      Show cursor (DECTCEM), VT220.
- ``30`` :      Show scrollbar (rxvt).
- ``35`` :      Enable font-shifting functions (rxvt).
- ``38`` :      Enter Tektronix mode (DECTEK), VT240, xterm.
- ``40`` :      Allow 80 => 132 mode, xterm.
- ``41`` :      more(1) fix (see curses resource).
- ``42`` :      Enable National Replacement Character sets (DECNRCM), VT220.
- ``43`` :      Enable Graphics Expanded Print Mode (DECGEPM).
- ``44`` :      Turn on margin bell, xterm.  ||  Enable Graphics Print Color Mode (DECGPCM).
- ``45`` :      Reverse-wraparound mode, xterm.  ||  Enable Graphics Print ColorSpace (DECGPCS).
- ``46`` :      Start logging, xterm. This is normally disabled by a compile-time option.
- ``47`` :      Use Alternate Screen Buffer, xterm. This may be disabled by the titeInhibit resource.  ||  Enable Graphics Rotated Print Mode (DECGRPM).
- ``66`` :      Application keypad mode (DECNKM), VT320.
- ``67`` :      Backarrow key sends backspace (DECBKM), VT340, VT420. This sets the backarrowKey resource to "true".
- ``69`` :      Enable left and right margin mode (DECLRMM), VT420 and up.
- ``80`` :      Disable Sixel Scrolling (DECSDM).
- ``95`` :      Do not clear screen when DECCOLM is set/reset (DECNCSM), VT510 and up.
- ``1000`` :    Send Mouse X & Y on button press and release. See the section Mouse Tracking. This is the X11 xterm mouse protocol.
- ``1001`` :    Use Highlight Mouse Tracking, xterm.
- ``1002`` :    Use Cell Motion Mouse Tracking, xterm.
- ``1003`` :    Use All Motion Mouse Tracking, xterm.
- ``1004`` :    Send FocusIn/FocusOut events, xterm.
- ``1005`` :    Enable UTF-8 Mouse Mode, xterm.
- ``1006`` :    Enable SGR Mouse Mode, xterm.
- ``1007`` :    Enable Alternate Scroll Mode, xterm. This corresponds to the alternateScroll resource.
- ``1010`` :    Scroll to bottom on tty output (rxvt). This sets the scrollTtyOutput resource to "true".
- ``1011`` :    Scroll to bottom on key press (rxvt). This sets the scrollKey resource to "true".
- ``1015`` :    Enable urxvt Mouse Mode.
- ``1016`` :    Enable SGR Mouse PixelMode, xterm.
- ``1034`` :    Interpret "meta" key, xterm. This sets the eighth bit of keyboard input (and enables the eightBitInput resource).
- ``1035`` :    Enable special modifiers for Alt and NumLock keys, xterm. This enables the numLock resource.
- ``1036`` :    Send ESC when Meta modifies a key, xterm. This enables the metaSendsEscape resource.
- ``1037`` :    Send DEL from the editing-keypad Delete key, xterm.
- ``1039`` :    Send ESC when Alt modifies a key, xterm. This enables the altSendsEscape resource, xterm.
- ``1040`` :    Keep selection even if not highlighted, xterm. This enables the keepSelection resource.
- ``1041`` :    Use the CLIPBOARD selection, xterm. This enables the selectToClipboard resource.
- ``1042`` :    Enable Urgency window manager hint when Control-G is received, xterm. This enables the bellIsUrgent resource.
- ``1043`` :    Enable raising of the window when Control-G is received, xterm. This enables the popOnBell resource.
- ``1044`` :    Reuse the most recent data copied to CLIPBOARD, xterm. This enables the keepClipboard resource.
- ``1046`` :    Enable switching to/from Alternate Screen Buffer, xterm. This works for terminfo-based systems, updating the titeInhibit resource.
- ``1047`` :    Use Alternate Screen Buffer, xterm. This may be disabled by the titeInhibit resource.
- ``1048`` :    Save cursor as in DECSC, xterm. This may be disabled by the titeInhibit resource.
- ``1049`` :    Save cursor as in DECSC, xterm. After saving the cursor, switch to the Alternate Screen Buffer, clearing it first. This may be disabled by the titeInhibit resource. This control combines the effects of the 1 0 4 7 and 1 0 4 8 modes. Use this with terminfo-based applications rather than the 4 7 mode.
- ``1050`` :    Set terminfo/termcap function-key mode, xterm.
- ``1051`` :    Set Sun function-key mode, xterm.
- ``1052`` :    Set HP function-key mode, xterm.
- ``1053`` :    Set SCO function-key mode, xterm.
- ``1060`` :    Set legacy keyboard emulation, i.e, X11R6, xterm.
- ``1061`` :    Set VT220 keyboard emulation, xterm.
- ``2004`` :    Set bracketed paste mode, xterm.
"""

from __future__ import annotations
from typing import Literal
import atexit as _atexit

try:
    from vtframework.iodata import requests
    __4doc1 = requests
except ImportError:
    pass

from vtframework.iodata.c1ctrl import CSI
from vtframework.iosys.gates import __DECPM_GATE__


class DECPModeIds:
    """DEC private mode numbers collection."""
    ApplicationCursorKeys: int = 1
    DesignateUSASCII: int = 2
    Column132Mode: int = 3
    SmoothScroll: int = 4
    ReverseVideo: int = 5
    OriginMode: int = 6
    AutoWrapMode: int = 7
    AutoRepeatKeys: int = 8
    SendMousePress_X10: int = 9
    ShowToolbar: int = 10
    StartBlinkingCursor: int = 12
    startBlinkingCursor: int = 13
    EnableXORblinkingCursor: int = 14
    PrintFormFeed: int = 18
    PrintFullScreen: int = 19
    ShowCursor: int = 25
    ShowScrollbar: int = 30
    EnableFontShifting: int = 35
    EnterTektronixMode: int = 38
    Allow80to132Mode: int = 40
    CursesMoreFix: int = 41
    NationalReplacementCharacter: int = 42
    ExpandedPrintMode: int = 43
    MarginBell: int = 44
    PrintColorMode: int = 44
    ReverseWraparound: int = 45
    PrintColorSpace: int = 45
    StartLogging: int = 46
    alternateScreenBuffer: int = 47
    RotatedPrintMode: int = 47
    ApplicationKeypad: int = 66
    BackarrowKeySendsBackspace: int = 67
    EnableLRmargin: int = 69
    DisableSixelScrolling: int = 80
    NotClearScreenDECCOLM: int = 95
    SendMousePress_X11: int = 1000
    HighlightMouseTracking: int = 1001
    CellMotionMouseTracking: int = 1002
    AllMotionMouseTracking: int = 1003
    SendFocusInFocusOut: int = 1004
    UTF8MouseMode: int = 1005
    SGRMouseMode: int = 1006
    AlternateScrollMode: int = 1007
    TTYoutScrollToBottom: int = 1010
    KeyPressScrollToBottom: int = 1011
    UrxvtMouseMode: int = 1015
    SGRMousePixelMode: int = 1016
    InterpretMetaKey: int = 1034
    SpecialModifiers: int = 1035
    SendESCMetaModifies: int = 1036
    SendDELEditingKeypad: int = 1037
    SendESCAltModifies: int = 1039
    KeepSelection: int = 1040
    SelectToClipboard: int = 1041
    BellIsUrgent: int = 1042
    PopOnBell: int = 1043
    KeepClipboard: int = 1044
    SwitchingAlternateScreenBuffer: int = 1046
    AlternateScreenBuffer: int = 1047
    SaveCursor: int = 1048
    SaveCursorAlternateScreenBuffer: int = 1049
    TerminfoTermcapKey: int = 1050
    SunFKey: int = 1051
    HPFKey: int = 1052
    SCOFKey: int = 1053
    LegacyKeyboard: int = 1060
    VT220Keyboard: int = 1061
    BracketedPasteMode: int = 2004


class _ReplyCache(dict[int, int]):
    """A global memory for DEC private mode status requests.
    See also: :class:`requests.RequestDECPM`"""


__ReplyCache__: _ReplyCache = _ReplyCache()


class DECPrivateMode:
    """
    - [DECSET] CSI ? n=mode h (.high)
    - [DECRST] CSI ? n=mode l (.low)

    mode =

    ````

    Mouse:
        - ``9`` :       Send Mouse X & Y on button press. (X10 xterm mouse protocol)
        - ``1000`` :    Send Mouse X & Y on button press and release. See the section `xterm/Mouse-Tracking`_. This is the X11 xterm mouse protocol.
        - ``1001`` :    Use Highlight Mouse Tracking, xterm.  (eq. to 1000)
        - ``1002`` :    Use Cell Motion Mouse Tracking, xterm.
        - ``1003`` :    Use All Motion Mouse Tracking, xterm.

    Extended Mouse Coordinates (supported by the vtiinterpreter):
        - ``1006`` :    Enable SGR Mouse Mode, xterm.
        - ``1016`` :    Enable SGR Mouse PixelMode, xterm.
        # Resources: `xterm/Extended-coordinates`_

    Screen:
        - ``5`` :       Reverse Video (DECSCNM), VT100.
        - ``1046`` :    Switching to/from Alternate Screen Buffer, xterm. This works for terminfo-based systems, updating the titeInhibit resource.
        - ``1047`` :    Use Alternate Screen Buffer, xterm. This may be disabled by the titeInhibit resource.
        - ``1049`` :    Save cursor as in DECSC, xterm. After saving the cursor, switch to the Alternate Screen Buffer, clearing it first. This may be disabled by the titeInhibit resource. This control combines the effects of the 1 0 4 7 and 1 0 4 8 modes. Use this with terminfo-based applications rather than the 4 7 mode.  **[i] Windows / UNIX compatible**
        # Resources: `xterm/The-Alternate-Screen-Buffer`_

    Cursor:
        - ``7`` :       Auto-Wrap Mode (DECAWM), VT100.
        - ``12`` :      Blinking cursor (AT&T 610).  **[i] Windows / UNIX compatible**
        - ``13`` :      Blinking cursor (set only via resource or menu).
        - ``14`` :      Enable XOR of blinking cursor control sequence and menu.
        - ``25`` :      Show cursor (DECTCEM), VT220.  **[i] Windows / UNIX compatible**
        - ``1048`` :    Save cursor as in DECSC, xterm. This may be disabled by the titeInhibit resource.

    Modes:
        - ``1`` :       Application Cursor Keys (DECCKM), VT100.  **[i] Windows / UNIX compatible**
        - ``2004`` :    Set bracketed paste mode, xterm.
        # Resources: `xterm/Bracketed-Paste-Mode`_

    ****

    Miscellaneous:
        - ``2`` :       Designate USASCII for character sets G0-G3 (DECANM), VT100, and set VT100 mode.
        - ``3`` :       132 Column Mode (DECCOLM), VT100.  **[i] Windows / UNIX compatible**
        - ``4`` :       Smooth (Slow) Scroll (DECSCLM), VT100.
        - ``6`` :       Origin Mode (DECOM), VT100.
        - ``8`` :       Auto-Repeat Keys (DECARM), VT100.
        - ``10`` :      Show toolbar (rxvt).
        - ``18`` :      Print Form Feed (DECPFF), VT220.
        - ``19`` :      Set print extent to full screen (DECPEX), VT220.
        - ``30`` :      Show scrollbar (rxvt).
        - ``35`` :      Enable font-shifting functions (rxvt).
        - ``38`` :      Enter Tektronix mode (DECTEK), VT240, xterm.
        - ``40`` :      Allow 80 => 132 mode, xterm.
        - ``41`` :      more(1) fix (see curses resource).
        - ``42`` :      Enable National Replacement Character sets (DECNRCM), VT220.
        - ``43`` :      Enable Graphics Expanded Print Mode (DECGEPM).
        - ``44`` :      Turn on margin bell, xterm.  ||  Enable Graphics Print Color Mode (DECGPCM).
        - ``45`` :      Reverse-wraparound mode, xterm.  ||  Enable Graphics Print ColorSpace (DECGPCS).
        - ``46`` :      Start logging, xterm. This is normally disabled by a compile-time option.
        - ``47`` :      Use Alternate Screen Buffer, xterm. This may be disabled by the titeInhibit resource.  ||  Enable Graphics Rotated Print Mode (DECGRPM).
        - ``66`` :      Application keypad mode (DECNKM), VT320.
        - ``67`` :      Backarrow key sends backspace (DECBKM), VT340, VT420. This sets the backarrowKey resource to "true".
        - ``69`` :      Enable left and right margin mode (DECLRMM), VT420 and up.
        - ``80`` :      Disable Sixel Scrolling (DECSDM).
        - ``95`` :      Do not clear screen when DECCOLM is set/reset (DECNCSM), VT510 and up.
        - ``1004`` :    Send FocusIn/FocusOut events, xterm.
        - ``1005`` :    Enable UTF-8 Mouse Mode, xterm.
        - ``1007`` :    Enable Alternate Scroll Mode, xterm. This corresponds to the alternateScroll resource.
        - ``1010`` :    Scroll to bottom on tty output (rxvt). This sets the scrollTtyOutput resource to "true".
        - ``1011`` :    Scroll to bottom on key press (rxvt). This sets the scrollKey resource to "true".
        - ``1015`` :    Enable urxvt Mouse Mode.
        - ``1034`` :    Interpret "meta" key, xterm. This sets the eighth bit of keyboard input (and enables the eightBitInput resource).
        - ``1035`` :    Enable special modifiers for Alt and NumLock keys, xterm. This enables the numLock resource.
        - ``1036`` :    Send ESC when Meta modifies a key, xterm. This enables the metaSendsEscape resource.
        - ``1037`` :    Send DEL from the editing-keypad Delete key, xterm.
        - ``1039`` :    Send ESC when Alt modifies a key, xterm. This enables the altSendsEscape resource, xterm.
        - ``1040`` :    Keep selection even if not highlighted, xterm. This enables the keepSelection resource.
        - ``1041`` :    Use the CLIPBOARD selection, xterm. This enables the selectToClipboard resource.
        - ``1042`` :    Enable Urgency window manager hint when Control-G is received, xterm. This enables the bellIsUrgent resource.
        - ``1043`` :    Enable raising of the window when Control-G is received, xterm. This enables the popOnBell resource.
        - ``1044`` :    Reuse the most recent data copied to CLIPBOARD, xterm. This enables the keepClipboard resource.
        - ``1050`` :    Set terminfo/termcap function-key mode, xterm.
        - ``1051`` :    Set Sun function-key mode, xterm.
        - ``1052`` :    Set HP function-key mode, xterm.
        - ``1053`` :    Set SCO function-key mode, xterm.
        - ``1060`` :    Set legacy keyboard emulation, i.e, X11R6, xterm.
        - ``1061`` :    Set VT220 keyboard emulation, xterm.

    ****

    # Resources:
     ; `xterm/CSI/DECPM/h`_
     ; `xterm/CSI/DECPM/l`_
     ; `microsoft/console-virtual-terminal-sequences/cursor-visibility`_
     ; `microsoft/console-virtual-terminal-sequences/mode-changes`_
     ; `microsoft/console-virtual-terminal-sequences/alternate-screen-buffer`_
     ; `microsoft/console-virtual-terminal-sequences/window-width`_

    .. _`xterm/Mouse-Tracking`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Mouse-Tracking
    .. _xterm/Extended-coordinates: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Extended-coordinates
    .. _xterm/The-Alternate-Screen-Buffer: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-The-Alternate-Screen-Buffer
    .. _xterm/Bracketed-Paste-Mode: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Bracketed-Paste-Mode

    .. _`xterm/CSI/DECPM/h`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3F-Pm-h.1D0E
    .. _`xterm/CSI/DECPM/l`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3F-Pm-l.1D12
    .. _`microsoft/console-virtual-terminal-sequences/cursor-visibility`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#cursor-visibility
    .. _`microsoft/console-virtual-terminal-sequences/mode-changes`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#mode-changes
    .. _`microsoft/console-virtual-terminal-sequences/alternate-screen-buffer`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#alternate-screen-buffer
    .. _`microsoft/console-virtual-terminal-sequences/window-width`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#window-width
    """

    @staticmethod
    @__DECPM_GATE__(CSI.new_nul)
    def high(mode: int) -> CSI:
        """:return: CSI ? { mode } h"""
        return CSI(f'?{mode}h')

    @staticmethod
    @__DECPM_GATE__(CSI.new_nul)
    def low(mode: int) -> CSI:
        """:return: CSI ? { mode } l"""
        return CSI(f'?{mode}l')

    @staticmethod
    def reply_cache(mode: int) -> int | None:
        """Query a reply value for `mode` from the `__ReplyCache__` (:class:`_ReplyCache`).

        :return: Reply value | None"""
        return __ReplyCache__.get(mode)


class DECPMHandler:

    mode: int

    def __init__(self, mode: int, atexit: Literal['h', 'l'] | str = None):
        """
        Handler for DEC private modes.
        `atexit`: optionally register the output of high/low when leaving the python interpreter.
        """
        self.mode = mode
        if atexit:
            _atexit.register(lambda: CSI(f'?{mode}{atexit}').out())

    def high(self) -> CSI:
        """:return: CSI ? { mode } h"""
        return DECPrivateMode.high(self.mode)

    def low(self) -> CSI:
        """:return: CSI ? { mode } l"""
        return DECPrivateMode.low(self.mode)

    def highout(self) -> None:
        """Output "``CSI ? { mode } h``" to stdout, then flush stdout."""
        DECPrivateMode.high(self.mode).out()

    def lowout(self) -> None:
        """Output "``CSI ? { mode } l``" to stdout, then flush stdout."""
        DECPrivateMode.low(self.mode).out()


def MouseSendPress(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (9, <atexit>)

    DECPM ``9``: Send Mouse X & Y on button press. (X10 xterm mouse protocol)
    """
    return DECPMHandler(9, atexit)


def MouseSendPressNRelease(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (1000, <atexit>)

    DECPM ``1000``: Send Mouse X & Y on button press and release. See the section Mouse Tracking. This is the X11 xterm mouse protocol.
    """
    return DECPMHandler(1000, atexit)


def MouseHighlightTracking(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (1001, <atexit>)

    DECPM ``1001``: Use Highlight Mouse Tracking, xterm.  (eq. to 1000)
    """
    return DECPMHandler(1001, atexit)


def MouseCellMotionTracking(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (1002, <atexit>)

    DECPM ``1002``: Use Cell Motion Mouse Tracking, xterm.
    """
    return DECPMHandler(1002, atexit)


def MouseAllTracking(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (1003, <atexit>)

    DECPM ``1003``: Use All Motion Mouse Tracking, xterm.
    """
    return DECPMHandler(1003, atexit)


def ScreenReverseVideo(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (5, <atexit>)

    DECPM ``5``: Reverse Video (DECSCNM), VT100.
    """
    return DECPMHandler(5, atexit)


def ScreenAlternateBuffer(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (1049, <atexit>)

    DECPM ``1049``: Save cursor as in DECSC, xterm. After saving the cursor, switch to the Alternate Screen Buffer, clearing it first. This may be disabled by the titeInhibit resource. This control combines the effects of the 1 0 4 7 and 1 0 4 8 modes. Use this with terminfo-based applications rather than the 4 7 mode.  **[i] Windows / UNIX compatible**
    """
    return DECPMHandler(1049, atexit)


def CursorAutowrapMode(atexit: Literal['h', 'l'] | str | None = 'h') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (7, <atexit>)

    DECPM ``7``: Auto-Wrap Mode (DECAWM), VT100.
    """
    return DECPMHandler(7, atexit)


def CursorBlinking(atexit: Literal['h', 'l'] | str | None = 'h') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (12, <atexit>)

    DECPM ``12``: Blinking cursor (AT&T 610).  **[i] Windows / UNIX compatible**
    """
    return DECPMHandler(12, atexit)


def CursorShow(atexit: Literal['h', 'l'] | str | None = 'h') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (25, <atexit>)

    DECPM ``25``: Show cursor (DECTCEM), VT220.  **[i] Windows / UNIX compatible**
    """
    return DECPMHandler(25, atexit)


def CursorSaveDEC(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (1048, <atexit>)

    DECPM ``1048``: Save cursor as in DECSC, xterm. This may be disabled by the titeInhibit resource.
    """
    return DECPMHandler(1048, atexit)


def ApplicationCursorKeys(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (1, <atexit>)

    DECPM ``1``: Application Cursor Keys (DECCKM), VT100.  **[i] Windows / UNIX compatible**
    """
    return DECPMHandler(1, atexit)


def BracketedPasteMode(atexit: Literal['h', 'l'] | str | None = 'l') -> DECPMHandler:
    """
    Factory function to :class:`DECPMHandler` (2004, <atexit>)

    DECPM ``2004``: Set bracketed paste mode, xterm.
    """
    return DECPMHandler(2004, atexit)
