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

from typing import NamedTuple, Generator, Sequence, Literal
from re import Pattern

try:
    from .._buffercomponents.row import _Row
    from ...iodata.esccontainer import EscSegment, EscContainer
    from .._buffercomponents.marker import _Marker
    __4doc1 = _Marker
    from .._buffercomponents.globcursor import _GlobCursor
    __4doc2 = _GlobCursor
    from .displays import _DisplayBase, DisplayScrollable, DisplayBrowsable, DisplayStatic
    __4doc3 = DisplayStatic
    __4doc4 = DisplayBrowsable
    __4doc5 = DisplayStatic
    from ..buffer import TextBuffer
    __4doc6 = TextBuffer
except ImportError:
    pass


class RowFrameItem(NamedTuple):
    """
    The first parameterization of a display row.

    - `display_pointer`: ``int``: relative x position of the cursor to the left display edge.
    - `part_cursor`: ``int``: relative x position of the cursor to the left frame edge.
    - `vis_slice`: ``tuple[int, int | None] | None``: visual slice for :class:`_Row`.
    - `len_l_prompts`: ``int``: sum of the space on the left side for prompt and overflow character.
    - `len_r_prompts`: ``int``: sum of the space on the right side for prompt and overflow character.
    - `content_width`: ``int``: the width of the shown content of the :class:`_Row`.
      Is always ``-1`` when using :class:`DisplayStatic`.
    - `part_id`: ``int``: the type designation of the area shown: 
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
    - `part_form`: ``EscSegment | None``: Frame format.
    - `lr_prompt`: ``tuple[`` :class:`EscSegment` ``|`` :class:`EscContainer` ``, EscSegment | EscContainer ]``: left/right prompt.
    """
    display_pointer: int
    part_cursor: int
    vis_slice: tuple[int, int | None] | None
    len_l_prompts: int
    len_r_prompts: int
    content_width: int
    part_id: Literal[0, 1, 2, 3, 4]
    part_form: EscSegment | None = None
    lr_prompt: Sequence[EscSegment | EscContainer, EscSegment | EscContainer] = ('', '')


class VisRowItem(NamedTuple):
    """
    Merging of :class:`RowFrameItem` parameterization and coordinates about tabs,
    marks (:class:`_Marker`) and anchors (:class:`_GlobCursor`).

    - `row`: :class:`_Row`
    - `tab_spaces`: ``tuple[int, ...]``
    - `v_marks`: ``list[tuple[list[int, int], tuple[int | None, int | None, int]]]``:
      [(<origin marking>, <inrow coordinates>), ...]
    - `v_anchors`: ``list[tuple[tuple[int | str, int], int]]``:
      [(<origin anchor>, <inrow coordinate>), ...]
    - `row_frame`: ``RowFrameItem``
    """
    row: _Row
    tab_spaces: tuple[int, ...]
    v_marks: list[tuple[list[int, int], tuple[int | None, int | None, int]]]
    v_anchors: list[tuple[tuple[int | str, int], int]]
    row_frame: RowFrameItem


class DisplayRowItem(NamedTuple):
    """
    The final display row and :class:`VisRowItem`.
    """
    display_row: EscSegment | EscContainer
    row_item: VisRowItem

    def __str__(self) -> EscSegment | EscContainer:
        return self.display_row


class DisplayItem(NamedTuple):
    """
    The display rows (list[:class:`DisplayRowItem`]) and relative cursor coordinates.
    """
    rows: list[DisplayRowItem]
    pointer_row: int
    pointer_column: int

    def __iter__(self) -> Generator[EscSegment | EscContainer]:
        return (r.__str__() for r in self.rows)


class DisplayCoordTarget(NamedTuple):
    """
    The translation of a visual coordinate to the :class:`_Row` (`row`) and the content data point
    (`cnt_cursor`). Includes a reference to the :class:`DisplayBrowsable` | :class:`DisplayScrollable` |
    :class:`DisplayStatic` object (`display`) and the :class:`DisplayRowItem` (`drow_item`) from the cache of the
    currently displayed area; can be ``None`` if the coordinate points to an area outside the display. `x_as_far` and
    `y_as_far` indicates whether the corresponding coordinate is the closest possible point.

    The item includes first methods for processing the item in the :class:`TextBuffer`:
        - ``set_cursor``
        - ``word_coord``
        - ``mark_word``
    """
    display: _DisplayBase
    drow_item: DisplayRowItem | None
    row: _Row
    cnt_cursor: int
    x_as_far: bool
    y_as_far: bool

    def set_cursor(self, mark: bool = False) -> bool:
        """
        Set the cursor to the position. Return whether the cursor was set.
        """
        try:
            self.display.__buffer__.__marker__.ready(mark)
            return self.display.__buffer__.cursor_set(self.row.__row_index__, self.cnt_cursor)
        finally:
            self.display.__buffer__.__marker__.set_current(mark)

    def word_coord(self, a_delimiter: str | Pattern, b_delimiter: str | Pattern = None) -> tuple[int, int]:
        """
        Return the data coordinate of the string pointed to ``(<data-start>, <data-stop>)``.
        Start and end of the word is defined by regex patterns `a_delimiter` and `b_delimiter`.
        If `b_delimiter` is ``None``, `b_delimiter` is equal to `a_delimiter`.
        """
        b = self.display.__buffer__
        cur = b.current_row.cursors.data_cursor
        self.set_cursor()
        if start := b.find(a_delimiter, reverse=True):
            start = start[0][0].__data_start__ + start[0][1].end()
        else:
            start = 0
        if stop := b.find(b_delimiter or a_delimiter):
            stop = stop[0][0].__data_start__ + stop[0][1].start()
        else:
            stop = b.__eof_data__
        b.goto_data(cur)
        return start, stop

    def mark_word(self, a_delimiter: str | Pattern, b_delimiter: str | Pattern = None) -> tuple[int, int]:
        """
        Create a marker on the string pointed to and return the data coordinate ``(<data-start>, <data-stop>)``.
        Start and end of the word is defined by regex patterns `a_delimiter` and `b_delimiter`.
        If `b_delimiter` is ``None``, `b_delimiter` is equal to `a_delimiter`.
        """
        b = self.display.__buffer__
        b.__marker__.stop()
        b.__marker__.add_marks(coord := self.word_coord(a_delimiter, b_delimiter))
        return coord

    def __eq__(self, other: DisplayCoordTarget) -> bool:
        """
        Return whether the :class:`_Row`'s and cursor positions of the items match.
        """
        return self.cnt_cursor == other.cnt_cursor and self.row == other.row
