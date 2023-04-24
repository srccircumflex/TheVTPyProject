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

from typing import Callable, Literal, overload, Any, Sequence
from abc import abstractmethod

try:
    from .._buffercomponents import _Row, ChunkLoad, _Marking
    from ..buffer import TextBuffer
    from ...video.items import VisualRealTarget
except ImportError:
    pass

from ...iodata.sgr import SGRReset
from ...iodata.esccontainer import EscSegment, EscContainer
from .items import VisRowItem, RowFrameItem, DisplayRowItem, DisplayItem, DisplayCoordTarget
from .highlighters import HighlighterBase, HighlightRegex, HighlightAdvanced


class _DisplayBase:
    """
    The basic object of the display types for a ``TextBuffer``.

    From the :class:`TextBuffer` data to the display:
        - Determination of the rows to be displayed -> list[ :class:`_Row` ].

        - Calibration of coordinates of tabs, markers, and cursor anchors per row -> :class:`VisRowItem`.
            - Calculation of the framing parameters of the row (this method determines the behavior
              of the display and is implemented in the final display types) -> :class:`RowFrameItem`.

        - Highlight row ->  :class:`EscContainer`.

        - Visual marked areas ->  ``EscContainer``.

        - Visual finishing ->  ``EscContainer``.
            ===== =========
            i     function
            ===== =========
            ``~`` Row end visualization
            ``#`` Cursor anchor visualization
            ``█`` Cursor visualization
            ``+`` Row framing
            ===== =========
            
            Orders:
                `visendpos` == ``"data"``:
                    ``~ # █ +``
                `visendpos` == ``"data f"``:
                    ``# █ ~ +``
                `visendpos` == ``"visN1"``:
                    ``# █ + ~``

        - Creation of the final display row -> :class:`DisplayRowItem`.
            - Append left/right prompts to the framed and visualized row.

        - Summarizing the display rows and setting the cursor x/y-position relative to the displayed area
          -> :class:`DisplayItem`.

    Basic parameters and settings:

        - `__buffer__`
            The :class:`TextBuffer` object for which the display is created.

        - `height`
            The number of rows in the area to be displayed.

        - `y_auto_scroll_distance`
            The number of rows that may remain between the current cursor position and the boundary of the currently
            displayed area until the automatic scrolling is triggered.

        - `highlighter`
            Which highlighter is to be assigned to attribute ``__highlighter__`` (required component of the display).

            - ``"regex"`` : :class:`HighlightRegex`
            - ``"advanced"`` : :class:`HighlightAdvanced`
            - ``None`` : :class:`HighlighterBase`

        - `highlighted_rows_cache_max`
            Has meaning when the highlighter is :class:`HighlightRegex` or :class:`HighlightAdvanced`.

        - `highlighted_row_segments_max`
            Has meaning when the highlighter is :class:`HighlightRegex` or :class:`HighlightAdvanced`.

        - `vis_tab` [OPTIONAL -- can be ``None``]
            Assigns a function to the visualization of relative tab ranges that receives the size of the range and
            must return a correspondingly long string.

        - `vis_marked` [OPTIONAL -- can be ``None``]
            Two executable objects for displaying marked areas.
            The first function is applied only to the first character of the range, remaining strings are passed to
            the second. The functions receive the applicable row string, the :class:`VisRowItem` and the marker
            coordinate calibrated to the row; the return value should be the visualized row string.

            >>> from vtframework.iodata.sgr import SGRWrap, Ground, Fore
            >>> vis_marked=(lambda c, itm, coord: SGRWrap(c, Ground.hex('11ACAE') + Fore.black, cellular=True),
            >>>             lambda c, itm, coord: SGRWrap(c, Ground.hex('66B8B1') + Fore.black, cellular=True))

        - `vis_end` [OPTIONAL -- fields or total can be ``None``]
            Defines the visual representation of breaking line breaks in ``(
            normal form,
            when a marking starts on it,
            and within a marked area
            )``

        - `vis_nb_end` [OPTIONAL -- fields or total can be ``None``]
            Defines the visual representation of non-breaking line breaks in ``(
            normal form,
            when a marking starts on it,
            and within a marked area
            )``

        - `visendpos`
            Define the position of the visual end character.

            - ``"data"`` : Equal to the data position (directly following).
            - ``"data f"`` : Equal to the data position (directly following) also overwrites the
              visualization of a cursor position.
            - ``"visN1"`` : At the last visual place of the display.

        - `vis_cursor` [OPTIONAL -- can be ``None``]
            Visualize the character at the cursor position. Receives the character and the
            ``VisRowItem`` when executed and should return the visualized version.

            >>> vis_cursor=lambda c, itm: (SGRWrap(c, Ground.name('red1'), inner=True, cellular=True)
            >>>                            if insert_mode
            >>>                            else c)

        - `vis_anchor` [OPTIONAL -- can be ``None``]
            Visualize the character of a cursor anchor. Receives the character, the ``VisRowItem`` and
            the anchor item when executed and should return the visualized version.

            >>> vis_anchor=lambda c, itm, itm: SGRWrap(c, Ground.hex('FFF800'), inner=True)

        - `vis_cursor_row` [OPTIONAL -- can be ``None``]
            Visualize the row of the current cursor position. Receives the characters of the row and the
            ``VisRowItem`` when executed and should return the visualized version.

        - `stdcurpos`
            Specify the standard cursor position for rows.

            - ``<as natural number>``
            - ``"follow"`` : follows as far as possible.
            - ``"parallel"`` : follows across row endings as well.
            - ``"end"`` : as the right end of a row.

        - `i_rowitem_generator` [OPTIONAL -- can be ``None``]
            An interface within the reverse iteration to determine the :class:`VisRowItem`. Receives the ``VisRowItem``.

        - `i_display_generator` [OPTIONAL -- can be ``None``]
            An interface within the iteration to create the :class:`DisplayRowItem`. Receives the ``DisplayRowItem``.

        - `i_before_framing` [OPTIONAL -- can be ``None``]
            An interface that receives the row before framing and the :class:`VisRowItem`, must return the row.
    """

    _vis_marked: Callable[[VisRowItem, str], tuple[str, int]]
    _vis_end: tuple[str, str, str]
    _vis_nb_end: tuple[str, str, str]
    _vis_cursor: Callable[[str, VisRowItem], str]
    _vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str]
    _vis_cursor_row: Callable[[str, VisRowItem], str]

    _visualfinish: Callable[[VisRowItem, bool, EscContainer, int], tuple[EscContainer, int]]
    _getstdcurpos: Callable[[int], int]

    _i_rowitem_generator: Callable[[VisRowItem], Any]
    _i_display_generator: Callable[[DisplayRowItem], Any]
    _i_before_framing: Callable[[str, VisRowItem], str]

    current_row_num: int
    current_cursor_row_area: tuple[int, int]
    current_slice: tuple[int, int]
    current_y_pointer: int
    current_x_pointer: int
    current_display: DisplayItem

    height: int
    height_central: int
    y_auto_scroll_distance: int
    _y_auto_scroll_distance: int

    _auto_scroll_top_distance: int
    _auto_scroll_bottom_distance: int
    _auto_scroll_top_display_row: int
    _auto_scroll_bottom_display_row: int

    _make_display_by_cursors_: Callable[[int, Callable[[_Row], int]], DisplayItem]
    _get_y_rows_by_hint: Callable[[int], list[_Row]] | None
    _y_scrolled: bool

    y_minimum_size_undercut: bool

    __buffer__: TextBuffer
    __highlighter__: HighlighterBase | HighlightRegex | HighlightAdvanced

    __slots__ = ('_vis_marked', '_vis_end', '_vis_nb_end', '_vis_cursor', '_vis_anchor', '_vis_cursor_row',
                 '_getstdcurpos', '_visualfinish', '__buffer__', '__highlighter__', 'current_display',
                 'current_row_num', 'current_cursor_row_area', 'current_slice', 'height', 'y_auto_scroll_distance',
                 '_y_auto_scroll_distance', '_auto_scroll_top_distance', '_auto_scroll_bottom_distance',
                 '_auto_scroll_top_display_row', '_auto_scroll_bottom_display_row', 'height_central',
                 '_get_y_rows_by_hint', '_make_display_by_cursors_', 'y_minimum_size_undercut', '_y_scrolled',
                 'current_y_pointer', 'current_x_pointer',
                 '_i_rowitem_generator', '_i_display_generator', '_i_before_framing')

    @property
    def current_display_row(self) -> DisplayRowItem:
        return self.current_display.rows[self.current_display.pointer_row]

    def __init__(self, __buffer__: TextBuffer,
                 height: int,
                 y_auto_scroll_distance: int,
                 highlighter: Literal["regex", "r", "advanced", "a"] | None,
                 highlighted_rows_cache_max: int | None,
                 highlighted_row_segments_max: int | None,
                 vis_tab: Callable[[int], str] | None,
                 vis_marked: Sequence[Callable[[str, VisRowItem, list[int, int]], str],
                                      Callable[[str, VisRowItem, list[int, int]], str]] | None,
                 vis_end: Sequence[str | None, str | None, str | None] | None,
                 vis_nb_end: Sequence[str | None, str | None, str | None] | None,
                 visendpos: Literal["data", "d", "data f", "df", "visN1", "v", "v1"],
                 vis_cursor: Callable[[str, VisRowItem], str] | None,
                 vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str] | None,
                 vis_cursor_row: Callable[[str, VisRowItem], str] | None,
                 stdcurpos: int | Literal["follow", "f", "parallel", "p", "end", "e"],
                 i_rowitem_generator: Callable[[VisRowItem], Any] | None,
                 i_display_generator: Callable[[DisplayRowItem], Any] | None,
                 i_before_framing: Callable[[str, VisRowItem], str] | None
                 ):
        self.__buffer__ = __buffer__
        __buffer__.__display__ = self

        self._y_scrolled = False
        self.current_row_num = __buffer__.current_row.__row_num__

        self.settings(height=height,
                      y_auto_scroll_distance=y_auto_scroll_distance,
                      highlighter=highlighter,
                      vis_marked=vis_marked,
                      vis_end=vis_end,
                      vis_nb_end=vis_nb_end,
                      vis_cursor=vis_cursor,
                      vis_anchor=vis_anchor,
                      vis_cursor_row=vis_cursor_row,
                      vis_tab=vis_tab,
                      stdcurpos=stdcurpos,
                      visendpos=visendpos,
                      i_rowitem_generator=i_rowitem_generator,
                      i_display_generator=i_display_generator,
                      i_before_framing=i_before_framing,
                      highlighted_rows_cache_max=highlighted_rows_cache_max,
                      highlighted_row_segments_max=highlighted_row_segments_max)

        self.get_next_y_by_hint('central')
        self.get_y_rows()

    @overload
    def settings(self, *,
                 height: int = ...,
                 y_auto_scroll_distance: int = ...,
                 highlighter: Literal["regex", "r", "advanced", "a"] | None = ...,
                 highlighted_rows_cache_max: int | None,
                 highlighted_row_segments_max: int | None,
                 vis_tab: Callable[[str], str] | None = ...,
                 vis_marked: tuple[Callable[[str, VisRowItem, list[int, int]], str],
                                   Callable[[str, VisRowItem, list[int, int]], str]] | None = ...,
                 vis_end: Sequence[str | None, str | None, str | None] | None = ...,
                 vis_nb_end: Sequence[str | None, str | None, str | None] | None = ...,
                 visendpos: Literal["data", "d", "data f", "df", "visN1", "v", "v1"] = ...,
                 vis_cursor: Callable[[str, VisRowItem], str] | None = ...,
                 vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str] | None = ...,
                 vis_cursor_row: Callable[[str, VisRowItem], str] | None = ...,
                 stdcurpos: int | Literal["follow", "f", "parallel", "p", "end", "e"] = ...,
                 i_rowitem_generator: Callable[[VisRowItem], Any] | None = ...,
                 i_display_generator: Callable[[DisplayRowItem], Any] | None = ...,
                 i_before_framing: Callable[[str, VisRowItem], str] | None = ...
                 ) -> None:
        ...

    def settings(self, **kwargs) -> None:
        """
        Change the :class:`_DisplayBase` settings.
        """

        try:
            if (param := kwargs.pop('highlighter')) is None:
                self.__highlighter__ = HighlighterBase()
            elif param[0] == 'r':
                self.__highlighter__ = HighlightRegex(self.__buffer__)
            elif param[0] == 'a':
                self.__highlighter__ = HighlightAdvanced(self.__buffer__)
        except KeyError:
            pass
        try:
            if (val := kwargs.pop('vis_tab')) is None:
                self.__highlighter__._vis_tab = lambda n: " " * n
            else:
                self.__highlighter__._vis_tab = val
        except KeyError:
            pass
        try:
            self.__highlighter__._highlighted_rows_cache_max = kwargs.pop('highlighted_rows_cache_max') or 1000
        except KeyError:
            pass
        try:
            self.__highlighter__._highlighted_row_segments_max = kwargs.pop('highlighted_row_segments_max') or 100
        except KeyError:
            pass

        for attr in ('i_rowitem_generator', 'i_display_generator'):
            try:
                setattr(self, '_' + attr, kwargs.pop(attr) or (lambda _: None))
            except KeyError:
                pass

        for attr in ('vis_end', 'vis_nb_end'):
            try:
                if param := kwargs.pop(attr):
                    param = (param[0] or ' ', param[1] or ' ', param[2] or ' ')
                else:
                    param = (' ', ' ', ' ')
                setattr(self, '_' + attr, param)
            except KeyError:
                pass

        try:
            if vis_marked := kwargs.pop('vis_marked'):
                def vis_mark(rowitm: VisRowItem, vis_row):
                    marked_end = 0
                    if vis_slice := rowitm.row_frame.vis_slice:
                        if vis_slice[1]:
                            for coord, mark in rowitm.v_marks:
                                if mark[0] is None:
                                    marked_end = 1
                                elif mark[1]:
                                    if (
                                            vis_slice[0] < mark[1] <= vis_slice[1] or
                                            vis_slice[0] <= mark[0] < vis_slice[1] or
                                            mark[0] < vis_slice[1] <= mark[1] or
                                            mark[0] <= vis_slice[0] < mark[1]
                                    ):
                                        vis_row = vis_row[:mark[0]] + vis_marked[mark[2]](
                                            vis_row[mark[0]:(e := mark[0] + 1)], rowitm, coord
                                        ) + vis_marked[1](vis_row[e:mark[1]], rowitm, coord) + vis_row[mark[1]:]
                                else:
                                    if (
                                            vis_slice[0] <= mark[0] < vis_slice[1] or
                                            mark[0] < vis_slice[1] or
                                            mark[0] <= vis_slice[0]
                                    ):
                                        vis_row = vis_row[:mark[0]] + vis_marked[mark[2]](
                                            vis_row[mark[0]:(e := mark[0] + 1)], rowitm, coord
                                        ) + vis_marked[1](vis_row[e:mark[1]], rowitm, coord)
                                    marked_end = 2
                        else:
                            for coord, mark in rowitm.v_marks:
                                if mark[0] is None:
                                    marked_end = 1
                                elif mark[1]:
                                    if (
                                            vis_slice[0] < mark[1] or
                                            vis_slice[0] <= mark[0] or
                                            mark[0] <= vis_slice[0] < mark[1]
                                    ):
                                        vis_row = vis_row[:mark[0]] + vis_marked[mark[2]](
                                            vis_row[mark[0]:(e := mark[0] + 1)], rowitm, coord
                                        ) + vis_marked[1](vis_row[e:mark[1]], rowitm, coord) + vis_row[mark[1]:]
                                else:
                                    if (
                                            vis_slice[0] <= mark[0] or
                                            mark[0] <= vis_slice[0]
                                    ):
                                        vis_row = vis_row[:mark[0]] + vis_marked[mark[2]](
                                            vis_row[mark[0]:(e := mark[0] + 1)], rowitm, coord
                                        ) + vis_marked[1](vis_row[e:mark[1]], rowitm, coord)
                                    marked_end = 2
                    return vis_row, marked_end

            else:
                def vis_mark(rowitm: VisRowItem, vis_row):
                    return vis_row, 0

            self._vis_marked = vis_mark
        except KeyError:
            pass

        try:
            if (stdcurpos := kwargs.pop('stdcurpos')) is not None:
                if isinstance(stdcurpos, int):
                    if stdcurpos < 0:
                        stdcurpos = abs(stdcurpos)

                        def gscp(cur, end):
                            return min(stdcurpos, end)
                    else:
                        def gscp(cur, end):
                            return stdcurpos
                elif stdcurpos[0] == 'p':
                    def gscp(cur, end):
                        return cur
                elif stdcurpos[0] == 'f':
                    def gscp(cur, end):
                        return min(cur, end)
                elif stdcurpos[0] == 'e':
                    def gscp(cur, end):
                        return end
                else:
                    raise ValueError(f"{stdcurpos=}")

                self._getstdcurpos = gscp
        except KeyError:
            pass

        for attr in ('vis_cursor', 'vis_cursor_row', 'i_before_framing'):
            try:
                setattr(self, '_' + attr, kwargs.pop(attr) or (lambda vr, itm: vr))
            except KeyError:
                pass

        try:
            self._vis_anchor = kwargs.pop('vis_anchor') or (lambda vr, itm, curitm: vr)
        except KeyError:
            pass

        try:
            visendpos = kwargs.pop('visendpos')

            def framing(__vis_row, __rowitm):
                __vis_row = self._i_before_framing(__vis_row, __rowitm
                                                   )[__rowitm.row_frame.vis_slice[0]:__rowitm.row_frame.vis_slice[1]]
                if __rowitm.row_frame.part_form:
                    return __rowitm.row_frame.part_form % __vis_row
                else:
                    return __vis_row

            def endvisd(__vis_row, __rowitm, __marked_end):
                if __rowitm.row_frame.vis_slice[1] is None and __rowitm.row.end is not None:
                    if __rowitm.row.end:
                        return __vis_row + self._vis_end[__marked_end]
                    else:
                        return __vis_row + self._vis_nb_end[__marked_end]
                else:
                    return __vis_row

            def endvis1(__frame, __rowitm, __marked_end):
                if __rowitm.row_frame.vis_slice[1] is None and __rowitm.row.end is not None:
                    if __rowitm.row.end:
                        return __frame[:-1] + self._vis_end[__marked_end]
                    else:
                        return __frame[:-1] + self._vis_nb_end[__marked_end]
                else:
                    return __frame

            def notslice(__rowitm, __pointer):
                return __rowitm.row_frame.part_form % '', (__rowitm.row_frame.display_pointer
                                                           if __rowitm.row.inrow()
                                                           else __pointer)

            def visanc(__vis_row, __rowitm: VisRowItem):
                for itm, anch in __rowitm.v_anchors:
                    __vis_row = __vis_row[:anch] + self._vis_anchor(
                        __vis_row[anch:(e := anch + 1)], __rowitm, itm
                    ) + __vis_row[e:]
                return __vis_row

            def viscur(__vis_row, __rowitm):
                __vis_row = __vis_row[:__rowitm.row.cursors.visual] + self._vis_cursor(
                    __vis_row[__rowitm.row.cursors.visual:(e := __rowitm.row.cursors.visual + 1)], __rowitm
                ) + __vis_row[e:]
                return self._vis_cursor_row(__vis_row, __rowitm)

            if (_vp := visendpos[0]) == 'd':

                if (_vp := visendpos[-1]) in ('a', 'd'):

                    def fin(rowitm: VisRowItem, marked_end, vis_row, pointer):

                        if not rowitm.row_frame.vis_slice:
                            return notslice(rowitm, pointer)

                        vis_row = endvisd(vis_row, rowitm, marked_end)

                        vis_row = visanc(vis_row, rowitm)

                        # relevant cursor position and cursor visualization
                        if rowitm.row.inrow():
                            vis_row = viscur(vis_row, rowitm)
                            pointer = rowitm.row_frame.display_pointer

                        return framing(vis_row, rowitm), pointer

                elif _vp == 'f':

                    def fin(rowitm: VisRowItem, marked_end, vis_row, pointer):

                        if not rowitm.row_frame.vis_slice:
                            return notslice(rowitm, pointer)

                        vis_row = visanc(vis_row, rowitm)

                        # relevant cursor position and cursor visualization
                        if rowitm.row.inrow():
                            vis_row = viscur(vis_row, rowitm)
                            pointer = rowitm.row_frame.display_pointer

                        return framing(endvisd(vis_row, rowitm, marked_end), rowitm), pointer

                else:
                    raise ValueError(f"{visendpos=}")

            elif _vp == 'v':

                def fin(rowitm: VisRowItem, marked_end, vis_row, pointer):

                    if not rowitm.row_frame.vis_slice:
                        return notslice(rowitm, pointer)

                    vis_row = visanc(vis_row, rowitm)

                    # relevant cursor position and cursor visualization
                    if rowitm.row.inrow():
                        vis_row = viscur(vis_row, rowitm)
                        pointer = rowitm.row_frame.display_pointer

                    return endvis1(framing(vis_row, rowitm), rowitm, marked_end), pointer

            else:
                raise ValueError(f"{visendpos=}")

            self._visualfinish = fin

        except KeyError:
            pass

        try:
            self._y_auto_scroll_distance = kwargs.pop('y_auto_scroll_distance')
        except KeyError:
            pass

        try:
            if (height := kwargs.pop('height')) <= 0:
                self.height = 0
                self._make_display_by_cursors_ = self._make_undercut_display
                self.height_central = 0
                self.y_auto_scroll_distance = 0
                self._auto_scroll_top_distance = 0
                self._auto_scroll_top_display_row = 0
                self._auto_scroll_bottom_display_row = 0
                self._auto_scroll_bottom_distance = 0
                self.y_minimum_size_undercut = True
            else:
                self.height = height
                self._make_display_by_cursors_ = self._make_display_by_cursors
                self.height_central = (self.height - 1) // 2
                self.y_auto_scroll_distance = min(self._y_auto_scroll_distance, self.height_central)
                if self.height_central:
                    self._auto_scroll_bottom_display_row = (self.height - self.y_auto_scroll_distance) - 1
                    self._auto_scroll_bottom_distance = self.y_auto_scroll_distance + 1
                    self._auto_scroll_top_distance = self.y_auto_scroll_distance
                    self._auto_scroll_top_display_row = self.y_auto_scroll_distance
                else:
                    self._auto_scroll_bottom_display_row = 0
                    self._auto_scroll_bottom_distance = 0
                    self._auto_scroll_top_distance = 0
                    self._auto_scroll_top_display_row = 0
                self.y_minimum_size_undercut = False
        except KeyError:
            self._auto_scroll_top_distance = self.y_auto_scroll_distance
            self._auto_scroll_top_display_row = self.y_auto_scroll_distance
            if self.height_central:
                self._auto_scroll_bottom_display_row = (self.height - self.y_auto_scroll_distance) - 1
                self._auto_scroll_bottom_distance = self.y_auto_scroll_distance + 1
                self._auto_scroll_top_distance = self.y_auto_scroll_distance
                self._auto_scroll_top_display_row = self.y_auto_scroll_distance
            else:
                self._auto_scroll_bottom_display_row = 0
                self._auto_scroll_bottom_distance = 0
                self._auto_scroll_top_distance = 0
                self._auto_scroll_top_display_row = 0
            self.y_minimum_size_undercut = False

        if kwargs:
            raise ValueError(kwargs)

    def get_y_rows(self) -> list[_Row]:
        """
        Determine the :class:`_Row`'s to be displayed.
        """

        cur_row = self.__buffer__.current_row.__row_num__
        cur_idx = self.__buffer__.current_row.__row_index__

        if self._get_y_rows_by_hint:
            rowarea = self._get_y_rows_by_hint(cur_row - self.current_row_num)
            self._get_y_rows_by_hint = None
        elif self._y_scrolled:
            rowarea = self.__buffer__.rows[slice(*self.current_slice)]
            self._y_scrolled = False
        elif not (self.current_cursor_row_area[0] <= cur_row):
            s = max(0, cur_idx - self._auto_scroll_top_distance)
            e = s + self.height
            self.current_y_pointer = min(cur_idx, self._auto_scroll_top_distance)
            rowarea = self.__buffer__.rows[s:e]
            self.current_slice = (s, e)
        elif not (cur_row <= self.current_cursor_row_area[1]):
            if (e := cur_idx + self._auto_scroll_bottom_distance) < self.height:
                e = self.height
                self.current_y_pointer = cur_idx
            else:
                self.current_y_pointer = self._auto_scroll_bottom_display_row
            s = e - self.height
            rowarea = self.__buffer__.rows[s:e]
            self.current_slice = (s, e)
        elif not (self.current_slice[0] + self._auto_scroll_top_distance
                  <= cur_idx < self.current_slice[1] - self._auto_scroll_bottom_distance):
            if (e := cur_idx + self._auto_scroll_bottom_distance) < self.height:
                e = self.height
                self.current_y_pointer = cur_idx
            else:
                self.current_y_pointer = self._auto_scroll_bottom_display_row
            s = e - self.height
            rowarea = self.__buffer__.rows[s:e]
            self.current_slice = (s, e)
        else:
            for row in reversed(self.__buffer__.rows[:cur_idx + 1]):
                if row.__row_num__ == self.current_cursor_row_area[0]:
                    s = max(0, row.__row_index__ - self._auto_scroll_top_distance)
                    e = s + self.height
                    self.current_slice = (s, e)
                    break
            rowarea = self.__buffer__.rows[slice(*self.current_slice)]
            self.current_y_pointer = max(0, self.__buffer__.current_row_idx - self.current_slice[0])

        self.current_cursor_row_area = ((start := rowarea[0].__row_num__) + self._auto_scroll_top_distance,
                                        start + self._auto_scroll_bottom_display_row)

        self.current_row_num = cur_row
        return rowarea

    def get_next_y_by_hint(self, hint: Literal["central", "c", "border", "b"] | None) -> None:
        """
        Determine the next rows to be displayed with a `hint`.
        Move the range of displayed rows until the current cursor position is located ``"central"`` in the
        display or is at the nearest ``"border"`` of the display. Remove the `hint` when ``None`` is passed.
        """

        if not hint:
            get_hinted_position = None

        elif hint[0] == 'c':

            def get_hinted_position(diff):
                s = max(0, self.__buffer__.current_row_idx - self.height_central)
                e = s + self.height
                self.current_y_pointer = min(self.height_central, self.__buffer__.current_row_idx)
                self.current_slice = (s, e)
                return self.__buffer__.rows[s:e]

        elif hint[0] == 'b':

            def get_hinted_position(diff):
                if diff > 0:
                    e = self.__buffer__.current_row_idx + self._auto_scroll_bottom_distance
                    s = max(0, e - self.height)
                    self.current_y_pointer = min(self._auto_scroll_bottom_display_row, self.__buffer__.current_row_idx)
                    self.current_slice = (s, e)
                    return self.__buffer__.rows[s:e]
                else:
                    s = max(0, self.__buffer__.current_row_idx - self._auto_scroll_top_distance)
                    e = s + self.height
                    self.current_y_pointer = min(self._auto_scroll_top_display_row, self.__buffer__.current_row_idx)
                    self.current_slice = (s, e)
                    return self.__buffer__.rows[s:e]

        else:
            raise ValueError(hint)

        self._get_y_rows_by_hint = get_hinted_position

    @abstractmethod
    def scroll_x(self, z: int, mark: bool) -> bool | None:
        ...

    def scroll_y(self, z: int, mark: bool) -> ChunkLoad | bool:
        """
        Scroll the displayed rows along the y-axis and move the cursor in the :class:`TextBuffer`
        when it is at the border of the automatic scroll area.
        """
        if ((slc_start := max(0, self.current_slice[0] + z))
                <= self.__buffer__.rows[-1].__row_index__ - self._auto_scroll_bottom_distance):
            self._y_scrolled = True
            area_start = (s := self.__buffer__.rows[slc_start].__row_num__) + self._auto_scroll_top_distance
            area_stop = s + self._auto_scroll_bottom_display_row
            cur_row = self.__buffer__.current_row.__row_num__
            if area_start > cur_row:
                cl = self.__buffer__.cursor_move(z_row=area_start - cur_row, mark=mark)
                s = max(0, self.__buffer__.current_row.__row_index__ - self._auto_scroll_top_distance)
                e = s + self.height
                self.current_y_pointer = min(self.__buffer__.current_row.__row_index__,
                                             self._auto_scroll_top_distance)
                self.current_slice = (s, e)
            elif cur_row > area_stop:
                cl = self.__buffer__.cursor_move(z_row=-(cur_row - area_stop), mark=mark)
                e = self.__buffer__.current_row.__row_index__ + self._auto_scroll_bottom_distance
                s = max(0, e - self.height)
                self.current_y_pointer = self._auto_scroll_bottom_display_row
                self.current_slice = (s, e)
            else:
                cl = self.__buffer__.cursor_move(mark=mark)
                self.current_slice = (slc_start, slc_start + self.height)
                self.current_y_pointer = max(0, self.__buffer__.current_row_idx - self.current_slice[0])
            return True if cl is None else cl
        return False

    def scroll(self, *, z_y: int = None, z_x: int = None, mark: bool = False
               ) -> ChunkLoad | bool:
        """
        Scroll the displayed rows along the y-axis or x-axis and move the cursor in the :class:`TextBuffer`
        when it is at the border of the automatic scroll area.
        """
        if z_y:
            return self.scroll_y(z_y, mark)
        if z_x:
            return self.scroll_x(z_x, mark)

    @abstractmethod
    def make_row_frame(self, __row: _Row, vis_cursor: int) -> RowFrameItem:
        """
        The characteristic framing for the display type.
        """
        ...

    def make_visual_row_frame(self,
                              row: _Row,
                              inrow_cursor: int,
                              other_cursors: Callable[[_Row], int],
                              default_item: VisRowItem | None,
                              markings: list[_Marking | list[int, int]],
                              anchors: list[tuple[int | str, int]],
                              new_markings: bool = True,
                              new_anchors: bool = True,
                              new_tabs: bool = True) -> VisRowItem:
        """
        Calibrate the coordinates of tabs, markers and cursor anchors for a `row`.
        The method can be used to overwrite an existing :class:`VisRowItem`, this is passed as `default_item`;
        the arguments `new_markings`, `new_anchors` and `new_tabs` specify which attributes are to be overwritten.
        """
        datend = row.data_cache.len_absdata_excl

        def vis_markings():
            _v_marks = list()
            while markings and markings[-1][0] > datend:
                markings.pop(-1)
            _i = len(markings) - 1
            while _i >= 0 and markings[_i][1] > row.__data_start__:
                if markings[_i][0] >= datend:
                    v_start = v_stop = None
                else:
                    v_start = row.cursors.tool_cnt_to_vis(max(0, markings[_i][0] - row.__data_start__))
                    if markings[_i][1] > datend:
                        v_stop = None
                    else:
                        v_stop = row.cursors.tool_cnt_to_vis(markings[_i][1] - row.__data_start__)
                _v_marks.insert(0, (
                    markings[_i],
                    (v_start, v_stop, int(not (row.__data_start__ <= markings[_i][0] < row.__next_data__)))
                )
                               )
                _i -= 1
            return _v_marks

        def vis_anchors():
            _v_anchors = list()
            while anchors and anchors[-1][1] > datend:
                anchors.pop(-1)
            _i = len(anchors) - 1
            while _i >= 0 and anchors[_i][1] >= row.__data_start__:
                _v_anchors.append((anchors[_i], row.cursors.tool_cnt_to_vis(anchors[_i][1] - row.__data_start__)))
                _i -= 1
            return _v_anchors

        if not default_item:
            v_marks = vis_markings()
            v_anchors = vis_anchors()
            tab_spaces = tuple((row.tab_size - (len(s) % row.tab_size)) for s in row.data_cache.raster[:-1]) + (0,)
        else:
            if new_markings:
                v_marks = vis_markings()
            else:
                v_marks = default_item.v_marks
            if new_anchors:
                v_anchors = vis_anchors()
            else:
                v_anchors = default_item.v_anchors
            if new_tabs:
                tab_spaces = tuple((row.tab_size - (len(s) % row.tab_size)) for s in row.data_cache.raster[:-1]) + (0,)
            else:
                tab_spaces = default_item.tab_spaces

        return VisRowItem(row=row, tab_spaces=tab_spaces, v_marks=v_marks, v_anchors=v_anchors,
                          row_frame=self.make_row_frame(row, (inrow_cursor if row.inrow() else other_cursors(row))))

    def make_display(self) -> DisplayItem:
        """
        Summarize the display rows and set the cursor x/y-position relative to the displayed area.
        """
        cursor = self.__buffer__.current_row.cursors.visual

        def cursor2(rowbuffer: _Row):
            return self._getstdcurpos(cursor, rowbuffer.data_cache.len_visual_incl)

        return self.make_display_by_cursors(cursor, cursor2)

    def _make_undercut_display(self, inrow_cursor: int, other_cursors: Callable[[_Row], int]) -> DisplayItem:
        self.current_display = DisplayItem([], 0, 0)
        return self.current_display
    
    def _make_display_by_cursors(self, inrow_cursor: int, other_cursors: Callable[[_Row], int]) -> DisplayItem:

        rowitems = list()
        markings = [m for m in self.__buffer__.__marker__.sorted_copy() if m[0] != m[1]]
        anchors = self.__buffer__.__glob_cursor__.cursor_anchors.copy()

        for row in reversed(self.get_y_rows()):

            rowitems.insert(0, rowitm := self.make_visual_row_frame(
                row, inrow_cursor, other_cursors, None, markings, anchors
            ))

            self._i_rowitem_generator(rowitm)

        # highlighter announce
        self.__highlighter__._announce(rowitems)

        display_rows = list()
        self.current_x_pointer = 0

        for rowitm in rowitems:

            # highlighting incl. tab visualization
            vis_row = self.__highlighter__.__call__(rowitm)

            # marking visualization
            vis_row, marked_end = self._vis_marked(rowitm, vis_row)

            # visualization finishing
            frame, self.current_x_pointer = self._visualfinish(rowitm, marked_end, vis_row, self.current_x_pointer)

            display_rows.append(disprow := DisplayRowItem(
                rowitm.row_frame.lr_prompt[0] + frame + rowitm.row_frame.lr_prompt[1], rowitm))

            self._i_display_generator(disprow)

        self.current_display = DisplayItem(display_rows, self.current_y_pointer, self.current_x_pointer)
        return self.current_display

    def make_display_by_cursors(self, inrow_cursor: int, other_cursors: Callable[[_Row], int]) -> DisplayItem:
        """
        Summarize, using the cursor position in the current row and an executable object that returns the cursor
        position for the remaining rows, the display rows and set the x/y position of the cursor relative to the
        displayed area.
        """
        return self._make_display_by_cursors_(inrow_cursor, other_cursors)

    def display_coord_target_border(
            self,
            quarter: Literal["N", "O", "S", "E", "NO", "NE", "SO", "SE"]
    ) -> DisplayCoordTarget:
        """
        Create a :class:`DisplayCoordTarget` that points to the edge of a display.
        """
        trowitm = self.current_display_row
        cnt_cur = trowitm.row_item.row.cursors.content
        if "S" in quarter:
            trowitm = self.current_display.rows[-1]
        elif "N" in quarter:
            trowitm = self.current_display.rows[0]
        if "O" in quarter:
            if slc := trowitm.row_item.row_frame.vis_slice:
                if not slc[1]:
                    cnt_cur = trowitm.row_item.row.data_cache.len_content
                else:
                    cnt_cur = trowitm.row_item.row.cursors.tool_vis_to_cnt(slc[1])
            else:
                cnt_cur = trowitm.row_item.row.data_cache.len_content
        elif "E" in quarter:
            if slc := trowitm.row_item.row_frame.vis_slice:
                cnt_cur = trowitm.row_item.row.cursors.tool_vis_to_cnt(slc[0])
            else:
                cnt_cur = trowitm.row_item.row.data_cache.len_content
        else:
            cnt_cur = min(cnt_cur, trowitm.row_item.row.data_cache.len_content)
        return DisplayCoordTarget(self, trowitm, trowitm.row_item.row, cnt_cur, False, False)

    @overload
    def display_coord_target(
            self,
            vis_coord: tuple[int, int],
            quarter: Literal["N", "O", "S", "E", "NO", "NE", "SO", "SE"] = "",
            quarter_focus: bool = False,
            quarter_border_focus: bool = False,
            column_rel_to_: Literal["display", "d", "origin", "o"] | None = "display",
            as_far: bool = True,
    ) -> DisplayCoordTarget:
        ...

    @overload
    def display_coord_target(
            self,
            vis_coord: tuple[int, int],
            *,
            column_rel_to_: Literal["display", "d", "origin", "o"] | None = "display",
            as_far: bool = True,
    ) -> DisplayCoordTarget:
        ...

    def display_coord_target(
            self,
            vis_coord: tuple[int, int],
            quarter: Literal["N", "O", "S", "E", "NO", "NE", "SO", "SE"] = "",
            quarter_focus: bool = False,
            quarter_border_focus: bool = False,
            column_rel_to_: Literal["display", "d", "origin", "o"] | None = "display",
            as_far: bool = True,
    ) -> DisplayCoordTarget:
        """
        Create a :class:`DisplayCoordTarget` that points to the visual coordinate (`vis_coord`) in the display.

        If `quarter` contains a cardinal direction, the coordinate in `vis_coord` of the associated axis is understood
        as the distance to the shown buffer. `vis_coord` is formulated as ``(<x>, <y>)``.

        Example:
        If `area` is ``"E"``, the x coordinate is understood as the distance to the left edge of the
        shown area; the y coordinate then describes an actual row number of the displayed area.
        If `area` is ``"NO"``, both the x and the y coordinate are understood as a distance specification.

        If a cardinal direction is set (`quarter`), the parameters `quarter_focus` and `quarter_border_focus` are
        evaluated:
        If `quarter_focus` is True, only the axis(es) of `vis_coord` that belongs to the cardinal direction is
        evaluated and the current position of the remaining axis is kept.
        If `quarter_border_focus` is True, before the evaluation of `quarter_focus` the DisplayCoordTarget is
        calculated starting from the edge on the side of the cardinal direction of the display.

        Example:

        >>>        ┌─<Widget>──────┐
        ... <row0> │               │
        ... <row1> │            █  │   # Cursor (x = 12, y = 1)
        ... <row2> │               │
        ... <row3> │               │
        ...        └───────────────┘
        >>> display_coord_target(vis_coord=(2, 1), quarter="S", quarter_focus=True, quarter_border_focus=True)
        ...        ┌─<Widget>──────┐
        ... <row1> │               │
        ... <row2> │               │
        ... <row3> │               │
        ... <row4> │            █  │   # Cursor (x = 12, y = 4)
        ...        └───────────────┘

        By default, DisplayCoordTarget is calculated in conjunction with the visual coordinate (`vis_coord`) starting 
        from the visual display (`column_rel_to_`\\ ``="display"``). If this parameter is set to ``origin``, the 
        coordinates are calculated from the original position.
        
        Example:

        >>>        ┌─<Widget>──────┐
        ... <row0> │0123456789ABCD>│
        ... <row1> │<CDEFGHIJKL█NO>│   # Cursor (x = 22, y = 1)
        ... <row2> │0123456789ABCD>│
        ... <row3> │0123456789ABCD>│
        ...        └───────────────┘
        >>> display_coord_target(vis_coord=(2, 2), column_rel_to_="origin")
        ...        ┌─<Widget>──────┐
        ... <row0> │0123456789ABCD>│
        ... <row1> │0123456789ABCD>│
        ... <row2> │<CDEFGHIJKLMN█>│   # Cursor (x = 24, y = 2)
        ... <row3> │0123456789ABCD>│
        ...        └───────────────┘
        >>> display_coord_target(vis_coord=(2, 1), column_rel_to_="display")
        ...        ┌─<Widget>──────┐
        ... <row0> │0123456789ABCD>│
        ... <row1> │01█3456789ABCD>│   # Cursor (x = 2, y = 1)
        ... <row2> │0123456789ABCD>│
        ... <row3> │0123456789ABCD>│
        ...        └───────────────┘

        If a visual coordinate cannot be reached due to the data in the buffer, the closest possible point in the data
        is selected by default. If the parameter `as_far` is set to False, an error is raised instead.
        """
        if as_far:
            def _raise(_e):
                pass
        else:
            def _raise(_e):
                raise _e

        x_as_far = False
        y_as_far = False

        if quarter:

            trowitm: None | DisplayRowItem
            _orowitm = trowitm = self.current_display_row
            _row = trowitm.row_item.row
            cnt_cur = trowitm.row_item.row.cursors.content
            vis_cur = trowitm.row_item.row.cursors.visual

            if quarter_border_focus:
                if "S" in quarter:
                    try:
                        _row = self.__buffer__.rows[self.current_display.rows[-1].row_item.row.__row_index__ + vis_coord[1]]
                    except IndexError as e:
                        _raise(e)
                        _row = self.__buffer__.rows[-1]
                        y_as_far = True
                    trowitm = None
                elif "N" in quarter:
                    try:
                        _row = self.__buffer__.rows[self.current_display.rows[0].row_item.row.__row_index__ - vis_coord[1]]
                    except IndexError as e:
                        _raise(e)
                        _row = self.__buffer__.rows[0]
                        y_as_far = True
                    trowitm = None
                elif not quarter_focus:
                    try:
                        trowitm = self.current_display.rows[vis_coord[1]]
                        _row = trowitm.row_item.row
                    except IndexError as e:
                        _raise(e)
                        y_as_far = True
                try:
                    tri = trowitm or _orowitm
                    if "O" in quarter:
                        if slc := tri.row_item.row_frame.vis_slice:
                            if not slc[1]:
                                cnt_cur = tri.row_item.row.data_cache.len_content
                            else:
                                cnt_cur = _row.cursors.tool_vis_to_cnt(slc[1] - 1 + vis_coord[0])
                        else:
                            cnt_cur = tri.row_item.row.data_cache.len_content
                    elif "E" in quarter:
                        if slc := tri.row_item.row_frame.vis_slice:
                            cnt_cur = _row.cursors.tool_vis_to_cnt(max(0, slc[0] - vis_coord[0]))
                        else:
                            cnt_cur = tri.row_item.row.data_cache.len_content
                    elif quarter_focus:
                        cnt_cur = min(cnt_cur, _row.cursors.content)
                    elif column_rel_to_:
                        if column_rel_to_[0] == "o" or trowitm is None:
                            if not (slc := _orowitm.row_item.row_frame.vis_slice):
                                raise IndexError
                            cnt_cur = _row.cursors.tool_vis_to_cnt(slc[0] + vis_coord[0] - _orowitm.row_item.row_frame.len_l_prompts)
                        elif not (slc := trowitm.row_item.row_frame.vis_slice):
                            raise IndexError
                        else:
                            cnt_cur = _row.cursors.tool_vis_to_cnt(slc[0] + vis_coord[0] - trowitm.row_item.row_frame.len_l_prompts)
                    else:
                        cnt_cur = _row.cursors.tool_vis_to_cnt(vis_coord[0])
                except IndexError as e:
                    _raise(e)
                    x_as_far = True
            else:
                if "S" in quarter:
                    try:
                        _row = self.__buffer__.rows[_orowitm.row_item.row.__row_index__ + vis_coord[1]]
                    except IndexError as e:
                        _raise(e)
                        _row = self.__buffer__.rows[-1]
                        y_as_far = True
                    trowitm = None
                elif "N" in quarter:
                    try:
                        _row = self.__buffer__.rows[_orowitm.row_item.row.__row_index__ - vis_coord[1]]
                    except IndexError as e:
                        _raise(e)
                        _row = self.__buffer__.rows[0]
                        y_as_far = True
                    trowitm = None
                elif not quarter_focus:
                    try:
                        _orowitm = trowitm = self.current_display.rows[vis_coord[1]]
                        _row = trowitm.row_item.row
                    except IndexError as e:
                        _raise(e)
                        y_as_far = True
                if "O" in quarter:
                    try:
                        cnt_cur = _row.cursors.tool_vis_to_cnt(vis_cur + vis_coord[0])
                    except IndexError as e:
                        _raise(e)
                        cnt_cur = _row.data_cache.len_content
                        x_as_far = True
                elif "E" in quarter:
                    try:
                        if (vc := vis_cur - vis_coord[0]) < 0:
                            raise IndexError
                        cnt_cur = _row.cursors.tool_vis_to_cnt(vc)
                    except IndexError as e:
                        _raise(e)
                        cnt_cur = 0
                        x_as_far = True
                elif quarter_focus:
                    cnt_cur = min(cnt_cur, _row.cursors.content)
                else:
                    try:
                        if column_rel_to_:
                            if column_rel_to_[0] == "o" or trowitm is None:
                                if not (slc := _orowitm.row_item.row_frame.vis_slice):
                                    raise IndexError
                                cnt_cur = _row.cursors.tool_vis_to_cnt(slc[0] + vis_coord[0] - _orowitm.row_item.row_frame.len_l_prompts)
                            elif not (slc := trowitm.row_item.row_frame.vis_slice):
                                raise IndexError
                            else:
                                cnt_cur = _row.cursors.tool_vis_to_cnt(slc[0] + vis_coord[0] - trowitm.row_item.row_frame.len_l_prompts)
                        else:
                            cnt_cur = _row.cursors.tool_vis_to_cnt(vis_coord[0])
                    except IndexError as e:
                        _raise(e)
                        x_as_far = True

            return DisplayCoordTarget(self, trowitm, _row, cnt_cur, x_as_far, y_as_far)

        else:

            try:
                trowitm = self.current_display.rows[vis_coord[1]]
            except IndexError as e:
                _raise(e)
                trowitm = self.current_display.rows[-1]
                y_as_far = True
            try:
                if column_rel_to_:
                    if column_rel_to_[0] == "o":
                        _row_item = self.current_display_row.row_item
                    else:
                        _row_item = trowitm.row_item
                    if not (slc := _row_item.row_frame.vis_slice):
                        raise IndexError
                    else:
                        cnt_cur = trowitm.row_item.row.cursors.tool_vis_to_cnt(slc[0] + (vis_coord[0] - trowitm.row_item.row_frame.len_l_prompts))
                else:
                    cnt_cur = trowitm.row_item.row.cursors.tool_vis_to_cnt(
                        vis_coord[0] - trowitm.row_item.row_frame.len_l_prompts)
            except IndexError as e:
                _raise(e)
                cnt_cur = trowitm.row_item.row.data_cache.len_content
                x_as_far = True

            return DisplayCoordTarget(self, trowitm, trowitm.row_item.row, cnt_cur, x_as_far, y_as_far)

    def display_coord_target_by_vrt(
            self,
            vrt: VisualRealTarget,
            quarter_focus: bool = False,
            quarter_border_focus: bool = False,
            column_rel_to_: Literal["display", "d", "origin", "o"] | None = "display",
            as_far: bool = True,
    ) -> DisplayCoordTarget:
        """
        Shortcut method to method ``display_coord_target`` for processing :class:`VisualRealTarget`.
        """
        return self.display_coord_target(vrt.area_coord, vrt.outer_quarter, quarter_focus, quarter_border_focus, column_rel_to_, as_far)


