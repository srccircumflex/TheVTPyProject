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

from abc import abstractmethod
from typing import Literal, TextIO, overload, Iterator, ContextManager, Callable
from sys import stdout

from vtframework.iodata import CursorNavigate
from vtframework.utils.types import SupportsString
from vtframework.video.geocalc import GeoCalculator
from vtframework.video.exceptions import GridConfigurationError, GeometrieError
from vtframework.video.items import VisualTarget
from vtframework.video.frame import FramePadding

try:
    from vtframework.iodata import Mouse
    __4doc1 = Mouse
except ImportError:
    pass

_cell_id_count: int = 1


class Cell:
    """
    This cell object is processed by the :class:`Grid` and contains various size and coordinate information.

    Methods ``get_cursor_position``, ``get_display`` and ``resize`` are declared as abstract methods for inheritance
    to a widget object, but are functional in this form.

    When initializing, the `master_grid` must be passed (, this itself can be subject to a master grid). Optionally the
    default character can be defined via `null_char` (default is ``<NBSP>``), this will be used as filler if the method
    ``get_display`` does not return enough lines. A framing can be defined by an :class:`FramePadding` object and
    passed to `frame`.
    """

    __id__: int

    master_grid: Grid  # | None

    frame: FramePadding
    null_char: str

    cell_display_lines: list[str]

    __y_rows__: set[int, ...]
    __x_columns__: set[int, ...]

    boundary_cells: dict[Literal["N", "O", "S", "E"], tuple[Cell | NullCell, ...]]

    widget_size: tuple[int, int]
    cell_size: tuple[int, int]

    cell_anchor: tuple[int, int]
    widget_anchor: tuple[int, int]

    cell_area_in_window: tuple[tuple[int, int], tuple[int, int]]
    cell_area_in_grid: tuple[tuple[int, int], tuple[int, int]]

    widget_area_in_window: tuple[tuple[int, int], tuple[int, int]]
    widget_area_in_grid: tuple[tuple[int, int], tuple[int, int]]
    widget_area_in_cell: tuple[tuple[int, int], tuple[int, int]]

    cursor_position_in_widget: tuple[int, int]

    _cursor_position_in_window: Callable[[], tuple[int, int]]
    _cursor_position_in_grid: Callable[[], tuple[int, int]]
    _cursor_position_in_cell: Callable[[], tuple[int, int]]

    @property
    def main_grid(self) -> Grid:
        """
        The topmost grid object.

        :raises AttributeError: when this value is accessed from the topmost grid object.
        """
        try:
            return self.master_grid.main_grid
        except AttributeError:
            if self.master_grid is None:
                raise AttributeError("is main grid")
            else:
                return self.master_grid

    @property
    def cursor_position_in_window(self) -> tuple[int, int]:
        return self._cursor_position_in_window()

    @property
    def cursor_position_in_grid(self) -> tuple[int, int]:
        return self._cursor_position_in_grid()

    @property
    def cursor_position_in_cell(self) -> tuple[int, int]:
        return self._cursor_position_in_cell()

    def __init__(self,
                 master_grid: Grid,
                 null_char: str = "\u00a0",
                 frame: FramePadding = None
                 ):
        self.master_grid = master_grid
        self.cell_anchor = (0, 0)
        self.frame = frame or FramePadding()
        global _cell_id_count
        self.__id__ = _cell_id_count
        _cell_id_count += 1
        self.__y_rows__ = set()
        self.__x_columns__ = set()
        self.null_char = null_char

    @abstractmethod
    def resize(self, size: tuple[int, int]) -> None:
        """
        This method is executed within the resizing by the master grid with the cell size minus the space for an
        eventual frame.
        """
        ...
    
    def _set_coordinates(
            self,
            master_anchor: tuple[int, int],
            x_geo_min: int,
            x_geo_max: int,
            y_geo_min: int,
            y_geo_max: int
    ) -> None:
        """
        Calculate and assign the coordinates of the cell. (Executed by the master grid during resizing)
        """
        self.cell_area_in_window = (
            (master_anchor[0] + x_geo_min,
             master_anchor[0] + x_geo_max),
            (master_anchor[1] + y_geo_min,
             master_anchor[1] + y_geo_max)
        )
        self.cell_area_in_grid = (
            (x_geo_min,
             x_geo_max),
            (y_geo_min,
             y_geo_max)
        )
        self.widget_area_in_window = (
            (self.cell_area_in_window[0][0] + self.frame.expanse_E,
             self.cell_area_in_window[0][1] - self.frame.expanse_O),
            (self.cell_area_in_window[1][0] + self.frame.expanse_N,
             self.cell_area_in_window[1][1] - self.frame.expanse_S)
        )
        self.widget_area_in_grid = (
            (self.cell_area_in_grid[0][0] + self.frame.expanse_E,
             self.cell_area_in_grid[0][1] - self.frame.expanse_O),
            (self.cell_area_in_grid[1][0] + self.frame.expanse_N,
             self.cell_area_in_grid[1][1] - self.frame.expanse_S)
        )
        self.widget_area_in_cell = (
            (self.frame.expanse_E,
             self.frame.expanse_E + self.widget_size[0]),
            (self.frame.expanse_N,
             self.frame.expanse_N + self.widget_size[1])
        )
        self.cell_anchor = self.cell_area_in_window[0][0], self.cell_area_in_window[1][0]
        self.widget_anchor = self.widget_area_in_window[0][0], self.widget_area_in_window[1][0]

    def _resize(self) -> None:
        """
        Retrieve the assigned and calculated sizes of the axes from the master grid, calculate and set the
        coordinates, adjust the frame and execute the ``resize`` method. (Executed by the master grid during resizing)
        """
        self.cell_size = (sum(int(self.master_grid.x_axis_geos[n]) for n in self.__x_columns__),
                          sum(int(self.master_grid.y_axis_geos[n]) for n in self.__y_rows__))
        self.frame.resize(self.cell_size)
        self.widget_size = self.frame.widget_size
        self._set_coordinates(
            self.master_grid.widget_anchor,
            self.master_grid.x_axis_geos[min(self.__x_columns__)].__grid_char_range__[0],
            self.master_grid.x_axis_geos[max(self.__x_columns__)].__grid_char_range__[1],
            self.master_grid.y_axis_geos[min(self.__y_rows__)].__grid_char_range__[0],
            self.master_grid.y_axis_geos[max(self.__y_rows__)].__grid_char_range__[1]
        )
        self.resize(self.widget_size)

    def _flush_grid_data(self) -> None:
        """
        Delete the grid information stored in the cell. (Executed by the master grid during resizing)
        """
        self.boundary_cells = {"N": list(), "O": list(), "S": list(), "E": list()}
        self.__y_rows__ = set()
        self.__x_columns__ = set()

    def _accept_grid_data(self) -> None:
        """
        Convert the grid information stored in the cell. (Executed by the master grid during resizing)
        """
        self.boundary_cells = {k: tuple(v) for k, v in self.boundary_cells.items()}

    @abstractmethod
    def get_cursor_position(self) -> tuple[int, int]:
        """
        Return the cursor position in the widget. (Is queried by method ``new_cursor``)
        """
        return 0, 0

    def new_cursor(self) -> None:
        """
        Query the cursor position in the widget and store the calculated positions relative to different
        reference points.
        """
        self.cursor_position_in_widget = self.get_cursor_position()

        def _cursor_position_in_window():
            cp = (self.widget_area_in_window[0][0] + self.cursor_position_in_widget[0],
                  self.widget_area_in_window[1][0] + self.cursor_position_in_widget[1])
            self._cursor_position_in_window = lambda: cp
            return cp

        def _cursor_position_in_grid():
            cp = (self.widget_area_in_grid[0][0] + self.cursor_position_in_widget[0],
                  self.widget_area_in_grid[1][0] + self.cursor_position_in_widget[1])
            self._cursor_position_in_grid = lambda: cp
            return cp

        def _cursor_position_in_cell():
            cp = (self.widget_area_in_cell[0][0] + self.cursor_position_in_widget[0],
                  self.widget_area_in_cell[1][0] + self.cursor_position_in_widget[1])
            self._cursor_position_in_cell = lambda: cp
            return cp

        self._cursor_position_in_window = _cursor_position_in_window
        self._cursor_position_in_grid = _cursor_position_in_grid
        self._cursor_position_in_cell = _cursor_position_in_cell

    @abstractmethod
    def get_display(self) -> list[SupportsString]:
        """
        Return the display of the widget. (Is queried by method ``new_display``)
        """
        return [self.null_char * self.widget_size[0] for _ in range(self.widget_size[1])]

    def new_display(self) -> None:
        """
        Query the widget's display; build and save the cell's display.
        """
        cell_display_lines = self.get_display()
        y_lines = self.frame.N + cell_display_lines + self.frame.S
        self.cell_display_lines = [e + str(y) + o for e, y, o in zip(self.frame.E, y_lines, self.frame.O)]

    def new_visual(self) -> None:
        """
        Query the cursor position and display of the widget, build and store the cell display,
        calculate and store the cursor coordinates.
        """
        self.new_display()
        self.new_cursor()

    def cursor_to_position(self, stream: TextIO = stdout) -> TextIO:
        """
        Create an escape sequence for cursor positioning (:class:`CursorNavigate`) based on the cursor coordinate
        in the window and write it to the `stream`.
        """
        x, y = self.cursor_position_in_window
        stream.write(CursorNavigate.position(x + 1, y + 1))
        return stream

    def print(self, stream: TextIO = stdout) -> TextIO:
        """
        Move the cursor to the cell anchor in the window by writing an escape sequence (:class:`CursorNavigate`)
        to `stream` and write the cell display to the `stream`.
        """
        self.print_to_anchor(*self.cell_anchor, stream=stream)
        return stream

    def print_to_anchor(self, x: int, y: int, stream: TextIO = stdout) -> TextIO:
        """
        Move the cursor to the `x`/`y`-coordinate in the window by writing an escape sequence (:class:`CursorNavigate`)
        to `stream` and write the cell display to the `stream`.
        """
        x, y = x + 1, y + 1
        for n, line in enumerate(self.cell_display_lines):
            stream.write(CursorNavigate.position(x, y + n))
            stream.write(line)
        return stream

    def visualisation(self, stream: TextIO = stdout) -> TextIO:
        """
        Move the cursor to the cell anchor in the window by writing an escape sequence (:class:`CursorNavigate`)
        to `stream` and write the cell display to the `stream`. Then place the cursor in the window to the stored
        position in the widget in the same way.
        """
        self.print(stream)
        self.cursor_to_position(stream)
        return stream

    def grid(self, row: int, column: int, row_span: int = 0, column_span: int = 0) -> None:
        """
        Place the cell at `row`/`column` in the master :class:`Grid`. Span n rows down/n columns to the right.

        (Shortcut method to the master grid)
        """
        self.master_grid.place_cell(self, row, column, row_span, column_span)

    def _trace_vistarg(self, x: int, y: int, vistarg: VisualTarget) -> None:
        """
        Interface for the extension of :class:`VisualTarget` objects.
        (Executed by the topmost :class:`Grid` when translating a visual coordinate;
        continues only in cells that are themselves a grid)
        """
        vistarg._finish_trace()

    def __repr__(self) -> str:
        try:
            return "<Cell %-2d : %-8r>" % (self.__id__, self.cell_size)
        except AttributeError:
            return "<Cell %-2d : (??, ??)>" % (self.__id__,)


