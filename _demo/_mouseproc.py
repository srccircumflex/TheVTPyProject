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


# TODO (SKETCH): Unification in grid derivative.

from __future__ import annotations

from re import Pattern
from threading import Thread
from typing import Callable
from sys import platform

from vtframework.io import InputRouter

try:
    if platform != "win32":
        from signal import signal, SIGWINCH
except ImportError:
    pass

from time import monotonic_ns, sleep

from vtframework.utils.types import NULL
from vtframework.iodata import Mouse
from vtframework.video.items import VisualRealTarget

from vtframework.textbuffer.display.items import DisplayCoordTarget
from vtframework.video import Grid, Cell


class MouseProcessing:
    grid: Grid
    current_target_cell: Cell
    input_router: InputRouter

    current_vrt: VisualRealTarget
    current_dct: DisplayCoordTarget

    double_click_t: int
    double_click_counter: int

    long_press_t: float
    long_press_counter: int

    word_delimiters: tuple[str | Pattern, str | Pattern | None]

    repeater_function: Callable[[], ...] | None
    repeater_intervals: list[float]

    repeat_intervals_inner: list[float]
    repeat_intervals_outer: list[float]

    def __init__(
            self,
            grid: Grid,
            input_router: InputRouter,
            start_cell: Cell,
            repeat_times_inner: list[float] = (.8,),
            repeat_times_outer: list[float] = (.8,),
            double_click: float = .3,
            long_press: float = .2,
            word_delimiters: tuple[str | Pattern, str | Pattern | None] = ("(^|$|\\W)", None),
    ):
        self.grid = grid
        self.current_mouse_target = start_cell
        self.input_router = input_router
        self.double_click_t = int(double_click * 1_000_000_000)
        self.double_click_counter = monotonic_ns()
        self.word_delimiters = word_delimiters
        assert repeat_times_inner
        assert repeat_times_outer
        self.repeater_function = None
        self.repeat_intervals_inner = list(repeat_times_inner)
        self.repeat_intervals_outer = list(repeat_times_outer)
        self.current_dct = self.current_vrt = NULL
        self.long_press_t = long_press
        self.long_press_counter = 0

    def x_eq_row_left_border(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget, mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_column=-1, repeat_mark=True, cross=False)

    def x_eq_row_right_border(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget, mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_column=1, repeat_mark=True, cross=False)

    def x_eq_row(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget, mark: bool) -> bool:
        self.repeater_function = None
        return dct.set_cursor(mark=mark)

    def x_upper_border_row_eq_column(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget,
                                     mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_row=-1, repeat_mark=True, cross=False)

    def x_upper_border_row_left_border(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget,
                                       mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_row=-1, z_column=-1, repeat_mark=True, cross=False)

    def x_upper_border_row_right_border(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget,
                                        mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_row=-1, z_column=1, repeat_mark=True, cross=False)

    def x_upper_border_row(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget, mark: bool) -> bool:
        self.repeater_function = None
        return dct.set_cursor(mark=mark)

    def x_lower_border_row_eq_column(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget,
                                     mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_row=1, repeat_mark=True, cross=False)

    def x_lower_border_row_left_border(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget,
                                       mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_row=1, z_column=-1, repeat_mark=True, cross=False)

    def x_lower_border_row_right_border(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget,
                                        mark: bool) -> bool:
        return self.f_set_and_repeat_cursor(m, dct, mark, z_row=1, z_column=1, repeat_mark=True, cross=False)

    def x_lower_border_row(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget, mark: bool) -> bool:
        self.repeater_function = None
        return dct.set_cursor(mark=mark)

    def x_nonspecific(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget, mark: bool) -> bool:
        self.repeater_function = None
        return dct.set_cursor(mark=mark)

    def x_double_click(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget) -> bool:
        dct.mark_word(*self.word_delimiters)
        return dct.set_cursor()

    def x_long_press(self, m: Mouse, vrt: VisualRealTarget, prev_cur_pos: int) -> None:
        vrt.cell.__buffer__.__marker__.stop()
        vrt.cell.__buffer__.__marker__.add_new(prev_cur_pos)
        vrt.cell.__buffer__.__marker__.set_current()
        vrt.cell.new_visual()
        vrt.cell.print()
        vrt.cell.cursor_to_position().flush()

    def x_outer_click(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget) -> bool:
        def repeat():
            return dct.row.__buffer__.__display__.display_coord_target_by_vrt(vrt).set_cursor(mark=False)

        if not self.repeater_function:
            self.repeater_function = repeat
            self.repeater_intervals = self.repeat_intervals_outer.copy()
            try:
                return dct.set_cursor()
            finally:
                self.f_repeater()
        else:
            try:
                return dct.set_cursor()
            finally:
                self.repeater_function = repeat

    def x_outer_move(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget) -> bool:
        def repeat():
            return vrt.cell.__display__.display_coord_target_by_vrt(vrt).set_cursor(mark=True)

        if not self.repeater_function:
            self.repeater_function = repeat
            self.repeater_intervals = self.repeat_intervals_outer.copy()
            try:
                return dct.set_cursor(mark=True)
            finally:
                self.f_repeater()
        else:
            try:
                return dct.set_cursor(mark=True)
            finally:
                self.repeater_function = repeat

    def x_release(self, m: Mouse, vrt: VisualRealTarget) -> bool:
        self.repeater_function = None
        self.long_press_counter += 1
        return False

    def x_wheel_down(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget) -> bool:
        if m.MOD == m.M.SHIFT:
            if vrt.cell.__display__.scroll_x(1, False) is not False:
                vrt.cell.new_display()
                vrt.cell.print()
                return True
        else:
            if vrt.cell.__display__.scroll_y(4, False) is not False:
                vrt.cell.new_display()
                vrt.cell.print()
                return True

    def x_wheel_up(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget) -> bool:
        if m.MOD == m.M.SHIFT:
            if vrt.cell.__display__.scroll_x(-1, False) is not False:
                vrt.cell.new_display()
                vrt.cell.print()
                return True
        else:
            if vrt.cell.__display__.scroll_y(-4, False) is not False:
                vrt.cell.new_display()
                vrt.cell.print()
                return True

    def f_set_and_repeat_cursor(
            self, m: Mouse,
            dct: DisplayCoordTarget, set_mark: bool,
            z_row: int = None, z_column: int = None,
            jump: bool = False, mark_jump: bool = False,
            border: bool = False, as_far: bool = False,
            repeat_mark: bool = False, cross: bool = True) -> bool:
        def repeat():
            return dct.row.__buffer__.cursor_move(
                z_row=z_row,
                z_column=z_column,
                jump=jump,
                mark_jump=mark_jump,
                border=border,
                as_far=as_far,
                mark=repeat_mark,
                cross=cross,
            )

        if not self.repeater_function:
            self.repeater_function = repeat
            self.repeater_intervals = self.repeat_intervals_inner.copy()
            try:
                return dct.set_cursor(mark=set_mark)
            finally:
                self.f_repeater()
        else:
            try:
                return dct.set_cursor(mark=set_mark)
            finally:
                self.repeater_function = repeat

    def f_set(self, m: Mouse, vrt: VisualRealTarget, dct: DisplayCoordTarget, mark: bool = False) -> bool:

        if dct.drow_item.row_item.row_frame.part_id in (0, 1):
            l_lapping = 0
        else:
            l_lapping = vrt.cell.__display__._lapping

        if dct.row == vrt.cell.__display__.__buffer__.current_row:
            # eq row : ← →
            if vrt.area_coord[0] <= dct.drow_item.row_item.row_frame.len_l_prompts + l_lapping:
                return self.x_eq_row_left_border(m, vrt, dct, mark)
            elif vrt.area_coord[
                0] + 1 >= dct.drow_item.row_item.row_frame.len_l_prompts + dct.drow_item.row_item.row_frame.content_width:
                return self.x_eq_row_right_border(m, vrt, dct, mark)
            else:
                return self.x_eq_row(m, vrt, dct, mark)

        elif vrt.area_coord[1] <= vrt.cell.__display__._auto_scroll_top_distance:
            # upper border
            if vrt.area_coord[0] == self.current_vrt.area_coord[0]:
                # eq column : ↑
                return self.x_upper_border_row_eq_column(m, vrt, dct, mark)
            elif vrt.area_coord[0] <= dct.drow_item.row_item.row_frame.len_l_prompts + l_lapping:
                # left border : ↑ ←
                return self.x_upper_border_row_left_border(m, vrt, dct, mark)
            elif vrt.area_coord[
                0] + 1 >= dct.drow_item.row_item.row_frame.len_l_prompts + dct.drow_item.row_item.row_frame.content_width:
                # right border : ↑ →
                return self.x_upper_border_row_right_border(m, vrt, dct, mark)
            else:
                return self.x_upper_border_row(m, vrt, dct, mark)

        elif vrt.area_coord[1] >= vrt.cell.__display__._auto_scroll_bottom_display_row:
            # lower border
            if vrt.area_coord[0] == self.current_vrt.area_coord[0]:
                # eq column : ↓
                return self.x_lower_border_row_eq_column(m, vrt, dct, mark)
            if vrt.area_coord[0] <= dct.drow_item.row_item.row_frame.len_l_prompts + l_lapping:
                # left border : ↓ ←
                return self.x_lower_border_row_left_border(m, vrt, dct, mark)
            elif vrt.area_coord[
                0] + 1 >= dct.drow_item.row_item.row_frame.len_l_prompts + dct.drow_item.row_item.row_frame.content_width:
                # right border : ↓ →
                return self.x_lower_border_row_right_border(m, vrt, dct, mark)
            else:
                return self.x_lower_border_row(m, vrt, dct, mark)

        else:
            return self.x_nonspecific(m, vrt, dct, mark)

    def f_repeater(self) -> None:

        def repeat():
            intervals = self.repeater_intervals.copy()
            t = intervals.pop(0)
            f = self.repeater_function
            while True:
                sleep(t)
                if f == self.repeater_function:
                    if f() is not None:
                        self.current_mouse_target.new_visual()
                        self.current_mouse_target.print()
                        self.current_mouse_target.cursor_to_position().flush()
                elif self.repeater_function:
                    f = self.repeater_function
                else:
                    break
                try:
                    t = intervals.pop(0)
                except IndexError:
                    pass

        Thread(target=repeat, daemon=True).start()

    def f_long_press_watcher(self, m: Mouse, vrt: VisualRealTarget) -> None:
        cur = vrt.cell.__buffer__.current_row.cursors.data_cursor
        c = self.long_press_counter

        def hold():
            sleep(self.long_press_t)
            if c == self.long_press_counter:
                self.x_long_press(m, vrt, cur)

        Thread(target=hold, daemon=True).start()

    def __call__(self, m: Mouse) -> bool:

        vistarg = self.grid.get_visualtarget(m.POS[0] - 1, m.POS[1] - 1)
        vistarg.trace()

        if m.BUTTON == m.B.L_PRESS:
            vrt = vistarg.real_target_from_trace()
            if vrt.cell != self.current_mouse_target:
                try:
                    self.input_router.switch_gate(vrt.cell)
                except KeyError:
                    return False
                self.current_mouse_target = vrt.cell
            dct = vrt.cell.__display__.display_coord_target_by_vrt(vrt)
            self.long_press_counter += 1
            self.f_long_press_watcher(m, vrt)
            t = monotonic_ns()

            try:
                if dct == self.current_dct:
                    if t - self.double_click_counter <= self.double_click_t:
                        # double click
                        return self.x_double_click(m, vrt, dct)
                elif vrt.outer_quarter:
                    # outer repeat
                    return self.x_outer_click(m, vrt, dct)
                else:
                    return self.f_set(m, vrt, dct)
            finally:
                self.current_mouse_target = vrt.cell
                self.current_vrt = vrt
                self.current_dct = dct
                self.double_click_counter = t

        elif m.BUTTON == m.B.L_MOVE:
            vrt = vistarg.real_target_relative_to_cell(self.current_mouse_target)
            self.long_press_counter += 1
            dct = vrt.cell.__display__.display_coord_target_by_vrt(vrt)

            try:
                if vrt.outer_quarter:
                    return self.x_outer_move(m, vrt, dct)
                else:
                    return self.f_set(m, vrt, dct, True)
            finally:
                self.current_mouse_target = vrt.cell
                self.current_vrt = vrt
                self.current_dct = dct

        elif m.BUTTON == m.B.RELEASE:
            vrt = vistarg.real_target_relative_to_cell(self.current_mouse_target)
            self.x_release(m, vrt)

        elif m.BUTTON == m.B.D_WHEEL:
            vrt = vistarg.real_target_from_trace()

            try:
                dct = vrt.cell.__display__.display_coord_target_by_vrt(vrt)
            except AttributeError:
                return False

            self.long_press_counter += 1

            try:
                return self.x_wheel_down(m, vrt, dct)
            finally:
                self.current_vrt = vrt
                self.current_dct = dct

        elif m.BUTTON == m.B.U_WHEEL:
            vrt = vistarg.real_target_from_trace()

            try:
                dct = vrt.cell.__display__.display_coord_target_by_vrt(vrt)
            except AttributeError:
                return False

            self.long_press_counter += 1

            try:
                return self.x_wheel_up(m, vrt, dct)
            finally:
                self.current_vrt = vrt
                self.current_dct = dct
