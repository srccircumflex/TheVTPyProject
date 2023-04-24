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
from threading import Thread
from time import sleep, time
from typing import Callable, Literal, Any, Sequence
from re import sub, Pattern, compile
import atexit

try:
    ROOT = sub("[/\\\\]_demo[/\\\\][^/\\\\]+$", "", __file__)
    sys.path.append(ROOT)
finally:
    pass

from vtframework.iosys.vtermios import mod_ansiin, mod_ansiout, mod_nonimpldef, mod_nonprocess

from vtframework.textbuffer.buffer import TextBuffer
from vtframework.textbuffer.exceptions import CursorError, DatabaseInitError
from vtframework.io.io import flushio, out, StdinAdapter, SpamHandleOne
from vtframework.io.modem import InputRouter, InputSuperModem
from vtframework.textbuffer.display.displays import DisplayScrollable, DisplayBrowsable, HighlighterBase
from vtframework.textbuffer.display.items import VisRowItem, DisplayRowItem

from vtframework.iodata.c1ctrl import ManualESC
from vtframework.iodata.esccontainer import EscSegment, EscContainer
from vtframework.iodata.sgr import BOLD, SGRParams, SGRSeqs, SGRWrap, Ground, INVERT, Fore, StyleResets, UNDERLINE
from vtframework.iodata.chars import Char
from vtframework.iodata.keys import NavKey, DelIns, Ctrl, Meta
from vtframework.iodata.cursor import CursorStyle, CursorNavigate
from vtframework.iodata.textctrl import Erase
from vtframework.iodata.decpm import (
    ScreenAlternateBuffer,
    CursorAutowrapMode,
    BracketedPasteMode,
    CursorShow,
    CursorBlinking
)
from vtframework.iodata.eval import BasicKeyComp

from _demo._geowatcher import GeoWatcher
from _demo._highlighter_factory import python_darkula

from vtframework.textbuffer._buffercomponents.row import _Row


HEAD_SGR: SGRParams = Fore.hex('D3D7CF') + Ground.hex('555954')

HEAD_HISTORY_STAR_PAST = "<"
HEAD_HISTORY_STAR_FUTURE = ">"
HEAD_HISTORY_STAR_SGR_NOTREACHABLE = Fore.name('red') + Ground.hex('555954') + BOLD
HEAD_HISTORY_STAR_SGR_REACHABLE_DO = Fore.hex('77FFFA') + Ground.hex('555954') + BOLD
HEAD_HISTORY_STAR_SGR_REACHABLE_FORK = Fore.name('magenta') + Ground.hex('555954') + BOLD

LOAD_ANIMATION_SGR: SGRParams = Fore.hex('77FFFA') + Ground.hex('555954') + BOLD

MSG_ERROR_SGR: SGRParams = Fore.yellow + Ground.red + BOLD
MSG_WARN_SGR: SGRParams = Fore.hex("C4A000") + Ground.hex("333333")
MSG_INFO_SGR: SGRParams = Fore.hex("06989A") + Ground.hex("D3D7CF")
MSG_DEBUG_SGR: SGRParams = Fore.black + Ground.hex("73C48F")

FOOTER_SGR: SGRParams = Fore.hex('D3D7CF') + Ground.hex('313030')
FOOTER_KEY_SGR: SGRParams = Fore.hex("A9F4E2") + Ground.hex('313030') + BOLD
FOOTER_DESCRIPTION_SGR: SGRParams = Fore.white + Ground.hex('313030')

INPUT_GOTO_ROWNUM_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_GOTO_LINENUM_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_GOTO_DATA_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_FILE_LOAD_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_FILE_OPEN_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_DB_EXPORT_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_DB_IMPORT_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_FILE_WRITE_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)
INPUT_FIND_PROMPT_SGR = (
    Fore.white + Ground.hex("242623"),
    SGRParams(),
    SGRParams()
)

MANUAL_KEY_SGR = Fore.cyan + BOLD
FOUND_SGR = Ground.yellow + BOLD

# EDITOR BUFFER BASE PARAMETERS

TAB_SIZE: int = 8
TAB_TO_BLANK: bool = False
JUMP_POINTS_RE: Pattern | None = None
BACK_JUMP_RE: Pattern | None = None

# EDITOR BUFFER SWAP PARAMETERS

SWAP_DB_PATH: Literal[':memory:'] | str = 'SWAP.db'
SWAP_DB_UNLINK_ATEXIT: bool = True

# EDITOR BUFFER LOCAL_HISTORY PARAMETERS

LOCAL_HISTORY_MAXITEMS: int = 20
LOCAL_HISTORY_CHUNK_SIZE: int = 10
LOCAL_HISTORY_MAXITEMS_ACTION: Callable[[], ...] = lambda: None
LOCAL_HISTORY_UNDO_LOCK: bool = False
LOCAL_HISTORY_BRANCH_FORKS: bool = True
LOCAL_HISTORY_DB_PATH: Literal[':memory:', ':swap:'] | str = 'LOCALHISTORY.db'
LOCAL_HISTORY_DB_UNLINK_ATEXIT: bool = True

# EDITOR BUFFER MARKER PARAMETERS

MARKER_MULTI_MARKS: bool = True
MARKER_BACKJUMP_MARKS: bool = True

# EDITOR BUFFER DISPLAY PARAMETERS

DISPLAY_TYPE: Literal['scrollable', 's', 'browsable', 'b'] = 'browsable'
HIGHLIGHTER_TYPE: Literal['regex', 'advanced'] | None = 'advanced'
STDCURPOS: int | Literal['follow', 'parallel', 'end'] = 0
VISENDPOS: Literal['data', 'data f', 'visN1'] = 'data'
HIGHLIGHTER_FACTORY: Callable[[HighlighterBase], Any] = python_darkula

# EDITOR BUFFER VISUALISATION PARAMETERS

VIS_OVERFLOW: tuple[str, str, str] = (
    SGRWrap('<', INVERT),
    SGRWrap('>', INVERT),
    SGRWrap('<<', INVERT)
)
VIS_TAB: tuple[str, str] = (
    SGRWrap('→', Fore.hex('FF761F')),
    SGRWrap('·', Fore.hex('C2AB00'))
)
VIS_MARK: tuple[Callable[[str], EscSegment | EscContainer], Callable[[str], EscSegment | EscContainer]] = (
    lambda c: SGRWrap(c, Ground.hex('11ACAE') + Fore.black, cellular=True),
    lambda c: SGRWrap(c, Ground.hex('66B8B1') + Fore.black, cellular=True)
)
VIS_END: Sequence[str | None, str | None, str | None] | None = (
    SGRWrap('↵', Fore.name("orange2")),
    SGRWrap('↵', Ground.hex('11ACAE') + Fore.name("orange")),
    SGRWrap('↵', Ground.hex('66B8B1') + Fore.name("orange"))
)
VIS_NB_END: Sequence[str | None, str | None, str | None] | None = (
    SGRWrap('↵', Fore.name("gray")),
    SGRWrap('↵', Ground.hex('11ACAE') + Fore.name("gray")),
    SGRWrap('↵', Ground.hex('66B8B1') + Fore.name("gray"))
)
VIS_ANCHOR: Callable[[str], EscSegment | EscContainer] = \
    lambda c: SGRWrap(c, Ground.hex('FFF800'), inner=True)

VIS_CURSOR_ROW: Callable[[str], EscSegment | EscContainer] = \
    lambda vr: SGRWrap(vr, Ground.name('gray10'), cellular=True) + SGRSeqs(Ground.name('gray10'))

VIS_CURSOR_INSERT: tuple[Callable[[], Any], Callable[[str], EscSegment | EscContainer]] = (
    (lambda: out(CursorStyle.blinking_underline())),
    (lambda c: SGRWrap(c, INVERT, inner=True, cellular=True))
)
VIS_CURSOR_LINEINSERT: tuple[Callable[[], Any], Callable[[str], EscSegment | EscContainer]] = (
    (lambda: out(CursorStyle.blinking_bar())),
    (lambda c: SGRWrap(c, Ground.name('red4'), inner=True, cellular=True))
)
VIS_CURSOR_LINEASSINSERT: tuple[Callable[[], Any], Callable[[str], EscSegment | EscContainer]] = (
    (lambda: out(CursorStyle.blinking_bar())),
    (lambda c: SGRWrap(c, Ground.name('red1'), inner=True, cellular=True))
)
VIS_CURSOR_NORMAL: tuple[Callable[[], Any], Callable[[str], EscSegment | EscContainer]] = (
    (lambda: out(CursorStyle.default())),
    (lambda c: c)
)
ENUM_BORDER_SGR: tuple[SGRParams, SGRParams] = (
        Fore.black + Ground.hex("73C48F"),
        Fore.black + Ground.hex("73C48F")
)
ENUM_ANCHOR_SGR: tuple[SGRParams, SGRParams] = (
        Fore.black + Ground.hex('D9A343'),
        Fore.black + Ground.hex('D9A343')
)


_error: Literal["e"] = "e"
_warning: Literal["w"] = "w"
_info: Literal["i"] = "i"
_debug: Literal["d"] = "d"


