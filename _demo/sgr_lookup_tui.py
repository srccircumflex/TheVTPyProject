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


# This code is neither beautiful, economical, innovative, or compatible -- do it better.


from __future__ import annotations

import sys
from re import sub, compile, IGNORECASE
from time import sleep
from typing import Callable


try:
    ROOT = sub("[/\\\\]_demo[/\\\\][^/\\\\]+$", "", __file__) + "/"
    sys.path.append(ROOT)
finally:
    pass

from vtframework.iodata.sgr import (
    SGRWrap,
    Fore,
    Ground,
    RGBTablesPrism,
    INVERT,
    StyleBasics,
    StyleFonts,
    StyleSpecials,
    _ColoredUnderline,
    UNDERLINE,
    SGRSeqs,
    BOLD,
    StyleResets
)
from _demo._geowatcher import GeoWatcher
from vtframework.iodata.cursor import CursorNavigate
from vtframework.iodata.textctrl import Erase
from vtframework.io import StdinAdapter, InputSuperModem, SpamHandleNicer
from vtframework.iodata import (
    NavKey,
    Ctrl,
    DelIns,
    Char,
    EscSegment,
    ManualESC,
    BasicKeyComp,
    EscContainer,
    Mouse,
    CursorShow, Meta
)
from vtframework.iodata.decpm import ScreenAlternateBuffer, MouseSendPressNRelease, DECPMHandler
from vtframework.iosys.vtermios import mod_ansiin, mod_ansiout
from vtframework.textbuffer import TextBuffer, DisplayScrollable

SPECTRA_WIDTH_HINT = 80

HEAD_FORE = Fore.hex("F5F4CA")
HEAD_GROUND = Ground.hex("88807C")

FOOTER_FORE = Fore.hex("6A6F7B")
FOOTER_GROUND = Ground.hex("DACEC8")

FOOTER_KEYS = Fore.blue + BOLD
FOOTER_INFO = Fore.red + UNDERLINE

PROMPT_FORE = Fore.hex("8CED7D")
PROMPT_GROUND = Ground.hex("2F3A38")

MAIN_MENU_HEAD = "SGR-LOOKUP"
MAIN_MENU_FOOTER = (
        SGRSeqs(FOOTER_KEYS) + "UP/DOWN" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": navigation  " +
        SGRSeqs(FOOTER_KEYS) + "RIGHT" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": enter  " +
        SGRSeqs(FOOTER_KEYS) + "META/ALT-m" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": mouse support  " +
        SGRSeqs(FOOTER_KEYS) + "<ESC>" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": exit"
)

SPECTRA_MENU_HEAD = "SGR-LOOKUP/COLOR-NAMES-SPECTRA"
SPECTRA_MENU_FOOTER = (
        SGRSeqs(FOOTER_KEYS) + "UP/DOWN" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": navigation  " +
        SGRSeqs(FOOTER_KEYS) + "RIGHT" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": enter  " +
        SGRSeqs(FOOTER_KEYS) + "LEFT" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": back  " +
        SGRSeqs(FOOTER_KEYS) + "META/ALT-m" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": mouse support"
)

SPECTRUM_FOOTER = (
        SGRSeqs(FOOTER_KEYS) + "[PAGE-]UP/DOWN" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": scrolling  " +
        SGRSeqs(FOOTER_KEYS) + "LEFT" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": back  " +
        SGRSeqs(FOOTER_KEYS) + "META/ALT-m" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": mouse support  " +
        SGRSeqs(FOOTER_KEYS) + "<ESC>" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": main menu"
)

BASE256_COLORS_HEAD = "SGR-LOOKUP/Base256 Colors"
BASE256_COLORS_FOOTER = (
        SGRSeqs(FOOTER_KEYS) + "[PAGE-]UP/DOWN" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": scrolling  " +
        SGRSeqs(FOOTER_KEYS) + "LEFT" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": back  " +
        SGRSeqs(FOOTER_KEYS) + "META/ALT-m" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": mouse support"
)

REL_COLORS_HEAD = "SGR-LOOKUP/Rel Colors"
REL_COLORS_FOOTER = (
        SGRSeqs(FOOTER_KEYS) + "[PAGE-]UP/DOWN" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": scrolling  " +
        SGRSeqs(FOOTER_KEYS) + "LEFT" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": back  " +
        SGRSeqs(FOOTER_KEYS) + "META/ALT-m" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": mouse support"
)

MODS_HEAD = "SGR-LOOKUP/SGR Mods"
MODS_FOOTER = (
        SGRSeqs(FOOTER_KEYS) + "[PAGE-]UP/DOWN" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": scrolling  " +
        SGRSeqs(FOOTER_KEYS) + "LEFT" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": back  " +
        SGRSeqs(FOOTER_KEYS) + "META/ALT-m" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": mouse support"
)

