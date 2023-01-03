# MIT License
#
# Copyright (c) 2022 Adrian F. Hoefflin [srccircumflex]
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

from typing import Callable, Literal, Any, overload, Type
from re import Pattern, compile, search, finditer, Match
from ast import literal_eval
from pathlib import Path
from sqlite3 import connect as sql_connect, OperationalError as SQLOperationalError, Connection as SQLConnection

from .display.displays import _DisplayBase
from .chunkiter import ChunkIter
from .bufferreader import Reader
from ._buffercomponents import (
    WriteItem,
    HistoryItem,
    ChunkLoad,
    ChunkData,
    DumpData,
    _EOFMetas,
    _GlobCursor,
    _LocalHistory,
    _Marker,
    _NullComponent,
    _Row,
    _Swap,
    _Trimmer,
    _Marking
)
from ._buffercomponents import _sql
from .exceptions import (
    ConfigurationError,
    CursorChunkLoadError,
    CursorChunkMetaError,
    CursorNegativeIndexingError,
    CursorPlacingError,
    DatabaseFilesError,
    DatabaseTableError,
    ConfigurationWarning
)
from ._buffercomponents.items import ChunkMetaItem


class TextBuffer:
    """
    Buffer object for dynamic editing of text.

    Functions, properties and behavior are modeled on those of a text editing program.

    Features and functions overview:
        Cursor navigation:
            - ordinary movement.
            - page up/down.
            - pos1/end.
            - jumping (like ctrl+arrow).
            - go to data point/row/line x.
            - ...

        Writing:
            - writing characters / strings (text).
            - four substitution modes.
            - non-breaking line breaks. (Count in length like one character, but are represented with ``""`` in the rows.)
            - tab transformation.
            - backspace / delete.
            - ...

        Subsequent components:
            __local_history__:
                - undo/redo support.
                - branch fork support.
            __marker__:
                - support for marking text areas (like shift+arrow).
                - further processing of markings.
            __trimmer__[/__swap__]:
                - management of the buffer size.

    This main object is practically the handler for the component objects that are created and processed in high
    dependence on the buffer and each other.

    Some features and functions can be installed after the
    initialization of the main object via methods with ``init_`` prefix.

    Subsequent installed or standard components of the buffer are assigned to the following attributes:

        ====================== ======================= ==================== ================================
        ``__swap__``           :class:`_Swap`          Optional Component   assigned by an ``init_*`` method
        ``__trimmer__``        :class:`_Trimmer`       Optional Component   assigned by an ``init_*`` method
        ``__local_history__``  :class:`_LocalHistory`  Optional Component   assigned by an ``init_*`` method
        ``__marker__``         :class:`_Marker`        Optional Component   assigned by an ``init_*`` method
        ``__glob_cursor__``    :class:`_GlobCursor`    Permanent Component
        ====================== ======================= ==================== ================================

    ****

    When editing the buffer, it must be noted that editing the buffer always results in an adjustment of the other
    data. Therefore and because of the conversion of data in Python types, the buffer is not suitable for "Big Data"
    and shows weaknesses with extremely long lines when a highlighter is used in the display. Nevertheless, the
    processing of even a larger number of rows is possible with the help of a swap.

    For this the attributes

    - __start_point_data__
    - __start_point_content__
    - __start_point_row_num__
    - __start_point_line_num__

    have meaning and indicate the current start of the data in the buffer.
    The attributes

    - __n_rows__
    - __n_newlines__

    indicate the number of lines and rows in the current buffer (a line, compared to a row, defines the data between line breaks).

    The properties

    - __eof_data__
    - __eof_content__
    - __eof_row_num__
    - __eof_line_num__

    calculate the endpoints of all data in the buffer and swap.

    ****

    Parameterization:
        - `top_row_vis_maxsize`
            Set a maximum width of the visual representation of row data for the first row.
        - `future_row_vis_maxsize`
            Set a maximum width of visual representation of row data for the remaining rows.
        - `tab_size`
            The visual size of a tab in characters.
        - `tab_to_blank`
            Replace the relative tab range directly when writing to blanks.
        - `autowrap_points`
            Specify a definition of characters via a ``re.Pattern`` at which a row should be wrapped when reaching the
            maximum width; then wrapping is done at the end of the ``re.Match``.
            If ``True`` is passed a predefined pattern is used, ``False`` disables the function.
        - `jump_points_re`
            Jump points for a special cursor movement defined as ``re.Pattern``. Applied when the cursor is moved
            forward in jump mode, the cursor is then moved to the end point of the ``re.Match`` or to the end of
            the row. If ``None`` is passed, a predefined pattern is used.
        - `back_jump_re`
            Jump points for a special cursor movement defined as ``re.Pattern``. Applied when the cursor is moved
            backward in jump mode, the cursor is then moved to the start point of the ``re.Match`` or to the
            beginning of the row. If ``None`` is passed, a predefined pattern is used.
    """

    __swap__: _Swap
    __trimmer__: _Trimmer
    __local_history__: _LocalHistory
    __marker__: _Marker

    __display__: _DisplayBase

    __glob_cursor__: _GlobCursor

    current_row_idx: int
    rows: list[_Row]
    _top_baserow: _Row
    _future_baserow: _Row
    _last_baserow: _Row

    _eof_metas: _EOFMetas

    __start_point_data__: int
    __start_point_content__: int
    __start_point_row_num__: int
    __start_point_line_num__: int

    __n_rows__: int
    __n_newlines__: int

    # slot 0:  tool_vis_to_cnt_excl          (default size: 4)
    # slot 1:  tool_seg_in_seg_to_vis        (default size: 8)
    # slot 2:  tool_cnt_to_seg_in_seg        (default size: 16)
    # slot 3:  tool_cnt_to_vis               (default size: 32)
    # slot 4:  tool_vis_to_cnt               (default size: 32)
    # slot 5:  content_limit                 (default size: 1)
    __cursor_translation_cache_sizes__: tuple[int, int, int, int, int, int]

    DEFAULT_JUMP_POINTS_RE: Pattern = compile('(?<=\\w)(?=\\W)|(?<=\\W)(?=\\w)')
    DEFAULT_BACK_JUMP_RE: Pattern = compile('(?<=\\w)(?=\\W)|(?<=\\W)(?=\\w)')
    DEFAULT_AUTOWRAP_RE: Pattern = compile('[\\s()\\[\\]{}\\\\/&_-](?=\\w*$)')

    ChunkBuffer: Type[ChunkBuffer]
    ChunkIter: Type[ChunkIter]

    __slots__ = ('__swap__', '__trimmer__', '__local_history__', '__marker__', '__display__', '__glob_cursor__',
                 'current_row_idx', 'rows', '_top_baserow', '_future_baserow', '_last_baserow',
                 '__start_point_data__', '__start_point_content__', '__start_point_row_num__',
                 '__start_point_line_num__', '_eof_metas', '__cursor_translation_cache_sizes__',
                 '__n_rows__', '__n_newlines__', 'ChunkBuffer', 'ChunkIter')

    @property
    def __eof_data__(self) -> int:
        return self._eof_metas.eof_data

    @property
    def __eof_content__(self) -> int:
        return self._eof_metas.eof_content

    @property
    def __eof_row_num__(self) -> int:
        return self._eof_metas.eof_row_num

    @property
    def __eof_line_num__(self) -> int:
        return self._eof_metas.eof_line_num

    @property
    def __eof_metas__(self) -> tuple[int, int, int, int]:
        return self.__eof_data__, self.__eof_content__, self.__eof_row_num__, self.__eof_line_num__

    @property
    def current_row(self) -> _Row:
        """
        The row where the cursor is located.

        :raises IndexError: Possible when called during an edit or after an external edit
            (after an edit a buffer indexing and cursor navigation should always be done).
        """
        return self.rows[self.current_row_idx]

    def init_rowmax__swap(
            self,
            rows_maximal: int,
            chunk_size: int,
            load_distance: int,
            keep_top_row_size: bool,
            db_path: str | Literal[':memory:', ':history:', 'file:...<uri>'],
            unlink_atexit: bool
    ) -> TextBuffer:
        """
        Set the upper limit of rows in the current buffer and initialize a swap for the cut chunks 
        ( :class:`_Trimmer` <-> :class:`_Swap` ).

        Parameterization:

        - `db_path`
            The location of the database can be specified as a filepath using an ordinal or
            `"Uniform Resource Identifier"`_ (URI) string;
            to create the database temporarily in RAM, the expression ``":memory:"`` can be used;
            another special expression is ``":history:"`` to create the database in the same location of the
            database in :class:`_LocalHistory`.
        - `from_db`
            To build the database and the object from an existing database, the origin can be passed as an ordinal
            path, a URI, or an existing SQL connection. The connection will be closed automatically afterwards,
            unless an SQL connection was passed.
        - `unlink_atexit`
            Registers the deletion of the database when exiting the Python interpreter.

            The process is performed depending on the location of the database:
                - If the database was created as simple files, the connection is closed and the files are deleted from disk (including journals);
                - If an existing connection was passed (internal usage) or the database was created in RAM, the connection will be closed;
                - If the expression ``":history:"`` was used during creation, all Swap entries in the database are deleted (unless the database was closed before).
        - `rows_maximal`
            Used as the limit for fillings.
        - `keep_top_row_size`
            After loading chunks, adjusts the top row in the buffer to the allocated size of the `"top row"`.
        - `load_distance`
            Distance between the cursor and the edge of the currently loaded chunks in the buffer at which loading is triggered.

        .. _`"Uniform Resource Identifier"`: https://docs.python.org/3.10/library/sqlite3.html#sqlite3-uri-tricks

        :raises ValueError: The quotient of `rows_maximal` - 1 and `chunk_size` - 1 is around 0.
        :raises ConfigurationError: Trimmer already initialized or ":history:" is used and there is no connection to a database in `__local_history__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        if self.__trimmer__:
            raise ConfigurationError('Trimmer already initialized.')
        if rows_maximal <= chunk_size * 2:
            raise ValueError('chunk_size must be at most half of maxsize - 1')

        self.__swap__ = _Swap(__buffer__=self,
                              db_path=db_path,
                              from_db=None,
                              unlink_atexit=unlink_atexit,
                              rows_maximal=rows_maximal,
                              keep_top_row_size=keep_top_row_size,
                              load_distance=load_distance)
        self.__trimmer__ = _Trimmer(self, rows_maximal,
                                    swap__chunk_size=chunk_size,
                                    swap__keep_top_row_size=keep_top_row_size)
        return self

    def init_rowmax__drop(
            self,
            rows_maximal: int,
            chunk_size: int,
            keep_top_row_size: bool,
            action: Callable[[DumpData], None]
    ) -> TextBuffer:
        """
        Set the upper limit of rows in the current buffer and drop the cut chunks into `action` ( :class:`_Trimmer` ).
        
        :raises ConfigurationError: Trimmer already initialized or LocalHistory is not compatible with Trimmer's drop-morph.
        :raises ValueError: The quotient of `rows_maximal` - 1 and `chunk_size` - 1 is around 0.
        """
        if self.__trimmer__:
            raise ConfigurationError("Trimmer already initialized.")
        if self.__local_history__:
            raise ConfigurationError("LocalHistory is not compatible with Trimmer's drop-morph.")
        if rows_maximal < chunk_size * 2:
            raise ValueError('maxsize must be at least twice chunk size')

        def _func():
            ct, cb = self.__trimmer__.__call__() or (None, None)
            return ct, cb, None, None

        self.__trimmer__ = _Trimmer(self, rows_maximal,
                                    drop__dump=action,
                                    drop__chunk_size=chunk_size,
                                    drop__keep_top_row_size=keep_top_row_size,
                                    drop__poll=_func,
                                    drop__demand=_func)
        return self

    def init_rowmax__restrict(
            self,
            rows_maximal: int,
            last_row_maxsize: int | None
    ) -> TextBuffer:
        """
        Limit the size of the buffer so that no further entries remain ( :class:`_Trimmer` ).
        
        :raises ConfigurationError: Trimmer already initialized.
        """
        if self.__trimmer__:
            raise ConfigurationError('Trimmer already initialized.')
        self.__trimmer__ = _Trimmer(self, rows_maximal,
                                    restrictive=True,
                                    restrictive__last_row_maxsize=last_row_maxsize)
        return self

    def init_localhistory(
            self,
            maximal_items: int | None,
            items_chunk_size: int,
            maximal_items_action: Callable[[], Any],
            undo_lock: bool,
            branch_forks: bool,
            db_path: str | Literal[':memory:', ':swap:', 'file:...<uri>'],
            unlink_atexit: bool
    ) -> TextBuffer:
        """
        Initialize local history ( :class:`_LocalHistory` ).
            
            Overview of some feature interfaces:
            
                >>> TextBuffer.__local_history__.undo()
                >>> TextBuffer.__local_history__.redo()
                >>> TextBuffer.__local_history__.lock_release()
                >>> TextBuffer.__local_history__.branch_fork()

        Parameterization:

        - `db_path`
            The location of the database can be specified as a filepath using an ordinal or
            `"Uniform Resource Identifier"`_ (URI) string;
            to create the database temporarily in RAM, the expression ``":memory:"`` can be used;
            another special expression is ``":swap:"`` to create the database in the same location of the database
            in :class:`_Swap`.
        - `unlink_atexit`
            Registers the deletion of the database when exiting the Python interpreter.

            The process is performed depending on the location of the database:
                - If the database was created as simple files, the connection is closed and the files are deleted
                  from disk (including journals);
                - If an existing connection was passed (internal usage) or the database was created in RAM, the
                  connection will be closed;
                - If the expression ``":swap:"`` was used during creation, all LocalHistory entries in the
                  database are deleted (unless the database was closed before).
        - `undo_lock`
            Enables the undo lock feature. Blocks processing of the buffer immediately after an undo action until the lock is released.
        - `branch_forks`
            Enables the chronological forks feature. Allows to switch between the last undo branch.
        - `maximal_items`
            Sets an upper limit for chronological items. ``None`` corresponds to no limit.
            The final value is composed of `maximum_items` + `items_chunk_size`.
        - `items_chunk_size`
            Defines the amount of chronological items that will be removed when the upper limit is reached.
            The final value of the upper limit is composed of `maximum_items` + `items_chunk_size`.
        - `maximal_items_action`
            Executed before chronological items are removed when the upper limit is reached. Does not receive any parameters.

        .. _`"Uniform Resource Identifier"`: https://docs.python.org/3.10/library/sqlite3.html#sqlite3-uri-tricks

        :raises ConfigurationError: LocalHistory is not compatible with Trimmer's drop-morph or if ":swap:" is used and there is no connection to a database in `__swap__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        if self.__trimmer__.morph == "drp":
            raise ConfigurationError("LocalHistory is not compatible with Trimmer's drop-morph.")
        self.__local_history__ = _LocalHistory(__buffer__=self,
                                               db_path=db_path,
                                               from_db=None,
                                               unlink_atexit=unlink_atexit,
                                               undo_lock=undo_lock,
                                               branch_forks=branch_forks,
                                               maximal_items=maximal_items,
                                               items_chunk_size=items_chunk_size,
                                               maximal_items_action=maximal_items_action)
        return self

    def init_marker(self, multy_marks: bool, backjump_mode: bool) -> TextBuffer:
        """
        Initialize markers ( :class:`_Marker` ).
        
            Overview of some feature interfaces:
            
            >>> TextBuffer.cursor_move(mark=, mark_jump=)
            >>> TextBuffer.__marker__.add_marks()
            >>> TextBuffer.__marker__.pop_aimed_mark()
            >>> TextBuffer.__marker__.reader()
            >>> TextBuffer.__marker__.marked_shift()
            >>> TextBuffer.__marker__.marked_tab_replace()
            >>> TextBuffer.__marker__.marked_remove()
        """
        self.__marker__ = _Marker(self, multy_marks, backjump_mode)
        return self

    def __init__(
            self,
            top_row_vis_maxsize: int | None,
            future_row_vis_maxsize: int | None,
            tab_size: int,
            tab_to_blank: bool,
            autowrap_points: bool | Pattern,
            jump_points_re: Pattern | None,
            back_jump_re: Pattern | None
    ):
        self.ChunkBuffer = ChunkBuffer
        self.ChunkIter = ChunkIter

        self.__cursor_translation_cache_sizes__ = (4, 8, 16, 32, 32, 1)

        if top_row_vis_maxsize or future_row_vis_maxsize:
            if isinstance(autowrap_points, bool):
                if autowrap_points:
                    autowrap_points = self.DEFAULT_AUTOWRAP_RE
                else:
                    autowrap_points = None
            else:
                autowrap_points = None

        jump_points_re = jump_points_re or self.DEFAULT_JUMP_POINTS_RE
        back_jump_re = back_jump_re or self.DEFAULT_BACK_JUMP_RE

        self._top_baserow = _Row(
            self,
            top_row_vis_maxsize, autowrap_points,
            jump_points_re,
            back_jump_re,
            tab_size, tab_to_blank)

        self._future_baserow = _Row(
            self,
            future_row_vis_maxsize, autowrap_points,
            jump_points_re,
            back_jump_re,
            tab_size, tab_to_blank)

        self._last_baserow = _Row(
            self,
            future_row_vis_maxsize, autowrap_points,
            jump_points_re,
            back_jump_re,
            tab_size, tab_to_blank)

        self.rows = [_Row.__newrow__(self._top_baserow)._set_start_index_(0, 0, 0, 0, 0)]

        self.__swap__ = _NullComponent()
        self.__marker__ = _NullComponent()
        self.__trimmer__ = _NullComponent()
        self.__local_history__ = _NullComponent()
        self.__display__ = _NullComponent()

        self.__glob_cursor__ = _GlobCursor(self)
        self._eof_metas = _EOFMetas(self)

        self.current_row_idx = 0
        self.__start_point_data__ = 0
        self.__start_point_content__ = 0
        self.__start_point_row_num__ = 0
        self.__start_point_line_num__ = 0
        self.__n_rows__ = 0
        self.__n_newlines__ = 0

    def indexing(self, start_idx: int = 0) -> tuple[int, int, int, int]:
        """
        Index the current buffer and return the index-start-data for the next chunk.

        :return: next (abs_dat,  abs_cnt,  row_num,  lin_num)
        """
        if not start_idx:
            lin_num = self.__start_point_line_num__
            abs_cnt = self.__start_point_content__
            abs_dat = self.__start_point_data__
            row_num = self.__start_point_row_num__
        else:
            lin_num = self.rows[start_idx].__line_num__
            abs_cnt = self.rows[start_idx].__content_start__
            abs_dat = self.rows[start_idx].__data_start__
            row_num = self.rows[start_idx].__row_num__
        for i in range(start_idx, len(self.rows)):
            (row := self.rows[i])._set_start_index_(i, row_num, lin_num, abs_cnt, abs_dat)
            abs_cnt += (_l := row.data_cache.len_content)
            abs_dat += _l + (e := (row.end is not None))
            lin_num += e
            row_num += bool(e or _l)
            row._set_next_index_(row_num, lin_num, abs_cnt, abs_dat)
        self.__n_rows__ = (lastrow := self.rows[-1]).__row_index__ + bool(lastrow)
        self.__n_newlines__ = lastrow.__line_num__ - self.rows[0].__line_num__
        return abs_dat, abs_cnt, row_num, lin_num

    def _adjust_rows(
            self, start_row_i: int, stop: int = None, endings: bool = False, dat_start: int = None, diff: int = 0
    ) -> tuple[int, int, int, int]:
        """
        Adjust the rows in the current buffer [across line breaks (`endings`)]
        from row at buffer index `start_row_i` [to `stop`]. [Adjust markings and cursor anchors. (`dat_start`, `diff`)]

        [+] __marker__.adjust [+] __glob_cursor__.adjust

        :return: next (abs_dat,  abs_cnt,  row_num,  lin_num)
        """
        self.current_row_idx = start_row_i
        while True:
            if stop is not None and self.current_row_idx > stop:
                break
            try:
                if not endings and self.current_row.end is not None:
                    self.current_row_idx += 1
                    continue
                rowbuffer = self.rows[self.current_row_idx + 1]
            except IndexError:
                break
            _row = self.rows.pop(self.current_row_idx)
            lines = [_row.content]
            if _row.end in ('\n', ''):
                lines.append('')
            rowbuffer._resize_bybaserow(_row)
            rowbuffer.cursors.reset()
            if of := rowbuffer.writelines(lines, nbnl=_row.end == '').overflow:
                self.current_row_idx += self._overflow_append(of)
        if diff:
            self.__marker__._adjust_markings(dat_start, diff)
            self.__glob_cursor__._adjust_anchors(dat_start, diff)
        while len(self.rows) > 1 and self.rows[-2].end is None and not self.rows[-1]:
            self.rows.pop(-1)
        return self.indexing()

    def _overflow_chunk_sub_lines(
            self, overflow: WriteItem.Overflow, last_had_end: bool, nl: str, pos_id: int, nlrudiment: bool
    ) -> tuple[
        list[tuple[str, str | bool | None]] | None,
        int | bool | None,
        int,
        bool
    ]:
        if not self.rows:  # possible in ChunkBuffer's
            return [], False, 0, last_had_end

        touch = 0
        removed = list()

        _nln_requi = len(overflow.lines)
        _end_count = 0
        _nln_count = 0

        if not last_had_end:
            removed.append(((row := self.rows.pop(0)).content, row.end))
            try:
                while row.end is None:
                    removed.append(((row := self.rows.pop(0)).content, row.end))
            except IndexError:
                return removed, False, touch, last_had_end
            else:
                _nln_count = 1
                _end_count = 1

        try:
            while _end_count < _nln_requi:
                removed.append(((row := self.rows.pop(0)).content, row.end))
                _end_count += (last_had_end := row.end is not None)
                _nln_count += last_had_end
        except IndexError:
            eo_removed = False
        else:
            eo_removed = self.rows[0].__data_start__

        rows = list()
        if pos_id == 1:
            if not self.rows and nlrudiment:
                nlrudiment = None
                overflow.lines.append('')
            while overflow.lines:
                rows.append(row := _Row.__newrow__(self._future_baserow))
                touch += 1
                if of := row._write_line(overflow.lines.pop(0))[0]:
                    overflow.lines.insert(0, of[0])
                elif overflow.lines:
                    row.end = nl
            if nlrudiment is not None:
                rows[-1].end = removed[-1][1]
            if not nlrudiment:
                removed[-1] = (removed[-1][0], False)
        elif _nln_count == _nln_requi:
            while overflow.lines:
                rows.append(row := _Row.__newrow__(self._future_baserow))
                touch += 1
                if of := row._write_line(overflow.lines.pop(0))[0]:
                    overflow.lines.insert(0, of[0])
                elif overflow.lines:
                    row.end = nl
            rows[-1].end = removed[-1][1]
            if not nlrudiment:
                removed[-1] = (removed[-1][0], False)
        else:
            for i in range(_nln_count):
                rows.append(row := _Row.__newrow__(self._future_baserow))
                touch += 1
                if of := row._write_line(overflow.lines.pop(0))[0]:
                    overflow.lines.insert(0, of[0])
                elif overflow.lines:
                    row.end = nl

        self.rows = rows + self.rows

        return removed, eo_removed, touch, last_had_end

    def _overflow_sub_lines(
            self, wi: WriteItem, nl_association: bool = False
    ) -> tuple[
        list[tuple[str, str | bool | None]] | None,
        int | bool | None,
        int,
        tuple[int, int] | None,
        bool
    ]:
        """
        Process the overflow of a row in `substitute lines` mode.

        Line substitution mode (default):
            - Substitute the first line until the next line break.
            - More will be inset.
            - Automatically appends the end of the starting row to the last inset row.

        Substitute lines with newline association:
            - Replaces x = n rows until the next line break, with x lines entered.

        If the overflow is newline rudiment:
            - Appends an empty row to the buffer if the last row ends with a newline.

        :param wi: WriteItem.
        :param nl_association: Associate lines.

        :return: ( list of replaced row data, endpoint of replaced data ->
            None(=no removals) | False(=removed to the end), rows touched )
        """
        overflow = wi.overflow
        touch = 0
        removed: list[tuple[str, str | None | False]] = list()
        eo_removed = None
        nl_rudiment = False

        cl_edran = None

        nl = ('' if overflow.nbnl else '\n')

        before, after = self.rows[:(i := self.current_row_idx + 1)], self.rows[i:]

        if nl_association:
            removed.append(('', overflow.end))
            if (_nln_requi := len(overflow.lines)) == wi.write_rows:
                last_had_end = _end_count = (overflow.end is not None)
                _nln_count = 0
            else:
                last_had_end = _nln_count = _end_count = 0

            if _end_count < _nln_requi and after:
                try:
                    while _end_count < _nln_requi:
                        removed.append(((row := after.pop(0)).content, row.end))
                        _end_count += (last_had_end := row.end is not None)
                        _nln_count += last_had_end
                    if after:
                        eo_removed = after[0].__data_start__ - bool(_end_count)
                    else:
                        eo_removed = row.data_cache.len_absdata
                except IndexError:
                    eo_removed = False

            for i in range(_nln_count):
                before.append(row := _Row.__newrow__(self._future_baserow))
                touch += 1
                if of := row._write_line(overflow.lines.pop(0))[0]:
                    overflow.lines.insert(0, of[0])
                elif overflow.lines:
                    row.end = nl

            if overflow.lines and (bottom_ids := self.__swap__.positions_bottom_ids):
                if nl_rudiment := (not overflow.lines[-1]):
                    overflow.lines.pop(-1)
                if overflow.lines:
                    next_metas = self.indexing(self.current_row_idx)
                    for i in range(len(bottom_ids)):
                        with self.ChunkBuffer(self, bottom_ids[i], False, True) as buffer, self.__swap__.__meta_index__:
                            _removed, eo_removed, _touch, last_had_end = buffer._overflow_chunk_sub_lines(overflow,
                                                                                                          last_had_end, nl,
                                                                                                          bottom_ids[i],
                                                                                                          nl_rudiment)
                            buffer.__start_point_data__, buffer.__start_point_content__, buffer.__start_point_row_num__, buffer.__start_point_line_num__ = next_metas
                            self.__swap__.__meta_index__._set(buffer.__chunk_slot__,
                                                              start_point_data=next_metas[0],
                                                              start_point_content=next_metas[1],
                                                              start_point_row=next_metas[2],
                                                              start_point_linenum=next_metas[3])
                            next_metas = buffer.indexing()
                        removed += _removed
                        touch += _touch
                        if not overflow.lines:
                            if adjust_bid := bottom_ids[i + 1:]:
                                self.__swap__.__meta_index__.adjust_by_adjacent(adjust_bid, *next_metas)
                            cl_edran = (self.__swap__.current_chunk_ids[0], bottom_ids[i])
                            break
                    else:
                        cl_edran = (self.__swap__.current_chunk_ids[0], 1)

            else:
                if after and overflow.lines and not overflow.lines[-1]:
                    # newline rudiment
                    overflow.lines.pop(-1)
                    removed_n1 = removed[-1]
                    nl_rudiment = True
                else:
                    removed_n1 = (removed[-1][0], False)

                while overflow.lines:
                    before.append(row := _Row.__newrow__(self._future_baserow))
                    touch += 1
                    if of := row._write_line(overflow.lines.pop(0))[0]:
                        overflow.lines.insert(0, of[0])
                    elif overflow.lines:
                        row.end = nl

                with before[-1]:
                    before[-1].end = removed[-1][1]

                removed[-1] = removed_n1

            while not before[-1]:
                before.pop(-1)
            if after:
                self.rows = before + after
            else:
                if before[-1].end is not None:
                    before.append(_Row.__newrow__(self._future_baserow))
                self.rows = before

        else:
            removed.append(('', overflow.end))
            if (_end_count := overflow.end) is None:
                try:
                    while _end_count is None:
                        removed.append(((row := after.pop(0)).content, row.end))
                        _end_count = row.end
                    if after:
                        eo_removed = after[0].__data_start__
                    else:
                        eo_removed = row.data_cache.len_absdata
                except IndexError:
                    if bottom_ids := self.__swap__.positions_bottom_ids:
                        next_metas = self.indexing(self.current_row_idx)
                        for i in range(len(bottom_ids)):
                            with self.ChunkBuffer(self, bottom_ids[i], False,
                                                  True) as buffer, self.__swap__.__meta_index__:
                                for _ in range(len(buffer.rows)):
                                    touch += 1
                                    removed.append(((row := after.pop(0)).content, row.end))
                                    if (_end_count := row.end) is not None:
                                        eo_removed = row.data_cache.len_absdata
                                        break
                                buffer.__start_point_data__, buffer.__start_point_content__, buffer.__start_point_row_num__, buffer.__start_point_line_num__ = next_metas
                                self.__swap__.__meta_index__._set(buffer.__chunk_slot__,
                                                                  start_point_data=next_metas[0],
                                                                  start_point_content=next_metas[1],
                                                                  start_point_row=next_metas[2],
                                                                  start_point_linenum=next_metas[3])
                                next_metas = buffer.indexing()
                            if _end_count is not None:
                                if adjust_bid := bottom_ids[i + 1:]:
                                    self.__swap__.__meta_index__.adjust_by_adjacent(adjust_bid, *next_metas)
                                cl_edran = (self.__swap__.current_chunk_ids[0], bottom_ids[i])
                                break
                        else:
                            cl_edran = (self.__swap__.current_chunk_ids[0], 1)
                            eo_removed = False
                    else:
                        eo_removed = False

            if overflow.lines and not overflow.lines[-1]:
                # newline rudiment
                overflow.lines.pop(-1)
                nl_rudiment = True
            else:
                removed[-1] = (removed[-1][0], False)

            while overflow.lines:
                before.append(row := _Row.__newrow__(self._future_baserow))
                touch += 1
                if of := row._write_line(overflow.lines.pop(0))[0]:
                    overflow.lines.insert(0, of[0])
                elif overflow.lines:
                    row.end = nl

            if after:
                with before[-1]:
                    before[-1].end = _end_count
                self.rows = before + after
            else:
                if before[-1].end is not None:
                    before.append(_Row.__newrow__(self._future_baserow))
                self.rows = before

        return removed, eo_removed, touch, cl_edran, nl_rudiment

    def _overflow_append(self, overflow: WriteItem.Overflow) -> int:
        """
        Process the overflow of a row.

        :return: rows touched
        """
        touch = 0

        before, after = self.rows[:(i := self.current_row_idx + 1)], self.rows[i:]

        nl = ('' if overflow.nbnl else '\n')

        fin = (overflow.end is not None) ^ 1
        while len(overflow.lines) > fin:
            touch += 1
            before.append(row := _Row.__newrow__(self._future_baserow))
            if of := row._write_line(overflow.lines.pop(0))[0]:
                overflow.lines.insert(0, of[0])
            else:
                row.end = nl
        if not fin:
            before[-1].end = overflow.end

        if after:
            before.append(row := after.pop(0))
        else:
            before.append(row := _Row.__newrow__(self._future_baserow))

        while overflow.lines:
            touch += 1
            row.cursors.reset()
            _end = row.end
            if of := row._write_line(overflow.lines.pop(0))[0]:
                if _end is not None:
                    before.append(row := _Row.__newrow__(self._future_baserow))
                    row.end = _end
                elif after:
                    before.append(row := after.pop(0))
                else:
                    before.append(row := _Row.__newrow__(self._future_baserow))
                overflow.lines.append(of[0])

        self.rows = before + after

        return touch

    def _enter_overflow(
            self,
            write_item: WriteItem,
            sub_line: bool,
            associate_lines: bool
    ) -> tuple[list[tuple[str, str | bool | None]] | None, tuple[int, int] | None, int, int | bool | None]:
        """
        Interface to `_overflow_sub_lines` and `_overflow_append`.

        [+] __marker__.adjust [+] __glob_cursor__.adjust

        :return: replaced row data
        """
        removed = cl_edran = rm_end = None
        if (sub_line or associate_lines) and write_item.overflow.substitution:
            len_of = len(write_item.overflow)
            removed, eo_removed, touch, cl_edran, nl_rud = self._overflow_sub_lines(write_item, associate_lines)
            len_of -= nl_rud
            if eo_removed is None:
                rm_end = write_item.begin + write_item.deleted
                total_diff = write_item.diff + len_of
            elif eo_removed:
                rm_end = eo_removed
                total_diff = (write_item.diff + len_of) - (eo_removed - (write_item.begin + write_item.deleted))
            else:
                rm_end = eo_removed
                total_diff = -0
        else:
            total_diff = write_item.diff + len(write_item.overflow)
            touch = self._overflow_append(write_item.overflow)
        return removed, cl_edran, total_diff, rm_end

    def write(
            self, string: str, *,
            sub_chars: bool = False,
            force_sub_chars: bool = False,
            sub_line: bool = False,
            associate_lines: bool = False,
            nbnl: bool = False,
            move_cursor: bool = True
    ) -> tuple[WriteItem, ChunkLoad]:
        """
        Write on the position of the cursor **[ ! ] CR ( "\\\\r" ) is not allowed**.

        Write in `substitute_chars` mode to replace characters associatively to the input in the row,
        at most up to the next tab (only used if neither a newline nor a tab is present in the `string`); OR

        don't care about tabs in the input and apply the substitution also to tabs when the mode
        `forcible_substitute_chars` is active; OR

        substitute the entire row(s) until the next linebreak from the cursor position in mode `substitute_line`; OR

        replace rows until the next line break `associative` to the number of entered lines;

        and replace line breaks with non-breaking line breaks when `nbnl`
        (`n`\\ on-`b`\\ reaking-`n`\\ ew-`l`\\ ine) is set to ``True``.

        Finally, `move_the_cursor` relative to the input.

        Returns:
            ( :class:`WriteItem`, :class:`ChunkLoad` )

        Relevant :class:`ChunkLoad` Fields:
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __trimmer__.trim
        [+] __highlighter__.prep_by_write [+] __marker__.conflict [+] __marker__.adjust [+] __glob_cursor__.adjust
        [+] __glob_cursor__.note

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__local_history__._lock_assert_()
        self.__glob_cursor__.note_globc()
        self.__marker__._in_conflict()
        wi = (row := self.current_row).write(
            string, sub_chars, force_sub_chars, sub_line or associate_lines, nbnl)
        of_removed = spec_pos = None
        top_id, btm_id = self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1]
        if wi.overflow:
            self._eof_metas._changed_rows_()
            gt_too = True
            of_removed, cl_edran, total_diff, rm_end = self._enter_overflow(wi, sub_line, associate_lines)
            self.indexing(self.current_row_idx)
            if move_cursor:
                spec_pos = self._goto_data(wi.begin + wi.write)
            if wi.overflow.substitution:
                cl = ChunkLoad(top_id, btm_id, *self.__trimmer__.action__demand__(),
                               spec_position=spec_pos, edited_ran=cl_edran)
            else:
                cl = ChunkLoad(top_id, btm_id,
                               *(self.__trimmer__.__call__() or (None, None)),
                               spec_position=spec_pos)
        elif sub_line and (end := row.end) is None:
            self._eof_metas._changed_rows_()
            gt_too = True
            wi = wi._replace(overflow=wi.Overflow(
                [], end, True, nbnl, 0
            ))
            of_removed, cl_edran, total_diff, rm_end = self._enter_overflow(wi, sub_line, False)
            self.indexing(self.current_row_idx)
            if move_cursor:
                spec_pos = self._goto_data(wi.begin + wi.write)
            cl = ChunkLoad(top_id, btm_id, *self.__trimmer__.action__demand__(),
                           spec_position=spec_pos, edited_ran=cl_edran)
        else:
            self._eof_metas._changed_data_()
            gt_too = False
            total_diff = wi.diff
            rm_end = None
            self.indexing(self.current_row_idx)
            if move_cursor:
                spec_pos = self._goto_data(wi.begin + wi.write)
            cl = ChunkLoad(top_id, btm_id, spec_position=spec_pos)

        self.__marker__._adjust_markings(wi.begin, total_diff, rm_end)
        self.__glob_cursor__._adjust_anchors(wi.begin, total_diff, rm_end)
        self.__local_history__._add_write(wi, of_removed, sub_line, cl.btm_cut)
        self.__display__.__highlighter__._prepare_by_chunkload(cl)
        self.__display__.__highlighter__._prepare_by_writeitem(wi.work_row, gt_too=gt_too, _row=row)
        return wi, cl

    def rowwork(
            self,
            coords: list[list[int, int]] | list[int] | None,
            coord_type: Literal['data', 'd', 'content', 'c', 'row', 'r', 'line', 'l', ''],
            worker: Callable[[_Row, list[int, int] | int | None], WriteItem | None],
            goto: Callable[[], int],
            unique_rows: bool = False
    ) -> tuple[list[tuple[list[int, int] | int, list[WriteItem | None]]], ChunkLoad] | None:
        """
        **[ ADVANCED USAGE ]**

        The method allows editing of rows by `worker` in an iteration with corresponding adjustment of components,
        the display and the metadata. For this, `worker` must always return a :class:`WriteItem` or ``None`` if the
        row was not edited. **WARNING:** :class:`WriteItem.Overflow` **is NOT handled.**

        `worker` receives in the iteration the :class:`_Row` and the corresponding coordinate, which is ORIENTED to
        the input and originates from :class:`ChunkIter.ParsedCoords`.

        The iteration mode is ``"coords reversed + s"``, the iteration runs backwards through the original coordinates
        and forwards through the rows of the respective coordinate. See also :class:`ChunkIter`.

        Finally, the cursor position is recalled via `goto`.

        The data coordinates are defined as a list of data points ``[ <int>, ... ]`` or as a list of data ranges ``[ [<int>, <int>], ... ]`` (both must be sorted). The data type is specified by `coord_type`;
            Possible values:
                - ``"data"``: Determine the rows using data coordinates, `coord` must be formulated with the data points for this.
                - ``"content"``: Determine the rows using content coordinates, `coord` must be formulated with the content points for this.
                - ``"row"``: Determine the rows by row numbers, `coord` must be formulated with the row numbers for this.
                - ``"line"``: Determine the rows by line numbers, `coord` must be formulated with the line numbers for this (compared to a row, a line is defined as the data between two line breaks + final line break).
            If `coords` is ``None``, then iterate through the entirety of the data and ignore `coord_type`.

        If `unique_rows` is ``True``, each row is processed only once, even if multiple coordinates apply to one.

        The return value is composed as follows:
            - At index 1 of the tuple is the :class:`ChunkLoad`.
            - At index 0 of the tuple there is a list of (coordinate to :class:`WriteItem`'s) pairs:
                - An pair is composed of the coordinate at index 0 and a list of ``WriteItem``'s | ``None`` at index 1:
                    The list of ``WriteItem``'s corresponds to the rows in the coordinate, an entry is ``None`` if editing has not taken place in a row.
        The total return value can be ``None`` if nothing was edited.

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust [+] __highlighter__.prep_by_chunkload

        :return: ( [ ( coordinates: list[int, int] | int, write items: [ WriteItem | None, ... ] ), ... ], ChunkLoad ) | None

        :raises AssertionError: __local_history__ lock is engaged.

        :raises CursorError: following are possible if the datapoint from `goto` is not reachable.

        :raises CursorChunkLoadError: if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are not available.
        :raises CursorChunkMetaError: Chunks of the required side could not be loaded sufficiently.
          The closest chunk was loaded and the cursor was placed at the beginning of the first row.
        :raises CursorPlacingError: if an error occurs during the final setting of the cursor (indicator of too high value).
          The cursor was set to the next possible position.
        :raises CursorNegativeIndexingError: when a negative value is passed.
        """
        self.__local_history__._lock_assert_()
        self._eof_metas._changed_rows_()

        curcur = self.current_row.cursors.data_cursor

        upper_rown = -0
        worked: list[tuple[list[int, int] | int, list[WriteItem | None]]] = list()
        adjust_start: int
        pre_upper_rown = None
        _pre_upper_rown = None
        work = False

        def __worker(row, coord):
            nonlocal _worker, work
            if wi := worker(row, coord):
                work = True
                _worker = worker
            return wi

        _worker = __worker

        def adjust():
            if adjust_start is not None:
                _diff = sum(wi.diff for wi in worked[-1][1] if wi)
                for wi in reversed(worked[-1][1]):
                    if wi:
                        rm_end = wi.begin + wi.deleted
                        break
                else:
                    rm_end = None
                self.__marker__._adjust_markings(adjust_start, _diff, rm_end)
                self.__glob_cursor__._adjust_anchors(adjust_start, _diff, rm_end)

        def __set_adjust_start(x):
            nonlocal _set_adjust_start, adjust_start
            adjust_start = x
            _set_adjust_start = lambda _: None

        _set_adjust_start = lambda _: None

        if unique_rows:
            def coord_enter(row: _Row, coord):
                nonlocal upper_rown, adjust_start, _set_adjust_start, pre_upper_rown, _pre_upper_rown, _coord_continue
                if worked:
                    adjust()
                if (upper_rown := row.__row_num__) == _pre_upper_rown:
                    adjust_start = None
                    worked.append((coord, [None]))
                    _coord_continue = lambda *_: worked[-1][1].append(None)
                else:
                    pre_upper_rown = _pre_upper_rown
                    _pre_upper_rown = upper_rown
                    _coord_continue = __coord_continue
                    if wi := _worker(row, coord):
                        __set_adjust_start(wi.begin)
                    else:
                        adjust_start = None
                        _set_adjust_start = __set_adjust_start
                    worked.append((coord, [wi]))

            def __coord_continue(row: _Row, coord):
                nonlocal _coord_continue
                if row.__row_num__ == pre_upper_rown:
                    worked[-1][1].append(None)
                    wi = None
                    _coord_continue = lambda *_: worked[-1][1].append(None)
                elif wi := _worker(row, coord):
                    _set_adjust_start(wi.begin)
                worked[-1][1].append(wi)

            _coord_continue = __coord_continue

            def coord_continue(row: _Row, coord):
                _coord_continue(row, coord)
        else:
            def coord_enter(row: _Row, coord):
                nonlocal upper_rown, adjust_start, _set_adjust_start
                if worked:
                    adjust()
                if wi := _worker(row, coord):
                    __set_adjust_start(wi.begin)
                else:
                    adjust_start = None
                    _set_adjust_start = __set_adjust_start
                worked.append((coord, [wi]))

            def coord_continue(row: _Row, coord):
                if wi := _worker(row, coord):
                    _set_adjust_start(wi.begin)
                worked[-1][1].append(wi)

        (ci := self.ChunkIter(
            self, 'coords reversed + s', coords, coord_type,
            coord_enter=coord_enter, coord_continue=coord_continue
        )).run()

        if work:
            with self.__local_history__.suit() as local_history:
                local_history._add_cursor(lambda: curcur)
                adjust()
                sp = self._goto_data(goto())
                cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1],
                               *self.__trimmer__.action__demand__(),
                               spec_position=sp, edited_ran=ci.parsed_coords.id_range)
                self.__local_history__._add_iterwork(worked)
                self.__local_history__._add_resremove((None, cl.btm_cut))

            self.__display__.__highlighter__._prepare_by_chunkload(cl)
            self.__display__.__highlighter__._prepare_by_writeitem(upper_rown, gt_too=True)
            return worked, cl
        else:
            self._goto_data(curcur)

    def shift_rows(
            self, coords: list[list[int, int]] | list[int] | None,
            coord_type: Literal['pointing data', 'p', 'content', 'c', 'row', 'r', 'line', 'l', ''],
            *,
            backshift: bool = False, unique_rows: bool = True
    ) -> tuple[list[tuple[list[int, int] | int, list[WriteItem | None]]], ChunkLoad] | None:
        r"""
        Shift rows.

        >>> \\t foo bar
        >>>     foo bar
        origin
        >>> \\t\\t foo bar
        >>> \\t    foo bar
        shifted origin (`tab-to-blanks-mode` not configured)
        >>>  foo bar
        >>> foo bar
        backshifted origin

        The data coordinates are defined as a list of data points ``[ <int>, ... ]`` or as a list of data ranges ``[ [<int>, <int>], ... ]`` (both must be sorted). The data type is specified by `coord_type`;
            Possible values:
                - ``"pointing data"``: Determine the rows using data coordinates.
                - ``"content"``: Determine the rows using content coordinates.
                - ``"row"``: Determine the rows by row numbers, `coord` must be formulated with the row numbers for this.
                - ``"line"``: Determine the rows by line numbers, `coord` must be formulated with the line numbers for this (compared to a row, a line is defined as the data between two line breaks + final line break).
            If `coords` is ``None``, then shift the entirety of the rows and ignore `coord_type`.

        If `unique_rows` is ``True`` (default), each row is processed only once, even if multiple coordinates apply to one.

        The return value is composed as follows:
            - At index 1 of the tuple is the :class:`ChunkLoad`.
            - At index 0 of the tuple there is a reversed list of (coordinate to :class:`WriteItem`'s) pairs:
                - An pair is composed of the coordinate at index 0 and a list of ``WriteItem``'s | ``None`` at index 1:
                    The list of ``WriteItem``'s corresponds to the rows in the coordinate, an entry is ``None`` if editing has not taken place in a row.
        The total return value can be ``None`` if nothing was edited.

        Relevant :class:`ChunkLoad` Fields:
            - `edited_ran`
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust [+] __highlighter__.prep_by_chunkload

        :return: ( [ ( coordinates: list[int, int] | int, write items: [ WriteItem | None, ... ] ), ... ], ChunkLoad ) | None

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__local_history__._lock_assert_()
        if coords and coord_type[0] == 'p':
            coord_type = 'd'
        goto = curcur = self.current_row.cursors.data_cursor

        def worker(row: _Row, coord):
            nonlocal goto
            if wi := row.shift(backshift):
                if wi.begin < curcur:
                    goto += wi.diff
            return wi

        return self.rowwork(coords, coord_type, worker, lambda: goto, unique_rows)

    def tab_replace(
            self, coords: list[list[int, int]] | list[int] | None,
            coord_type: Literal['pointing data', 'p', 'data', 'd', 'row', 'r', 'line', 'l', ''],
            *, to_char: str = " "
    ) -> tuple[list[tuple[list[int, int] | int, list[WriteItem | None]]], ChunkLoad] | None:
        r"""
        Replace tab spaces in `coords` (of type `coord_type`) `to_char`. Adjust the cursor accordingly.

        The data coordinates are defined as a list of data points ``[ <int>, ... ]`` or as a list of data ranges ``[ [<int>, <int>], ... ]`` (both must be sorted). The data type is specified by `coord_type`;
            Possible values:
                - ``"pointing data"``: Replace tab spaces of the whole rows that match the data coordinates.
                - ``"data"``: Replace tab spaces in data ranges, `coord` must be defined as a list of ranges for this type.
                - ``"row"``: Replace tab spaces in entire rows, `coord` must be formulated with the row numbers for this.
                - ``"line"``: Replace tab spaces in entire lines, `coord` must be formulated with the line numbers for this (compared to a row, a line is defined as the data between two line breaks + final line break).
            If `coords` is ``None``, then replace tab spaces of the entirety of the data and ignore `coord_type`.

        The return value is composed as follows:
            - At index 1 of the tuple is the :class:`ChunkLoad`.
            - At index 0 of the tuple there is a list of (coordinate to :class:`WriteItem`'s) pairs:
                - An pair is composed of the coordinate at index 0 and a list of ``WriteItem``'s | ``None`` at index 1:
                    The list of ``WriteItem``'s corresponds to the rows in the coordinate, an entry is ``None`` if editing has not taken place in a row.
        The total return value can be ``None`` if nothing was edited.

        Relevant :class:`ChunkLoad` Fields:
            - `edited_ran`
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust [+] __highlighter__.prep_by_chunkload

        :return: ( [ ( coordinates: list[int, int] | int, write items: [ WriteItem | None, ... ] ), ... ], ChunkLoad ) | None

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__local_history__._lock_assert_()

        cur_row = self.current_row
        goto = curcur = cur_row.cursors.data_cursor
        cur_row_num = cur_row.__row_num__
        cur_inrow_cur = cur_row.cursors.content

        def widiff(wi):
            nonlocal goto
            if wi and wi.begin < curcur:
                goto += wi.diff

        if to_char:

            def _if_in_ran_diff(_row, _start, _stop):
                nonlocal goto, if_in_ran_diff

                if cur_row_num == _row.__row_num__:
                    if _start <= cur_inrow_cur < _stop:
                        start_seg, _ = _row.cursors.tool_cnt_to_seg_in_seg(_start)
                        try:
                            stop_seg, _ = _row.cursors.tool_cnt_to_seg_in_seg(cur_inrow_cur)
                        except IndexError:
                            stop_seg = None
                        lc = len(to_char)
                        goto += sum(
                            (lc * (_row.tab_size - (len(s) % _row.tab_size))) - 1
                            for s in _row.data_cache.raster[start_seg:stop_seg])

                        if_in_ran_diff = lambda *_: widiff
                        return lambda *_: None

                    elif _stop <= cur_inrow_cur:
                        if_in_ran_diff = lambda *_: widiff
                        return lambda *_: None

                return widiff

        else:

            def _if_in_ran_diff(_row, _start, _stop):
                nonlocal goto, if_in_ran_diff

                if cur_row_num == _row.__row_num__:
                    if _start <= cur_inrow_cur < _stop:
                        start_seg, _ = _row.cursors.tool_cnt_to_seg_in_seg(_start)
                        try:
                            stop_seg, _ = _row.cursors.tool_cnt_to_seg_in_seg(cur_inrow_cur)
                        except IndexError:
                            stop_seg = None
                        goto += start_seg - stop_seg

                        if_in_ran_diff = lambda *_: widiff
                        return lambda *_: None

                    elif _stop <= cur_inrow_cur:
                        if_in_ran_diff = lambda *_: widiff
                        return lambda *_: None

                return widiff

        if_in_ran_diff = _if_in_ran_diff

        if coords and coord_type[0] != 'd':
            unique_rows = True
            if coord_type[0] == 'p':
                coord_type = 'd'

            def worker(row: _Row, coord):
                nonlocal goto
                if_in_ran_diff(row, 0, row.__next_data__)(wi := row.replace_tabs(0, None, to_char))
                return wi

        elif coords and isinstance(coords[0], int):
            raise ValueError('For coordinate type "data", the coordinates must be defined as a list of ranges.')

        else:
            unique_rows = False

            def worker(row, coord):
                if coord is None:
                    start, stop = 0, row.__next_data__
                    _work_stop = None
                else:
                    start, stop = max(0, coord[0] - row.__data_start__), coord[1] - row.__data_start__
                    _work_stop = stop
                if_in_ran_diff(row, start, stop)(wi := row.replace_tabs(start, _work_stop, to_char))
                return wi

        return self.rowwork(coords, coord_type, worker, lambda: goto, unique_rows)

    def remove(
            self, coords: list[list[int, int]] | list[int],
            coord_type: Literal['pointing data', 'p', 'data', 'd', 'row', 'r', 'line', 'l']
    ) -> tuple[list[tuple[int, list[tuple[list[str], str | Literal[False] | None]]]], ChunkLoad]:
        r"""
        Remove data from the buffer and return it. Adjust the cursor accordingly.

        The data coordinates are defined as a list of data points ``[ <int>, ... ]`` or as a list of data ranges ``[ [<int>, <int>], ... ]`` (both must be sorted). The data type is specified by `coord_type`;
            Possible values:
                - ``"pointing data"``: Remove the whole rows that match the data coordinates.
                - ``"data"``: Remove data ranges, `coord` must be defined as a list of ranges for this type.
                - ``"row"``: Remove entire rows, `coord` must be formulated with the row numbers for this.
                - ``"line"``: Remove entire lines, `coord` must be formulated with the line numbers for this (compared to a row, a line is defined as the data between two line breaks + final line break).

        The return value is composed as follows:
            - At index 1 of the tuple is the :class:`ChunkLoad`.
            - At index 0 of the tuple there is a list of items of the removed data:
                - An item is composed of the starting point of the coordinate at index 0 and a list of row data at index 1:
                    Row data is a tuple of the remoted content data (tab-separated string of printable characters) at
                    index 0 and the remoted row end (can be ``"\n"`` for a line break, ``""`` for a non-breaking line
                    break, ``None`` if the row has no line break, or ``False`` as a non-removed end) at index 1.

        Relevant :class:`ChunkLoad` Fields:
            - `edited_ran`
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust [+] __highlighter__.prep_by_chunkload

        :return: ( [ ( coord start: int, removed rows: [ ( row raster: [str], row end: "" | "\n" | None | False ), ... ] ), ... ], final chunk load item)

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__local_history__._lock_assert_()
        self._eof_metas._changed_rows_()

        if coord_type[0] != 'd':
            if coord_type[0] == 'p':
                coord_type = 'd'

            def coord_enter(row: _Row, coord):
                nonlocal rmbuffer, upper_rown, current_row, adjust_start
                current_row = row
                adjust_start = row.__data_start__
                removed.append((row.__data_start__, list()))
                rmbuffer = [row._remove_area(0, None)]
                upper_rown = row.__row_num__

            def __coord_continue(row: _Row, coord):
                nonlocal current_row
                current_row = row
                rmbuffer.append(row._remove_area(0, None))

            def _rm_end(row, len_last_rm, coord):
                return row.__data_start__ + len_last_rm

        elif isinstance(coords[0], int):
            raise ValueError('For coordinate type "data", the coordinates must be defined as a list of ranges.')

        else:

            def coord_enter(row: _Row, coord):
                nonlocal rmbuffer, upper_rown, current_row, adjust_start
                current_row = row
                adjust_start = coord[0]
                removed.append((coord[0], list()))
                rmbuffer = [row._remove_area(coord[0] - row.__data_start__, coord[1] - row.__data_start__)]
                upper_rown = row.__row_num__

            def __coord_continue(row: _Row, coord):
                nonlocal current_row
                current_row = row
                rmbuffer.append(row._remove_area(0, coord[1] - row.__data_start__))

            def _rm_end(row, len_last_rm, coord):
                return coord[1]

        upper_rown = -0
        removed: list[tuple[int, list[tuple]]] = list()
        rmbuffer: list[tuple] = list()
        chunktotal = False
        adjust_start: int
        current_row: _Row
        curcur = goto = self.current_row.cursors.data_cursor

        _coord_continue = __coord_continue

        def coord_continue(row: _Row, coord):
            _coord_continue(row, coord)

        def chunk_enter(cb: ChunkBuffer, coords):
            nonlocal chunktotal, _coord_continue
            if coords is None:
                _coord_continue = lambda *_: None
                chunktotal = True
            else:
                _coord_continue = __coord_continue
                chunktotal = False

        def coord_break(cb: ChunkBuffer, coord):
            nonlocal goto
            if chunktotal:
                removed[-1][1].extend(row.read_row_content(0, None) for row in cb.rows)
                diff = cb.__start_point_data__ - (rm_end := cb.rows[-1].data_cache.len_absdata)
                cb.rows = [_Row.__newrow__(self._future_baserow)._set_start_index_(
                    0, cb.__start_point_row_num__, cb.__start_point_line_num__, cb.__start_point_content__,
                    cb.__start_point_data__
                )]
                self.__marker__._adjust_markings(cb.__start_point_data__, diff, rm_end)
                self.__glob_cursor__._adjust_anchors(cb.__start_point_data__, diff, rm_end)
                if adjust_start <= curcur:
                    if rm_end > curcur:
                        goto = adjust_start
                    else:
                        goto += diff
            else:
                removed[-1][1].extend(rmbuffer)
                len_last_rm = -0
                rm_dat = sum((len_last_rm := (len(row[0]) + isinstance(row[1], str))) for row in rmbuffer)
                rmbuffer.clear()
                self.__marker__._adjust_markings(adjust_start, -rm_dat,
                                                 (rm_end := _rm_end(current_row, len_last_rm, coord)))
                self.__glob_cursor__._adjust_anchors(adjust_start, -rm_dat, rm_end)
                if adjust_start <= curcur:
                    if rm_end > curcur:
                        goto = adjust_start
                    else:
                        goto -= rm_dat

        (ci := self.ChunkIter(
            self, 'coords reversed + s', coords, coord_type,
            chunk_enter=chunk_enter, coord_enter=coord_enter, coord_continue=coord_continue, coord_break=coord_break
        )).run()

        with self.__local_history__.suit() as local_history:
            local_history._add_cursor(lambda: curcur)
            local_history._add_removed(removed)
        spec_pos = self._goto_data(goto)
        cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1],
                       *self.__trimmer__.action__demand__(),
                       spec_position=spec_pos, edited_ran=ci.parsed_coords.id_range)
        self.__display__.__highlighter__._prepare_by_chunkload(cl)
        self.__display__.__highlighter__._prepare_by_writeitem(upper_rown, gt_too=True)

        return removed, cl

    def delete(self) -> tuple[WriteItem, ChunkLoad] | None:
        """
        Delete the character to the right of the cursor;
        return ``None`` if there is none, ( :class:`WriteItem`, :class:`ChunkLoad` )
        otherwise.

        Relevant :class:`ChunkLoad` Fields:
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.fill [+] __trimmer__.trim
        [+] __highlighter__.prep_by_chunkload | __highlighter__.prep_by_write
        [+] __marker__.conflict [+] __marker__.adjust [+] __glob_cursor__.adjust
        [+] __glob_cursor__.note

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__local_history__._lock_assert_()
        self.__glob_cursor__.note_globc()
        self._eof_metas._changed_data_()
        self.__marker__._in_conflict(rm__eq_start=True)
        end = False
        goto = (row := self.current_row).cursors.data_cursor
        if not (wi := row.delete()):
            if row.end is not None:
                self._eof_metas._changed_rows_()
                wi = WriteItem(0, False, None, row.__data_start__ + row.cursors.content,
                               row.__row_num__,
                               1, '', row.end, -1)
                end = row.end
                with row:
                    row.end = None
                gt_too = True
            elif self.current_row_idx == len(self.rows) - 1:
                return
            else:
                row = self.rows[self.current_row_idx + 1]
                row.cursors.reset()
                wi = row.delete()
                gt_too = row.end is None
        else:
            gt_too = row.end is None

        self._adjust_rows(
            self.current_row_idx,
            self.current_row_idx,
            dat_start=goto,
            diff=-1
        )
        self._goto_data(goto)

        if end is not False:
            self.__local_history__._add_rmchr(HistoryItem.TYPEVALS.DELETED_NEWLINE, wi, end)
            cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1],
                           *self.__trimmer__.action__poll__())
        else:
            self.__local_history__._add_rmchr(HistoryItem.TYPEVALS.DELETE, wi, end)
            cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1])

        self.__display__.__highlighter__._prepare_by_chunkload(cl)
        self.__display__.__highlighter__._prepare_by_writeitem(wi.work_row, gt_too=gt_too, _row=row)
        return wi, cl

    def backspace(self) -> tuple[WriteItem, ChunkLoad] | None:
        """
        Delete the character to the left of the cursor;
        return ``None`` if there is none, ( :class:`WriteItem`, :class:`ChunkLoad` )
        otherwise.

        Relevant :class:`ChunkLoad` Fields:
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.fill [+] __trimmer__.trim
        [+] __highlighter__.prep_by_chunkload | __highlighter__.prep_by_write
        [+] __marker__.conflict [+] __marker__.adjust [+] __glob_cursor__.adjust
        [+] __glob_cursor__.note

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__local_history__._lock_assert_()
        self.__glob_cursor__.note_globc()
        self._eof_metas._changed_data_()
        self.__marker__._in_conflict(rm__beside=-1, rm__eq_start=True)
        end = False
        goto = self.current_row.cursors.data_cursor - 1
        if not (wi := (row := self.current_row).backspace()):
            if not self.current_row_idx:
                return
            else:
                gt_too = True
                self.current_row_idx -= 1
                row = self.current_row
                if row.end is not None:
                    self._eof_metas._changed_rows_()
                    wi = WriteItem(0, False, None,
                                   row.__data_start__ + row.data_cache.len_content,
                                   row.__row_num__, 1, '', row.end, -1)
                    end = row.end
                    with row:
                        row.end = None
                else:
                    with row:
                        removed = row.content[-1]
                        row.content = row.content[:-1]
                    wi = WriteItem(
                        0, False, None, row.__data_start__ + row.data_cache.len_content, row.__row_num__,
                        1, removed, None, -1, None)
        else:
            gt_too = row.end is None
        self._adjust_rows(
            (self.current_row_idx if not self.current_row_idx else self.current_row_idx - 1),
            self.current_row_idx,
            dat_start=(row := self.current_row).__data_start__ + row.cursors.content,
            diff=-1
        )
        self._goto_data(goto)

        if end is not False:
            self.__local_history__._add_rmchr(HistoryItem.TYPEVALS.BACKSPACED_NEWLINE, wi,
                                              end)
            cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1],
                           *self.__trimmer__.action__poll__())
        else:
            self.__local_history__._add_rmchr(HistoryItem.TYPEVALS.BACKSPACE, wi, end)
            cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1])

        self.__display__.__highlighter__._prepare_by_chunkload(cl)
        self.__display__.__highlighter__._prepare_by_writeitem(wi.work_row, gt_too=gt_too, _row=row)
        return wi, cl

    def find(self, regex: Pattern | str, end: Literal["", "\n"] | None | bool = False, *,
             all: bool = False, reverse: bool = False) -> list[tuple[_Row, Match]]:
        r"""
        Find the regular expression, starting from the current row, before the cursor or find `reverse`.

        If `end` is ``""``, ``"\n"`` or ``None``, the ``end`` of a :class:`_Row` is part of the condition and must be
        exactly the same, if `end` is ``True`` the end of a row must be ``""`` or ``"\n"``, ``False`` skips the
        comparison.

        If `all` is ``True``, the search is started from the top and all matches are returned.

        The return value for matches is:  ( :class:`_Row`, ``re.Match`` )
        """
        if end is True:
            def eval_end(___row):
                return isinstance(___row.end, str)
        elif end is False:
            def eval_end(___row):
                return True
        else:
            def eval_end(___row):
                return end == ___row.end

        if all:
            matches = list()
            for row, _ in self.ChunkIter(self, 'm'):
                if not eval_end(row):
                    continue
                for m in finditer(regex, row.content):
                    matches.append((row, m))
            if reverse:
                matches.reverse()
            return matches
        else:
            row = self.current_row
            if reverse:
                for m in reversed(list(finditer(regex, row.content))):
                    if m.start() < row.cursors.content:
                        return [(row, m)]

                def _find(start, rows):
                    while start >= 0:
                        _row = rows[start]
                        start -= 1
                        if not eval_end(_row):
                            continue
                        if __m := list(finditer(regex, _row.content)):
                            return [(_row, __m[-1])]

                if self.current_row_idx and (m := _find(self.current_row_idx - 1, self.rows)):
                    return m
            else:
                if eval_end(row) and (m := list(finditer(regex, row.content))):
                    for _m in m:
                        if _m.start() > row.cursors.content:
                            return [(row, _m)]

                def _find(rows):
                    for _row in rows:
                        if not eval_end(_row):
                            continue
                        if __m := search(regex, _row.content):
                            return [(_row, __m)]

                if m := _find(self.rows[self.current_row_idx + 1:]):
                    return m

            if self.__swap__:
                self.__swap__.__meta_index__.adjust_bottom_auto()
                if reverse:
                    posids = self.__swap__.positions_top_ids
                    for cpos in reversed(posids):
                        if m := _find(len(_rows := self.ChunkBuffer(self, cpos, True, False).rows) - 1, _rows):
                            return m
                else:
                    posids = self.__swap__.positions_bottom_ids
                    for cpos in posids:
                        if m := _find(self.ChunkBuffer(self, cpos, True, False).rows):
                            return m

            return []

    def cursor_set(self, n_row_index: int, n_column: int, as_far: bool = False) -> bool:
        """
        Set the cursor to the `n_column` in `n_row_index`; in case of errors `as_far` as possible.
        Return whether the cursor was set.
        """
        if (_max := len(self.rows) - 1) >= n_row_index >= 0:
            pass
        elif as_far:
            n_row_index = max(0, min(n_row_index, _max))
        else:
            return False
        if (_max := self.rows[n_row_index].cursors.content_limit) >= n_column >= 0:
            pass
        elif as_far:
            n_column = max(0, min(n_column, _max))
        else:
            return False
        self.current_row_idx = n_row_index
        self.current_row.cursors.set_by_cnt(n_column)
        return True

    def cursor_new(
            self,
            z_row: int = None, z_column: int = None,
            jump: bool = False, mark_jump: bool = False,
            border: bool = False, as_far: bool = False
    ) -> tuple[int | None, int | None] | int | None:
        """
        Calculate new cursor coordinates.

        :param z_row: This summand is added to the current row position.
        :param z_column: This summand is added to the current column position. Or direction hint for `jump`, `mark_jump` and `border`.
        :param jump: Jump to a predefined location.
        :param mark_jump: Jump to the next boundary point of a marking.
        :param border: Jump to the beginning or end of a row.
        :param as_far: in case of errors, as far as possible.

        :return: (new row, new column) | boundary point of a marking | None
        """
        if z_row is None:
            row = None
            col_row = self.current_row_idx
        elif (_max := len(self.rows) - 1) >= (row := self.current_row_idx + z_row) >= 0:
            col_row = row
        elif as_far:
            col_row = row = max(0, min(row, _max))
        else:
            return

        if z_column is None:
            column = None
        elif mark_jump:
            return self.__marker__.mark_jump_point(z_column)
        elif (column := self.rows[col_row].cursors.new_cnt_cursor(z_column, jump, border, as_far)) is None:
            return

        return row, column

    def cursor_move(
            self, *,
            z_row: int = None, z_column: int = None,
            jump: bool = False, mark_jump: bool = False,
            border: bool = False, as_far: bool = False,
            mark: bool = False, cross: bool = True
    ) -> ChunkLoad | None:
        """
        Move the cursor and return :class:`ChunkLoad` if the cursor was moved, otherwise ``None``.

        Relevant :class:`ChunkLoad` Fields:
            - `spec_position` (possible with mark_jump or __marker__.backjump_mode)
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __swap__.fill [+] __trimmer__.trim [+] __highlighter__.prep_by_chunkload [+] __glob_cursor__.note

        :param z_row: This summand is added to the current row position.
        :param z_column: This summand is added to the current column position. Or direction hint for `jump`, `mark_jump` and `border`.
        :param jump: Jump to a predefined location.
        :param mark_jump: Jump to the next boundary point of a marking.
        :param border: Jump to the beginning or end of a row.
        :param as_far: In case of errors, as far as possible.
        :param mark: Expand / create a marker.
        :param cross: Allow the crossing of the row borders.

        :raises CursorError: following are only possible if mark_jump used or mark-back-jump triggered and the
          datapoint is not reachable.
          
        :raises CursorChunkLoadError: if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are not available.
        :raises CursorChunkMetaError: Chunks of the required side could not be loaded sufficiently.
          The closest chunk was loaded and the cursor was placed at the beginning of the first row.
        :raises CursorPlacingError: if an error occurs during the final setting of the cursor (indicator of too high value).
          The cursor was set to the next possible position.
        :raises CursorNegativeIndexingError: when the final value is negative.

        :raises AssertionError: mark_jump used or mark-back-jump triggered and __local_history__ lock is engaged.
        """
        if self.__marker__ and not (jump or mark_jump or border or as_far) and (
                trend := (z_column or z_row)) is not None:
            if (dat_pos := self.__marker__.ready(mark, trend)) is not None:
                return self.goto_data(dat_pos)
        else:
            self.__marker__.ready(mark)
        moved = False
        if (cursor := self.cursor_new(
                z_row=z_row,
                z_column=z_column,
                jump=jump,
                mark_jump=mark_jump,
                border=border,
                as_far=as_far
        )) is not None:
            if mark_jump:
                return self.goto_data(cursor)
            row, column = cursor
            if row is not None:
                if column is None:
                    column = min(
                        self.__glob_cursor__.get_globc(self.current_row.cursors.content),
                        self.rows[row].cursors.content_limit
                    )
                if mark:
                    if row > self.current_row_idx:
                        for i in range(self.current_row_idx + 1, row):
                            self.__marker__.set(self.rows[i].__data_start__)
                    else:
                        for i in range(self.current_row_idx - 1, row, -1):
                            self.__marker__.set(self.rows[i].__data_start__)
                self.cursor_set(row, column)
                self.__marker__.set_current(mark)
                moved = True
            elif column is not None:
                self.__glob_cursor__.note_globc()
                self.current_row.cursors.set_by_cnt(column)
                self.__marker__.set_current(mark)
                moved = True
        elif cross and z_row is None and z_column is not None and not mark_jump:
            self.__glob_cursor__.note_globc()
            if z_column < 0:
                if self.current_row_idx:
                    self.cursor_set(*self.cursor_new(z_row=-1, z_column=1, border=True))
                    self.__marker__.set_current(mark)
                    moved = True
            elif self.current_row_idx != len(self.rows) - 1:
                self.cursor_set(*self.cursor_new(z_row=1, z_column=0, border=True))
                self.__marker__.set_current(mark)
                moved = True

        if moved:
            cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1],
                           *self.__trimmer__.action__poll__())
            self.__display__.__highlighter__._prepare_by_chunkload(cl)
            return cl

    def _goto_chunk(self, position_id: int, autofill: bool = False) -> ChunkLoad:
        """
        Dump the currently loaded chunks then load a specific chunk.

        Return:
            :class:`ChunkLoad`
            
        Relevant :class:`ChunkLoad` Fields:
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __swap__.fill [+] __trimmer__.trim [+] __glob_cursor__.note

        :raises CursorChunkLoadError: if the position is not available.
        """
        top_id, btm_id = self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1]
        if self.__swap__:
            if not position_id or (position_id < top_id or position_id > btm_id):
                raise CursorChunkLoadError(position_id, " - not available")
            self.__glob_cursor__.note_globc()
            if position_id > 0:
                self.__swap__._dump_current_buffer(0)
            else:
                self.__swap__._dump_current_buffer(1)
            self.current_row_idx = 0
            self.current_row.cursors.reset()
            chunk = self.__swap__._pop_specific(position_id)
            self.rows = [
                _Row.__newrow__(self._future_baserow)._set_start_index_(
                    0,
                    chunk.start_point_row,
                    chunk.start_point_linenum,
                    chunk.start_point_content,
                    chunk.start_point_data
                )
            ]
            self.__start_point_data__ = chunk.start_point_data
            self.__start_point_content__ = chunk.start_point_content
            self.__start_point_row_num__ = chunk.start_point_row
            self.__start_point_line_num__ = chunk.start_point_linenum

            self.__swap__._load_chunk(position_id, chunk)

            if autofill:
                return ChunkLoad(top_id, btm_id, *self.__trimmer__.action__demand__(), spec_position=position_id)
            else:
                return ChunkLoad(top_id, btm_id, spec_position=position_id)
        else:
            return ChunkLoad(top_id, btm_id)

    def goto_chunk(self, position_id: int, autofill: bool = False) -> ChunkLoad:
        """
        Dump the currently loaded chunks then load a specific chunk.
        Record the current position in ``__local_history__`` beforehand.

        Return:
            :class:`ChunkLoad`
        
        Relevant :class:`ChunkLoad` Fields:
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.fill [+] __trimmer__.trim
        [+] __highlighter__.prep_by_chunkload [+] __glob_cursor__.note

        :raises CursorChunkLoadError: if the position is not available.
        """
        if self.__swap__:
            self.__local_history__._lock_assert_()
            self.__local_history__._add_cursor(lambda: self.current_row.cursors.data_cursor)
            cl = self._goto_chunk(position_id, autofill)
            self.__display__.__highlighter__._prepare_by_chunkload(cl)
            return cl

        return ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1])

    def goto_row(self, __n: int = 0, *, to_bottom: bool = False, as_far: bool = False) -> ChunkLoad:
        """
        Go to the beginning of the row with number n, as far as possible instead of raising the
        ``CursorChunkLoadError`` or to the last one.
        Record the current position in ``__local_history__`` beforehand.

        Return:
            :class:`ChunkLoad`
        
        Relevant :class:`ChunkLoad` Fields:
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __highlighter__.prep_by_chunkload [+] __glob_cursor__.note

        :raises AssertionError: __local_history__ lock is engaged.
        :raises CursorChunkLoadError: if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are available.
        :raises CursorNegativeIndexingError: when a negative value is passed and `as_far` is False.
        """
        self.__local_history__._lock_assert_()
        self.__local_history__._add_cursor(lambda: self.current_row.cursors.data_cursor)
        self.__glob_cursor__.note_globc()

        top_id, btm_id = self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1]
        pos_id = None

        if __n < 0:
            if as_far:
                __n = 0
            else:
                raise CursorNegativeIndexingError

        def to_b():
            nonlocal __n, pos_id
            if self.__swap__.current_chunk_ids[1]:
                self._goto_chunk(pos_id := 1)
            __n = self.rows[-1].__row_num__

        if to_bottom:
            to_b()
        elif self.rows[0].__row_num__ > __n:
            if __n < 0:
                if as_far:
                    self._goto_chunk(pos_id := -1)
                    __n = 0
                else:
                    raise CursorChunkLoadError(__n, " - unable to load top chunks")
            else:
                self.__swap__.__meta_index__.adjust_bottom_auto()
                chunk_top_ids = self.__swap__.positions_top_ids
                __lcti = len(chunk_top_ids)
                __mcti = __lcti // 2
                __i = 0

                def __search():
                    nonlocal __i, __mcti
                    if (x := self.__swap__.__meta_index__[self.__swap__.slot(
                            chunk_top_ids[(_i := __i + __mcti)])].start_point_row) < __n:
                        __i = _i
                        if _mcti := __mcti // 2:
                            __mcti = _mcti
                            __search()
                    elif x == __n:
                        __i = _i
                    else:
                        if _mcti := __mcti // 2:
                            __mcti = _mcti
                            __search()

                try:
                    __search()
                except IndexError:
                    pass

                for i in range(__i, -1, -1):
                    if self.__swap__.__meta_index__[
                        self.__swap__.slot(tid := chunk_top_ids[i])].start_point_row <= __n:
                        self._goto_chunk(pos_id := tid)
                        break
                else:
                    if as_far:
                        if chunk_top_ids:
                            self._goto_chunk(pos_id := -1)
                        __n = self.rows[0].__row_num__
                    else:
                        raise CursorChunkLoadError(__n, " - unable to load top chunks")

        elif self.rows[-1].__row_num__ < __n:
            self.__swap__.__meta_index__.adjust_bottom_auto()
            chunk_bottom_ids = self.__swap__.positions_bottom_ids
            __lcbi = len(chunk_bottom_ids)
            __mcbi = __lcbi // 2
            __i = 0

            def __search():
                nonlocal __i, __mcbi
                if self.__swap__.__meta_index__[self.__swap__.slot(
                        chunk_bottom_ids[(_i := __i + __mcbi)])].start_point_row < __n:
                    __i = _i
                    if _mcbi := __mcbi // 2:
                        __mcbi = _mcbi
                        __search()
                else:
                    if _mcbi := __mcbi // 2:
                        __mcbi = _mcbi
                        __search()

            try:
                __search()
            except IndexError:
                pass

            _ppos = None
            for i in range(__i, __lcbi):
                if (_lrn := self.__swap__.__meta_index__[
                    self.__swap__.slot(bid := chunk_bottom_ids[i])].start_point_row) == __n:
                    self._goto_chunk(pos_id := bid)
                    break
                elif _lrn > __n:
                    self._goto_chunk(pos_id := _ppos)
                    break
                _ppos = bid
            else:
                if _ppos and self.ChunkBuffer(self, _ppos, True, False).rows[-1].__row_num__ >= __n:
                    self._goto_chunk(pos_id := _ppos)
                elif as_far:
                    to_b()
                else:
                    raise CursorChunkLoadError(__n, " - unable to load bottom chunks")

        for i in range(len(self.rows)):
            if self.rows[i].__row_num__ == __n:
                self.cursor_set(i, 0)
                break

        cl = ChunkLoad(top_id, btm_id,
                       *(self.__trimmer__.action__demand__()
                         if pos_id
                         else self.__trimmer__.action__poll__()),
                       spec_position=pos_id)
        self.__display__.__highlighter__._prepare_by_chunkload(cl)
        return cl

    def goto_line(self, __n: int = 0, *, to_bottom: bool = False, as_far: bool = False) -> ChunkLoad:
        """
        Go to the beginning of the line with number n, as far as possible instead of raising the
        ``CursorChunkLoadError`` or to the last one.
        Record the current position in ``__local_history__`` beforehand.

        Return:
            :class:`ChunkLoad`
        
        Relevant :class:`ChunkLoad` Fields:
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __highlighter__.prep_by_chunkload [+] __glob_cursor__.note

        :raises AssertionError: __local_history__ lock is engaged.
        :raises CursorChunkLoadError: if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are available.
        :raises CursorNegativeIndexingError: when a negative value is passed and `as_far` is False.
        """
        self.__local_history__._lock_assert_()
        self.__local_history__._add_cursor(lambda: self.current_row.cursors.data_cursor)

        top_id, btm_id = self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1]
        pos_id = None

        if __n < 0:
            if as_far:
                __n = 0
            else:
                raise CursorNegativeIndexingError

        def to_b(top_ids: tuple[int] = None, bottom_ids: tuple[int] = None,
                 index: dict[int, ChunkData] = None):
            nonlocal __n, pos_id
            if bottom_ids:
                _last_chunk_line = index[self.__swap__.slot(bottom_ids[-1])].start_point_linenum
                __i = len(bottom_ids) - 1
                while __i >= 0:
                    if index[self.__swap__.slot(bottom_ids[__i])].start_point_linenum != _last_chunk_line:
                        self._goto_chunk(pos_id := bottom_ids[__i + 1])
                        break
                    __i -= 1
            else:
                _last_chunk_line = self.__start_point_line_num__
            if top_ids and pos_id is None:
                if self.__start_point_line_num__ == index[
                    self.__swap__.slot(top_ids[-1])].start_point_linenum == _last_chunk_line:
                    __i = len(top_ids) - 1
                    while __i >= 0:
                        if index[self.__swap__.slot(top_ids[__i])].start_point_linenum != _last_chunk_line:
                            self._goto_chunk(pos_id := top_ids[__i + 1])
                            break
                        __i -= 1

            __n = self.rows[-1].__line_num__

        self.__glob_cursor__.note_globc()

        self.__swap__.__meta_index__.adjust_bottom_auto()
        chunk_top_ids, chunk_bottom_ids = self.__swap__.positions_top_ids, self.__swap__.positions_bottom_ids

        if to_bottom:
            to_b(chunk_top_ids, chunk_bottom_ids, self.__swap__.__meta_index__)
        elif self.rows[0].__line_num__ == __n:
            if chunk_top_ids:
                _pos = None
                i = -1
                try:
                    while (meta := self.__swap__.__meta_index__[
                        self.__swap__.slot(chunk_top_ids[i])
                    ]).start_point_linenum + meta.nnl == __n:
                        _pos = chunk_top_ids[i]
                        i -= 1
                except IndexError:
                    pass
                if _pos:  # cant be 0
                    self._goto_chunk(pos_id := _pos)
            else:
                __n = self.rows[0].__line_num__
        elif self.rows[0].__line_num__ > __n:
            if chunk_top_ids:

                __lcti = len(chunk_top_ids)
                __mcti = __lcti // 2
                __i = 0

                def __search():
                    nonlocal __i, __mcti
                    if self.__swap__.__meta_index__[self.__swap__.slot(
                            chunk_top_ids[(_i := __i + __mcti)])].start_point_linenum < __n:
                        __i = _i
                        if _mcti := __mcti // 2:
                            __mcti = _mcti
                            __search()
                    else:
                        if _mcti := __mcti // 2:
                            __mcti = _mcti
                            __search()

                try:
                    __search()
                except IndexError:
                    pass

                for i in range(__i, __lcti):
                    if (meta := self.__swap__.__meta_index__[
                        self.__swap__.slot(chunk_top_ids[i])
                    ]).start_point_linenum + meta.nnl >= __n:
                        self._goto_chunk(pos_id := chunk_top_ids[i])
                        break
                else:
                    if as_far:
                        self._goto_chunk(pos_id := chunk_top_ids[0])
                        __n = self.rows[0].__line_num__
                    else:
                        raise CursorChunkLoadError(__n, " - unable to load top chunks")
            elif as_far:
                __n = self.rows[0].__line_num__
            else:
                raise CursorChunkLoadError(__n, " - unable to load top chunks")
        elif self.rows[-1].__line_num__ < __n:
            if chunk_bottom_ids:

                __lcbi = len(chunk_bottom_ids)
                __mcbi = __lcbi // 2
                __i = 0

                def __search():
                    nonlocal __i, __mcbi
                    if (x := (meta := self.__swap__.__meta_index__[
                        self.__swap__.slot(chunk_bottom_ids[(_i := __i + __mcbi)])
                    ]).start_point_linenum + meta.nnl) > __n:
                        if _mcbi := __mcbi // 2:
                            __mcbi = _mcbi
                            __search()
                    elif x == __n:
                        __i = _i
                    else:
                        __i = _i
                        if _mcbi := __mcbi // 2:
                            __mcbi = _mcbi
                            __search()

                try:
                    __search()
                except IndexError:
                    pass

                for i in range(__i, __lcbi):
                    if (meta := self.__swap__.__meta_index__[
                        self.__swap__.slot(chunk_bottom_ids[i])
                    ]).start_point_linenum + meta.nnl >= __n:
                        self._goto_chunk(pos_id := chunk_bottom_ids[i])
                        break
                else:
                    if as_far:
                        self._goto_chunk(pos_id := 1)
                        __n = self.rows[-1].__line_num__
                    else:
                        raise CursorChunkLoadError(__n, " - unable to load bottom chunks")
            elif as_far:
                __n = self.rows[-1].__line_num__
            else:
                raise CursorChunkLoadError(__n, " - unable to load bottom chunks")

        for i in range(len(self.rows)):
            if self.rows[i].__line_num__ == __n:
                self.cursor_set(i, 0)
                break

        cl = ChunkLoad(top_id, btm_id,
                       *(self.__trimmer__.action__demand__()
                         if pos_id
                         else self.__trimmer__.action__poll__()),
                       spec_position=pos_id)
        self.__display__.__highlighter__._prepare_by_chunkload(cl)
        return cl

    def _goto_data(self, __n: int) -> int | None:
        """
        Go to data point n.

        [+] __swap__.adjust

        :return: `position_id` if a specific chunk was loaded

        :raises CursorChunkLoadError: if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are not available.
        :raises CursorChunkMetaError: Chunks of the required side could not be loaded sufficiently.
          The closest chunk was loaded and the cursor was placed at the beginning of the first row.
        :raises CursorPlacingError: if an error occurs during the final setting of the cursor (indicator of too high value).
          The cursor was set to the next possible position.
        :raises CursorNegativeIndexingError: when a negative value is passed.
        """
        err = pos_id = None
        if __n < 0:
            raise CursorNegativeIndexingError
        if self.__start_point_data__ > __n:
            self.__swap__.__meta_index__.adjust_bottom_auto()
            if not (self.__swap__ and (
                    chunk_top_ids := self.__swap__.positions_top_ids) and self.__swap__.__meta_index__):
                raise CursorChunkLoadError(__n, " - unable to load top chunks")
            else:

                __lcti = len(chunk_top_ids)
                __mcti = __lcti // 2
                __i = 0

                def __search():
                    nonlocal __i, __mcti
                    if (x := self.__swap__.__meta_index__[self.__swap__.slot(
                            chunk_top_ids[(_i := __i + __mcti)])].start_point_data) < __n:
                        __i = _i
                        if _mcti := __mcti // 2:
                            __mcti = _mcti
                            __search()
                    elif x == __n:
                        __i = _i
                    else:
                        if _mcti := __mcti // 2:
                            __mcti = _mcti
                            __search()

                try:
                    __search()
                except IndexError:
                    pass

                p_i = None
                try:
                    for i in range(__i, __lcti):
                        if self.__swap__.__meta_index__[self.__swap__.slot(chunk_top_ids[i])].start_point_data > __n:
                            self._goto_chunk(pos_id := chunk_top_ids[p_i])
                            break
                        p_i = i
                    else:
                        if p_i is not None:
                            self._goto_chunk(pos_id := chunk_top_ids[p_i])
                        else:
                            err = -1
                except TypeError:
                    err = -1

        elif self.rows[-1].__next_data__ < __n:
            self.__swap__.__meta_index__.adjust_bottom_auto()
            if not (self.__swap__ and (
                    chunk_bottom_ids := list(self.__swap__.positions_bottom_ids)) and self.__swap__.__meta_index__):
                raise CursorChunkLoadError(__n, " - unable to load bottom chunks")
            else:
                __lcbi = len(chunk_bottom_ids)
                __mcbi = __lcbi // 2
                __i = 0

                def __search():
                    nonlocal __i, __mcbi
                    if (x := self.__swap__.__meta_index__[self.__swap__.slot(
                            chunk_bottom_ids[(_i := __i + __mcbi)])].start_point_data) > __n:
                        if _mcbi := __mcbi // 2:
                            __mcbi = _mcbi
                            __search()
                    elif x == __n:
                        __i = _i
                    else:
                        __i = _i
                        if _mcbi := __mcbi // 2:
                            __mcbi = _mcbi
                            __search()

                try:
                    __search()
                except IndexError:
                    pass

                p_i = None
                try:
                    for i in range(__i, __lcbi):
                        if self.__swap__.__meta_index__[self.__swap__.slot(chunk_bottom_ids[i])].start_point_data > __n:
                            self._goto_chunk(pos_id := chunk_bottom_ids[p_i])
                            break
                        p_i = i
                    else:
                        if p_i is not None:
                            self._goto_chunk(pos_id := chunk_bottom_ids[p_i])
                        else:
                            err = 1
                except TypeError:
                    err = 1

        if err:
            self._goto_chunk(err)
            self.cursor_set(0, 0)
            raise CursorChunkMetaError(__n, " - chunk load not sufficiently")
        for i in range(len(self.rows) - 1, -1, -1):
            if (_start_p := self.rows[i].__data_start__) <= __n:
                if not self.cursor_set(i, (_n := __n - _start_p)):
                    self.cursor_set(i, _n, as_far=True)
                    row = self.current_row.__row_num__
                    col = self.current_row.cursors.content
                    dat = self.current_row.cursors.data_cursor
                    raise CursorPlacingError(__n, " - setting cursor failed, set as far: dat=", dat, ":row=", row, ":col=", col)
                break

        return pos_id

    def goto_data(self, __n: int) -> ChunkLoad:
        """
        Go to data point n.
        Record the current position in ``__local_history__`` beforehand.

        Return:
            :class:`ChunkLoad`
        
        Relevant :class:`ChunkLoad` Fields:
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __highlighter__.prep_by_chunkload [+] __glob_cursor__.note

        :raises CursorChunkLoadError: if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are not available.
        :raises CursorChunkMetaError: Chunks of the required side could not be loaded sufficiently.
          The closest chunk was loaded and the cursor was placed at the beginning of the first row.
        :raises CursorPlacingError: if an error occurs during the final setting of the cursor (indicator of too high value).
          The cursor was set to the next possible position.
        :raises CursorNegativeIndexingError: when a negative value is passed.

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__local_history__._lock_assert_()
        self.__local_history__._add_cursor(lambda: self.current_row.cursors.data_cursor)
        cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1],
                       *(self.__trimmer__.action__demand__()
                         if (spec_chunk_load := self._goto_data(__n))
                         else self.__trimmer__.action__poll__()),
                       spec_position=spec_chunk_load)
        self.__display__.__highlighter__._prepare_by_chunkload(cl)
        self.__glob_cursor__.note_globc()
        return cl

    @overload
    def resize(self, *, size_top_row: int = ..., size_future_row: int = ...,
               trimmer__rows_maximal: int = ..., trimmer__chunk_size: int = ...
               ) -> ChunkLoad:
        ...

    @overload
    def resize(self, *, size_top_row: int = ..., size_future_row: int = ...,
               trimmer__rows_maximal: int = ..., trimmer__last_row_maxsize: int = ...
               ) -> ChunkLoad:
        ...

    def resize(self, **kwargs: int) -> ChunkLoad:
        """
        Change the parameterization of the maximum lengths of the rows and perform an adjustment.

        Return:
            :class:`ChunkLoad`
        
        Relevant :class:`ChunkLoad` Fields:
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim [+] __highlighter__.prep_by_chunkload
        [+] __marker__.adjust [+] __glob_cursor__.adjust
        """
        for itm in (
                (self._top_baserow, 'size_top_row'),
                (self._future_baserow, 'size_future_row'),
                (self._last_baserow, 'trimmer__last_row_maxsize')):
            try:
                itm[0]._resize(kwargs[itm[1]])
            except KeyError:
                pass

        if self.__trimmer__:
            for row in self.rows:
                row._resize_bybaserow(self._future_baserow)

            self.__trimmer__._resize(
                kwargs.get('trimmer__rows_maximal', None),
                kwargs.get('trimmer__chunk_size', kwargs.get('trimmer__last_row_maxsize', None)))

            self.__trimmer__.__call__()

        elif self.rows[0].__row_num__ == 0:
            self.rows[0]._resize_bybaserow(self._top_baserow)
            for row in self.rows[1:]:
                row._resize_bybaserow(self._future_baserow)
        else:
            for row in self.rows:
                row._resize_bybaserow(self._future_baserow)

        goto = self.current_row.cursors.data_cursor
        self._adjust_rows(0, endings=True)
        spec_pos = self._goto_data(goto)
        cl = ChunkLoad(self.__swap__.current_chunk_ids[0], self.__swap__.current_chunk_ids[1],
                       *self.__trimmer__.action__demand__(), spec_position=spec_pos)
        self.__display__.__highlighter__._prepare_by_chunkload(cl)

        return cl

    def reader(self, *,
               bin_mode: bool | str = False,
               endings: dict[Literal['', '\n'] | None, bytes] = None,
               tabs_to_blanks: int | bool = False,
               replace_tabs: bytes = None,
               progress: int = 0,
               dat_ranges: list[list[int, int]] = None) -> Reader:
        """
        Factory method for :class:`Reader`.
        """
        return Reader(self, bin_mode=bin_mode, endings=endings, tabs_to_blanks=tabs_to_blanks,
                      replace_tabs=replace_tabs, progress=progress, dat_ranges=dat_ranges)

    def export_bufferdb(self,
                        dst: str | Literal['file:...<uri>'] | SQLConnection,
                        *,
                        invoke_marker: bool = True,
                        invoke_history: bool = True,
                        invoke_cursor_anchors: bool = True) -> None:
        """
        Export a backup database in sqlite 3 format; invoke_* component data.
        The destination database can be defined by an ordinary path, a URI or a SQL connection.

        :raises ValueError: if ":history:" , ":swap:" or ":memory:" is used as `dst`.
        :raises DatabaseError: unspecific sql database error.
        :raises DatabaseFilesError: `dst` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        if isinstance(dst, SQLConnection):
            db = dst
        else:
            if dst in (':memory:', ':swap:', ':history:'):
                raise ValueError('":history:" , ":swap:" or ":memory:" is not designated as a destination.')
            if path := _sql.path_from_uri(dst):
                if path[1]:
                    raise ValueError('"mode=memory" is not designated as a destination.')
                path = path[0]
            else:
                path = dst
            with _sql.DATABASE_FILES_ERROR_SUIT:
                if Path(path).exists():
                    raise DatabaseFilesError("file exists: ", path)
            db = sql_connect(dst, check_same_thread=False, uri=True)
        cur = db.cursor()
        with _sql.DATABASE_TABLE_ERROR_SUIT:
            try:
                cur.execute(
                    'CREATE TABLE main_metas (swap INT, history INT, marker INT, markings TEXT, cursor INT, anchors TEXT)')
            except SQLOperationalError as e:
                raise DatabaseTableError(*e.args)
        cur.execute(
            'INSERT INTO main_metas VALUES (?, ?, ?, NULL, ?, NULL)', (
                int(bool(self.__swap__)), int(bool(self.__local_history__)), int(bool(self.__marker__)),
                self.current_row.cursors.data_cursor))
        if not self.__swap__:
            _Swap(__buffer__=self,
                  db_path=':memory:',
                  from_db=None,
                  unlink_atexit=False,
                  rows_maximal=0,
                  keep_top_row_size=False,
                  load_distance=0).backup(db)
        else:
            self.__swap__.backup(db)
        if invoke_cursor_anchors:
            cur.execute('UPDATE main_metas SET anchors = ?', (repr(self.__glob_cursor__.cursor_anchors),))
        if invoke_marker and self.__marker__:
            cur.execute('UPDATE main_metas SET markings = ?', (repr(self.__marker__.markings),))
            if invoke_history:
                self.__local_history__.backup(db)
        elif invoke_history and self.__marker__:
            self.__local_history__._add_marks(HistoryItem.TYPEVALS.MARKERCOMMENTS.PURGED, self.__marker__.sorted_copy)
            self.__local_history__.backup(db)
        elif invoke_history:
            self.__local_history__.backup(db)
        db.commit()
        db.close()

    def import_bufferdb(self, src: str | Literal['file:...<uri>'] | SQLConnection,
                        *,
                        init: bool = False,
                        warnings: bool = False,
                        errors: bool = True,
                        critical: bool = True) -> None:
        """
        Import a sqlite 3 backup database.

        :param src: The source database can be defined by an ordinary path, a URI or a SQL connection.
        :param init: Reinitialize the buffer and components if the buffer is not in the initial state.
        :param warnings: Raise warnings (if a component is present in the buffer but corresponding data is missing in the database).
        :param errors: Raise errors (if a component is not present in the buffer but corresponding data is in the database).
        :param critical: Raise critical errors (when a swap is not present in the buffer but corresponding data is in the database).
            Reads the first chunk from above into the buffer when ignored. [ ! ] Makes the buffer unstable.

        :raises DatabaseError: unspecific sql database error.
        :raises DatabaseFilesError: `src` not exists.

        :raises CursorError: following are possible if the datapoint of the cursor from the database is not reachable.

        :raises CursorChunkLoadError: if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are not available.
        :raises CursorChunkMetaError: Chunks of the required side could not be loaded sufficiently.
          The closest chunk was loaded and the cursor was placed at the beginning of the first row.
        :raises CursorPlacingError: if an error occurs during the final setting of the cursor (indicator of too high value).
          The cursor was set to the next possible position.
        :raises CursorNegativeIndexingError: when a negative value is passed.
        """
        if (self.__local_history__._current_item or self.__local_history__._chronicle_progress_id or
                self.__swap__.current_chunk_ids[0] or self.__swap__.current_chunk_ids[1] or
                self.__marker__.markings or len(self.rows) > 1 or self.rows[0]):
            if init:
                self.reinitialize()
            else:
                raise ConfigurationError('TextBuffer not in initial state')

        if isinstance(src, SQLConnection):
            db = src
        elif not Path(src).is_file():
            raise DatabaseFilesError("file not exists: ", src)
        else:
            db = sql_connect(src, check_same_thread=False, uri=True)
        cur = db.cursor()
        has_sw, has_hi, has_mk, markings, cursor, anchors = cur.execute('SELECT * FROM main_metas').fetchone()

        def init_swap():

            def _init():
                self.__swap__.unlink()
                self.__swap__ = self.__swap__.__new_db__(from_db=db)
                self.__swap__._load_chunk(0, self.__swap__._pop_current(0))
                self.__trimmer__.action__demand__()

            def _load():
                swap = _Swap(__buffer__=self,
                             db_path=':memory:',
                             from_db=None,
                             unlink_atexit=False,
                             rows_maximal=100,
                             keep_top_row_size=False,
                             load_distance=0)
                current_chunk_ids, _, _, _ = cur.execute(
                    'SELECT * FROM swap_metas WHERE cur_ids IS NOT NULL').fetchone()
                swap.current_chunk_ids = literal_eval(current_chunk_ids)
                _, _, position, slot = cur.execute(
                    'SELECT * FROM swap_metas WHERE slot_index_key = ?', (swap.current_chunk_ids[0],)).fetchone()
                swap.__slot_index__ = {position: slot}
                swap.sql_cursor.executemany('INSERT INTO swap_rows VALUES (?, ?, ?)',
                                            cur.execute('SELECT * FROM swap_rows WHERE slot = ?', (slot,)).fetchall()
                                            )
                swap.__meta_index__[slot] = ChunkMetaItem(*cur.execute(
                    'SELECT * FROM swap_chunk_index WHERE slot = ?', (slot,)).fetchone()[1:]
                                                                   )
                swap._load_chunk(0, swap._pop_current(0))
                swap.unlink()

            if has_sw:
                if not self.__swap__:
                    if critical:
                        raise ConfigurationError('__swap__ not initialled')
                    else:
                        _load()
                else:
                    _init()
            elif self.__swap__:
                if warnings:
                    raise ConfigurationWarning('__swap__ not required')
                else:
                    _init()
            else:
                _load()

        def init_history():
            if has_hi:
                if not self.__local_history__:
                    if errors:
                        raise ConfigurationError('__local_history__ not initialled')
                else:
                    self.__local_history__.unlink()
                    self.__local_history__ = self.__local_history__.__new_db__(from_db=db)
            elif self.__local_history__:
                if warnings:
                    raise ConfigurationWarning('__local_history__ not required')
                else:
                    self.__local_history__.unlink()
                    self.__local_history__ = self.__local_history__.__new_db__()

        if self.__local_history__.db_path == ':swap:':
            init_swap()
            init_history()
        else:
            init_history()
            init_swap()

        if has_mk:
            if not self.__marker__:
                if errors:
                    raise ConfigurationError('__marker__ not initialled')
            elif markings:
                self.__marker__.markings = [_Marking.make(ran) for ran in literal_eval(markings)]
        elif self.__marker__ and warnings:
            raise ConfigurationWarning('__marker__ not required')

        if anchors:
            self.__glob_cursor__.cursor_anchors = literal_eval(anchors)

        self._goto_data(cursor)

    def reinitialize(self) -> None:
        """
        Reinitialize the buffer.
        
        [+] __local_history__ [+] __swap__ [+] __marker__ [+] __highlighter__.prep_by_none
        """
        if self.__local_history__.db_path == ':swap:':
            self.__local_history__.unlink()
            self.__swap__.unlink()
            self.__swap__ = self.__swap__.__new_db__()
            self.__local_history__ = self.__local_history__.__new_db__()
        else:
            self.__swap__.unlink()
            self.__local_history__.unlink()
            self.__local_history__ = self.__local_history__.__new_db__()
            self.__swap__ = self.__swap__.__new_db__()
        self.__marker__.markings = list()
        self.rows = [_Row.__newrow__(self._top_baserow)._set_start_index_(0, 0, 0, 0, 0)]
        self.current_row_idx = 0
        self.__n_newlines__ = 0
        self.__n_rows__ = 0
        self.__start_point_content__ = 0
        self.__start_point_data__ = 0
        self.__start_point_line_num__ = 0
        self.__start_point_row_num__ = 0
        self.__display__.__highlighter__._prepare_by_none()