class _Manual:
    geo_watcher: GeoWatcher
    __buffer__: TextBuffer
    __display__: DisplayBrowsable | DisplayScrollable
    __inputmodem__: InputSuperModem

    info: _Head

    def __init__(self, geo_watcher: GeoWatcher):

        self.geo_watcher = geo_watcher

        self.__buffer__ = TextBuffer(
            top_row_vis_maxsize=None,
            future_row_vis_maxsize=None,
            tab_size=4,
            tab_to_blank=False,
            autowrap_points=True,
            jump_points_re=None,
            back_jump_re=None
        )

        self.__display__ = DisplayScrollable(
            __buffer__=self.__buffer__,
            width=self.geo_watcher.size[0],
            height=self.geo_watcher.size[1] - 4,
            y_auto_scroll_distance=3,
            prompt_factory=lambda *_: (EscSegment(""), EscSegment("")),
            promptl_len=0,
            promptr_len=0,
            lapping=0,
            vis_overflow=("", "", ""),
            width_min_char=EscSegment(" "),
            highlighter="regex",
            highlighted_rows_cache_max=None,
            highlighted_row_segments_max=None,
            vis_tab=None,
            vis_marked=None,
            vis_end=None,
            vis_nb_end=None,
            visendpos="data",
            vis_cursor=None,
            vis_anchor=None,
            vis_cursor_row=None,
            stdcurpos="parallel",
            i_rowitem_generator=None,
            i_display_generator=None,
            i_before_framing=None,
        )

        self.__display__.__highlighter__.globals.add(compile("^\\S+(?=\\s )"), MANUAL_KEY_SGR)
        self.__display__.__highlighter__.globals.add(compile("GNU-NANO"), Ground.black + Fore.hex("9200FF") + BOLD)
        self.__display__.__highlighter__.globals.add(compile("VT-Python"), Ground.hex("2D7078") + Fore.hex("5ADC3C") + BOLD)
        self.__display__.__highlighter__.globals.add(compile("^__.+__"), Ground.hex("2D7078") + Fore.hex("5ADC3C"))
        self.__display__.__highlighter__.globals.add(compile("^.+:"), Fore.hex("C9C90B") + UNDERLINE)

        self.__inputmodem__ = InputSuperModem(thread_spam=SpamHandleOne(),
                                              manual_esc_tt=0,
                                              use_alter_bindings=True,
                                              find_all_bindings=True)

        with open(ROOT + "/_demo/_editor_man.txt", encoding="utf8") as f:
            self.__buffer__.write(f.read(), move_cursor=False)

    def move_cursor(self, nk: NavKey):
        if nk in BasicKeyComp.NavKeys.arrow_lr:
            return self.__buffer__.cursor_move(z_column=int(nk), cross=False) is not None
        elif nk in BasicKeyComp.NavKeys.arrow_ud:
            return self.__display__.scroll_y({2: 1, -2: -1}[int(nk)], False) is not None

    def resize(self):
        self.__display__.settings(width=self.geo_watcher.size[0], height=self.geo_watcher.size[1] - 4)

    def img(self):
        return self.__display__.make_display()


class _Body:
    geo_watcher: GeoWatcher
    __buffer__: TextBuffer
    __display__: DisplayBrowsable | DisplayScrollable
    __inputmodem__: InputSuperModem

    info: _Head

    _get_prompt: Callable[
        [_Row, Literal[0, 1, 2, 3, 4]], Sequence[EscSegment | EscContainer, EscSegment | EscContainer]]
    _i_rowitem: Callable[[VisRowItem], None]

    mode_insert: bool
    mode_lineinsert: bool
    mode_enum: bool
    mode_move_cursor: bool

    def __init__(
            self,
            geo_watcher: GeoWatcher,
            # buffer base parameter
            tab_size: int,
            tab_to_blank: bool,
            jump_points_re: Pattern | None,
            back_jump_re: Pattern | None,
            # buffer swap parameter
            swap_db_path: Literal[':memory:'] | str,
            swap_db_unlink_atexit: bool,
            # buffer local history parameter
            local_history_maxitems: int,
            local_history_chunk_size: int,
            local_history_maxitems_action: Callable[[], ...],
            local_history_undo_lock: bool,
            local_history_branch_forks: bool,
            local_history_db_path: Literal[':memory:', ':swap:'] | str,
            local_history_db_unlink_atexit: bool,
            # buffer marker parameter
            marker_multi_marks: bool,
            marker_backjump_marks: bool,
            # display parameter
            display_type: Literal['scrollable', 's', 'browsable', 'b'],
            highlighter: Literal['regex', 'advanced'] | None,
            stdcursor: int | Literal['follow', 'parallel', 'end'],
            visendpos: Literal['data', 'data f', 'visN1'],
            highlighter_factory: Callable[[HighlighterBase], Any]
    ):

        self.geo_watcher = geo_watcher

        self.__buffer__ = TextBuffer(
            top_row_vis_maxsize=None,
            future_row_vis_maxsize=None,
            tab_size=tab_size,
            tab_to_blank=tab_to_blank,
            autowrap_points=True,
            jump_points_re=jump_points_re,
            back_jump_re=back_jump_re
        )
        self.__buffer__.init_localhistory(
            maximal_items=local_history_maxitems,
            items_chunk_size=local_history_chunk_size,
            maximal_items_action=local_history_maxitems_action,
            undo_lock=local_history_undo_lock,
            branch_forks=local_history_branch_forks,
            db_path=local_history_db_path,
            unlink_atexit=local_history_db_unlink_atexit
        )
        self.__buffer__.init_rowmax__swap(
            rows_maximal=300,
            chunk_size=80,
            load_distance=80,
            keep_top_row_size=False,
            db_path=swap_db_path,
            unlink_atexit=swap_db_unlink_atexit
        )
        self.__buffer__.init_marker(
            multy_marks=marker_multi_marks,
            backjump_mode=marker_backjump_marks
        )

        __buffer__: TextBuffer = \
            self.__buffer__
        width: int = \
            self.geo_watcher.size[0]
        height: int = \
            self.geo_watcher.size[1] - 4  # header=1, info=1, footer=2
        y_auto_scroll_distance: int = \
            3
        prompt_factory: Callable[[_Row, Literal[0, 1, 2, 3, 4]], Sequence[EscSegment | EscContainer, EscSegment | EscContainer]] = \
            lambda *args: self._get_prompt(*args)
        promptl_len: int = \
            0
        promptr_len: int = \
            0
        lapping: int = \
            3
        vis_overflow: Sequence[str, str, str] = \
            VIS_OVERFLOW
        highlighter: Literal["regex", "r", "advanced", "a"] | None = \
            highlighter
        highlighted_rows_cache_max: int | None = \
            1000
        highlighted_row_segments_max: int | None = \
            None
        vis_tab: Callable[[int], str] | None = \
            lambda n: (VIS_TAB[0] * bool(n) + VIS_TAB[1] * (n - 1) if n else '')
        vis_marked: Sequence[Callable[[str, VisRowItem, list[int, int]], str], Callable[[str, VisRowItem, list[int, int]], str]] | None = \
            (lambda c, itm, coord: VIS_MARK[0](c), lambda c, itm, coord: VIS_MARK[1](c))
        vis_end: Sequence[str | None, str | None, str | None] | None = \
            VIS_END
        vis_nb_end: Sequence[str | None, str | None, str | None] | None = \
            VIS_NB_END
        visendpos: Literal["data", "d", "data f", "df", "visN1", "v", "v1"] = visendpos
        vis_cursor: Callable[[str, VisRowItem], str] | None = self._cursor_visual
        vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str] | None = lambda c, itm, _: VIS_ANCHOR(c)
        vis_cursor_row: Callable[[str, VisRowItem], str] | None = lambda vr, itm: VIS_CURSOR_ROW(vr)
        stdcurpos: int | Literal["follow", "f", "parallel", "p", "end", "e"] = stdcursor
        i_rowitem_generator: Callable[[VisRowItem], Any] | None = lambda *args: self._i_rowitem(*args)
        i_display_generator: Callable[[DisplayRowItem], Any] | None = None
        i_before_framing: Callable[[str, VisRowItem], str] | None = None
        
        if display_type[0] == 's':
            self.__display__ = DisplayScrollable(
                __buffer__=__buffer__, width=width, height=height, y_auto_scroll_distance=y_auto_scroll_distance,
                prompt_factory=prompt_factory, promptl_len=promptl_len, promptr_len=promptr_len, lapping=lapping,
                vis_overflow=vis_overflow, width_min_char=EscSegment(" "), highlighter=highlighter,
                highlighted_rows_cache_max=highlighted_rows_cache_max, 
                highlighted_row_segments_max=highlighted_row_segments_max,
                vis_tab=vis_tab, vis_marked=vis_marked, vis_end=vis_end, vis_nb_end=vis_nb_end, visendpos=visendpos,
                vis_cursor=vis_cursor, vis_anchor=vis_anchor, vis_cursor_row=vis_cursor_row, stdcurpos=stdcurpos,
                i_rowitem_generator=i_rowitem_generator, i_display_generator=i_display_generator, 
                i_before_framing=i_before_framing,
            )
        else:
            self.__display__ = DisplayBrowsable(
                __buffer__=__buffer__, width=width, height=height, y_auto_scroll_distance=y_auto_scroll_distance,
                prompt_factory=prompt_factory, promptl_len=promptl_len, promptr_len=promptr_len, lapping=lapping,
                vis_overflow=vis_overflow, width_min_char=EscSegment(" "), highlighter=highlighter,
                highlighted_rows_cache_max=highlighted_rows_cache_max, 
                highlighted_row_segments_max=highlighted_row_segments_max,
                vis_tab=vis_tab, vis_marked=vis_marked, vis_end=vis_end, vis_nb_end=vis_nb_end, visendpos=visendpos,
                vis_cursor=vis_cursor, vis_anchor=vis_anchor, vis_cursor_row=vis_cursor_row, stdcurpos=stdcurpos,
                i_rowitem_generator=i_rowitem_generator, i_display_generator=i_display_generator, 
                i_before_framing=i_before_framing,
            )

        highlighter_factory(self.__display__.__highlighter__)

        self.mode_move_cursor = True
        self.mode_insert = False
        self.mode_lineinsert = False
        self.mode_enum = True
        self.enum()

        self.__inputmodem__ = InputSuperModem(thread_spam=SpamHandleOne(), 
                                              manual_esc_tt=0, 
                                              use_alter_bindings=True,
                                              find_all_bindings=True)
        self.__inputmodem__.__interpreter__.SPACE_TARGETS.set(*self.__inputmodem__.__interpreter__.SPACE_TARGETS.ANY)

    def _cursor_visual(self, c: str, _=None):
        if self.mode_lineinsert:
            if self.mode_insert:
                VIS_CURSOR_LINEASSINSERT[0]()
                c = VIS_CURSOR_LINEASSINSERT[1](c)
            else:
                VIS_CURSOR_LINEINSERT[0]()
                c = VIS_CURSOR_LINEINSERT[1](c)
        elif self.mode_insert:
            VIS_CURSOR_INSERT[0]()
            c = VIS_CURSOR_INSERT[1](c)
        else:
            VIS_CURSOR_NORMAL[0]()
            c = VIS_CURSOR_NORMAL[1](c)
        return c

    def enum(self):
        def _vis_anchor(rowitm: VisRowItem):
            if (_l := len(rowitm.v_anchors)) > 1:
                rowitm.row_frame.lr_prompt[1] = (
                        SGRWrap('|   ', ENUM_BORDER_SGR[1]) + 
                        SGRWrap('+', ENUM_ANCHOR_SGR[1]))
            elif _l == 1:
                rowitm.row_frame.lr_prompt[1] = (
                        SGRWrap('|   ', ENUM_BORDER_SGR[1]) + 
                        SGRWrap(str(rowitm.v_anchors[0][0][0]), ENUM_ANCHOR_SGR[0]))
            else:
                pass

        def _none_vis_anchor(*_):
            pass

        def _get_none_prompt(*args):
            return EscSegment(''), EscSegment('')

        def _get_num_prompt(row: _Row, disp_part: Literal[0, 1, 2, 3, 4]):

            nonlocal plen
            if (_plen := len(str(self.__buffer__.__eof_line_num__))) != plen:
                plen = _plen
                self.__display__.settings(promptl_len=plen + 2, promptr_len=5)
            prompt_l = SGRWrap(('%%-%dd|' % plen) % row.__row_num__, ENUM_BORDER_SGR[0]) + ' '
            if row.inrow():
                curn = str(row.cursors.content)
                if len(curn) >= 4:
                    prompt_r = SGRWrap('|999+', ENUM_BORDER_SGR[1])
                else:
                    prompt_r = SGRWrap('|%-4s' % curn, ENUM_BORDER_SGR[1])
            else:
                prompt_r = SGRWrap('|    ', ENUM_BORDER_SGR[1])
            return [prompt_l, prompt_r]

        if self.mode_enum:
            self._get_prompt = _get_none_prompt
            self._i_rowitem = _none_vis_anchor
            self.__display__.settings(promptl_len=0, promptr_len=0)
            self.mode_enum = False
        else:
            self._get_prompt = _get_num_prompt
            self._i_rowitem = _vis_anchor
            self.__display__.settings(
                promptl_len=(plen := len(str(self.__buffer__.__eof_line_num__))) + 2,
                promptr_len=5)
            self.mode_enum = True

        return True

    def resize(self):
        self.__display__.settings(width=self.geo_watcher.size[0], height=self.geo_watcher.size[1] - 4)

    def img(self):
        return self.__display__.make_display()