FIND_COLORS_HEAD = "SGR-LOOKUP/Find Named Colors"
FIND_COLORS_FOOTER = (
        SGRSeqs(FOOTER_KEYS) + "PAGE-(UP/DOWN)" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": scrolling  " +
        SGRSeqs(FOOTER_KEYS) + "UP/DOWN" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": history  " +
        SGRSeqs(FOOTER_KEYS) + "<ESC>" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": main menu  " +
        SGRSeqs(FOOTER_KEYS) + "META/ALT-m" + SGRSeqs(StyleResets.any) +
        SGRSeqs(FOOTER_FORE) + ": mouse support  " +
        SGRSeqs(FOOTER_INFO) + "[i]: re.IGNORECASE is set" + SGRSeqs(StyleResets.any)
)

_PAGEKEY_MAIN_MENU = "//main"
_PAGEKEY_SPECTRA_MENU = "//main/spectra"
_PAGEKEY_SPECTRUM = "//main/spectra/spectrum"
_PAGEKEY_BASE256_COLORS = "//main/base256"
_PAGEKEY_REL_COLORS = "//main/rel"
_PAGEKEY_MODS = "//main/mods"
_PAGEKEY_FIND_COLORS = "//main/find"

_MAIN_MENU_LABEL_SPECTRA_MENU = "Named Colors"
_MAIN_MENU_LABEL_BASE256_COLORS = "Base256 Colors"
_MAIN_MENU_LABEL_REL_COLORS = "Relative Terminal Colors"
_MAIN_MENU_LABEL_MODS = "SGR Modifications"
_MAIN_MENU_LABEL_FIND_COLORS = "Find Named Colors"


