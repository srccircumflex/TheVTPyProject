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

# sys.stderr = open("stderrfile", "w")
# sys.stdout = open("stdoutfile", "w")

from re import sub
import atexit

try:
    ROOT = sub("[/\\\\]_demo[/\\\\][^/\\\\]+$", "", __file__)
    sys.path.append(ROOT)
finally:
    pass

from vtframework.video import Cell, FramePadding, GeoCalculator, Grid
from _demo._geowatcher import GeoWatcher
from vtframework.iodata import Mouse
from _demo._mouseproc import MouseProcessing
from _demo._highlighter_factory import python_darkula

from vtframework.iosys.vtermios import mod_ansiin, mod_ansiout

from vtframework.io.io import StdinAdapter, SpamHandleOne
from vtframework.io.modem import InputRouter, InputSuperModem

from vtframework.iodata.sgr import SGRWrap, Ground, Fore, INVERT
from vtframework.iodata.chars import Char
from vtframework.iodata.keys import NavKey, DelIns, Meta, FKey, Ctrl
from vtframework.iodata.cursor import CursorStyle
from vtframework.iodata.decpm import (
    BracketedPasteMode,
    CursorShow,
    CursorBlinking,
    MouseAllTracking,
    CursorAutowrapMode
)
from vtframework.iodata.eval import BasicKeyComp

from _demo._notepadwidget import SimpleNotepad


grid = Grid(GeoCalculator(.5, -1), GeoCalculator(.7), frame=FramePadding(SGRWrap("↑N↑", Fore.white), SGRWrap("→O→", Fore.white), SGRWrap("↓S↓", Fore.white), SGRWrap("←E←", Fore.white), (SGRWrap("/", Fore.white), SGRWrap("/", Fore.white)), (SGRWrap("\\", Fore.white), SGRWrap("\\", Fore.white)), (SGRWrap("/", Fore.white), SGRWrap("/", Fore.white)), (SGRWrap("\\", Fore.white), SGRWrap("\\", Fore.white)), widget_y_calc=GeoCalculator(1., -6), widget_x_calc=GeoCalculator(1., -6)),)
grid.add_row(GeoCalculator(1))
grid.add_row(GeoCalculator(None, comp_remain="always:use remain"))
grid.add_column(GeoCalculator(1))
grid.add_column(GeoCalculator(None, comp_remain=("always", "use remain")))

grid2 = Grid(GeoCalculator(.7), GeoCalculator(.5, -1), grid, frame=FramePadding("═", "║", "═", "║", "╗", "╝", "╚", "╔", widget_y_calc=GeoCalculator(1., -2), widget_x_calc=GeoCalculator(1., -2)),)
grid2.add_row(GeoCalculator(1))
grid2.add_row(GeoCalculator(None, comp_remain=("always", "use remain")))
grid2.add_column(GeoCalculator(1))
grid2.add_column(GeoCalculator(None, comp_remain=("always", "use remain")))

widget1 = SimpleNotepad(grid, display_type='b', frame=FramePadding("─", "╡", "─", "╞", "┐", "┘", "└", "┌", widget_y_calc=GeoCalculator(1., -2), widget_x_calc=GeoCalculator(1., -2)),)
widget1.__display__.settings(
    vis_overflow=(SGRWrap('<', INVERT), SGRWrap('>', INVERT), SGRWrap('<<', INVERT)),
    prompt_factory=lambda *_: (SGRWrap("╣", Fore.red), SGRWrap("╠", Fore.red)), promptl_len=1, promptr_len=1,
    stdcurpos="parallel"
)
widget3 = SimpleNotepad(grid, display_type='s')
widget3.__display__.settings(
    vis_overflow=(SGRWrap('<', INVERT), SGRWrap('>', INVERT), SGRWrap('<<', INVERT)),
    highlighter="advanced"
)
python_darkula(widget3.__display__.__highlighter__)
widget4 = SimpleNotepad(grid2)
widget4.__display__.settings(
    vis_overflow=(SGRWrap('<', Ground.red), SGRWrap('>', Ground.red), SGRWrap('<<', Ground.red))
)
widget4.null_char = SGRWrap('~', Fore.cyan)
widget5 = SimpleNotepad(grid2, tab_size=4, frame=FramePadding("━", "┃", "━", "┃", "┓", "┛", "┗", "┏", widget_y_calc=GeoCalculator(1., -4), widget_x_calc=GeoCalculator(1., -4)),)
widget6 = SimpleNotepad(grid2, display_type='s', frame=FramePadding("━", "┃", "━", "┃", "┓", "┛", "┗", "┏", widget_y_calc=GeoCalculator(1., -4), widget_x_calc=GeoCalculator(1., -4)),)
widget6.__display__.settings(stdcurpos="parallel")