class NullCell(Cell):
    """
    This cell object is created and assigned by the :class:`Grid` as a placeholder.
    The visual representation of the cell consists entirely of the `null_char` defined in the grid.
    ``bool(<nullcell>)`` always returns ``False``.
    """

    def __init__(self, master_grid: Grid, null_char: str):
        Cell.__init__(self, master_grid, null_char, frame=FramePadding())

    def __bool__(self) -> bool:
        """:returns: False"""
        return False


class Grid(Cell, ContextManager):
    """
    This object is used to create a grid that processes the :class:`Cell` objects. Grid is itself a derivative of the
    cell object, so it can also be passed to a parent grid object as a cell entry.

    >>> ggggggggggggg<Grid 3 x 2>ggggggggggggggggggggggggggggggggggg
    ... g                       ggg<Grid 2 x 1>gggg                g
    ... g   <Cell>              g        │        g    <Cell>      g
    ... g   row: 0              g        │        g    row: 0      g
    ... g   column: 0           g        │        g    column: 2   g
    ... g                       g        │        g                g
    ... g———————————————————————ggggggggggggggggggg————————————————g
    ... g   <Cell>                                                 g
    ... g   row: 1  column: 0  column_span: 3                      g
    ... g                                                          g
    ... gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg

    For initalization, the first cell at the top left of the grid is defined by the :class:`GeoCalculator` objects
    passed to `column0_geo_calc` and `row0_geo_calc`.
    If the grid object is subordinate to a parent (as <Grid 2 x 1> above), the `master_grid` must be passed
    (is ``None`` in the main grid).
    The stadard character used for free spaces can be changed via `null_cell` (``<NBSP>`` by default).
    As in the cell object, a :class:`FramePadding` can optionally be passed to parameter `frame`.
    The parameter `trace_vistarg` specifies whether the translation of visual coordinates in this grid is
    continued and the :class:`VisualTarget` object is extended or terminated with this cell.

    The grid can be expanded or edited using the ``add_row``, ``add_column``, ``remove_row`` and ``remove_column``
    methods. The height of a row or width of a column is determined by :class:`GeoCalculator` objects, these are
    stored in the grid per axis in a priority list. When the size is changed, the ``GeoCalculator`` objects from the
    priority list are executed one after the other.
    Cell objects are assigned or removed via the ``place_cell``, ``erase_cell``, ``erase_row`` and
    ``erase_column`` methods.

    If the grid layout or cell entries are changed, the ``make_grid`` method and then ``resize`` must always be
    executed. Tip: If subordinate grids are changed, always execute the ``make_grid`` method of this grid and execute
    the size assignment via the ``resize`` method of the main grid object.
    If the size of the cell was assigned for the first time via the ``resize`` method, the grid object can be used
    as an context manager for this.

    >>> with grid as g:
    ...     # changes in runtime
    ...     g.add_column(...
    ...     g.place_cell(...
    ...     ...

    Methods ``print``, ``new_cursor``/``new_display``/``new_visual`` recursively execute the same
    in all child cells (and grids). Tip: after finishing the creation or editing or after resizing the main grid
    execute its method ``new_visual`` and ``print``, within the main loop of the program then execute only the
    ``print``, ``new_cursor``/``new_display``/``new_visual`` methods of the changed cells.
    """

    cells: set[Cell | NullCell | Grid]
    _grid: list[list[Cell | NullCell | Grid]]

    x_axis_geos: list[GeoCalculator]
    y_axis_geos: list[GeoCalculator]

    x_axis_geos_priolist: list[GeoCalculator]
    y_axis_geos_priolist: list[GeoCalculator]

    def __init__(self,
                 column0_geo_calc: GeoCalculator,
                 row0_geo_calc: GeoCalculator,
                 master_grid: Grid = None,
                 null_char: str = "\u00a0",
                 frame: FramePadding = None,
                 trace_vistarg: bool = True
                 ):
        self._grid = list()
        Cell.__init__(self, master_grid, null_char, frame)
        self.cells = set()
        self.null_char = null_char
        self.x_axis_geos = [column0_geo_calc]
        self.x_axis_geos_priolist = [column0_geo_calc]
        self.y_axis_geos = [row0_geo_calc]
        self.y_axis_geos_priolist = [row0_geo_calc]
        self._grid.append([NullCell(self, self.null_char)])

        if not trace_vistarg:
            self._trace_vistarg = lambda *_, **__: None

    @overload
    def add_row(self, geo_calc: GeoCalculator, *, grid_insert_index: int = None, prio_insert_index: int = None) -> None:
        ...

    @overload
    def add_row(self, geo_calc: GeoCalculator, *, grid_replace_index: int = None, prio_insert_index: int = None) -> None:
        ...

    def add_row(self,
                geo_calc: GeoCalculator,
                *,
                grid_insert_index: int = None,
                grid_replace_index: int = None,
                prio_insert_index: int = None) -> None:
        """
        Add a row to the grid.
        By default, the row is appended below the grid and the :class:`GeoCalculator` to the priority list.
        To exchange a row definition the row index must be passed over `grid_replace_index`.
        If the row is to be placed at a specific position in the grid, the row index must be passed to
        `grid_insert_index`.
        If `prio_insert_index` is defined, the ``GeoCalculator`` is placed at this position in the priority list.
        Info: the ``GeoCalculator`` passed at initialization are always at position 0 in the priority list.
        """
        if grid_insert_index is not None:
            self.y_axis_geos.insert(grid_insert_index, geo_calc)
            self._grid.append([NullCell(self, self.null_char) for _ in range(len(self[0]))])
        elif grid_replace_index is not None:
            self.y_axis_geos_priolist.remove(self.y_axis_geos[grid_replace_index])
            self.y_axis_geos[grid_replace_index] = geo_calc
        else:
            self.y_axis_geos.append(geo_calc)
            self._grid.append([NullCell(self, self.null_char) for _ in range(len(self[0]))])
        if prio_insert_index is not None:
            self.y_axis_geos_priolist.insert(prio_insert_index, geo_calc)
        else:
            self.y_axis_geos_priolist.append(geo_calc)

    @overload
    def add_column(self, geo_calc: GeoCalculator, *, grid_insert_index: int = None, prio_insert_index: int = None) -> None:
        ...

    @overload
    def add_column(self, geo_calc: GeoCalculator, *, grid_replace_index: int = None, prio_insert_index: int = None) -> None:
        ...

    def add_column(self,
                   geo_calc: GeoCalculator,
                   *,
                   grid_insert_index: int = None,
                   grid_replace_index: int = None,
                   prio_insert_index: int = None) -> None:
        """
        Add a column to the grid.
        By default, the column is appended on the right side of the grid and the :class:`GeoCalculator` to the
        priority list.
        To exchange a column definition the column index must be passed over `grid_replace_index`.
        If the column is to be placed at a specific position in the grid, the column index must be passed to
        `grid_insert_index`.
        If `prio_insert_index` is defined, the ``GeoCalculator`` is placed at this position in the priority list.
        Info: the ``GeoCalculator`` passed at initialization are always at position 0 in the priority list.
        """
        if grid_insert_index is not None:
            self.x_axis_geos.insert(grid_insert_index, geo_calc)
            for r in self:
                r.append(NullCell(self, self.null_char))
        elif grid_replace_index is not None:
            self.x_axis_geos_priolist.remove(self.x_axis_geos[grid_replace_index])
            self.x_axis_geos[grid_replace_index] = geo_calc
        else:
            self.x_axis_geos.append(geo_calc)
            for r in self:
                r.append(NullCell(self, self.null_char))
        if prio_insert_index is not None:
            self.x_axis_geos_priolist.insert(prio_insert_index, geo_calc)
        else:
            self.x_axis_geos_priolist.append(geo_calc)

    def remove_row(self, i: int) -> None:
        """
        Remove the row on y-axis index `i`.

        :raises GridConfigurationError: The last remaining row cannot be removed.
        """
        if len(self.y_axis_geos) == 1:
            raise GridConfigurationError("The last remaining row cannot be removed.")
        touched = set()
        for cell in self[i]:
            if cell in touched:
                continue
            touched.add(cell)
            cell.__y_rows__.remove(i)
        self._grid.pop(i)
        self.y_axis_geos_priolist.remove(self.y_axis_geos.pop(i))

    def remove_column(self, i: int) -> None:
        """
        Remove the column on x-axis index `i`.

        :raises GridConfigurationError: The last remaining column cannot be removed.
        """
        if len(self.x_axis_geos) == 1:
            raise GridConfigurationError("The last remaining column cannot be removed.")
        touched = set()
        for row in self:
            cell = row[i]
            if cell in touched:
                continue
            touched.add(cell)
            cell.__x_columns__.remove(i)
        for row in self:
            row.pop(i)
        self.x_axis_geos_priolist.remove(self.x_axis_geos.pop(i))

    def place_cell(self, cell: Cell | NullCell,
                   row: int, column: int,
                   row_span: int = 0, column_span: int = 0) -> None:
        """
        Sets a cell object in place of `row`/`column` in the grid.
        A span of multiple rows or columns is specified via `row_span`/`column_span` (1 is equal to 0).

        :raises GridConfigurationError: Cell place occupied.
        """
        row_span = max(row_span, 1) - 1
        column_span = max(column_span, 1) - 1

        for r in range(row, row + row_span + 1):
            for c in range(column, column + column_span + 1):
                if self[r][c]:
                    raise GridConfigurationError("Cell place %d/%d used by %r.", (r, c, self[r][c]))

        for r in range(row, row + row_span + 1):
            for c in range(column, column + column_span + 1):
                self[r][c] = cell

        self.cells.add(cell)

    @overload
    def erase_cell(self, cell: Cell | NullCell) -> None:
        ...

    @overload
    def erase_cell(self, cell: tuple[int, int]) -> None:
        ...

    @overload
    def erase_cell(self, cell: tuple[int, int], partial_orient: Literal["N", "O", "S", "E"]) -> None:
        ...

    def erase_cell(
            self,
            cell: Cell | NullCell | tuple[int, int],
            partial_orient: Literal["N", "O", "S", "E", "NO", "NE", "SO", "SE"] = None
    ) -> None:
        """
        Erase `cell` entry in the grid.
        The `cell` can be specified as a Cell object or ``(row, column)`` tuple.
        If `partial_orient` is defined the `cell` must be defined as ``(row, column)`` coordinate, starting from this
        coordinate all cell entries in direction(s) of `partial_orient`, including the coordinate, will be erased.

        >>> erase_cell((2, 3))
        ...     |col0     |col1     |col2     |col3     |col4    |
        ...     ┌─────────┬─────────┬───────────────────┬────────┐
        ... row0│         │         │                   │        │
        ... ____├─────────┼─────────┼─────────┬─────────┼────────│
        ... row1│         │         │         │         │        │
        ... ____│         │─────────┼─────────┴─────────┴────────│
        ... row2│         │         │ XXXXXXXXXXXXXXXXXXXXXXXXXX │
        ... ____│         │─────────┼─────────┬─────────┬────────│
        ... row3│         │         │         │         │        │
        ...     └─────────┴─────────┴─────────┴─────────┴────────┘
        >>> erase_cell((2, 3), partial_orient="O")
        ...     |col0     |col1     |col2     |col3     |col4    |
        ...     ┌─────────┬─────────┬───────────────────┬────────┐
        ... row0│         │         │           XXXXXXX │ XXXXXX │
        ... ____├─────────┼─────────┼─────────┬─────────┼────────│
        ... row1│         │         │         │ XXXXXXX │ XXXXXX │
        ... ____│         │─────────┼─────────┴─────────┴────────│
        ... row2│         │         │          XXXXXXXXXXXXXXXXX │
        ... ____│         │─────────┼─────────┬─────────┬────────│
        ... row3│         │         │         │ XXXXXXX │ XXXXXX │
        ...     └─────────┴─────────┴─────────┴─────────┴────────┘
        >>> erase_cell((2, 3), partial_orient="SO")
        ...     |col0     |col1     |col2     |col3     |col4    |
        ...     ┌─────────┬─────────┬───────────────────┬────────┐
        ... row0│         │         │           XXXXXXX │ XXXXXX │
        ... ____├─────────┼─────────┼─────────┬─────────┼────────│
        ... row1│         │         │         │ XXXXXXX │ XXXXXX │
        ... ____│         │─────────┼─────────┴─────────┴────────│
        ... row2│ XXXXXXX │ XXXXXXX │ XXXXXXXXXXXXXXXXXXXXXXXXXX │
        ... ____│ XXXXXXX │─────────┼─────────┬─────────┬────────│
        ... row3│ XXXXXXX │ XXXXXXX │ XXXXXXX │ XXXXXXX │ XXXXXX │
        ...     └─────────┴─────────┴─────────┴─────────┴────────┘
        """
        if isinstance(cell, tuple):
            row, column = cell
            cell = self[row][column]
            if partial_orient:
                if "N" in partial_orient:
                    for r in cell.__y_rows__:
                        if r <= row:
                            for c in cell.__x_columns__:
                                self[r][c] = NullCell(self, self.null_char)
                elif "O" in partial_orient:
                    for c in cell.__x_columns__:
                        if c >= column:
                            for r in cell.__y_rows__:
                                self[r][c] = NullCell(self, self.null_char)
                if "S" in partial_orient:
                    for r in cell.__y_rows__:
                        if r >= row:
                            for c in cell.__x_columns__:
                                self[r][c] = NullCell(self, self.null_char)
                elif "E" in partial_orient:
                    for c in cell.__x_columns__:
                        if c <= column:
                            for r in cell.__y_rows__:
                                self[r][c] = NullCell(self, self.null_char)
                else:
                    raise ValueError(partial_orient)
                return

        for r in cell.__y_rows__:
            for c in cell.__x_columns__:
                if self[r][c] is cell:
                    self[r][c] = NullCell(self, self.null_char)

    def erase_row(self, i: int) -> None:
        """
        Erase all cell entries in row `i`.

        :raises GridConfigurationError: Erasing the row would split a cell.
        """
        touched = set()
        for cell in self[i]:
            if cell in touched:
                continue
            touched.add(cell)
            if i not in (min(cell.__y_rows__), max(cell.__y_rows__)):
                raise GridConfigurationError("Erasing the row would split %r." % cell)
            else:
                cell.__y_rows__.remove(i)
        self[i] = [NullCell(self, self.null_char) for _ in range(len(self[0]))]

    def erase_column(self, i: int) -> None:
        """
        Erase all cell entries in column `i`.

        :raises GridConfigurationError: Erasing the column would split a cell.
        """
        touched = set()
        for row in self:
            cell = row[i]
            if cell in touched:
                continue
            touched.add(cell)
            if i not in (min(cell.__x_columns__), max(cell.__x_columns__)):
                raise GridConfigurationError("Erasing the column would split %r." % cell)
            else:
                cell.__x_columns__.remove(i)
        for row in self:
            row[i] = NullCell(self, self.null_char)

    def make_grid(self) -> None:
        """
        Assign the :class:`GeoCalculator` to the :class:`Cell`'s in the grid, store all cells in the grid unsorted
        under attribute ``cells`` and set the ``boundary_cells`` attribute in the cells.
        """
        self.cells = set()
        for row in self:
            for cell in row:
                cell._flush_grid_data()
        n_rows = len(self)
        n_cols = len(self[0])
        if n_cols > 1:
            for i in range(n_rows):
                self[i][0].boundary_cells["O"].append(self[i][1])
                self[i][0].__y_rows__.add(i)
                self[i][0].__x_columns__.add(0)
                self.cells.add(self[i][0])
        else:
            for i in range(n_rows):
                self[i][0].__y_rows__.add(i)
                self[i][0].__x_columns__.add(0)
                self.cells.add(self[i][0])
        if n_rows > 1:
            for i in range(n_cols):
                self[0][i].boundary_cells["S"].append(self[1][i])
                self[0][i].__y_rows__.add(0)
                self[0][i].__x_columns__.add(i)
                self.cells.add(self[0][i])
        else:
            for i in range(n_cols):
                self[0][i].__y_rows__.add(0)
                self[0][i].__x_columns__.add(i)
                self.cells.add(self[0][i])
        for i in range(1, n_rows - 1):
            for ii in range(1, n_cols - 1):
                self[i][ii].boundary_cells["N"].append(self[i - 1][ii])
                self[i][ii].boundary_cells["O"].append(self[i][ii + 1])
                self[i][ii].boundary_cells["S"].append(self[i + 1][ii])
                self[i][ii].boundary_cells["E"].append(self[i][ii - 1])
                self[i][ii].__x_columns__.add(ii)
                self[i][ii].__y_rows__.add(i)
                self.cells.add(self[i][ii])
        if n_cols > 1:
            ii = n_cols - 1
            for i in range(n_rows):
                self[i][-1].boundary_cells["E"].append(self[i][-2])
                self[i][-1].__y_rows__.add(i)
                self[i][-1].__x_columns__.add(ii)
                self.cells.add(self[i][-1])
        else:
            ii = n_cols - 1
            for i in range(n_rows):
                self[i][-1].__y_rows__.add(i)
                self[i][-1].__x_columns__.add(ii)
                self.cells.add(self[i][-1])
        if n_rows > 1:
            ii = n_rows - 1
            for i in range(n_cols):
                self[-1][i].boundary_cells["N"].append(self[-2][i])
                self[-1][i].__y_rows__.add(ii)
                self[-1][i].__x_columns__.add(i)
                self.cells.add(self[-1][i])
        else:
            ii = n_rows - 1
            for i in range(n_cols):
                self[-1][i].__y_rows__.add(ii)
                self[-1][i].__x_columns__.add(i)
                self.cells.add(self[-1][i])

        for cell in self.cells:
            cell._accept_grid_data()

    #                            w/x  h/y
    def resize(self, size: tuple[int, int]) -> None:
        """
        Set the size and coordinates of the grid and all child cells (and grids).

        :raises GeometrieError: The sum of calculated sizes of an axis exceeds the available space
         (Incorrect composition of GeoCalculator's of an axis).
        """
        if self.master_grid is None:
            self.cell_size = size
            self.frame.resize(self.cell_size)
            self.widget_size = self.frame.widget_size
            self._set_coordinates((0, 0), 0, size[0], 0, size[1])
            size = self.widget_size

        x_r, y_r = x, y = size
        for x_calc in self.x_axis_geos_priolist:
            x_r -= x_calc(x, x_r)
        for y_calc in self.y_axis_geos_priolist:
            y_r -= y_calc(y, y_r)
        _x = 0
        for i, x_calc in enumerate(self.x_axis_geos):
            x_calc.__grid_char_range__ = (_x, _x := _x + x_calc.size)
            x_calc.__axis_index__ = i
        if _x > x:
            raise GeometrieError("The sum of the calculated column widths (%d) exceeds the available width (%d)." % (_x, x))
        _y = 0
        for i, y_calc in enumerate(self.y_axis_geos):
            y_calc.__grid_char_range__ = (_y, _y := _y + y_calc.size)
            y_calc.__axis_index__ = i
        if _y > y:
            raise GeometrieError("The sum of the calculated row heights (%d) exceeds the available height (%d)." % (_y, y))
        for cell in self.cells:
            cell._resize()

    def print(self, stream: TextIO = stdout) -> TextIO:
        """
        Move the cursor to the grid anchor in the window by writing an escape sequence (:class:`CursorNavigate`)
        to `stream` and write the grid display and the display of all child cells to the `stream`.
        """
        super().print()
        for cell in self.cells:
            cell.print(stream)
        return stream

    def new_cursor(self) -> None:
        """
        Query the cursor position in the widget of the grid and of all child cells and store the calculated positions
        relative to different reference points.
        """
        super().new_cursor()
        for cell in self.cells:
            cell.new_cursor()

    def new_display(self) -> None:
        """
        Query the widget display of the grid and of all child cells; build and save the cells displays.
        """
        super().new_display()
        for cell in self.cells:
            cell.new_display()

    def new_visual(self) -> None:
        """
        Query the cursor position and display of the widget of the grid and of all child cells, build and store the
        cells displays, calculate and store the cursor coordinates.
        """
        super().new_visual()
        for cell in self.cells:
            cell.new_visual()

    def get_visualtarget(self, x: int, y: int) -> VisualTarget:
        """
        Translates a character coordinate within the main grid to :class:`VisualTarget`.

        Attention if the coordinates of a :class:`Mouse` object are passed; this starts at 1 instead of 0.

        :raises IndexError: Coordinate of an axis not within the grid axis.
        """
        _x = x - self.widget_anchor[0]
        _y = y - self.widget_anchor[1]

        if _x not in range(0, self.widget_size[0]):
            return VisualTarget((x, y), (x, y), self, False)
        if _y not in range(0, self.widget_size[1]):
            return VisualTarget((x, y), (x, y), self, False)

        def __search(start: int, stop: int, axis: list[GeoCalculator], val: int):
            if stop >= start:

                mid = (start + stop) // 2
                geo_calc = axis[mid]

                if val >= geo_calc.__grid_char_range__[0]:
                    if val < geo_calc.__grid_char_range__[1]:
                        return geo_calc
                    else:
                        return __search(mid + 1, stop, axis, val)
                else:
                    return __search(start, mid - 1, axis, val)
            else:
                return

        x_calc = __search(0, len(self.x_axis_geos), self.x_axis_geos, _x)
        y_calc = __search(0, len(self.y_axis_geos), self.y_axis_geos, _y)

        return VisualTarget((x, y), (_x, _y), self[y_calc.__axis_index__][x_calc.__axis_index__])

    def _trace_vistarg(self, x: int, y: int, vistarg: VisualTarget) -> None:
        (vistarg << self.get_visualtarget(x, y)).trace()

    def get_cell(self, row: int, column: int) -> Cell | NullCell | Grid:
        return self[row][column]

    def __getitem__(self, item: int) -> list[Cell | NullCell | Grid]:
        return self._grid.__getitem__(item)
    
    def __setitem__(self, key: int, value: list[Cell | NullCell | Grid]):
        self._grid.__setitem__(key, value)

    def __iter__(self) -> Iterator[list[Cell | NullCell | Grid]]:
        return self._grid.__iter__()

    def __len__(self) -> int:
        return self._grid.__len__()

    def __enter__(self) -> Grid:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.make_grid()
        self.resize(self.cell_size)

    def __repr__(self) -> str:
        return str().join(str().join("%-30r" % c for c in row) + "\n" for row in self)