class DisplayBrowsable(_DisplayBase):
    """
    The completed display type for browsable display of :class:`TextBuffer` data.

    >>> # |- - - - - - - -  displayed area   - - - - - - - - - - - - - - - - - - - - - - - - - - - - -|
    >>> # |                                                                                           |
    >>> # |his is the content of a row  and is scrolled by the size of a defined area when passing█the|edge of the displayed area, the lapping indicates how many characters from the previous area are visible at the left edge.
    >>>
    >>> #                                                                                         |- - - - - - - -  displayed area   - - - - - - - - - - - - - - - - - - - - - - - - - - - - -|
    >>> #                                                                                         |                                                                                           |
    >>> # This is the content of a row  and is scrolled by the size of a defined area when passing|the█edge of the displayed area, the lapping indicates how many characters from the previous|area are visible at the left edge.

    Parameters and settings in addition to the basic ones of the :class:`_DisplayBase`:

        - `width`
            The total width of the display.
            The space reserved for prompts is subtracted for the display of the row data.

        - `prompt_factory`
            A factory to create the right and left prompt at the edge of the displayed area.
            Receives the :class:`_Row` object and the type of the displayed area when queried, and must return the
            prompts as :class:`EscSegment` or :class:`EscContainer` type.

            Types of a displayed area:
                - ``0`` ( Basic area )
                    The characters of the row do not span the size of the displayed area.
                - ``1`` ( First area )
                    The number of characters in the row is larger than the space in the display
                    and the area at the left end is displayed.
                - ``2`` ( Middle area )
                    ... and neither the area at the left end nor the area at the right end is displayed.
                - ``3`` ( Last area )
                    ... and the area at the right end is displayed.
                - ``4`` ( Out of range )
                    Occurs only when the visual representation of remaining rows follows the cursor in
                    parallel even beyond the data limits of a row (see parameter `stdcurpos`).

            >>> prompt_factory=lambda row, dispt: (EscSegment("%-4s|" % row.__row_num__), EscSegment("|%-4s" % (row.cursors.content if row.inrow() else "")))

        - `promptl_len`
            The reserved area for the prompt on the left side of the display, 
            the prompt from the query through `prompt_factory` must have this length.

        - `promptr_len`
            The reserved area for the prompt on the right side of the display,
            the prompt from the query through `prompt_factory` must have this length.

        - `lapping`
            This number of characters of the previous area will be displayed in the next part
            after passing the displayed area of a row.

        - `vis_overflow`
            Characters to represent the overspan of the displayed area by row data.

            ``(
            <overspan on the left side>,
            <overspan on the right side>,
            <wide overspan on the left side -- only relevant if the rows follows the cursor in
            parallel even beyond the data limits of a row (see parameter`` `stdcurpos`\\ ``)>
            )``

            >>> vis_overflow=("<", ">", "<<")

        - `width_min_char`
            This character is displayed multiplied by the remaining width if the minimum width
            is not reached. The minimum width consists of the prompt lengths, the lapping and
            the characters for the displayed overflow.
    """

    _width: int
    _cont_width: int
    _vis_overflow: Sequence[str, str, str]
    _overflow_space: tuple[int, int, int]
    _lapping: int
    _prompt_factory: Callable[
        [
            _Row,
            Literal[0, 1, 2, 3, 4]
        ], Sequence[EscSegment | EscContainer, EscSegment | EscContainer]]
    _promptl_len: int
    _promptr_len: int

    _basic_part_area: int
    _first_part_area: int
    _middle_part_area: int
    _last_part_area: int
    _basic_part_f: EscSegment | EscContainer
    _first_part_f: EscSegment | EscContainer
    _middle_part_f: EscSegment | EscContainer
    _last_part_f: EscSegment | EscContainer
    _outofran_f: EscSegment | EscContainer

    _basic_llp: int
    _overflow_llp: int
    _outofran_llp: int
    _basic_lrp: int
    _overflow_lrp: int

    _width_min: int
    _width_min_char: EscSegment | EscContainer
    _make_row_frame_: Callable[[_Row, int], RowFrameItem]

    x_minimum_size_undercut: bool

    _pointer_start_ovf: int
    _pointer_start_oor: int

    __slots__ = ('_width', '_cont_width', '_vis_overflow', '_overflow_space', '_lapping', '_prompt_factory',
                 '_promptl_len', '_promptr_len', '_basic_part_area', '_first_part_area', '_middle_part_area',
                 '_last_part_area', '_basic_part_f', '_first_part_f', '_middle_part_f', '_last_part_f', '_outofran_f',
                 '_basic_llp', '_overflow_llp', '_outofran_llp', '_basic_lrp', '_overflow_lrp', '_width_min',
                 '_width_min_char', '_make_row_frame_', 'x_minimum_size_undercut', '_pointer_start_ovf',
                 '_pointer_start_oor')

    def __init__(self,
                 __buffer__: TextBuffer,
                 width: int,
                 height: int,
                 y_auto_scroll_distance: int,
                 prompt_factory: Callable[[_Row, Literal[0, 1, 2, 3, 4]],
                                          Sequence[EscSegment | EscContainer, EscSegment | EscContainer]],
                 promptl_len: int,
                 promptr_len: int,
                 lapping: int,
                 vis_overflow: Sequence[str, str, str],
                 width_min_char: EscSegment | EscContainer,
                 highlighter: Literal["regex", "r", "advanced", "a"] | None,
                 highlighted_rows_cache_max: int | None,
                 highlighted_row_segments_max: int | None,
                 vis_tab: Callable[[int], str] | None,
                 vis_marked: Sequence[Callable[[str, VisRowItem, list[int, int]], str],
                                      Callable[[str, VisRowItem, list[int, int]], str]] | None,
                 vis_end: Sequence[str | None, str | None, str | None] | None,
                 vis_nb_end: Sequence[str | None, str | None, str | None] | None,
                 visendpos: Literal["data", "d", "data f", "df", "visN1", "v", "v1"],
                 vis_cursor: Callable[[str, VisRowItem], str] | None,
                 vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str] | None,
                 vis_cursor_row: Callable[[str, VisRowItem], str] | None,
                 stdcurpos: int | Literal["follow", "f", "parallel", "p", "end", "e"],
                 i_rowitem_generator: Callable[[VisRowItem], Any] | None,
                 i_display_generator: Callable[[DisplayRowItem], Any] | None,
                 i_before_framing: Callable[[str, VisRowItem], str] | None
                 ):
        _DisplayBase.__init__(self, __buffer__, height, y_auto_scroll_distance, highlighter,
                              highlighted_rows_cache_max, highlighted_row_segments_max, vis_tab,
                              vis_marked, vis_end, vis_nb_end, visendpos, vis_cursor, vis_anchor, vis_cursor_row,
                              stdcurpos, i_rowitem_generator, i_display_generator, i_before_framing)
        self.settings(width=width, vis_overflow=vis_overflow, width_min_char=width_min_char, lapping=lapping,
                      promptl_len=promptl_len, promptr_len=promptr_len, prompt_factory=prompt_factory)

    @overload
    def settings(self, *,
                 width: int = ...,
                 height: int = ...,
                 y_auto_scroll_distance: int = ...,
                 lapping: int = ...,
                 prompt_factory: Callable[[_Row, Literal[0, 1, 2, 3, 4]],
                                          Sequence[EscSegment | EscContainer, EscSegment | EscContainer]] = ...,
                 promptl_len: int = ...,
                 promptr_len: int = ...,
                 vis_overflow: Sequence[str, str, str] = ...,
                 width_min_char: EscSegment | EscContainer = ...,
                 vis_marked: tuple[Callable[[str, VisRowItem, list[int, int]], str],
                                   Callable[[str, VisRowItem, list[int, int]], str]] | None = ...,
                 vis_end: Sequence[str | None, str | None, str | None] | None = ...,
                 vis_nb_end: Sequence[str | None, str | None, str | None] | None = ...,
                 visendpos: Literal["data", "d", "data f", "df", "visN1", "v", "v1"] = ...,
                 vis_cursor: Callable[[str, VisRowItem], str] | None = ...,
                 vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str] | None = ...,
                 vis_cursor_row: Callable[[str, VisRowItem], str] | None = ...,
                 highlighter: Literal["regex", "r", "advanced", "a"] | None = ...,
                 highlighted_rows_cache_max: int | None = ...,
                 highlighted_row_segments_max: int | None = ...,
                 vis_tab: Callable[[str], str] | None = ...,
                 stdcurpos: int | Literal["follow", "f", "parallel", "p", "end", "e"] = ...,
                 i_rowitem_generator: Callable[[VisRowItem], Any] | None = ...,
                 i_display_generator: Callable[[DisplayRowItem], Any] | None = ...,
                 i_before_framing: Callable[[str, VisRowItem], str] | None = ...
                 ) -> None:
        ...

    def settings(self, **kwargs) -> None:
        """
        Change the :class:`_DisplayBase` | :class:`DisplayBrowsable` | :class:`DisplayScrollable` settings.
        """

        newsize = False
        for attr in ('width', 'lapping', 'vis_overflow', 'promptl_len', 'promptr_len'):
            try:
                setattr(self, '_' + attr, kwargs.pop(attr))
                newsize = True
            except KeyError:
                pass

        for attr in ('prompt_factory', 'width_min_char',):
            try:
                setattr(self, '_' + attr, kwargs.pop(attr))
            except KeyError:
                pass

        if newsize:
            self._cont_width = self._width - (self._promptl_len + self._promptr_len)
            self._overflow_space = (len(self._vis_overflow[0]), len(self._vis_overflow[1]), len(self._vis_overflow[2]))
            self._basic_part_area = self._cont_width - 1  # cursor
            self._first_part_area = self._cont_width - self._overflow_space[1]
            _middle_part_width = self._cont_width - (self._overflow_space[0] + self._overflow_space[1])
            self._middle_part_area = _middle_part_width - self._lapping
            _last_part_width = self._cont_width - self._overflow_space[0]
            self._last_part_area = _last_part_width - (1  # cursor
                                                       + self._lapping)
            self._basic_part_f = EscSegment.new('', '%%-%ds' % self._cont_width, SGRReset())
            self._first_part_f = EscContainer.more('%%-%ds' % self._first_part_area,
                                                   SGRReset(),
                                                   self._vis_overflow[1])
            self._middle_part_f = EscContainer.more(self._vis_overflow[0],
                                                    '%%-%ds' % _middle_part_width,
                                                    SGRReset(),
                                                    self._vis_overflow[1])
            self._last_part_f = EscContainer.more(self._vis_overflow[0],
                                                  '%%-%ds' % _last_part_width,
                                                  SGRReset())
            self._outofran_f = EscContainer.more(self._vis_overflow[2],
                                                 '%%-%ds' % (self._cont_width - self._overflow_space[2]),
                                                 SGRReset())
            self._pointer_start_ovf = self._promptl_len + self._overflow_space[0] + self._lapping
            self._pointer_start_oor = self._promptl_len + self._overflow_space[2]

            self._width_min = (self._promptl_len + self._promptr_len +
                               max(self._lapping + self._overflow_space[0] + self._overflow_space[1],
                                   self._overflow_space[2]))
            self._basic_llp = self._promptl_len
            self._overflow_llp = self._promptl_len + self._overflow_space[0]
            self._outofran_llp = self._promptl_len + self._overflow_space[2]
            self._basic_lrp = self._promptr_len
            self._overflow_lrp = self._promptr_len + self._overflow_space[1]
            if self._width <= self._width_min:
                def make_row_frame(row: _Row, vis_cursor: int) -> RowFrameItem:
                    return RowFrameItem(
                        display_pointer=0,
                        part_cursor=0,
                        vis_slice=(0, 0),
                        len_l_prompts=0,
                        len_r_prompts=0,
                        content_width=0,
                        part_id=4,
                        part_form=EscSegment("%s"),
                        lr_prompt=(self._width_min_char * self._width, EscSegment(""))
                    )
                self._make_row_frame_ = make_row_frame
                self.x_minimum_size_undercut = True
            else:
                self._make_row_frame_ = self._make_row_frame
                self.x_minimum_size_undercut = False

        super().settings(**kwargs)

    def scroll_x(self, z: int, mark: bool) -> bool:
        """
        Move the cursor in the :class:`TextBuffer` by display part(s) on the x-axis.
        """
        currow = self.__buffer__.current_row
        if currow.data_cache.len_visual_incl <= self._basic_part_area:
            return False
        else:
            cursor = currow.cursors.visual
            self.__buffer__.__marker__.ready(mark)
            _curset = False
            try:
                if cursor < self._first_part_area:
                    if z > 0:
                        _curset = self.__buffer__.cursor_set(
                            self.__buffer__.current_row_idx,
                            currow.cursors.tool_vis_to_cnt(self._first_part_area + self._middle_part_area * (z - 1)),
                            as_far=True)
                else:
                    a = cursor - ((cursor - self._first_part_area) % self._middle_part_area)
                    _curset = self.__buffer__.cursor_set(
                        self.__buffer__.current_row_idx,
                        currow.cursors.tool_vis_to_cnt(max(0, a + self._middle_part_area * z)),
                        as_far=True)
            except IndexError:
                pass
            self.__buffer__.__marker__.set_current(mark)
            return _curset

    def make_row_frame(self, row: _Row, vis_cursor: int) -> RowFrameItem:
        """
        The characteristic row-framing method for completing :class:`_DisplayBase`.
        """
        return self._make_row_frame_(row, vis_cursor)

    def _make_row_frame(self, row: _Row, vis_cursor: int) -> RowFrameItem:
        """
        The characteristic row-framing method for completing :class:`_DisplayBase`.
        """

        lenrow = row.data_cache.len_visual_incl

        if lenrow <= self._basic_part_area:
            if vis_cursor > self._basic_part_area:
                return RowFrameItem(
                    display_pointer=self._pointer_start_oor,
                    part_cursor=vis_cursor,
                    vis_slice=None,
                    len_l_prompts=self._outofran_llp,
                    len_r_prompts=self._basic_lrp,
                    content_width=0,
                    part_id=4,
                    part_form=self._outofran_f,
                    lr_prompt=self._prompt_factory(row, 4)
                )
            else:
                return RowFrameItem(
                    display_pointer=self._promptl_len + vis_cursor,
                    part_cursor=vis_cursor,
                    vis_slice=(0, None),  # slice(stop=None) identifier for visual end
                    len_l_prompts=self._basic_llp,
                    len_r_prompts=self._basic_lrp,
                    content_width=self._basic_part_area,
                    part_id=0,
                    part_form=self._basic_part_f,
                    lr_prompt=self._prompt_factory(row, 0)
                )
        elif vis_cursor < self._first_part_area:
            return RowFrameItem(
                display_pointer=self._promptl_len + vis_cursor,
                part_cursor=vis_cursor,
                vis_slice=(0, self._first_part_area),
                len_l_prompts=self._basic_llp,
                len_r_prompts=self._overflow_lrp,
                content_width=self._first_part_area,
                part_id=1,
                part_form=self._first_part_f,
                lr_prompt=self._prompt_factory(row, 1)
            )
        else:

            frame_pnt = (vis_cursor - self._first_part_area) % self._middle_part_area
            visslc_start = vis_cursor - frame_pnt
            visslc_stop = visslc_start + self._middle_part_area

            if visslc_start > lenrow:
                return RowFrameItem(
                    display_pointer=self._pointer_start_oor,
                    part_cursor=vis_cursor,
                    vis_slice=None,
                    len_l_prompts=self._outofran_llp,
                    len_r_prompts=self._basic_lrp,
                    content_width=0,
                    part_id=4,
                    part_form=self._outofran_f,
                    lr_prompt=self._prompt_factory(row, 4)
                )

            elif visslc_stop >= lenrow:
                if lenrow - (_s := visslc_start - self._middle_part_area) <= self._last_part_area:
                    visslc_start = _s
                    frame_pnt += self._middle_part_area
                return RowFrameItem(
                    display_pointer=self._pointer_start_ovf + frame_pnt,
                    part_cursor=frame_pnt,
                    vis_slice=(visslc_start - self._lapping, None),
                    len_l_prompts=self._overflow_llp,
                    len_r_prompts=self._basic_lrp,
                    content_width=self._last_part_area,
                    part_id=3,
                    part_form=self._last_part_f,
                    lr_prompt=self._prompt_factory(row, 3)
                )
            else:
                return RowFrameItem(
                    display_pointer=self._pointer_start_ovf + frame_pnt,
                    part_cursor=frame_pnt,
                    vis_slice=(visslc_start - self._lapping, visslc_stop),
                    len_l_prompts=self._overflow_llp,
                    len_r_prompts=self._overflow_lrp,
                    content_width=self._middle_part_area,
                    part_id=2,
                    part_form=self._middle_part_f,
                    lr_prompt=self._prompt_factory(row, 2)
                )