class ChunkBuffer(TextBuffer):
    """
    **[ ADVANCED USAGE ]**
    
    Create a restricted editable buffer from a chunk in memory.

    >>> with ChunkBuffer(<buffer>, <position>, <do not overwrite chunk slot>, <delete chunk from swap if empty>) as cb:
    >>>    cb.[...]
    >>> ... # overwrites chunk and adjusts the metadata index here

    Basically the methods of the :class:`TextBuffer` should not be used in the ``ChunkBuffer`` to avoid recursion and
    data corruption. However, if methods are used, the following may raise an ``AttributeError``, since the entries for
    :class:`ChunkIter` and ``ChunkBuffer`` in the ``ChunkBuffer`` are deleted:

    - ``write`` (when a substitution mode is selected)
    - ``rowwork``
    - ``remove``
    - ``find``
    - ``goto_row``
    - ``__marker__.marked_remove``
    - ``__local_history__.undo``
    - ``__local_history__.redo``
    - ``__local_history__.branch_fork``

    If the `sandbox` is not set, these following components are available in the ``ChunkBuffer`` **but referencing to** ``TextBuffer``:

    - ``__marker__``
    - ``__local_history__``
    - ``__display__``
    - ``__glob_cursor__``

    The ``__diffs__`` and ``__empty__`` attributes are not set until the override. ``__diffs__`` consists of the
    differences of (data length, content length, row number, line number) and ``__empty__`` indicates whether the
    chunk is empty after overwriting, can be ``None`` if the current buffer is loaded into a ChunkBuffer.
    """

    _overwrite_: Callable[[], None]
    _del_empty_: Callable[[], None]
    __chunk_slot__: int | None
    __chunk_pos_id__: int | None
    __diffs__: tuple[int, int, int, int]
    __empty__: bool | None

    __slots__ = ('_overwrite_', '_del_empty_', '__chunk_slot__', '__chunk_pos_id__', '__diffs__', '__empty__')

    def __init__(self, __buffer__: TextBuffer, position_id: int | None, sandbox: bool, delete_empty: bool):

        if not sandbox:
            if not position_id:
                def overwrite():
                    __buffer__.rows.clear()
                    for _row in self.rows:
                        __buffer__.rows.append(row := _Row.__newrow__(_row))
                        with row:
                            row.content = _row.content
                            row.end = _row.end
                    self.__diffs__ = __buffer__.__swap__.__meta_index__.adjust_by_position(
                        position_id, *__buffer__._adjust_rows(0, endings=True))
                    self.__empty__ = None

                def _del_empty():
                    pass
            else:
                def _del_empty():
                    if self.__empty__:
                        __buffer__.__swap__.remove_chunk_positions(self.__chunk_pos_id__)
                    self._del_empty_ = lambda *_: None

                def overwrite():
                    __buffer__.__swap__._del_chunk(self.__chunk_slot__)
                    __buffer__.__swap__._dump_to_slot(self.__chunk_slot__,
                                                      DumpData(0,
                                                               self.__start_point_data__,
                                                               self.__start_point_content__,
                                                               self.__start_point_row_num__,
                                                               self.__start_point_line_num__,
                                                               self.rows))
                    self.__diffs__ = __buffer__.__swap__.__meta_index__.adjust_by_position(
                        position_id, *self.indexing())
                    for __row in self.rows:
                        if __row:
                            self.__empty__ = False
                            break
                    else:
                        self.__empty__ = True
                    if delete_empty:
                        _del_empty()

            TextBuffer.__init__(self, None, None,
                                __buffer__._top_baserow.tab_size,
                                __buffer__._top_baserow.tab_to_blanks,
                                False,
                                __buffer__._top_baserow.cursors.jump_points,
                                __buffer__._top_baserow.cursors.back_jump_points)

            self.__marker__ = __buffer__.__marker__
            self.__local_history__ = __buffer__.__local_history__
            self.__display__ = __buffer__.__display__
            self.__glob_cursor__ = __buffer__.__glob_cursor__

            self._top_baserow = __buffer__._top_baserow
            self._future_baserow = __buffer__._future_baserow
            self._last_baserow = __buffer__._last_baserow

            self.rows = [_Row.__newrow__(self._top_baserow)._set_start_index_(0, 0, 0, 0, 0)]
        else:
            def overwrite():
                pass

            def _del_empty():
                pass

            TextBuffer.__init__(self, None, None,
                                __buffer__._top_baserow.tab_size,
                                __buffer__._top_baserow.tab_to_blanks,
                                False,
                                __buffer__._top_baserow.cursors.jump_points,
                                __buffer__._top_baserow.cursors.back_jump_points)

        self._overwrite_ = overwrite
        self._del_empty_ = _del_empty

        del self.ChunkBuffer, self.ChunkIter

        if not position_id:
            self.__chunk_slot__ = None
            self.__chunk_pos_id__ = None
            self.__start_point_data__ = __buffer__.__start_point_data__
            self.__start_point_content__ = __buffer__.__start_point_content__
            self.__start_point_row_num__ = __buffer__.__start_point_row_num__
            self.__start_point_line_num__ = __buffer__.__start_point_line_num__
            self.rows.clear()
            for _row in __buffer__.rows:
                self.rows.append(row := _Row.__newrow__(_row))
                with row:
                    row.content = _row.content
                    row.end = _row.end
            self.indexing()
        else:
            self.__chunk_slot__ = __buffer__.__swap__.slot(position_id)
            self.__chunk_pos_id__ = position_id
            chunk = __buffer__.__swap__.get_chunk(position_id)
            _Swap(__buffer__=self,
                  db_path=':memory:',
                  from_db=None,
                  unlink_atexit=False,
                  rows_maximal=0,
                  keep_top_row_size=__buffer__.__swap__._keep_top_row_size,
                  load_distance=0)._load_chunk(0, chunk)

    def strip(self) -> None:
        """
        An empty row is automatically appended by the buffer after a line break, this method removes the last row
        in the buffer if it is empty.
        """
        if not self.rows[-1]:
            self.rows.pop(-1)

    def __enter__(self) -> ChunkBuffer:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._overwrite_()