with open(ROOT + "/_demo/testdata/bricks2.txt", encoding="utf8") as f:
    widget1.__buffer__.write(f.read(), move_cursor=False)
with open(ROOT + "/_demo/testdata/code.txt", encoding="utf8") as f:
    widget3.__buffer__.write(f.read(), move_cursor=False)
widget4.__buffer__.write("~ Widget grid and mouse support ~", move_cursor=False)
widget5.__buffer__.write(str().join(" %-12s\n" % chr(i) for i in range(10025, 10060)), move_cursor=False)
widget6.__buffer__.write("Mouse Support:" + (" " * 150) + """
                                                                              #
Left click in buffer:,,,,,,Set cursor.                                        #
...and hold:,,,,,,,,,,,,,,,Mark from previous position.                       #
...and move:,,,,,,,,,,,,,,,Mark.                                              #
...move outwards and hold:,Increase marker and repeat automatically.          #
                                                                              #
Double left click in                                                          #
buffer:,,,,,,,,,,,,,,,,,,,,Mark word.                                         #
                                                                              #
Left click in the                                                             #
autoscroll area and hold:,,Cursor movement and auto repeat.                   #
                                                                              #
Left click in the cell                                                        #
frame:,,,,,,,,,,,,,,,,,,,,,Cursor movement by the                             #
                           distance to the widget.                            #
...and Hold:,,,,,,,,,,,,,,,Automatic repetition.                              #
                                                                              #
Wheel:,,,,,,,,,,,,,,,,,,,,,Scroll vertical in buffer.                         #
Shift + Wheel:,,,,,,,,,,,,,Scroll horizontal in buffer.                       #
""", move_cursor=False)

widget1.__buffer__.goto_row(27)

for wg in (widget1, widget3, widget4, widget5, widget6,):
    wg.__buffer__.init_marker(False, True)
    wg.__display__.settings(
        vis_marked=(
            lambda c, itm, coord: SGRWrap(c, Ground.hex('11ACAE') + Fore.black, cellular=True),
            lambda c, itm, coord: SGRWrap(c, Ground.hex('66B8B1') + Fore.black, cellular=True))
    )

widget4.grid(0, 0)
widget5.grid(0, 2)
widget6.grid(2, 0, column_span=3)
Cell(grid2, SGRWrap(":", Fore.white)).grid(0, 1)
Cell(grid2, SGRWrap("·", Fore.white)).grid(1, 0, column_span=3)

grid2.make_grid()
grid2.grid(0, 2)

widget1.grid(0, 0)
widget3.grid(2, 0, column_span=3)

Cell(grid, SGRWrap(":", Fore.white)).grid(0, 1)
Cell(grid, SGRWrap("·", Fore.white)).grid(1, 0, column_span=3)

grid.make_grid()

StdinAdapter()

inputmodem1 = InputSuperModem(thread_spam=SpamHandleOne())
inputmodem3 = InputSuperModem()
inputmodem4 = InputSuperModem(thread_spam=SpamHandleOne())
inputmodem5 = InputSuperModem()
inputmodem6 = InputSuperModem()

input_router = InputRouter(thread_smoothness=.003)

input_router[widget1] = inputmodem1
input_router[widget3] = inputmodem3
input_router[widget4] = inputmodem4
input_router[widget5] = inputmodem5
input_router[widget6] = inputmodem6

input_router.switch_gate(widget1)


