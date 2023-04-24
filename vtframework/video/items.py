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

from __future__ import annotations

from typing import Literal, NamedTuple
from functools import lru_cache

try:
    from .grid import Cell, NullCell, Grid
    __4doc1 = Grid
except ImportError:
    pass


class VisualRealTarget(NamedTuple):
    """
    The object represents the point of a visual coordinate in the area of the widget of a :class:`Cell` or
    relative to it.

    If attribute ``outer_quarter`` is ``""``, attribute ``area_coord`` represents the coordinate within the widget of
    ``cell``.

    If attribute ``outer_quarter`` is a cardinal direction, the corresponding axis of ``area_coord`` represents the
    distance to the edge of the widget of ``cell``.

    Examples:

        >>> VisualRealTarget(cell=cell, outer_quarter="", area_coord=(1, 3))
        ... ┌──<Cell>─────────────┐
        ... │\\ NNNNNNNNNNNNNNNNN /│
        ... │ \\nnnnnnnnnnnnnnnnn/ │
        ... │Ee┌─<Widget>──────┐oO│
        ... │Ee│               │oO│
        ... │Ee│   ×           │oO│
        ... │Ee│               │oO│
        ... │Ee│               │oO│
        ... │Ee└───────────────┘oO│
        ... │ /sssssssssssssssss\\ │
        ... │/ SSSSSSSSSSSSSSSSS \\│
        ... └─────────────────────┘
        >>> VisualRealTarget(cell=cell, outer_quarter="S", area_coord=(10, 1))
        ... ┌──<Cell>─────────────┐
        ... │\\ NNNNNNNNNNNNNNNNN /│
        ... │ \\nnnnnnnnnnnnnnnnn/ │
        ... │Ee┌─<Widget>──────┐oO│
        ... │Ee│               │oO│
        ... │Ee│               │oO│
        ... │Ee│               │oO│
        ... │Ee│               │oO│
        ... │Ee└───────────────┘oO│
        ... │ /sssssssssssssssss\\ │
        ... │/ SSSSSSSSSSS×SSSSS \\│
        ... └─────────────────────┘
        >>> VisualRealTarget(cell=cell, outer_quarter="NO", area_coord=(0, 4))
        ... ┌──<Cell>─────────────┐
        ... │\\ NNNNNNNNNNNNNNNNN /│
        ... │ \\nnnnnnnnnnnnnnnnn/ │ ×
        ... │Ee┌─<Widget>──────┐oO│
        ... │Ee│               │oO│
        ... │Ee│               │oO│
        ... │Ee│               │oO│
        ... │Ee│               │oO│
        ... │Ee└───────────────┘oO│
        ... │ /sssssssssssssssss\\ │
        ... │/ SSSSSSSSSSSSSSSSS \\│
        ... └─────────────────────┘
    """

    cell: Cell | NullCell
    outer_quarter: Literal["", "N", "O", "S", "E", "NO", "NE", "SO", "SE"]
    area_coord: tuple[int, int]