class _Input:
    __buffer__: TextBuffer
    __display__: DisplayScrollable
    __inputmodem__: InputSuperModem
    geo_watcher: GeoWatcher

    _prompt: tuple[EscSegment, EscSegment]
    cache: list[str]
    cache_cur: int
    action: Callable

    def __init__(self, geo_watcher: GeoWatcher, prompt: EscSegment | EscContainer, eol: EscSegment = SGRSeqs(StyleResets.purge_sgr)):
        self._prompt = (prompt, eol)

        self.geo_watcher = geo_watcher

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
            width=self.geo_watcher.size[0],
            lapping=int((self.geo_watcher.size[0] - (len(prompt) + len(eol))) * .8),
            vis_overflow=VIS_OVERFLOW,
            width_min_char=EscSegment(" "),
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
            highlighted_row_segments_max=None
        )
        self.__inputmodem__ = InputSuperModem(thread_spam=SpamHandleOne(), manual_esc_tt=0, use_alter_bindings=True)

        self.cache = list()
        self.cache_cur = 0

        self.action = lambda: None

    def bind(self, func: Callable):
        self.action = func

    def move_cursor(self, nk: NavKey):
        if nk in BasicKeyComp.NavKeys.arrow_lr:
            return self.__buffer__.cursor_move(
                z_column=int(nk),
                jump=NavKey.M.CTRL in nk.MOD)
        elif nk in BasicKeyComp.NavKeys.border:
            return self.__buffer__.cursor_move(
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
                    return True
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
                return True

    def resize(self):
        self.__display__.settings(
            width=self.geo_watcher.size[0], height=1,
            lapping=int(
                (self.geo_watcher.size[0] - ((_ll := len(self._prompt[0])) + (_lr := len(self._prompt[1])))) * .8),
            promptl_len=_ll, promptr_len=_lr
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


class _Head:
    geo_watcher: GeoWatcher
    text: str
    _text: str
    star: str
    sgr: SGRParams

    def __init__(self, geo_watcher: GeoWatcher, sgr: SGRParams):
        self.geo_watcher = geo_watcher
        self.text = self._text = str()
        self.star = "  "
        self.sgr = sgr

    def settitle(self, head: str):
        self._text = head
        if (lt := len(head)) > (width := self.geo_watcher.size[0] - 2):
            space = width - 3
            _l = space // 2
            _r = (space - _l) - 2
            self.text = head[:_l] + ' … ' + head[-_r:]
        else:
            space = self.geo_watcher.size[0] - lt
            _l = space // 2
            _r = (space - _l) - 2
            self.text = (" " * _l) + head + (" " * _r)

    def setstar(self, star: str):
        self.star = " " + star

    def img(self):
        return SGRSeqs(self.sgr) + self.text + self.star + "\x1b[m"

    def resize(self):
        self.settitle(self._text)


class _Info(_Head):
    timestamp: float
    msg: bool

    def __init__(self, geo_watcher: GeoWatcher, sgr: SGRParams):
        _Head.__init__(self, geo_watcher, sgr)
        self.timestamp = time()
        self.msg = False

    def setmsg(self, msg, level: Literal["error", "e", "warn", "w", "info", "i", "debug", "d"]):
        self.timestamp = time()
        self.msg = True
        self.settitle(SGRWrap(msg, {
            "e": MSG_ERROR_SGR,
            "w": MSG_WARN_SGR,
            "i": MSG_INFO_SGR,
            "d": MSG_DEBUG_SGR
        }[level[0]]))

    def img(self):
        return self.text

    def poll_time(self):
        if self.msg and time() - self.timestamp > 32:
            self.settitle("")
            self.msg = False


class _Footer:
    geo_watcher: GeoWatcher
    footer: tuple[str, str]
    _footer: tuple[str, str]
    _footers: dict[Any, tuple[str, str]]

    def __init__(self, geo_watcher: GeoWatcher):
        self.geo_watcher = geo_watcher

        def key_desc(key, sep, desc):
            return (SGRWrap(desc, FOOTER_DESCRIPTION_SGR) +
                    SGRWrap(sep, FOOTER_SGR) +
                    SGRWrap(key, FOOTER_KEY_SGR) +
                    SGRSeqs(FOOTER_SGR))

        self._footers = {
            0: (
                SGRSeqs(FOOTER_SGR)
                + key_desc("^_", ": ", "|manual")
                + key_desc("^T", ": ", "|open testfile")
                + key_desc("M-l", ": ", "|line-insert")
                + key_desc("M-l;<ins>", ": ", "|associative line-insert")
                + key_desc("^<backspace>", ": ", "|remove marked")
                + key_desc("M-u", ": ", "|undo")
                + key_desc("M-r", ": ", "|redo")
                + key_desc("M-H", ": ", "|history branch")
                + key_desc("M-[sS]", ": ", "|shift marked")
                + key_desc("M-[tT]", ": ", "|replace marked tabs")
                + key_desc("^C", ": ", "|cat")
                ,
                SGRSeqs(FOOTER_SGR)
                + key_desc("^Q", ": ", "|quit")
                + key_desc("^O", ": ", "|open file")
                + key_desc("^W", ": ", "|write file")
                + key_desc("^G", ": ", "|goto row")
                + key_desc("^D", ": ", "|goto data")
                + key_desc("^S", ": ", "|load file")
                + key_desc("^B", ": ", "|export")
                + key_desc("^U", ": ", "|import")
                + key_desc("M-[0-9]", ": ", "|set anchor")
                + key_desc("^A", ": ", "|goto anchor")
                + key_desc("^F", ": ", "|find pattern")
                + key_desc("M-f", ": ", "|find next")
                + key_desc("M-w", ": ", "|where was")
                + key_desc("M-c", ": ", "|cursor movement")
            ),
            1: (
                SGRSeqs(FOOTER_SGR)
                + key_desc("◂▸▴▾", ": ", "|scrolling")
                ,
                SGRSeqs(FOOTER_SGR)
                + key_desc("<ESC>", ": ", "|back")
                + key_desc("^Q", ": ", "|quit program")
            ),
            2: (
                SGRSeqs(FOOTER_SGR)
                + key_desc("<enter>", ": ", "|execute")
                + key_desc("^<backspace>", ": ", "|clear buffer")
                ,
                SGRSeqs(FOOTER_SGR)
                + key_desc("<ESC>", ": ", "|cancel")
                + key_desc("▴▾", ": ", "|history")
            )
        }
        self.switch_footer(0)

    def resize(self):
        self.footer = (
            (self._footer[0][:self.geo_watcher.width - 1] + SGRSeqs(FOOTER_SGR) + '…'
             if len(self._footer[0]) > self.geo_watcher.width
             else (EscSegment("%%-%ds" % self.geo_watcher.width) % self._footer[0])),
            (self._footer[1][:self.geo_watcher.width - 1] + SGRSeqs(FOOTER_SGR) + '…'
             if len(self._footer[1]) > self.geo_watcher.width
             else (EscSegment("%%-%ds" % self.geo_watcher.width) % self._footer[1]))
        )

    def switch_footer(self, key):
        self._footer = self._footers[key]
        self.resize()

    def img(self):
        return self.footer


class _LoadAnimation(Thread):
    val: bool
    ani: tuple[str, ...]

    def __init__(self):
        Thread.__init__(self, daemon=True)
        self.val = False
        self.start()
        self.ani = tuple(SGRWrap(s, LOAD_ANIMATION_SGR) for s in ('[·    ]',
                                                                  '[··   ]',
                                                                  '[···  ]',
                                                                  '[ ··· ]',
                                                                  '[  ···]',
                                                                  '[   ··]',
                                                                  '[    ·]'))

    def run(self) -> None:
        while True:
            sleep(1)
            if self.val:
                _cursor_show.lowout()
                _cursor_show.highout()
                _cursor_show.lowout()
                while True:
                    if not self.val:
                        break
                    for i in self.ani:
                        if not self.val:
                            break
                        out(CursorNavigate.line_absolute(), CursorNavigate.column(), i, flush=True)
                        sleep(.2)
                    for i in reversed(self.ani):
                        if not self.val:
                            break
                        out(CursorNavigate.line_absolute(), CursorNavigate.column(), i, flush=True)
                        sleep(.2)

    def enable(self):
        self.val = True

    def disable(self):
        self.val = False


class Editor:
    __inputrouter__: InputRouter

    head: _Head
    body: _Body
    info: _Info
    footer: _Footer
    manual: _Manual

    input_goto_rownum: _Input
    input_goto_data: _Input
    input_goto_linenum: _Input
    input_file_load: _Input
    input_file_open: _Input
    input_db_export: _Input
    input_db_import: _Input
    input_file_write: _Input
    input_goto_anchor: _Input
    input_find: _Input

    current_infoline: _Input | _Info
    inputfocus: bool
    manualfocus: bool

    cur_find_pattern: str

    geo_watcher: GeoWatcher

    load_animation: _LoadAnimation

    def __init__(
            self,
            # buffer base parameter
            tab_size: int,
            tab_to_blank: bool,
            jump_points_re: Pattern | None,
            back_jump_re: Pattern | None,
            # buffer swap parameter
            swap_db_path: Literal[':memory:'] | str,
            swap_db_unlink_atexit: bool,
            # buffer local history parameter
            local_history_maxitems: int,
            local_history_chunk_size: int,
            local_history_maxitems_action: Callable[[], ...],
            local_history_undo_lock: bool,
            local_history_branch_forks: bool,
            local_history_db_path: Literal[':memory:', ':swap:'] | str,
            local_history_db_unlink_atexit: bool,
            # buffer marker parameter
            marker_multi_marks: bool,
            marker_backjump_marks: bool,
            # display parameter
            display_type: Literal['scrollable', 's', 'browsable', 'b'],
            highlighter_type: Literal['regex', 'advanced'] | None,
            stdcursor: int | Literal['follow', 'parallel', 'end'],
            visendpos: Literal['data', 'data f', 'visN1'],
            highlighter_factory: Callable[[HighlighterBase], Any],
    ):
        self.geo_watcher = GeoWatcher()
        self.geo_watcher.bind(self.resize)

        self.__inputrouter__ = InputRouter(thread_block=True)

        self.load_animation = _LoadAnimation()

        self.head = _Head(self.geo_watcher, HEAD_SGR)
        self.head.settitle("Welcome to the VT-Python Editor")

        self.current_infoline = self.info = _Info(self.geo_watcher, SGRParams())
        self.inputfocus = False
        self.info.setmsg("| <DEMO>  press ctrl+_ for basic help |", _debug)

        self.footer = _Footer(self.geo_watcher)

        self.manual = _Manual(self.geo_watcher)
        self.manualfocus = False

        self.body = _Body(
            geo_watcher=self.geo_watcher,
            tab_size=tab_size,
            tab_to_blank=tab_to_blank,
            jump_points_re=jump_points_re,
            back_jump_re=back_jump_re,
            swap_db_path=swap_db_path,
            swap_db_unlink_atexit=swap_db_unlink_atexit,
            local_history_maxitems=local_history_maxitems,
            local_history_chunk_size=local_history_chunk_size,
            local_history_maxitems_action=local_history_maxitems_action,
            local_history_undo_lock=local_history_undo_lock,
            local_history_branch_forks=local_history_branch_forks,
            local_history_db_path=local_history_db_path,
            local_history_db_unlink_atexit=local_history_db_unlink_atexit,
            marker_multi_marks=marker_multi_marks,
            marker_backjump_marks=marker_backjump_marks,
            display_type=display_type,
            highlighter=highlighter_type,
            stdcursor=stdcursor,
            visendpos=visendpos,
            highlighter_factory=highlighter_factory
        )

        self.__inputrouter__.add_table_entry(self.body, self.body.__inputmodem__)

        self.__inputrouter__.switch_gate(self.body)

        def bindingwrapper(func):

            def wrap(c, v):
                self.load_animation.enable(),
                if func(c, v):
                    self.head.setstar(self.get_history_star())
                    self.window_out()
                self.load_animation.disable()
                self.info.poll_time()

            return wrap

        self.body.__inputmodem__.__binder__.bind(
            NavKey,
            bindingwrapper(lambda k, _: self.move_cursor(k)))
        self.body.__inputmodem__.__binder__.bind(
            Char,
            bindingwrapper(lambda c, _: self.write(c)))
        self.body.__inputmodem__.__binder__.bind(
            Meta("\n"),
            bindingwrapper(lambda *_: self.body.__buffer__.write("\n", nbnl=True,
                                                                 sub_chars=self.body.mode_insert,
                                                                 move_cursor=self.body.mode_move_cursor,
                                                                 sub_line=self.body.mode_lineinsert)))
        self.body.__inputmodem__.__binder__.bind(
            DelIns(DelIns.K.BACKSPACE),
            bindingwrapper(lambda k, _: self.body.__buffer__.backspace()))
        self.body.__inputmodem__.__binder__.bind(
            DelIns(DelIns.K.DELETE, None),
            bindingwrapper(lambda k, _: self.delete(k)))

        self.body.__inputmodem__.__binder__.bind(
            DelIns(DelIns.K.BACKSPACE, DelIns.M.CTRL),
            bindingwrapper(lambda k, _: self.body.__buffer__.__marker__.marked_remove()))

        self.body.__inputmodem__.__binder__.bind(
            Meta("u"),
            bindingwrapper(lambda *_: self.undo()))
        self.body.__inputmodem__.__binder__.bind(
            Meta("r"),
            bindingwrapper(lambda *_: self.redo()))
        self.body.__inputmodem__.__binder__.bind(
            Meta("H"),
            bindingwrapper(lambda *_: self.body.__buffer__.__local_history__.branch_fork()))

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("N"),
            bindingwrapper(lambda *_: self.body.enum()))

        self.body.__inputmodem__.__binder__.bind(
            Meta("s"),
            bindingwrapper(lambda *_: self.body.__buffer__.__marker__.marked_shift()))
        self.body.__inputmodem__.__binder__.bind(
            Meta("S"),
            bindingwrapper(lambda *_: self.body.__buffer__.__marker__.marked_shift(backshift=True)))
        self.body.__inputmodem__.__binder__.bind(
            Meta("t"),
            bindingwrapper(lambda *_: self.body.__buffer__.__marker__.marked_tab_replace()))
        self.body.__inputmodem__.__binder__.bind(
            Meta("T"),
            bindingwrapper(lambda *_: self.body.__buffer__.__marker__.marked_tab_replace(to_chr="")))

        self.body.__inputmodem__.__binder__.bind(
            Meta("c"),
            bindingwrapper(lambda *_: (self.body.__setattr__('mode_move_cursor', self.body.mode_move_cursor ^ True),)))
        self.body.__inputmodem__.__binder__.bind(
            DelIns(DelIns.K.INSERT),
            bindingwrapper(lambda *_: (self.body.__setattr__('mode_insert', self.body.mode_insert ^ True),)))
        self.body.__inputmodem__.__binder__.bind(
            Meta("l"),
            bindingwrapper(lambda *_: (self.body.__setattr__('mode_lineinsert', self.body.mode_lineinsert ^ True),)))

        self.body.__inputmodem__.__binder__.bind(Meta('1'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('2'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('3'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('4'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('5'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('6'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('7'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('8'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('9'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))
        self.body.__inputmodem__.__binder__.bind(Meta('0'), bindingwrapper(lambda k, _: self.cursor_anchors(k.KEY)))

        self.input_goto_anchor = _Input(self.geo_watcher,
                                        SGRWrap('[ Select a anchor from 0 to 9 ]', INPUT_FILE_WRITE_PROMPT_SGR[0])
                                        + SGRWrap(" ", INPUT_FILE_WRITE_PROMPT_SGR[1])
                                        + SGRSeqs(INPUT_FILE_WRITE_PROMPT_SGR[2]))

        self.input_goto_rownum = _Input(self.geo_watcher,
                                        SGRWrap('Goto row:', INPUT_GOTO_ROWNUM_PROMPT_SGR[0])
                                        + SGRWrap(" ", INPUT_GOTO_ROWNUM_PROMPT_SGR[1])
                                        + SGRSeqs(INPUT_GOTO_ROWNUM_PROMPT_SGR[2]))
        self.input_goto_rownum.action = self.goto_row

        self.input_goto_linenum = _Input(self.geo_watcher,
                                         SGRWrap('Goto line:', INPUT_GOTO_LINENUM_PROMPT_SGR[0])
                                         + SGRWrap(" ", INPUT_GOTO_LINENUM_PROMPT_SGR[1])
                                         + SGRSeqs(INPUT_GOTO_LINENUM_PROMPT_SGR[2]))
        self.input_goto_linenum.action = self.goto_line

        self.input_goto_data = _Input(self.geo_watcher,
                                      SGRWrap('Goto data:', INPUT_GOTO_DATA_PROMPT_SGR[0])
                                      + SGRWrap(" ", INPUT_GOTO_DATA_PROMPT_SGR[1])
                                      + SGRSeqs(INPUT_GOTO_DATA_PROMPT_SGR[2]))
        self.input_goto_data.action = self.goto_data

        self.input_file_load = _Input(self.geo_watcher,
                                      SGRWrap('Load file:', INPUT_FILE_LOAD_PROMPT_SGR[0])
                                      + SGRWrap(" ", INPUT_FILE_LOAD_PROMPT_SGR[1])
                                      + SGRSeqs(INPUT_FILE_LOAD_PROMPT_SGR[2]))
        self.input_file_load.action = self.load_file

        self.input_file_open = _Input(self.geo_watcher,
                                      SGRWrap('Open file:', INPUT_FILE_OPEN_PROMPT_SGR[0])
                                      + SGRWrap(" ", INPUT_FILE_OPEN_PROMPT_SGR[1])
                                      + SGRSeqs(INPUT_FILE_OPEN_PROMPT_SGR[2]))
        self.input_file_open.action = self.open_file

        self.input_db_export = _Input(self.geo_watcher,
                                      SGRWrap('Export DB:', INPUT_DB_EXPORT_PROMPT_SGR[0])
                                      + SGRWrap(" ", INPUT_DB_EXPORT_PROMPT_SGR[1])
                                      + SGRSeqs(INPUT_DB_EXPORT_PROMPT_SGR[2]))
        self.input_db_export.action = self.db_export

        self.input_db_import = _Input(self.geo_watcher,
                                      SGRWrap('Import DB:', INPUT_DB_IMPORT_PROMPT_SGR[0])
                                      + SGRWrap(" ", INPUT_DB_IMPORT_PROMPT_SGR[1])
                                      + SGRSeqs(INPUT_DB_IMPORT_PROMPT_SGR[2]))
        self.input_db_import.action = self.db_import

        self.input_file_write = _Input(self.geo_watcher,
                                       SGRWrap('Write file:', INPUT_FILE_WRITE_PROMPT_SGR[0])
                                       + SGRWrap(" ", INPUT_FILE_WRITE_PROMPT_SGR[1])
                                       + SGRSeqs(INPUT_FILE_WRITE_PROMPT_SGR[2]))
        self.input_file_write.action = self.write_file

        self.input_find = _Input(self.geo_watcher,
                                 SGRWrap('Find Pattern []:', INPUT_FIND_PROMPT_SGR[0])
                                 + SGRWrap(" ", INPUT_FIND_PROMPT_SGR[1])
                                 + SGRSeqs(INPUT_FIND_PROMPT_SGR[2]))
        self.input_find.action = self.find

        self.__inputrouter__.add_table_entry(self.input_goto_rownum, self.input_goto_rownum.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_goto_linenum, self.input_goto_linenum.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_goto_data, self.input_goto_data.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_file_load, self.input_file_load.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_file_open, self.input_file_open.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_db_export, self.input_db_export.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_db_import, self.input_db_import.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_file_write, self.input_file_write.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_goto_anchor, self.input_goto_anchor.__inputmodem__)
        self.__inputrouter__.add_table_entry(self.input_find, self.input_find.__inputmodem__)

        def enter_input(inp_):
            self.current_infoline = inp_
            self.__inputrouter__.switch_gate(inp_)
            self.inputfocus = True
            self.footer.switch_footer(2)
            return True

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("G"),
            bindingwrapper(lambda *_: enter_input(self.input_goto_rownum)))
        self.body.__inputmodem__.__binder__.bind(
            Ctrl("L"),
            bindingwrapper(lambda *_: enter_input(self.input_goto_linenum)))
        self.body.__inputmodem__.__binder__.bind(
            Ctrl("D"),
            bindingwrapper(lambda *_: enter_input(self.input_goto_data)))
        self.body.__inputmodem__.__binder__.bind(
            Ctrl("S"),
            bindingwrapper(lambda *_: enter_input(self.input_file_load)))
        self.body.__inputmodem__.__binder__.bind(
            Ctrl("O"),
            bindingwrapper(lambda *_: enter_input(self.input_file_open)))
        self.body.__inputmodem__.__binder__.bind(
            Ctrl("B"),
            bindingwrapper(lambda *_: enter_input(self.input_db_export)))
        self.body.__inputmodem__.__binder__.bind(
            Ctrl("U"),
            bindingwrapper(lambda *_: enter_input(self.input_db_import)))
        self.body.__inputmodem__.__binder__.bind(
            Ctrl("W"),
            bindingwrapper(lambda *_: enter_input(self.input_file_write)))

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("F"),
            bindingwrapper(lambda *_: enter_input(self.input_find)))

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("A"),
            bindingwrapper(lambda *_: enter_input(self.input_goto_anchor)))

        def exit_input():
            self.current_infoline = self.info
            self.__inputrouter__.switch_gate(self.body)
            self.inputfocus = False
            self.footer.switch_footer(0)

        for inp in (self.input_goto_rownum, self.input_goto_data, self.input_goto_linenum, self.input_file_load,
                    self.input_file_open, self.input_db_export, self.input_db_import, self.input_file_write,
                    self.input_find):

            for bnd in (
                    (Char,
                     bindingwrapper(lambda c, _: self.current_infoline.__buffer__.write(c))),
                    (NavKey,
                     bindingwrapper(lambda k, _: self.current_infoline.move_cursor(k) is not None)),
                    (DelIns(DelIns.K.BACKSPACE),
                     bindingwrapper(lambda c, _: self.current_infoline.__buffer__.backspace())),
                    (DelIns(DelIns.K.DELETE),
                     bindingwrapper(lambda c, _: self.current_infoline.__buffer__.delete())),
                    (DelIns(DelIns.K.BACKSPACE, DelIns.M.CTRL),
                     bindingwrapper(lambda c, _: {self.current_infoline.__buffer__.reinitialize()})),
                    (DelIns(DelIns.K.DELETE, DelIns.M.CTRL),
                     bindingwrapper(lambda c, _: {self.current_infoline.__buffer__.reinitialize()})),
                    (Ctrl("enter"),
                     bindingwrapper(lambda c, _: (self.current_infoline.action(), exit_input()))),
                    (ManualESC,
                     bindingwrapper(lambda c, _: (self.current_infoline.pop(), exit_input()))),
            ):
                inp.__inputmodem__.__binder__.bind(*bnd)

        self.input_goto_anchor.__inputmodem__.__binder__.bind(Char, bindingwrapper(lambda c, _: (self.cursor_anchors(c, goto=True), exit_input())))
        self.input_goto_anchor.__inputmodem__.__binder__.bind(ManualESC, bindingwrapper(lambda c, _: (self.current_infoline.pop(), exit_input())))

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("C"),
            bindingwrapper(lambda *_: (self.info.setmsg(
                "[ eo-data:%d eo-content:%d eo-rows:%d eo-lines:%d ]" % self.body.__buffer__.__eof_metas__, _debug),)))

        self.__inputrouter__.add_table_entry(self.manual, self.manual.__inputmodem__)

        self.body.__inputmodem__.__binder__.bind(Meta("w"), bindingwrapper(lambda *_: self.find(prev=True)))
        self.body.__inputmodem__.__binder__.bind(Meta("f"), bindingwrapper(lambda *_: self.find(next_=True)))

        def manual_enter(*_):
            self.footer.switch_footer(1)
            self.manualfocus = True
            self.__inputrouter__.switch_gate(self.manual)
            self.head.setstar(self.get_history_star())
            self.info.poll_time()
            self.window_out()
            _cursor_show.lowout()
            _cursor_show.highout()
            _cursor_show.lowout()

        def manual_exit(*_):
            self.footer.switch_footer(0)
            self.manualfocus = False
            self.__inputrouter__.switch_gate(self.body)
            self.head.setstar(self.get_history_star())
            self.info.poll_time()
            self.window_out()
            _cursor_show.highout()
            _cursor_show.lowout()
            _cursor_show.highout()

        def manual_move_cursor(k, _):
            self.manual.move_cursor(k)
            self.head.setstar(self.get_history_star())
            self.info.poll_time()
            self.window_out()
            _cursor_show.lowout()
            _cursor_show.highout()
            _cursor_show.lowout()

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("_"),
            manual_enter)

        self.manual.__inputmodem__.__binder__.bind(
            Ctrl("_"),
            manual_exit)
        self.manual.__inputmodem__.__binder__.bind(
            ManualESC,
            manual_exit)

        self.manual.__inputmodem__.__binder__.bind(
            NavKey,
            manual_move_cursor)

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("Q"),
            lambda *_: exit(0))

        self.manual.__inputmodem__.__binder__.bind(
            Ctrl("Q"),
            lambda *_: exit(0))

        self.body.__inputmodem__.__binder__.bind(
            Ctrl("T"),
            bindingwrapper(lambda *_: (
                self.input_file_open.__buffer__.reinitialize(),
                self.input_file_open.__buffer__.write(ROOT + "/_demo/testdata/bricks.txt"),
                self.open_file())))

    def find(self, next_=False, prev=False, purge=False):
        try:
            match = None
            if next_:
                if self.cur_find_pattern:
                    if match := self.body.__buffer__.find(self.cur_find_pattern):
                        found_pos = match[0][0].__data_start__ + match[0][1].start()
                        self.body.__buffer__.goto_data(found_pos)
                    else:
                        self.info.setmsg("[ %r not found → ]" % self.cur_find_pattern, _warning)
                else:
                    self.info.setmsg("[ no pattern entered ]", _error)
            elif prev:
                if self.cur_find_pattern:
                    if match := self.body.__buffer__.find(self.cur_find_pattern, reverse=True):
                        found_pos = match[0][0].__data_start__ + match[0][1].start()
                        self.body.__buffer__.goto_data(found_pos)
                    else:
                        self.info.setmsg("[ %r not found ← ]" % self.cur_find_pattern, _warning)
                else:
                    self.info.setmsg("[ no pattern entered ]", _error)
            elif purge:
                self.cur_find_pattern = ""
                self.body.__display__.__highlighter__.globals.remove_by_label(label=1)
                self.body.__display__.__highlighter__.purge_cache()
                self.input_find._prompt = (SGRWrap('Find Pattern []:', INPUT_FIND_PROMPT_SGR[0])
                                           + SGRWrap(" ", INPUT_FIND_PROMPT_SGR[1])
                                           + SGRSeqs(INPUT_FIND_PROMPT_SGR[2]),
                                           EscSegment(""))
                self.input_find.resize()
                return
            else:
                self.cur_find_pattern = self.input_find.pop()
                if not self.cur_find_pattern:
                    self.input_find.cache.pop(-1)
                    return self.find(purge=True)
                self.body.__display__.__highlighter__.globals.add(self.cur_find_pattern, FOUND_SGR, label=1)
                self.body.__display__.__highlighter__.purge_cache()
                self.input_find._prompt = (SGRWrap('Find Pattern [%s]:' % self.cur_find_pattern, INPUT_FIND_PROMPT_SGR[0])
                                           + SGRWrap(" ", INPUT_FIND_PROMPT_SGR[1])
                                           + SGRSeqs(INPUT_FIND_PROMPT_SGR[2]),
                                           EscSegment(""))
                self.input_find.resize()
                if match := self.body.__buffer__.find(self.cur_find_pattern):
                    found_pos = match[0][0].__data_start__ + match[0][1].start()
                    self.body.__buffer__.goto_data(found_pos)
                else:
                    self.info.setmsg("[ %r not found → ]" % self.cur_find_pattern, _warning)

        except Exception as e:
            self.info.setmsg("[ %s ]" % e, _error)
        finally:
            return True

    def write_file(self):
        try:
            with open(file := self.input_file_write.pop(), "w") as f:
                f.write(self.body.__buffer__.reader().read())
            self.body.__buffer__.__local_history__.clamp_set()
        except Exception as e:
            self.info.setmsg("[ %s ]" % e, _error)
        else:
            self.info.setmsg("[ Written: %s ]" % file, _info)

    def db_export(self):
        try:
            self.body.__buffer__.export_bufferdb(db := self.input_db_export.pop())
        except DatabaseInitError as e:
            self.info.setmsg("[ %s ]" % e, _error)
        else:
            self.info.setmsg("[ Exported: %s ]" % db, _info)
        return True

    def db_import(self):
        try:
            if self.body.__buffer__.__local_history__.clamp_is_diff():
                pass  # todo
            self.body.__buffer__.import_bufferdb(db := self.input_db_import.pop(),
                                                 init=True,
                                                 errors=True,
                                                 critical=True)
        except DatabaseInitError as e:
            self.info.setmsg("[ %s ]" % e, _error)
        except CursorError as e:
            self.info.setmsg("[ FATAL: %s ]" % e, _error)
        except Exception as e:
            self.info.setmsg("[ %s ]" % e, _error)
        else:
            self.info.setmsg("[ Imported: %s ]" % db, _info)
        return True

    def goto_row(self):
        try:
            self.body.__buffer__.goto_row(int(self.input_goto_rownum.pop()), as_far=True)
        except ValueError as e:
            self.input_goto_rownum.cache.pop(-1)
            self.info.setmsg("[ %s ]" % e, _error)
        return True

    def goto_line(self):
        try:
            self.body.__buffer__.goto_line(int(self.input_goto_linenum.pop()), as_far=True)
        except ValueError as e:
            self.input_goto_linenum.cache.pop(-1)
            self.info.setmsg("[ %s ]" % e, _error)
        return True

    def goto_data(self):
        try:
            self.body.__buffer__.goto_data(int(self.input_goto_data.pop()))
        except ValueError as e:
            self.input_goto_data.cache.pop(-1)
            self.info.setmsg("[ %s ]" % e, _error)
        except CursorError as e:
            self.input_goto_data.cache.pop(-1)
            self.info.setmsg("[ %s ]" % e, _error)
        return True

    def load_file(self):
        try:
            with open(self.input_file_load.pop()) as f:
                while cont := f.read(50000):
                    self.body.__buffer__.write(cont)
        except Exception as e:
            self.info.setmsg("[ %s ]" % e, _error)
        return True

    def open_file(self):
        try:
            if self.body.__buffer__.__local_history__.clamp_is_diff():
                pass  # todo
            self.body.__buffer__.reinitialize()
            with open(file := self.input_file_open.pop()) as f:
                while cont := f.read(50000):
                    self.body.__buffer__.write(cont)
            self.body.__buffer__.goto_data(0)
            self.body.__buffer__.__local_history__.clamp_set()
            self.head.settitle(file)
        except Exception as e:
            self.info.setmsg("[ %s ]" % e, _error)
        return True

    def write(self, c: Char):
        return self.body.__buffer__.write(c,
                                          sub_chars=self.body.mode_insert,
                                          sub_line=self.body.mode_lineinsert,
                                          associate_lines=self.body.mode_insert and self.body.mode_lineinsert,
                                          move_cursor=self.body.mode_move_cursor)

    def cursor_anchors(self, k: str, goto=False):
        if goto:
            try:
                with self.body.__buffer__.__local_history__.suit('_ignore'):
                    self.body.__buffer__.__glob_cursor__.goto_anchor(k)
            except KeyError as e:
                self.info.setmsg(f"[ {k} not present ]", _warning)
        else:
            try:
                self.body.__buffer__.__glob_cursor__.add_anchor(k)
            except KeyError as e:
                self.info.setmsg(f"[ {k} present ]", _warning)
        return True

    def delete(self, k: DelIns):
        if k.M.SHIFT in k.MOD:
            return self.body.__buffer__.__marker__.pop_aimed_mark()
        else:
            return self.body.__buffer__.delete()

    def move_cursor(self, nk: NavKey):
        if nk in BasicKeyComp.NavKeys.arrow_lr:
            return self.body.__buffer__.cursor_move(
                z_column=int(nk),
                jump=NavKey.M.CTRL in nk.MOD,
                mark=NavKey.M.SHIFT in nk.MOD
            ) is not None
        elif nk in BasicKeyComp.NavKeys.border:
            if NavKey.M.CTRL in nk.MOD:
                return self.body.__display__.scroll_x({3: 1, -3: -1}[int(nk)], NavKey.M.SHIFT in nk.MOD
                                                      ) is not None
            else:
                return self.body.__buffer__.cursor_move(
                    z_column=int(nk),
                    border=True,
                    mark=NavKey.M.SHIFT in nk.MOD,
                    mark_jump=NavKey.M.ALT in nk.MOD
                ) is not None
        elif nk in BasicKeyComp.NavKeys.arrow_ud:
            if NavKey.M.CTRL in nk.MOD:
                return self.body.__display__.scroll_y({2: 1, -2: -1}[int(nk)], NavKey.M.SHIFT in nk.MOD
                                                      ) is not None
            else:
                return self.body.__buffer__.cursor_move(z_row={2: 1, -2: -1}[int(nk)], mark=NavKey.M.SHIFT in nk.MOD
                                                        ) is not None
        elif nk in BasicKeyComp.NavKeys.page_ud:
            if NavKey.M.CTRL in nk.MOD:
                return self.body.__display__.scroll_y(int(nk), NavKey.M.SHIFT in nk.MOD
                                                      ) is not None
            else:
                return self.body.__buffer__.cursor_move(z_row=int(nk), mark=NavKey.M.SHIFT in nk.MOD, as_far=True
                                                        ) is not None

    def undo(self):
        labels = {
            -8: "restrict removemend - ",
            -2: "removed range - ",
            -1: "removed - ",
            0: "cursor - ",
            1: "written - ",
            2: "rewritten - ",
            4: "marks - "
        }
        if items := self.body.__buffer__.__local_history__.undo():
            self.info.setmsg(
                ("UNDO: " + str().join(
                    labels.pop(i.type_, "") for i in items[0]
                ))[:-3],
                _info
            )
        else:
            self.info.setmsg("[ nothing to undo ]", _warning)
        return True

    def redo(self):
        labels = {
            -8: "restrict removemend - ",
            -2: "removed range - ",
            -1: "removed - ",
            0: "cursor - ",
            1: "written - ",
            2: "rewritten - ",
            4: "marks - "
        }
        if items := self.body.__buffer__.__local_history__.redo():
            self.info.setmsg(
                ("REDO: " + str().join(
                    labels.pop(i.type_, "") for i in items[0]
                ))[:-3],
                _info
            )
        else:
            self.info.setmsg("[ nothing to redo ]", _warning)
        return True

    def resize(self, size):
        self.geo_watcher.size = size
        self.body.resize()
        self.head.resize()
        self.footer.resize()
        self.info.resize()
        self.manual.resize()

        self.input_goto_rownum.resize()
        self.input_goto_data.resize()
        self.input_goto_linenum.resize()
        self.input_file_load.resize()
        self.input_file_open.resize()
        self.input_db_export.resize()
        self.input_db_import.resize()

        self.window_out()

    def get_history_star(self) -> str:
        star = " "
        if self.body.__buffer__.__local_history__.clamp_is_diff():
            if self.body.__buffer__.__local_history__.clamp_in_past():
                _star = HEAD_HISTORY_STAR_PAST
            else:
                _star = HEAD_HISTORY_STAR_FUTURE
            star = {
                0: SGRWrap(_star, HEAD_HISTORY_STAR_SGR_NOTREACHABLE),
                1: SGRWrap(_star, HEAD_HISTORY_STAR_SGR_REACHABLE_DO),
                2: SGRWrap(_star, HEAD_HISTORY_STAR_SGR_REACHABLE_FORK),
            }[self.body.__buffer__.__local_history__.clamp_is_reachable()]
        return star

    def window_out(self):

        title_img = self.head.img()
        if self.manualfocus:
            body_img = self.manual.img()
        else:
            body_img = self.body.img()
        info_img = self.current_infoline.img()

        _cursor_show.lowout()
        _cursor_show.highout()
        _cursor_show.lowout()

        out(CursorNavigate.line_absolute(), CursorNavigate.column(), flush=False)

        out(title_img, '\r\n', flush=False)

        out(*(str(ln) for ln in body_img.rows), sep='\r\n', flush=False)
        out(*(Erase.line() + '\n' for _ in range((self.geo_watcher.size[1] - 4) - len(body_img.rows))))

        if self.inputfocus:
            out(Erase.line(), str(info_img.rows[0]), '\r\n')
        else:
            out(Erase.line(), info_img, '\r\n')

        out(Erase.line(), self.footer.footer[0], '\r\n', Erase.line(), self.footer.footer[1])

        if self.inputfocus:
            out(
                CursorNavigate.line_absolute(self.geo_watcher.size[1] - 2),
                CursorNavigate.column(info_img.pointer_column + 1)
            )
        else:
            out(
                CursorNavigate.line_absolute(body_img.pointer_row + 2),
                CursorNavigate.column(body_img.pointer_column + 1)
            )

        flushio()

        _cursor_show.highout()
        _cursor_show.lowout()
        _cursor_show.highout()


def _init():
    global _cursor_show, notipl, altbuffer, editor
    try:
        notipl = mod_nonimpldef()
        mod_nonprocess()
        mod_ansiin()
        mod_ansiout()
        _cursor_show = CursorShow()
        CursorBlinking()
        atexit.register(lambda *_: CursorStyle.default().out())
        altbuffer = ScreenAlternateBuffer()
        altbuffer.highout()
        CursorAutowrapMode().lowout()
        BracketedPasteMode().highout()
        StdinAdapter()
        editor = Editor(
            tab_size=TAB_SIZE,
            tab_to_blank=TAB_TO_BLANK,
            jump_points_re=JUMP_POINTS_RE,
            back_jump_re=BACK_JUMP_RE,
            swap_db_path=SWAP_DB_PATH,
            swap_db_unlink_atexit=SWAP_DB_UNLINK_ATEXIT,
            local_history_maxitems=LOCAL_HISTORY_MAXITEMS,
            local_history_chunk_size=LOCAL_HISTORY_CHUNK_SIZE,
            local_history_maxitems_action=LOCAL_HISTORY_MAXITEMS_ACTION,
            local_history_undo_lock=LOCAL_HISTORY_UNDO_LOCK,
            local_history_branch_forks=LOCAL_HISTORY_BRANCH_FORKS,
            local_history_db_path=LOCAL_HISTORY_DB_PATH,
            local_history_db_unlink_atexit=LOCAL_HISTORY_DB_UNLINK_ATEXIT,
            marker_multi_marks=MARKER_MULTI_MARKS,
            marker_backjump_marks=MARKER_BACKJUMP_MARKS,
            display_type=DISPLAY_TYPE,
            highlighter_type=HIGHLIGHTER_TYPE,
            stdcursor=STDCURPOS,
            visendpos=VISENDPOS,
            highlighter_factory=HIGHLIGHTER_FACTORY
        )
        editor.window_out()
    except Exception:
        try:
            altbuffer.lowout()
        except:
            pass
        try:
            notipl.reset()
        except:
            pass
        raise


def _mainloop():
    try:
        editor.__inputrouter__.run()
    except Exception:
        try:
            altbuffer.lowout()
        except:
            pass
        try:
            notipl.reset()
        except:
            pass
        raise


def main_demo():
    _init()
    _mainloop()


def _demo_lorem():
    global HIGHLIGHTER_TYPE, STDCURPOS, HIGHLIGHTER_FACTORY, VIS_END, VIS_NB_END
    HIGHLIGHTER_TYPE = None
    STDCURPOS = 'parallel'
    HIGHLIGHTER_FACTORY = lambda *_: None
    VIS_END = (
        SGRWrap('¶', Fore.name("orange2")),
        SGRWrap('¶', Ground.hex('11ACAE') + Fore.name("orange")),
        SGRWrap('¶', Ground.hex('66B8B1') + Fore.name("orange"))
    )
    VIS_NB_END = (
        SGRWrap('¶', Fore.name("gray")),
        SGRWrap('¶', Ground.hex('11ACAE') + Fore.name("gray")),
        SGRWrap('¶', Ground.hex('66B8B1') + Fore.name("gray"))
    )
    _init()
    try:
        for seq, end in (
            ("Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore", 1),
            ("magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo", 1),
            ("consequat.", 0),
            ("Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.", 1),
            ("Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.", 0),
            ("", 0),
            ("\tLorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore", 1),
            ("\tet dolore magna aliqua.", 0),
            ("\tUt enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.", 0),
        ):
            for c in seq:
                editor.body.__buffer__.write(Char(c))
                editor.window_out()
                if c == "\t":
                    sleep(.18)
                sleep(.02)
            editor.body.__buffer__.write("\n", nbnl=end)
            editor.window_out()
            sleep(.2)
        sleep(.2)
        for key, timeout in (
                (NavKey(NavKey.K.A_UP, NavKey.M.SHIFT), .3),
                (NavKey(NavKey.K.A_UP, NavKey.M.SHIFT), .3),
                (NavKey(NavKey.K.A_UP, NavKey.M.SHIFT), .3),
                (Meta("s"), .3),
                (Meta("s"), .8),
                (Meta("S"), 1),
                (Meta("t"), 1.2),
                (DelIns(DelIns.K.DELETE, DelIns.M.SHIFT), 1.1),
                (Meta("u"), .3),
                (Meta("u"), .8),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
                (Meta("u"), .3),
        ):
            editor.__inputrouter__.current_modem.__binder__.send(key)
            sleep(timeout)
        _mainloop()
    except Exception:
        try:
            altbuffer.lowout()
        except:
            pass
        try:
            notipl.reset()
        except:
            pass
        raise


def _demo_insert():
    global HIGHLIGHTER_TYPE, STDCURPOS, HIGHLIGHTER_FACTORY, VIS_END, VIS_NB_END
    HIGHLIGHTER_TYPE = None
    HIGHLIGHTER_FACTORY = lambda *_: None
    _init()

    editor.window_out()
    sleep(2)
    try:
        editor.body.__buffer__.write(Char("""
=====================================================
 The reStructuredText_ Cheat Sheet: Syntax Reminders
=====================================================
.. module:: parrot
   :platform: Unix, Windows
   :synopsis: Analyze and reanimate dead parrots.
.. moduleauthor:: Eric Cleese <eric@python.invalid>
.. moduleauthor:: John Idle <john@python.invalid>

.. NOTE:: If you are reading this as HTML, please read
   `<cheatsheet.txt>`_ instead to see the input syntax examples!

Section Structure
=================
Section titles are underlined or overlined & underlined.

Body Elements
=============
Grid table:

+--------------------------------+-----------------------------------+
| Paragraphs are flush-left,     | Literal block, preceded by "::":: |
| separated by blank lines.      |                                   |
|                                |     Indented                      |
|     Block quotes are indented. |                                   |
+--------------------------------+ or::                              |
| >>> print 'Doctest block'      |                                   |
| Doctest block                  | > Quoted                          |
+--------------------------------+-----------------------------------+
| | Line blocks preserve line breaks & indents. [new in 0.3.6]       |
| |     Useful for addresses, verse, and adornment-free lists; long  |
|       lines can be wrapped with continuation lines.                |
+--------------------------------------------------------------------+

Simple tables:

================  ============================================================
List Type         Examples (syntax in the `text source <cheatsheet.txt>`_)
================  ============================================================
Bullet list       * items begin with "-", "+", or "*"
Enumerated list   1. items use any variation of "1.", "A)", and "(i)"
                  #. also auto-enumerated
Definition list   Term is flush-left : optional classifier
                      Definition is indented, no blank line between
Field list        :field name: field body
Option list       -o  at least 2 spaces between option & description
================  ============================================================
"""))

        editor.window_out()

        sleep(2)

        for key, timeout in (
                (Ctrl("G"), .3),
                (Char("0"), .3),
                (Ctrl("enter"), .3),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .09),
                (NavKey(NavKey.K.A_DOWN), .3),
                (NavKey(NavKey.K.A_DOWN), .3),
                (NavKey(NavKey.K.A_DOWN), .3),
                (NavKey(NavKey.K.A_DOWN), .3),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .09),
                (NavKey(NavKey.K.A_RIGHT), .2),
                (NavKey(NavKey.K.A_RIGHT), .2),
                (NavKey(NavKey.K.A_RIGHT), .2),
                (DelIns(DelIns.K.INSERT), .8),
                (Char("("), .18),
                (Char('"'), .18),
                (Char("p"), .18),
                (Char("y"), .18),
                (Char("3"), .18),
                (Char(" "), .18),
                (Char("D"), .18),
                (Char("o"), .18),
                (Char("c"), .18),
                (Char("T"), .18),
                (Char("e"), .18),
                (Char("s"), .18),
                (Char("t"), .18),
                (Char(" "), .18),
                (Char("B"), .18),
                (Char("l"), .18),
                (Char("o"), .18),
                (Char("c"), .18),
                (Char("k"), .18),
                (Char('"'), .18),
                (Char(")"), .18),
                (NavKey(NavKey.K.A_DOWN), .3),
                (NavKey(NavKey.K.A_LEFT, NavKey.M.CTRL), .3),
                (NavKey(NavKey.K.A_LEFT, NavKey.M.CTRL), .3),
                (NavKey(NavKey.K.A_LEFT, NavKey.M.CTRL), .3),
                (NavKey(NavKey.K.A_LEFT, NavKey.M.CTRL), .3),
                (Char("py3 DockTest Block"), .8),
                (DelIns(DelIns.K.INSERT), .4),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .12),
                (NavKey(NavKey.K.A_UP), .12),
                (NavKey(NavKey.K.A_UP), .16),
                (NavKey(NavKey.K.A_UP), .16),
                (NavKey(NavKey.K.C_HOME), .6),
                (Meta("l"), .6),
                (Char("\n"), .3),
                (Char("\n"), .3),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .09),
                (NavKey(NavKey.K.A_UP), .2),
                (NavKey(NavKey.K.A_UP), .2),
                (NavKey(NavKey.K.A_UP), .2),
                (NavKey(NavKey.K.A_UP), .2),
                (NavKey(NavKey.K.A_UP), .2),
                (NavKey(NavKey.K.A_UP), .2),
                (DelIns(DelIns.K.INSERT), 1.4),
                (Char(""":Info: See <http://docutils.sf.net/rst.html> for introductory docs.
:Author: David Goodger <goodger@python.org>
:Date: $Date: 2013-02-20 01:10:53 +0000 (Wed, 20 Feb 2013) $
:Revision: $Revision: 7612 $
:Description: This is a "docinfo block", or bibliographic field list"""), 1.3),
                (NavKey(NavKey.K.A_UP), .3),
                (NavKey(NavKey.K.A_UP), .3),
                (NavKey(NavKey.K.A_UP), .3),
                (NavKey(NavKey.K.A_UP), .3),
                (NavKey(NavKey.K.A_UP), .3),
                (NavKey(NavKey.K.C_HOME), .3),
                (DelIns(DelIns.K.INSERT), 1.4),
                (Meta("l"), 1.4),
                (DelIns(DelIns.K.INSERT), 1.4),
                (DelIns(DelIns.K.INSERT), 1.4),
        ):
            editor.__inputrouter__.current_modem.__binder__.send(key)
            sleep(timeout)
        _mainloop()
    except Exception:
        try:
            altbuffer.lowout()
        except:
            pass
        try:
            notipl.reset()
        except:
            pass
        raise


