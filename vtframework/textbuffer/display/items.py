# MIT License
#
# Copyright (c) 2022 Adrian F. Hoefflin [srccircumflex]
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

from typing import NamedTuple, Generator, Sequence

try:
    from .._buffercomponents.row import _Row
    from ...iodata.esccontainer import EscSegment, EscContainer
    from .._buffercomponents.marker import _Marker
    __4doc1 = _Marker
    from .._buffercomponents.globcursor import _GlobCursor
    __4doc2 = _GlobCursor
except ImportError:
    pass


class RowFrameItem(NamedTuple):
    """
    The first parameterization of a display row.

    - `display_pointer`: ``int``: relative x position of the cursor to the left display edge.
    - `part_cursor`: ``int``: relative x position of the cursor to the left frame edge.
    - `vis_slice`: ``tuple[int, int | None] | None``: visual slice for :class:`_Row`.
    - `part_form`: ``EscSegment | None``: Frame format.
    - `lr_prompt`: ``tuple[`` :class:`EscSegment` ``|`` :class:`EscContainer` ``, EscSegment | EscContainer ]``: left/right prompt.
    """
    display_pointer: int
    part_cursor: int
    vis_slice: tuple[int, int | None] | None
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