class VisualTarget:
    """
    This object is created to represent visual coordinates in the :class:`Grid` and deeper tracing.

    During creation, the original coordinate (`origin_coord`), the coordinate associative to the cell widget anchor
    (`rel_coord`) and the targeted [parent] `cell` are passed.
    Via the method ``trace`` the trace can be initiated. This extends the attribute ``cell_trace`` until the final cell
    of the target is reached or a grid interrupts the trace tracking (See parameter `trace_vistarg` in :class:`Grid`).

    ``cell_trace`` is constructed as follows:
        ``[ (<[child]cell>, <coordinate associative to the cell widget anchor of this cell>), ... ]``

    Finally, the object :class:`VisualRealTarget` can be retrieved, which represents the actual point of the
    coordinate within the widget of a cell or relative to it. Since the VisualRealTarget is cached after calculation,
    the object may become invalid if the structure or size of the grid changes.
    """

    origin_coord: tuple[int, int]
    cell_trace: list[tuple[Cell | NullCell, tuple[int, int]]]
    real_targets: dict[Cell | NullCell, VisualRealTarget]

    def __init__(self, origin_coord: tuple[int, int], rel_coord: tuple[int, int], cell: Cell | NullCell, trace: bool = True):
        self.origin_coord = origin_coord
        self.cell_trace = [(cell, rel_coord)]
        self.real_targets = {}
        if not trace:
            self._finish_trace()

    def trace(self) -> None:
        """
        Trace the main coordinate to the targeted cell
        (Can be suppressed by :class:`Grid`'s, see parameter `trace_vistarg`).

        Expands the lists ``cell_trace``.
        """
        self.cell_trace[-1][0]._trace_vistarg(*self.origin_coord, vistarg=self)

    def _finish_trace(self) -> None:
        self.trace = lambda *_, **__: None

    def real_target_from_trace(self, cell_trace_idx: int = -1) -> VisualRealTarget:
        """
        Create a :class:`VisualRealTarget` based on the trace.

        By default, the last :class:`Cell` reached in the trace is used as the target (`cell_trace_idx`).

        Since the VisualRealTarget is cached after calculation, the object may become invalid if the structure or
        size of the grid changes.
        """
        return self.real_target_relative_to_cell(self.cell_trace[cell_trace_idx][0])

    def real_target_relative_to_cell(self, cell: Cell | NullCell) -> VisualRealTarget:
        """
        Create a :class:`VisualRealTarget` relative to a specific `cell`.

        Since the VisualRealTarget is cached after calculation, the object may become invalid if the structure or
        size of the grid changes.
        """
        return self.real_target(cell, self.origin_coord)

    @lru_cache(4)
    def real_target(
            self,
            cell: Cell | NullCell,
            coord: tuple[int, int]
    ) -> VisualRealTarget:
        """
        Create a :class:`VisualRealTarget` by `coord`\\ inate relative to a specific `cell`.

        The calculation of the inner coordinates of the cell is done by the :class:`Cell` coordinate
        ``widget_area_in_window``, so the passed coordinate in VisualTarget should be the coordinate in the window
        (``origin_coord``).

        Since the VisualRealTarget is cached after calculation, the object may become invalid if the structure or
        size of the grid changes.
        """
        outer: Literal["", "N", "O", "S", "E", "NO", "NE", "SO", "SE"]
        if (xb := cell.widget_area_in_window[0][0]) <= coord[0]:
            if (xe := cell.widget_area_in_window[0][1]) > coord[0]:
                if (yb := cell.widget_area_in_window[1][0]) <= coord[1]:
                    if (ye := cell.widget_area_in_window[1][1]) > coord[1]:
                        outer = ""
                        rel_coord = (coord[0] - xb, coord[1] - yb)
                    else:
                        outer = "S"
                        rel_coord = (coord[0] - xb, coord[1] - ye)
                else:
                    outer = "N"
                    rel_coord = (coord[0] - xb, yb - coord[1] - 1)
            elif (yb := cell.widget_area_in_window[1][0]) <= coord[1]:
                if (ye := cell.widget_area_in_window[1][1]) > coord[1]:
                    outer = "O"
                    rel_coord = (coord[0] - xe, coord[1] - yb)
                else:
                    outer = "SO"
                    rel_coord = (coord[0] - xe, coord[1] - ye)
            else:
                outer = "NO"
                rel_coord = (coord[0] - xe, yb - coord[1] - 1)
        elif (yb := cell.widget_area_in_window[1][0]) <= coord[1]:
            if (ye := cell.widget_area_in_window[1][1]) > coord[1]:
                outer = "E"
                rel_coord = (xb - coord[0] - 1, coord[1] - yb)
            else:
                outer = "SE"
                rel_coord = (xb - coord[0] - 1, coord[1] - ye)
        else:
            outer = "NE"
            rel_coord = (xb - coord[0] - 1, yb - coord[1] - 1)
        self.real_targets[cell] = (itm := VisualRealTarget(cell, outer, rel_coord))
        return itm

    def __lshift__(self, other: VisualTarget) -> VisualTarget:
        self.cell_trace += other.cell_trace
        self.trace = other.trace
        return self

    def __repr__(self) -> str:
        return "<%s %r>" % (self.__class__.__name__, self.cell_trace)