class SGRLookUp:

    prism = RGBTablesPrism(ROOT + "vtframework/iodata/_rgb")
    cursor_show: DECPMHandler
    mouse_support: DECPMHandler = MouseSendPressNRelease()
    mouse_val = False

    class Input:
        __buffer__: TextBuffer
        __display__: DisplayScrollable
        _prompt: tuple[EscSegment | EscContainer, EscSegment | EscContainer]
        geo_handler: GeoWatcher
        cache: list[str]
        cache_cur: int
        action: Callable

        def __init__(self, geo_handler: GeoWatcher, prompt: EscSegment | EscContainer, eol: EscSegment | EscContainer = EscSegment('')):
            self._prompt = (prompt, eol)

            self.geo_handler = geo_handler

            self.__buffer__ = TextBuffer(
                top_row_vis_maxsize=None,
                future_row_vis_maxsize=None,
                tab_size=4,
                tab_to_blank=False,
                autowrap_points=False,
                jump_points_re=None,
                back_jump_re=None
            )
            self.__buffer__.init_rowmax__restrict(
                rows_maximal=1,
                last_row_maxsize=None
            )
            self.__display__ = DisplayScrollable(
                self.__buffer__,
                height=1,
                y_auto_scroll_distance=0,
                prompt_factory=lambda *_: self._prompt,
                promptl_len=len(prompt),
                promptr_len=len(eol),
                width=self.geo_handler.width,
                lapping=int((self.geo_handler.width - (len(prompt) + len(eol))) * .8),
                vis_overflow=(SGRWrap('<', INVERT), SGRWrap('>', INVERT), SGRWrap('<<', INVERT)),
                vis_marked=None,
                vis_end=None,
                vis_nb_end=None,
                vis_tab=None,
                vis_cursor=None,
                vis_anchor=None,
                vis_cursor_row=None,
                highlighter=None,
                stdcurpos=0,
                visendpos='visN1',
                i_rowitem_generator=None,
                i_display_generator=None,
                i_before_framing=None,
                highlighted_rows_cache_max=1000,
                highlighted_row_segments_max=None,
                width_min_char=EscSegment(" ")
            )

            self.cache = list()
            self.cache_cur = 0

            self.action = lambda: None

        def write(self, c: Char, __=None):
            self.__buffer__.write(c)

        def _move_cursor(self, nk: NavKey, __=None):
            if nk in BasicKeyComp.NavKeys.arrow_lr:
                self.__buffer__.cursor_move(
                    z_column=int(nk),
                    jump=NavKey.M.CTRL in nk.MOD)
            elif nk in BasicKeyComp.NavKeys.border:
                self.__buffer__.cursor_move(
                    z_column=int(nk),
                    border=True)
            elif nk in BasicKeyComp.NavKeys.arrow_ud:
                if nk.KEY == nk.K.A_UP:
                    try:
                        cont = self.cache[(cache_cur := self.cache_cur - 1)]
                    except IndexError:
                        return
                    else:
                        self.cache_cur = cache_cur
                        self.__buffer__.reinitialize()
                        self.__buffer__.write(cont)
                else:
                    if self.cache_cur:
                        self.cache_cur += 1
                        if self.cache_cur:
                            self.__buffer__.reinitialize()
                            self.__buffer__.write(self.cache[self.cache_cur])
                        else:
                            self.__buffer__.reinitialize()
                    else:
                        self.__buffer__.reinitialize()

        def resize(self):
            self.__display__.settings(
                width=self.geo_handler.size[0], height=1,
                lapping=int((self.geo_handler.size[0] - ((ll := len(self._prompt[0])) + (rl := len(self._prompt[1])))) * .8),
                promptl_len=ll, promptr_len=rl
            )

        def pop(self) -> str:
            cont = self.__buffer__.reader(endings={'\n': b''}).read()
            self.__buffer__.reinitialize()
            self.cache.append(cont)
            if len(self.cache) > 120:
                self.cache = self.cache[-100:]
            self.cache_cur = 0
            return cont

        def img(self):
            return self.__display__.make_display()

    geo_watcher: GeoWatcher
    input_modem: InputSuperModem

    cursor = 0
    pre_cursors = []
    current_page = _PAGEKEY_MAIN_MENU

    def __init__(self):

        self.geo_watcher = GeoWatcher()
        self.geo_watcher.bind(lambda *_: self.pages[self.current_page][16]())

        self.pages = {
            _PAGEKEY_MAIN_MENU: (
                SGRSeqs(HEAD_GROUND + HEAD_FORE) + MAIN_MENU_HEAD,  # head
                [  # body
                    _MAIN_MENU_LABEL_SPECTRA_MENU,
                    _MAIN_MENU_LABEL_BASE256_COLORS,
                    _MAIN_MENU_LABEL_REL_COLORS,
                    _MAIN_MENU_LABEL_MODS,
                    _MAIN_MENU_LABEL_FIND_COLORS,
                ],
                SGRSeqs(FOOTER_FORE + FOOTER_GROUND) + MAIN_MENU_FOOTER,  # footer
                # arrow up/down
                lambda *_: self._move_menu_cursor(-1),
                lambda *_: self._move_menu_cursor(1),
                # arrow left/right
                lambda *_: self._move_page(-1),
                lambda *_: self._move_page(1),
                # page up/down
                lambda *_: self._move_menu_cursor(-8),
                lambda *_: self._move_menu_cursor(8),
                # cursor home/end
                lambda *_: self._move_menu_cursor(-99999),
                lambda *_: self._move_menu_cursor(99999),
                # enter/backspace/delete
                lambda *_: self._move_page(1),
                lambda *_: self._move_page(-1),
                lambda *_: None,
                # chars
                lambda c: (exit(0) if c in ("q", "Q") else None),
                # esc
                lambda *_: exit(0),
                # resize
                lambda: self._move_menu_cursor(0),
                # tab/shift-tab
                lambda *_: self._move_menu_cursor(1),
                lambda *_: self._move_menu_cursor(-1),
                # mouse
                lambda m: {
                    64: lambda: self._move_menu_cursor(-1),
                    65: lambda: self._move_menu_cursor(1),
                    0: lambda: self._move_page(1),
                }.get(int(m), lambda: None)(),
                self._mouse
            ),
            _PAGEKEY_SPECTRA_MENU: (
                SGRSeqs(HEAD_GROUND + HEAD_FORE) + SPECTRA_MENU_HEAD,
                [
                    "ALL",
                    "blue",
                    "cyan",
                    "dark",
                    "gray",
                    "green",
                    "light",
                    "magenta",
                    "red",
                    "yellow",
                ],
                SGRSeqs(FOOTER_FORE + FOOTER_GROUND) + SPECTRA_MENU_FOOTER,
                # arrow up/down
                lambda *_: self._move_menu_cursor(-1),
                lambda *_: self._move_menu_cursor(1),
                # arrow left/right
                lambda *_: self._move_page(-1),
                lambda *_: self._move_page(1),
                # page up/down
                lambda *_: self._move_menu_cursor(-8),
                lambda *_: self._move_menu_cursor(8),
                # cursor home/end
                lambda *_: self._move_menu_cursor(-99999),
                lambda *_: self._move_menu_cursor(99999),
                # enter/backspace/delete
                lambda *_: self._move_page(1),
                lambda *_: self._move_page(-1),
                lambda *_: None,
                # chars
                lambda c: (self._move_page(-1) if c in ("q", "Q") else None),
                # esc
                lambda *_: self._move_page(-1),
                # resize
                lambda: self._move_menu_cursor(0),
                # tab/shift-tab
                lambda *_: self._move_menu_cursor(1),
                lambda *_: self._move_menu_cursor(-1),
                # mouse
                lambda m: {
                    64: lambda: self._move_menu_cursor(-1),
                    65: lambda: self._move_menu_cursor(1),
                    0: lambda: self._move_page(1),
                    2: lambda: self._move_page(-1),
                }.get(int(m), lambda: None)(),
                self._mouse
            ),
            _PAGEKEY_SPECTRUM: [
                "-*-",
                [],
                SGRSeqs(FOOTER_FORE + FOOTER_GROUND) + SPECTRUM_FOOTER,
                # arrow up/down
                lambda *_: self._move_content_cursor(-1),
                lambda *_: self._move_content_cursor(1),
                # arrow left/right
                lambda *_: self._move_page(-1),
                lambda *_: self._move_page(1),
                # page up/down
                lambda *_: self._move_content_cursor(-8),
                lambda *_: self._move_content_cursor(8),
                # cursor home/end
                lambda *_: self._move_content_cursor(-99999),
                lambda *_: self._move_content_cursor(99999),
                # enter/backspace/delete
                lambda *_: self._move_page(1),
                lambda *_: self._move_page(-1),
                lambda *_: None,
                # chars
                lambda c: (self._move_page(0, _PAGEKEY_MAIN_MENU) if c in ("q", "Q") else None),
                # esc
                lambda *_: self._move_page(0, _PAGEKEY_MAIN_MENU),
                # resize
                lambda: self._move_content_cursor(0),
                # tab/shift-tab
                lambda *_: self._move_content_cursor(1),
                lambda *_: self._move_content_cursor(-1),
                # mouse
                lambda m: {
                    64: lambda: self._move_content_cursor(-1),
                    65: lambda: self._move_content_cursor(1),
                    2: lambda: self._move_page(-1),
                }.get(int(m), lambda: None)(),
                self._mouse
                ],
            _PAGEKEY_BASE256_COLORS: [
                SGRSeqs(HEAD_GROUND + HEAD_FORE) + BASE256_COLORS_HEAD,
                [],
                SGRSeqs(FOOTER_FORE + FOOTER_GROUND) + BASE256_COLORS_FOOTER,
                # arrow up/down
                lambda *_: self._move_content_cursor(-1),
                lambda *_: self._move_content_cursor(1),
                # arrow left/right
                lambda *_: self._move_page(-1),
                lambda *_: self._move_page(1),
                # page up/down
                lambda *_: self._move_content_cursor(-8),
                lambda *_: self._move_content_cursor(8),
                # cursor home/end
                lambda *_: self._move_content_cursor(-99999),
                lambda *_: self._move_content_cursor(99999),
                # enter/backspace/delete
                lambda *_: self._move_page(1),
                lambda *_: self._move_page(-1),
                lambda *_: None,
                # chars
                lambda c: (self._move_page(-1) if c in ("q", "Q") else None),
                # esc
                lambda *_: self._move_page(-1),
                # resize
                lambda: self._move_content_cursor(0),
                # tab/shift-tab
                lambda *_: self._move_content_cursor(1),
                lambda *_: self._move_content_cursor(-1),
                # mouse
                lambda m: {
                    64: lambda: self._move_content_cursor(-1),
                    65: lambda: self._move_content_cursor(1),
                    2: lambda: self._move_page(-1),
                }.get(int(m), lambda: None)(),
                self._mouse
                ],
            _PAGEKEY_REL_COLORS: [
                SGRSeqs(HEAD_GROUND + HEAD_FORE) + REL_COLORS_HEAD,
                [],
                SGRSeqs(FOOTER_FORE + FOOTER_GROUND) + REL_COLORS_FOOTER,
                # arrow up/down
                lambda *_: self._move_content_cursor(-1),
                lambda *_: self._move_content_cursor(1),
                # arrow left/right
                lambda *_: self._move_page(-1),
                lambda *_: self._move_page(1),
                # page up/down
                lambda *_: self._move_content_cursor(-8),
                lambda *_: self._move_content_cursor(8),
                # cursor home/end
                lambda *_: self._move_content_cursor(-99999),
                lambda *_: self._move_content_cursor(99999),
                # enter/backspace/delete
                lambda *_: self._move_page(1),
                lambda *_: self._move_page(-1),
                lambda *_: None,
                # chars
                lambda c: (self._move_page(-1) if c in ("q", "Q") else None),
                # esc
                lambda *_: self._move_page(-1),
                # resize
                lambda: self._move_content_cursor(0),
                # tab/shift-tab
                lambda *_: self._move_content_cursor(1),
                lambda *_: self._move_content_cursor(-1),
                # mouse
                lambda m: {
                    64: lambda: self._move_content_cursor(-1),
                    65: lambda: self._move_content_cursor(1),
                    2: lambda: self._move_page(-1),
                }.get(int(m), lambda: None)(),
                self._mouse
                ],
            _PAGEKEY_MODS: [
                SGRSeqs(HEAD_GROUND + HEAD_FORE) + MODS_HEAD,
                [],
                SGRSeqs(FOOTER_FORE + FOOTER_GROUND) + MODS_FOOTER,
                # arrow up/down
                lambda *_: self._move_content_cursor(-1),
                lambda *_: self._move_content_cursor(1),
                # arrow left/right
                lambda *_: self._move_page(-1),
                lambda *_: self._move_page(1),
                # page up/down
                lambda *_: self._move_content_cursor(-8),
                lambda *_: self._move_content_cursor(8),
                # cursor home/end
                lambda *_: self._move_content_cursor(-99999),
                lambda *_: self._move_content_cursor(99999),
                # enter/backspace/delete
                lambda *_: self._move_page(1),
                lambda *_: self._move_page(-1),
                lambda *_: None,
                # chars
                lambda c: (self._move_page(-1) if c in ("q", "Q") else None),
                # esc
                lambda *_: self._move_page(-1),
                # resize
                lambda: self._move_content_cursor(0),
                # tab/shift-tab
                lambda *_: self._move_content_cursor(1),
                lambda *_: self._move_content_cursor(-1),
                # mouse
                lambda m: {
                    64: lambda: self._move_content_cursor(-1),
                    65: lambda: self._move_content_cursor(1),
                    2: lambda: self._move_page(-1),
                }.get(int(m), lambda: None)(),
                self._mouse
                ],
            _PAGEKEY_FIND_COLORS: [
                SGRSeqs(HEAD_GROUND + HEAD_FORE) + FIND_COLORS_HEAD,
                [],
                SGRSeqs(FOOTER_FORE + FOOTER_GROUND) + FIND_COLORS_FOOTER,
                # arrow up/down
                lambda nk: self._move_input_cursor(nk),
                lambda nk: self._move_input_cursor(nk),
                # arrow left/right
                lambda nk: self._move_input_cursor(nk),
                lambda nk: self._move_input_cursor(nk),
                # page up/down
                lambda *_: self._move_content_cursor(-8),
                lambda *_: self._move_content_cursor(8),
                # cursor home/end
                lambda nk: self._move_input_cursor(nk),
                lambda nk: self._move_input_cursor(nk),
                # enter/backspace/delete
                lambda *_: (self.pages[self.current_page][-1].action(), self._input_body_out()),
                lambda *_: (self.pages[self.current_page][-1].__buffer__.backspace(), self._input_body_out()),
                lambda *_: (self.pages[self.current_page][-1].__buffer__.delete(), self._input_body_out()),
                # chars
                lambda c: self._write_input(c),
                # esc
                lambda *_: self._move_page(-1),
                # resize
                lambda: (self.pages[self.current_page][-1].resize(), self._input_body_out()),
                # tab/shift-tab
                lambda *_: self._move_content_cursor(1),
                lambda *_: self._move_content_cursor(-1),
                # mouse
                lambda m: {
                    64: lambda: self._move_content_cursor(-1),
                    65: lambda: self._move_content_cursor(1),
                    2: lambda: self._move_page(-1),
                }.get(int(m), lambda: None)(),
                self._mouse,
                # input @ -1
                self.Input(self.geo_watcher, SGRWrap("Color Name REGEX []:", PROMPT_FORE + PROMPT_GROUND) + " "),
            ],
        }

        StdinAdapter()

        self.input_modem = InputSuperModem(manual_esc_tt=0, thread_block=True, thread_spam=SpamHandleNicer(Mouse, spamtime=.2))

        self.input_modem.__binder__.bind(NavKey(NavKey.K.A_UP), lambda o, _: self.pages[self.current_page][3](o))
        self.input_modem.__binder__.bind(NavKey(NavKey.K.A_DOWN), lambda o, _: self.pages[self.current_page][4](o))

        self.input_modem.__binder__.bind(NavKey(NavKey.K.A_LEFT), lambda o, _: self.pages[self.current_page][5](o))
        self.input_modem.__binder__.bind(NavKey(NavKey.K.A_RIGHT), lambda o, _: self.pages[self.current_page][6](o))

        self.input_modem.__binder__.bind(NavKey(NavKey.K.P_UP), lambda o, _: self.pages[self.current_page][7](o))
        self.input_modem.__binder__.bind(NavKey(NavKey.K.P_DOWN), lambda o, _: self.pages[self.current_page][8](o))

        self.input_modem.__binder__.bind(NavKey(NavKey.K.C_HOME), lambda o, _: self.pages[self.current_page][9](o))
        self.input_modem.__binder__.bind(NavKey(NavKey.K.C_END), lambda o, _: self.pages[self.current_page][10](o))

        self.input_modem.__binder__.bind(Ctrl("enter"), lambda o, _: self.pages[self.current_page][11](o))
        self.input_modem.__binder__.bind(DelIns(DelIns.K.BACKSPACE), lambda o, _: self.pages[self.current_page][12](o))
        self.input_modem.__binder__.bind(DelIns(DelIns.K.DELETE), lambda o, _: self.pages[self.current_page][13](o))

        self.input_modem.__binder__.bind(Char, lambda o, _: self.pages[self.current_page][14](o))

        self.input_modem.__binder__.bind(ManualESC(""), lambda o, _: self.pages[self.current_page][15](o))

        # 16 -> resize

        self.input_modem.__binder__.bind(Ctrl("tab"), lambda o, _: self.pages[self.current_page][17](o))
        self.input_modem.__binder__.bind(NavKey(NavKey.K.SHIFT_TAB, NavKey.M.SHIFT), lambda o, _: self.pages[self.current_page][18](o))
        self.input_modem.__binder__.bind(Mouse, lambda o, _: self.pages[self.current_page][19](o))
        self.input_modem.__binder__.bind(Meta("m"), lambda o, _: self.pages[self.current_page][20](o))

        def name_regex_action():
            inp: SGRLookUp.Input = self.pages[self.current_page][-1]
            regex = inp.pop()
            self.pages[self.current_page][1] = self.lookup_name_regex(regex)
            self.cursor = 0
            inp._prompt = (SGRWrap("Color Name REGEX [%s]:" % regex, PROMPT_FORE + PROMPT_GROUND) + " ", inp._prompt[1])
            inp.resize()
            self._input_body_out()

        self.pages[_PAGEKEY_FIND_COLORS][-1].action = name_regex_action

    @staticmethod
    def lookup_name_regex(regex: str) -> list[str]:
        _spectra = SGRLookUp.prism._get_spectra_file_func()
        spectra = []
        for __spectrum, item in _spectra.items():
            spectra.append(SGRWrap(": " + __spectrum + " :", UNDERLINE))
            with open(item[0], "rb") as f:
                _ln = EscSegment("")
                while ln := f.readline():
                    if rgb_id := SGRLookUp.prism.rgb_from_row_by_pattern_obj(ln, compile(regex.encode(), IGNORECASE)):
                        r, g, b, name = rgb_id
                        name = name.decode()
                        _ln += SGRWrap('                ', Ground.rgb(int(r), int(g), int(b))) + '%-18s' % name
                        if len(_ln) > 120:
                            spectra.append(_ln)
                            _ln = EscSegment("")
                spectra.append(_ln)
        return spectra

    @staticmethod
    def lookup_modi() -> list[str]:
        spectra = []
        for cat in (StyleBasics, StyleFonts, StyleSpecials):
            for attr, val in cat.__dict__.items():
                if attr.startswith('_'):
                    continue
                if attr[0].isupper():
                    for _attr, _val in val.__dict__.items():
                        if _attr.startswith('_'):
                            continue
                        label = "%s.%s.%s" % (cat.__name__, attr, _attr)
                        spectra.append(SGRWrap(label, _val) + ('(%s)' % label if _attr == "hide" else ""))
                else:
                    spectra.append(SGRWrap("%s.%s" % (cat.__name__, attr), val))
        spectra.append(SGRWrap('SGRWrap(..., _ColoredUnderline.red)', _ColoredUnderline.red))
        spectra.append(SGRWrap('SGRWrap(..., _ColoredUnderline.name("yellow"))', _ColoredUnderline.name("yellow")))
        spectra.append(SGRWrap('SGRWrap(..., _ColoredUnderline.hex("0000FF"))', _ColoredUnderline.hex("0000FF")))
        return spectra

    @staticmethod
    def lookup_rel() -> list[str]:
        spectra = []
        for c, v in Fore.__dict__.items():
            if c.endswith('_rel'):
                spectra.append(EscSegment('%-12s' % c) + SGRWrap('%-18s' % str(v)[2], v, INVERT))
        return spectra

    @staticmethod
    def lookup_256() -> list[str]:
        spectra = []
        for p in range(2):
            ln = EscSegment("")
            for sc in range(8):
                sc += 8 * p
                ln += SGRWrap('%-4d' % sc, Fore.b256(sc), INVERT)
            spectra.append(ln)
        spectra.append("")
        for c in ((16, 47), (52, 83)):
            for y in range(*c, 6):
                ln = EscSegment("")
                for cy in range(3):
                    for x in range(6):
                        x = y + x + 36 * cy
                        ln += SGRWrap('%-4d' % x, Fore.b256(x), INVERT)
                    ln += "  "
                spectra.append(ln)
            spectra.append("")
        for p in range(2):
            ln = EscSegment("")
            for gs in range(232, 244):
                gs += 12 * p
                ln += SGRWrap('%-4d' % gs, Fore.b256(gs), INVERT)
            spectra.append(ln)
        return spectra

    @staticmethod
    def lookup_spectra(__spectrum: str = None, width_hint=80) -> list[str]:
        _spectra = SGRLookUp.prism._get_spectra_file_func()
        if __spectrum:
            if not (_item := _spectra.get(__spectrum)):
                raise LookupError(__spectrum)
            _spectra = {__spectrum: _item}
        spectra = []
        for __spectrum, item in _spectra.items():
            spectra.append(SGRWrap(": " + __spectrum + " :", UNDERLINE))
            with open(item[0], "rb") as f:
                _ln = EscSegment("")
                while ln := f.readline():
                    if rgb_id := SGRLookUp.prism.rgb_from_row(ln):
                        r, g, b, name = rgb_id
                        name = name.decode()
                        _ln += SGRWrap('                ', Ground.name(name)) + '%-18s' % name
                        if len(_ln) > width_hint:
                            spectra.append(_ln)
                            _ln = EscSegment("")
                spectra.append(_ln)
        return spectra

    def _page_out(self, head: str, body: list[str], tail: str):

        self.cursor_show.lowout()
        self.cursor_show.highout()
        self.cursor_show.lowout()

        CursorNavigate.position().out()

        if len(head) > self.geo_watcher.width:
            head = head[:self.geo_watcher.width - 1] + '…'
        sys.stdout.write(EscSegment("%%-%ds\x1b[m\r\n" % self.geo_watcher.width) % head)

        for ln in body:
            if len(ln) > self.geo_watcher.width:
                ln = ln[:self.geo_watcher.width - 1] + '…'
            sys.stdout.write(EscSegment("%%-%ds\x1b[m\r\n" % self.geo_watcher.width) % ln)

        for nl in range(max(0, self.geo_watcher.height - 2 - len(body))):
            sys.stdout.write("\r\n")

        if len(tail) > self.geo_watcher.width:
            tail = tail[:self.geo_watcher.width - 1] + '…'
        sys.stdout.write(EscSegment("%%-%ds\x1b[m" % self.geo_watcher.width) % tail)

        self.cursor_show.highout()

        sys.stdout.flush()

    def _input_body_out(self):
        inp: SGRLookUp.Input = self.pages[self.current_page][-1]
        img = inp.img()
        _body = [str(img.rows[0])] + self.pages[self.current_page][1][self.cursor:self.cursor + (self.geo_watcher.height - 3)]
        self._page_out(self.pages[self.current_page][0], _body, self.pages[self.current_page][2])
        CursorNavigate.position().out()
        CursorNavigate.down().out()
        CursorNavigate.forward(img.pointer_column).out()

    def _move_input_cursor(self, nk: NavKey):
        inp: SGRLookUp.Input = self.pages[self.current_page][-1]
        inp._move_cursor(nk)
        self._input_body_out()

    def _write_input(self, c: Char):
        inp: SGRLookUp.Input = self.pages[self.current_page][-1]
        inp.write(c)
        self._input_body_out()

    def _move_page(self, n: int, goto: str = None):

        Erase.display().out()

        def _goto():
            if self.current_page in (_PAGEKEY_MAIN_MENU, _PAGEKEY_SPECTRA_MENU):
                self.cursor = 0
                self._move_menu_cursor(0)
            elif self.current_page in (_PAGEKEY_BASE256_COLORS, _PAGEKEY_REL_COLORS, _PAGEKEY_SPECTRUM):
                self.cursor = 0
                self._move_content_cursor(0)

        if goto is not None:
            self.current_page = goto
            _goto()
        elif n > 0:
            self.pre_cursors.append(self.cursor)
            if self.current_page == _PAGEKEY_MAIN_MENU:
                if self.cursor == 0:
                    self.current_page = _PAGEKEY_SPECTRA_MENU
                    self.cursor = 0
                    self._move_menu_cursor(0)
                elif self.cursor == 1:
                    self.current_page = _PAGEKEY_BASE256_COLORS
                    self.pages[self.current_page][1] = self.lookup_256()
                    self.cursor = 0
                    self._move_content_cursor(0)
                elif self.cursor == 2:
                    self.current_page = _PAGEKEY_REL_COLORS
                    self.pages[self.current_page][1] = self.lookup_rel()
                    self.cursor = 0
                    self._move_content_cursor(0)
                elif self.cursor == 3:
                    self.current_page = _PAGEKEY_MODS
                    self.pages[self.current_page][1] = self.lookup_modi()
                    self.cursor = 0
                    self._move_content_cursor(0)
                elif self.cursor == 4:
                    self.current_page = _PAGEKEY_FIND_COLORS
                    self.cursor = 0
                    self._move_input_cursor(NavKey(NavKey.K.A_LEFT))
            elif self.current_page == _PAGEKEY_SPECTRA_MENU:
                spectra = self.pages[self.current_page][1][self.cursor]
                self.current_page = _PAGEKEY_SPECTRUM
                if spectra == "ALL":
                    self.pages[self.current_page][0] = SGRSeqs(HEAD_GROUND + HEAD_FORE) + SPECTRA_MENU_HEAD + "/ALL"
                    self.pages[self.current_page][1] = self.lookup_spectra(width_hint=SPECTRA_WIDTH_HINT)
                else:
                    self.pages[self.current_page][0] = SGRSeqs(HEAD_GROUND + HEAD_FORE) + SPECTRA_MENU_HEAD + "/" + spectra
                    self.pages[self.current_page][1] = self.lookup_spectra(spectra, width_hint=SPECTRA_WIDTH_HINT)

                self.cursor = 0
                self._move_content_cursor(0)
        else:
            if self.current_page in (_PAGEKEY_SPECTRA_MENU, _PAGEKEY_BASE256_COLORS, _PAGEKEY_REL_COLORS, _PAGEKEY_MODS, _PAGEKEY_FIND_COLORS):
                self.current_page = _PAGEKEY_MAIN_MENU
            elif self.current_page == _PAGEKEY_SPECTRUM:
                self.current_page = _PAGEKEY_SPECTRA_MENU

            self.cursor = (self.pre_cursors.pop(-1) if self.pre_cursors else 0)
            self._move_menu_cursor(0)

    def _content_body_out(self, body: list[str]):
        _body = body[self.cursor:self.cursor + (self.geo_watcher.height - 2)]
        self._page_out(self.pages[self.current_page][0], _body, self.pages[self.current_page][2])

    def _move_content_cursor(self, n: int):
        if (_l := len(self.pages[self.current_page][1])) > self.geo_watcher.height - 2:
            self.cursor = max(0, min(_l - (self.geo_watcher.height - 2), self.cursor + n))
        self._content_body_out(self.pages[self.current_page][1])

    def _menu_body_out(self, body: list[str]):
        _body = []
        for i in range(len(body)):
            if i == self.cursor:
                _body.append(SGRWrap("[>] " + body[i], INVERT))
            else:
                _body.append("[ ] " + body[i])
        self._page_out(self.pages[self.current_page][0], _body, self.pages[self.current_page][2])

    def _move_menu_cursor(self, n: int):
        body = self.pages[self.current_page][1]
        self.cursor = max(0, min(len(body) - 1, self.cursor + n))
        self._menu_body_out(body)

    def _mouse(self, *_):
        self.mouse_val ^= True
        if self.mouse_val:
            self.mouse_support.highout()
        else:
            self.mouse_support.lowout()

    def mainloop(self):
        mod_ansiin()
        mod_ansiout()
        ScreenAlternateBuffer().highout()
        self.cursor_show = CursorShow()
        self._menu_body_out(self.pages[self.current_page][1])
        # sleep(1)
        # for key, timeout in (
        #     (NavKey(NavKey.K.A_DOWN), .57),
        #     (NavKey(NavKey.K.A_DOWN), .5),
        #     (NavKey(NavKey.K.A_UP), .57),
        #     (NavKey(NavKey.K.A_RIGHT), 2.4),
        #     (NavKey(NavKey.K.A_LEFT), .55),
        #     (NavKey(NavKey.K.A_DOWN), .355),
        #     (NavKey(NavKey.K.A_DOWN), .355),
        #     (NavKey(NavKey.K.A_DOWN), .355),
        #     (NavKey(NavKey.K.A_RIGHT), .6),
        #     (Char("."), .3),
        #     (Char("*"), .19),
        #     (Char("l"), .19),
        #     (Char("i"), .19),
        #     (Char("g"), .19),
        #     (Char("h"), .19),
        #     (Char("t"), .19),
        #     (Char("."), .19),
        #     (Char("*"), .19),
        #     (Ctrl("enter"), .6),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .05),
        #     (Mouse(Mouse.B.D_WHEEL), .8),
        #     (ManualESC(""), .6),
        #     (NavKey(NavKey.K.A_UP), .2),
        #     (NavKey(NavKey.K.A_UP), .2),
        #     (NavKey(NavKey.K.A_UP), .2),
        #     (NavKey(NavKey.K.A_UP), .4),
        #     (NavKey(NavKey.K.A_RIGHT), .2),
        #     (NavKey(NavKey.K.A_DOWN), .26),
        #     (NavKey(NavKey.K.A_DOWN), .26),
        #     (NavKey(NavKey.K.A_DOWN), .26),
        # ):
        #     self.input_modem.__binder__.send(key)
        #     sleep(timeout)
        self.input_modem.start(daemon=False)


if __name__ == "__main__":
    SGRLookUp().mainloop()