class DisplayScrollable(DisplayBrowsable):
    """
    A derivative of the :class:`DisplayBrowsable` to represent the display as scrolling text.

    >>> # |- - - - - - - -  displayed area   - - - - - - - - - - - - - - - - - - - - - - - - - - - - -|
    >>> # |                                                                                           |
    >>> # |his is the content of a row, which█is successively scrolled when the lapping is passed. The|cursor then remains at the visual position of the lapping (scrolling text).
    >>>
    >>> #  |- - - - - - - -  displayed area   - - - - - - - - - - - - - - - - - - - - - - - - - - - - -|
    >>> #  |                                                                                           |
    >>> # T|is is the content of a row, which █s successively scrolled when the lapping is passed. The |ursor then remains at the visual position of the lapping (scrolling text).
    >>>
    >>> #   |- - - - - - - -  displayed area   - - - - - - - - - - - - - - - - - - - - - - - - - - - - -|
    >>> #   |                                                                                           |
    >>> # Th|s is the content of a row, which i█ successively scrolled when the lapping is passed. The c|rsor then remains at the visual position of the lapping (scrolling text).

    The parameter `lapping` specifies in this type from which character, counted from the left side of the display,
    the visual text scrolling is triggered.
    """

    def _make_row_frame(self, row: _Row, vis_cursor: int) -> RowFrameItem:
        """
        The characteristic row-framing method for completing :class:`_DisplayBase`.
        """

        lenrow = row.data_cache.len_visual_incl

        if lenrow <= self._basic_part_area:
            if vis_cursor > self._basic_part_area or vis_cursor > lenrow:
                return RowFrameItem(
                    display_pointer=self._pointer_start_oor,
                    part_cursor=vis_cursor,
                    vis_slice=None,
                    len_l_prompts=self._outofran_llp,
                    len_r_prompts=self._basic_lrp,
                    content_width=0,
                    part_id=4,
                    part_form=self._outofran_f,
                    lr_prompt=self._prompt_factory(row, 4)
                )
            elif vis_cursor <= self._lapping:
                return RowFrameItem(
                    display_pointer=self._promptl_len + vis_cursor,
                    part_cursor=vis_cursor,
                    vis_slice=(0, None),  # slice(stop=None) identifier for visual end
                    len_l_prompts=self._basic_llp,
                    len_r_prompts=self._basic_lrp,
                    content_width=self._basic_part_area,
                    part_id=0,
                    part_form=self._basic_part_f,
                    lr_prompt=self._prompt_factory(row, 0)
                )
            else:
                return RowFrameItem(
                    display_pointer=self._pointer_start_ovf,
                    part_cursor=self._lapping,
                    vis_slice=(vis_cursor - self._lapping, None),  # slice(stop=None) identifier for visual end
                    len_l_prompts=self._overflow_llp,
                    len_r_prompts=self._basic_lrp,
                    content_width=self._last_part_area,
                    part_id=3,
                    part_form=self._last_part_f,
                    lr_prompt=self._prompt_factory(row, 3)
                )
        elif vis_cursor < self._first_part_area and vis_cursor <= self._lapping:
            return RowFrameItem(
                display_pointer=self._promptl_len + vis_cursor,
                part_cursor=vis_cursor,
                vis_slice=(0, self._first_part_area),
                len_l_prompts=self._basic_llp,
                len_r_prompts=self._overflow_lrp,
                content_width=self._first_part_area,
                part_id=1,
                part_form=self._first_part_f,
                lr_prompt=self._prompt_factory(row, 1)
            )
        elif (visslc_start := vis_cursor - self._lapping) > lenrow:
            return RowFrameItem(
                display_pointer=self._pointer_start_oor,
                part_cursor=vis_cursor,
                vis_slice=None,
                len_l_prompts=self._outofran_llp,
                len_r_prompts=self._basic_lrp,
                content_width=0,
                part_id=4,
                part_form=self._outofran_f,
                lr_prompt=self._prompt_factory(row, 4)
            )
        elif vis_cursor + self._last_part_area >= lenrow:
            return RowFrameItem(
                display_pointer=self._pointer_start_ovf,
                part_cursor=self._lapping,
                vis_slice=(visslc_start, None),  # slice(stop=None) identifier for visual end
                len_l_prompts=self._overflow_llp,
                len_r_prompts=self._basic_lrp,
                content_width=self._last_part_area,
                part_id=3,
                part_form=self._last_part_f,
                lr_prompt=self._prompt_factory(row, 3)
            )
        else:
            return RowFrameItem(
                display_pointer=self._pointer_start_ovf,
                part_cursor=self._lapping,
                vis_slice=(visslc_start, vis_cursor + self._middle_part_area),
                len_l_prompts=self._overflow_llp,
                len_r_prompts=self._overflow_lrp,
                content_width=self._middle_part_area,
                part_id=2,
                part_form=self._middle_part_f,
                lr_prompt=self._prompt_factory(row, 2)
            )