def move_cursor(_wg: SimpleNotepad, nk: NavKey):
    if nk in BasicKeyComp.NavKeys.arrow_lr:
        return _wg.__buffer__.cursor_move(
            z_column=int(nk),
            jump=NavKey.M.CTRL in nk.MOD,
            mark=NavKey.M.SHIFT in nk.MOD
        ) is not None
    elif nk in BasicKeyComp.NavKeys.border:
        if NavKey.M.CTRL in nk.MOD:
            return _wg.__display__.scroll_x({3: 1, -3: -1}[int(nk)], NavKey.M.SHIFT in nk.MOD
                                            ) is not None
        else:
            return _wg.__buffer__.cursor_move(
                z_column=int(nk),
                border=True,
                mark=NavKey.M.SHIFT in nk.MOD,
                mark_jump=NavKey.M.ALT in nk.MOD
            ) is not None
    elif nk in BasicKeyComp.NavKeys.arrow_ud:
        if NavKey.M.CTRL in nk.MOD:
            return _wg.__display__.scroll_y({2: 1, -2: -1}[int(nk)], NavKey.M.SHIFT in nk.MOD
                                            ) is not None
        else:
            return _wg.__buffer__.cursor_move(z_row={2: 1, -2: -1}[int(nk)], mark=NavKey.M.SHIFT in nk.MOD
                                              ) is not None
    elif nk in BasicKeyComp.NavKeys.page_ud:
        if NavKey.M.CTRL in nk.MOD:
            return _wg.__display__.scroll_y(int(nk), NavKey.M.SHIFT in nk.MOD
                                            ) is not None
        else:
            return _wg.__buffer__.cursor_move(z_row=int(nk), mark=NavKey.M.SHIFT in nk.MOD, as_far=True
                                              ) is not None


mp = MouseProcessing(grid, input_router, widget1)


def change_cell(fkey: FKey):
    mp.current_mouse_target = globals()['widget' + str(int(fkey))]
    input_router.switch_gate(mp.current_mouse_target)
    return True


def bindingwrapper(func):
    def wrap(c, v):
        if func(c, v):
            mp.current_mouse_target.new_visual()
            mp.current_mouse_target.print()
            mp.current_mouse_target.cursor_to_position().flush()
    return wrap


for wg, _in in zip((widget1, widget3, widget4, widget5, widget6), (inputmodem1, inputmodem3, inputmodem4, inputmodem5, inputmodem6)):
    _in.__binder__.bind(NavKey, bindingwrapper(lambda k, _, _wg=wg: move_cursor(_wg, k)))
    _in.__binder__.bind(Char, bindingwrapper(lambda c, _, _wg=wg: _wg.write(c)))
    _in.__binder__.bind(
        Meta("\n"),
        bindingwrapper(lambda *_, _wg=wg: _wg.__buffer__.write("\n", nbnl=True,)))
    _in.__binder__.bind(
        Ctrl("enter"),
        bindingwrapper(lambda *_, _wg=wg: _wg.__buffer__.write("\n", )))
    _in.__binder__.bind(
        DelIns(DelIns.K.BACKSPACE),
        bindingwrapper(lambda k, _, _wg=wg: _wg.__buffer__.backspace()))
    _in.__binder__.bind(
        DelIns(DelIns.K.DELETE, None),
        bindingwrapper(lambda k, _, _wg=wg: _wg.__buffer__.delete()))
    _in.__binder__.bind(FKey, bindingwrapper(lambda k, *_: change_cell(k)))
    _in.__binder__.bind(Mouse, bindingwrapper(lambda m, *_: mp(m)))


geo_watcher = GeoWatcher()


def resize(size: tuple[int, int]):
    grid.resize(size)
    grid.new_visual()
    grid.print()
    mp.current_mouse_target.cursor_to_position().flush()


geo_watcher.bind(resize)

try:
    mod_ansiin()
    mod_ansiout()
    _cursor_show = CursorShow()
    CursorBlinking()
    atexit.register(lambda *_: CursorStyle.default().out())
    BracketedPasteMode().highout()
    MouseAllTracking().highout()
    (autow := CursorAutowrapMode()).lowout()
    grid.make_grid()
    grid.resize(geo_watcher.size)
    grid.new_visual()
    grid.print()
    mp.current_mouse_target.cursor_to_position().flush()
except Exception:
    autow.highout()
    raise


try:
    input_router.run()
except Exception:
    autow.highout()
    raise


