def _demo_mark():
    global HIGHLIGHTER_TYPE, STDCURPOS, HIGHLIGHTER_FACTORY, VIS_END, VIS_NB_END, VIS_CURSOR_ROW, VIS_MARK, MARKER_MULTI_MARKS
    HIGHLIGHTER_TYPE = None
    HIGHLIGHTER_FACTORY = lambda *_: None
    STDCURPOS = "parallel"
    # VIS_CURSOR_ROW = lambda vr: SGRWrap(vr, Ground.name('gray'), cellular=True) + SGRSeqs(Ground.name('gray'))
    VIS_CURSOR_ROW = lambda vr: SGRWrap(vr, Ground.name('blue'), cellular=True) + SGRSeqs(Ground.name('blue'))
    VIS_MARK = (
        lambda c: SGRWrap(c, Ground.hex('FFF84D') + Fore.black, cellular=True),
        lambda c: SGRWrap(c, Ground.hex('FFFA8C') + Fore.black, cellular=True)
    )
    # MARKER_MULTI_MARKS = False
    _init()

    editor.window_out()
    sleep(0)
    try:
        editor.body.__buffer__.write(Char(r"""Some type Fe (C1 set element) ANSI escape sequences (not an exhaustive list)

Code    C1      Abbr 	Name 				Effect
=======================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================
ESC N   0x8E    SS2 	Single Shift Two 		Select a single character from one of the alternative character sets. SS2 selects the G2 character set, and SS3 selects the G3 character set.[29] In a 7-bit environment, this is followed by one or more GL bytes (0x20–0x7F) specifying a character from that set.[28]: 9.4  In an 8-bit environment, these may instead be GR bytes (0xA0–0xFF).[28]: 8.4 
ESC O   0x8F    SS3 	Single Shift Three
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ESC P   0x90    DCS 	Device Control String 		Terminated by ST.[5]: 5.6  Xterm's uses of this sequence include defining User-Defined Keys, and requesting or setting Termcap/Terminfo data.[29]
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ESC [   0x9B    CSI 	Control Sequence Introducer 	Starts most of the useful sequences, terminated by a byte in the range 0x40 through 0x7E.[5]: 5.4 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ESC \   0x9C    ST 	String Terminator 		Terminates strings in other controls.[5]: 8.3.143 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ESC ]   0x9D    OSC 	Operating System Command 	Starts a control string for the operating system to use, terminated by ST.[5]: 8.3.89 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ESC X   0x98    SOS 	Start of String 		Takes an argument of a string of text, terminated by ST.[5]: 5.6  The uses for these string control sequences are defined by the application[5]: 8.3.2, 8.3.128  or privacy discipline.[5]: 8.3.94  These functions are rarely implemented and the arguments are ignored by xterm.[29] Some Kermit clients allow the server to automatically execute Kermit commands on the client by embedding them in APC sequences; this is a potential security risk if the server is untrusted.[30]
ESC ^   0x9E    PM 	Privacy Message
ESC _   0x9F    APC 	Application Program Command
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

: https://en.wikipedia.org/wiki/ANSI_escape_code#Fe_Escape_sequences
"""))
        editor.window_out()
        _mainloop()
    except Exception:
        try:
            altbuffer.lowout()
        except:
            pass
        try:
            notipl.reset()
        except:
            pass
        raise


if __name__ == "__main__":
    main_demo()
    #_demo_lorem()
    #_demo_insert()
    #_demo_mark()