class DisplayStatic(_DisplayBase):
    """
    The completed display type for the restricted bounding display of :class:`TextBuffer` data.
    This display does not allow to limit the width of the visual representation of the data over this component.

    Apart from the parameters and settings of the :class:`_DisplayBase`, this display type has only one other feature:

        - `prompt_factory`
                A factory to create the right and left prompt at the edge of the displayed area.
                Receives the :class:`_Row` object when queried, and must return the
                prompts as :class:`EscSegment` or :class:`EscContainer` type.

            >>> prompt_factory=lambda row: (EscSegment("%-4s|" % row.__row_num__), EscSegment("|%-4s" % (row.cursors.content if row.inrow() else "")))
    """
    
    _prompt_factory: Callable[[_Row], Sequence[EscSegment | EscContainer, EscSegment | EscContainer]]

    __slots__ = ('_prompt_factory',)

    def __init__(self,
                 __buffer__: TextBuffer,
                 height: int,
                 y_auto_scroll_distance: int,
                 highlighter: Literal["regex", "r", "advanced", "a"] | None,
                 highlighted_rows_cache_max: int | None,
                 highlighted_row_segments_max: int | None,
                 vis_tab: Callable[[int], str] | None,
                 prompt_factory: Callable[[_Row], Sequence[EscSegment | EscContainer, EscSegment | EscContainer]],
                 vis_marked: Sequence[Callable[[str, VisRowItem, list[int, int]], str],
                                      Callable[[str, VisRowItem, list[int, int]], str]] | None,
                 vis_end: Sequence[str | None, str | None, str | None] | None,
                 vis_nb_end: Sequence[str | None, str | None, str | None] | None,
                 visendpos: Literal["data", "d", "data f", "df", "visN1", "v", "v1"],
                 vis_cursor: Callable[[str, VisRowItem], str] | None,
                 vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str] | None,
                 vis_cursor_row: Callable[[str, VisRowItem], str] | None,
                 i_rowitem_generator: Callable[[VisRowItem], Any] | None,
                 i_display_generator: Callable[[DisplayRowItem], Any] | None,
                 i_before_framing: Callable[[str, VisRowItem], str] | None
                 ):

        _DisplayBase.__init__(self, __buffer__, height, y_auto_scroll_distance, highlighter,
                              highlighted_rows_cache_max, highlighted_row_segments_max, vis_tab, vis_marked,
                              vis_end, vis_nb_end, visendpos, vis_cursor, vis_anchor, vis_cursor_row, 0,
                              i_rowitem_generator, i_display_generator, i_before_framing)
        self.settings(prompt_factory=prompt_factory)

    @overload
    def settings(self, *,
                 height: int = ...,
                 y_auto_scroll_distance: int = ...,
                 prompt_factory: Callable[[_Row], Sequence[EscSegment | EscContainer, EscSegment | EscContainer]] = ...,
                 vis_marked: tuple[Callable[[str, VisRowItem, list[int, int]], str],
                                   Callable[[str, VisRowItem, list[int, int]], str]] | None = ...,
                 vis_end: Sequence[str | None, str | None, str | None] | None = ...,
                 vis_nb_end: Sequence[str | None, str | None, str | None] | None = ...,
                 visendpos: Literal["data", "d", "data f", "df", "visN1", "v", "v1"] = ...,
                 vis_cursor: Callable[[str, VisRowItem], str] | None = ...,
                 vis_anchor: Callable[[str, VisRowItem, tuple[int | str, int]], str] | None = ...,
                 vis_cursor_row: Callable[[str, VisRowItem], str] | None = ...,
                 highlighter: Literal["regex", "r", "advanced", "a"] | None = ...,
                 highlighted_rows_cache_max: int | None = ...,
                 highlighted_row_segments_max: int | None = ...,
                 vis_tab: Callable[[str], str] | None = ...,
                 i_rowitem_generator: Callable[[VisRowItem], Any] | None = ...,
                 i_display_generator: Callable[[DisplayRowItem], Any] | None = ...,
                 i_before_framing: Callable[[str, VisRowItem], str] | None = ...
                 ) -> None:
        ...

    def settings(self, **kwargs) -> None:
        """
        Change the :class:`_DisplayBase` | :class:`DisplayStatic` settings.
        """
        super().settings(**kwargs)

    def scroll_x(self, z: int, mark: bool) -> bool:
        """:raises TypeError:"""
        raise TypeError

    def make_row_frame(self, row: _Row, vis_cursor: int) -> RowFrameItem:
        """
        The characteristic row-framing method for completing :class:`_DisplayBase`.
        """
        return RowFrameItem(display_pointer=(llp := len((prompt := self._prompt_factory(row))[0])) + vis_cursor,
                            part_cursor=vis_cursor,
                            vis_slice=(0, None),
                            len_l_prompts=llp,
                            len_r_prompts=len(prompt[1]),
                            content_width=-1,
                            part_id=1,
                            lr_prompt=prompt)
