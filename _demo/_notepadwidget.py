# MIT License
#
# Copyright (c) 2023 Adrian F. Hoefflin [srccircumflex]
#
# Permission is hereby granted, free of chunk, to any person obtaining a copy
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

# TODO (SKETCH)

from __future__ import annotations

from re import Pattern
from typing import Literal

from vtframework.iodata import Fore, SGRWrap
from vtframework.textbuffer._buffercomponents import WriteItem, ChunkLoad
from vtframework.textbuffer.buffer import TextBuffer
from vtframework.textbuffer.display.displays import DisplayScrollable, DisplayBrowsable
from vtframework.iodata.esccontainer import EscSegment
from vtframework.utils.types import SupportsString
from vtframework.video import Cell, FramePadding, Grid


class SimpleNotepad(Cell):

    __buffer__: TextBuffer
    __display__: DisplayBrowsable | DisplayScrollable

    def __init__(
            self,
            # cell parameter
            master_grid: Grid,
            null_char: str = "*",
            frame: FramePadding = None,
            # buffer base parameter
            tab_size: int = 8,
            tab_to_blank: bool = False,
            autowrap_points: Pattern | bool = False,
            jump_points_re: Pattern | None = None,
            back_jump_re: Pattern | None = None,
            # display parameter
            display_type: Literal['scrollable', 's', 'browsable', 'b'] = 'browsable'
    ):
        Cell.__init__(self, master_grid, null_char, frame)
        self.__buffer__ = TextBuffer(
            top_row_vis_maxsize=None,
            future_row_vis_maxsize=None,
            tab_size=tab_size,
            tab_to_blank=tab_to_blank,
            autowrap_points=autowrap_points,
            jump_points_re=jump_points_re,
            back_jump_re=back_jump_re
        )
        if display_type[0] == 's':
            self.__display__ = DisplayScrollable(
                __buffer__=self.__buffer__,
                width=1,
                height=1,
                y_auto_scroll_distance=3,
                prompt_factory=lambda *_: (EscSegment(''), EscSegment('')),
                promptl_len=0,
                promptr_len=0,
                lapping=3,
                vis_overflow=('', '', ''),
                width_min_char=SGRWrap('~', Fore.cyan),
                highlighter=None,
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
                stdcurpos=0,
                i_rowitem_generator=None,
                i_display_generator=None,
                i_before_framing=None,
            )
        else:
            self.__display__ = DisplayBrowsable(
                __buffer__=self.__buffer__,
                width=1,
                height=1,
                y_auto_scroll_distance=3,
                prompt_factory=lambda *_: (EscSegment(''), EscSegment('')),
                promptl_len=0,
                promptr_len=0,
                lapping=3,
                vis_overflow=('', '', ''),
                width_min_char=SGRWrap('~', Fore.cyan),
                highlighter=None,
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
                stdcurpos=0,
                i_rowitem_generator=None,
                i_display_generator=None,
                i_before_framing=None,
            )

    ####################################################################################################################

    def write(
            self, string: str, *,
            sub_chars: bool = False,
            force_sub_chars: bool = False,
            sub_line: bool = False,
            associate_lines: bool = False,
            nbnl: bool = False,
            move_cursor: bool = True
    ) -> tuple[WriteItem, ChunkLoad]:
        return self.__buffer__.write(
            string,
            sub_chars=sub_chars,
            force_sub_chars=force_sub_chars,
            sub_line=sub_line,
            associate_lines=associate_lines,
            nbnl=nbnl,
            move_cursor=move_cursor
        )

    def delete(self) -> tuple[WriteItem, ChunkLoad] | None:
        return self.__buffer__.delete()

    def backspace(self) -> tuple[WriteItem, ChunkLoad] | None:
        return self.__buffer__.backspace()

    def cursor_move(
            self, *,
            z_row: int = None,
            z_column: int = None,
            jump: bool = False,
            mark_jump: bool = False,
            border: bool = False,
            as_far: bool = False,
            mark: bool = False,
            cross: bool = True
    ) -> ChunkLoad | None:
        return self.__buffer__.cursor_move(
            z_row=z_row,
            z_column=z_column,
            jump=jump,
            mark_jump=mark_jump,
            border=border,
            as_far=as_far,
            mark=mark,
            cross=cross,
        )

    def goto_row(self, __n: int = 0, *, to_bottom: bool = False, as_far: bool = False) -> ChunkLoad:
        return self.__buffer__.goto_row(__n, to_bottom=to_bottom, as_far=as_far)

    def goto_line(self, __n: int = 0, *, to_bottom: bool = False, as_far: bool = False) -> ChunkLoad:
        return self.__buffer__.goto_line(__n, to_bottom=to_bottom, as_far=as_far)

    def goto_data(self, __n: int) -> ChunkLoad:
        return self.__buffer__.goto_data(__n)

    ####################################################################################################################

    def resize(self, size: tuple[int, int]) -> None:
        self.__display__.settings(width=size[0], height=size[1])

    def get_display(self) -> list[SupportsString]:
        display_rows: list[SupportsString] = self.__display__.make_display().rows
        return display_rows + [self.null_char * self.widget_size[0] for _ in range(self.widget_size[1] - len(self.__display__.current_display.rows))]

    def get_cursor_position(self) -> tuple[int, int]:
        return self.__display__.current_display.pointer_column, self.__display__.current_display.pointer_row

