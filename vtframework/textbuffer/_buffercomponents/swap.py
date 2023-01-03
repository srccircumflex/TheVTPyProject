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

from typing import Callable, Literal, Iterable, Sequence, overload, ContextManager
from ast import literal_eval
from os import unlink
from pathlib import Path
import atexit
from sqlite3 import (connect as sql_connect,
                     Connection as SQLConnection,
                     ProgrammingError as SQLProgrammingError,
                     OperationalError as SQLOperationalError)

try:
    from ..buffer import TextBuffer, ChunkBuffer
    from .items import ChunkLoad
    _ = ChunkLoad
    from .trimmer import _Trimmer
    _ = _Trimmer
    from ..chunkiter import ChunkIter
    _ = ChunkIter
    from .localhistory import _LocalHistory
    _ = _LocalHistory
except ImportError:
    pass

from .row import _Row
from .items import DumpData, ChunkData, ChunkMetaItem
from . import _sql
from ._suit import _Suit
from ..exceptions import DatabaseTableError, DatabaseFilesError, ConfigurationError


class _Swap:
    """
    Optionally Buffer Component for swapping data chunks into an SQL database.

    The chunks are cut out by :class:`_Trimmer` when reaching a defined number of :class:`_Row`'s in the
    :class:`TextBuffer`, depending on the current cursor position, and passed to Swap as ``DumpData``.
    :class:`DumpData` contains the cut rows, the corresponding data points and the parameter for the position
    addressing. For runtime reduction, only the content of the rows is written to the database, the metadata and
    position addressing remain in memory.

    Swap stores the data chunks in the database under unique slot numbers that never repeat for the existence of a
    database. Position addressing is done using an associative dictionary and the list ``current_chunk_ids`` that
    indicates the above (index ``0``) and below (index ``1``) adjacent chunks to those loaded in the ``TextBuffer``.
    A ``0`` on a position indicates that there are no chunks on that side.
    If chunks are `"shifted to the side"`, the position number is extended by 1, starting from ``-1`` for chunks above
    and ``1`` for chunks below the currently loaded buffer, the data chunks directly adjacent to the ``TextBuffer``
    thus always have the highest absolute position number, the uppermost always ``-1`` and the lowest always ``1``.

    The storage, processing and adjustment of metadata (data points) is done under the slot numbers with
    :class:`ChunkMetaItem`'s in :class:`_MetaIndex` (modified dictionary).

    ****

    The handling of the swap is performed in the main methods of :class:`TextBuffer` and via
    :class:`_Trimmer`. The item :class:`ChunkLoad` is created by ``TextBuffer`` and gives information about the
    actions done in the swap during an edit of the current buffer.

    ****


    Information about parameterization and interaction for a smooth program flow:
        - Even if in ``_Trimmer`` the size of the chunks is specified, it can NOT be guaranteed, because in runtime it
          is possible to store all lines of the current buffer as one chunk and chunks can be edited inplace
          (See :class:`ChunkIter`, :class:`ChunkBuffer`).
        - Note that cursor movement via the ``cursor_move`` method in the ``TextBuffer`` is limited by the loaded rows
          in the ``TextBuffer``.
        - To ensure a display that is always filled, the number of displayable rows should be considered when
          parameterizing `rows_maximal` in ``_Swap`` and ``_Trimmer``, and `load_distance` in ``_Swap``.
        - In addition, an appropriate average value should be found when selecting the `chunk_size`; larger to reduce
          accesses to the database and cache memory, smaller for faster processing of the chunks.


    **WARNING**: the connection of the SQL Database is NOT threadsave, but the cursor (:class:`_sql.SQLTSCursor`).
    """
    __buffer__: TextBuffer
    __params__: dict
    __meta_index__: _MetaIndex
    __slot_index__: dict[int, int]
    db_path: str | Literal[':memory:', ':history:', 'file:...<uri>']
    db_attached: bool
    db_in_mem: bool
    sql_connection: SQLConnection
    sql_cursor: _sql.SQLTSCursor
    current_chunk_ids: list[int, int]
    _prev_chunk_ids: tuple[int, int]
    _top_ids: tuple[int, ...]
    _bottom_ids: tuple[int, ...]
    _slot_count: int
    _dump_auto_commit_: Callable[[], None]
    _keep_top_row_size: bool
    _rows_max: int
    _load_distance: int
    _unlink_: Callable[[], None]
    _active_suits: list[_Suit | None, _Suit | None]

    __slots__ = ('__buffer__', '__params__', 'db_path', 'sql_connection', 'sql_cursor', 'current_chunk_ids',
                 '__slot_index__', '_slot_count', '_dump_auto_commit_', '_keep_top_row_size', '_rows_max',
                 '_load_distance', '_unlink_', '_active_suits', '__meta_index__',
                 '_prev_chunk_ids', '_top_ids', '_bottom_ids', 'db_attached', 'db_in_mem')

    @property
    def positions_top_ids(self) -> tuple[int, ...] | tuple:
        """
        All position numbers of the chunks above the current buffer ordered from top to bottom.

        Scheme: ``-1, -2, -3``
        """
        if self.current_chunk_ids[0] != self._prev_chunk_ids[0]:
            self._prev_chunk_ids = (self.current_chunk_ids[0], self._prev_chunk_ids[1])
            self._top_ids = tuple(i for i in range(-1, self.current_chunk_ids[0] - 1, -1))
        return self._top_ids

    @property
    def positions_bottom_ids(self) -> tuple[int, ...] | tuple:
        """
        All position numbers of the chunks below the current buffer ordered from top to bottom.

        Scheme: ``7, 6, 5, 4, 3, 2, 1``
        """
        if self.current_chunk_ids[1] != self._prev_chunk_ids[1]:
            self._prev_chunk_ids = (self._prev_chunk_ids[0], self.current_chunk_ids[1])
            self._bottom_ids = tuple(i for i in range(self.current_chunk_ids[1], 0, -1))
        return self._bottom_ids

    @property
    def positions_ids(self) -> tuple[int, ...] | tuple:
        """
        All position numbers of the chunks ordered from top to bottom.

        Scheme: ``-1, -2, -3, -4,  2,  1``
        """
        return self.positions_top_ids + self.positions_bottom_ids

    @overload
    def __init__(self, *,
                 __buffer__: TextBuffer,
                 db_path: str | Literal[':memory:', ':history:', 'file:...<uri>'],
                 from_db: str | SQLConnection | None | Literal['file:...<uri>'], unlink_atexit: bool,
                 rows_maximal: int, keep_top_row_size: bool, load_distance: int):
        ...

    def __init__(self, **kwargs):
        """
        Create a new Swap object.

        Keyword parameter:
            - `__buffer__`
                The :class:`TextBuffer` object for which Swap is created.
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

        :raises ConfigurationError: if ":history:" is used and there is no connection to a database in `__local_history__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        __buffer__ = kwargs['__buffer__']
        db_path = kwargs['db_path']
        from_db = kwargs['from_db']
        unlink_atexit = kwargs['unlink_atexit']
        rows_max = kwargs['rows_maximal']
        keep_top_row_size = kwargs['keep_top_row_size']
        load_distance = kwargs['load_distance']

        self.__params__ = kwargs
        self.__buffer__ = __buffer__
        self.__meta_index__ = _MetaIndex(self)
        self.current_chunk_ids = [0, 0]
        self._prev_chunk_ids = (0, 0)
        self._top_ids = self._bottom_ids = ()
        self.__slot_index__ = dict()
        self._slot_count = 0
        self._rows_max = rows_max
        self._keep_top_row_size = keep_top_row_size
        self._load_distance = load_distance

        self._active_suits = [None, None]

        self.db_path = db_path

        if isinstance(db_path, SQLConnection):
            self.sql_connection = db_path
            self.sql_cursor = db_path.cursor(_sql.SQLTSCursor)
            self._unlink_ = self.sql_connection.close
            self.db_attached = True
        elif db_path == ':history:':
            if not __buffer__.__local_history__.sql_connection:
                raise ConfigurationError('__local_history__: no db connection')
            self.sql_connection = __buffer__.__local_history__.sql_connection
            self.sql_cursor = __buffer__.__local_history__.sql_cursor
            self.db_attached = True
            self.db_in_mem = __buffer__.__local_history__.db_in_mem

            def _unlink():
                try:
                    self.dropall()
                except SQLProgrammingError:  # closed db
                    pass

            self._unlink_ = _unlink
        elif db_path == ':memory:':
            self.sql_connection = sql_connect(':memory:', check_same_thread=False)
            self.sql_cursor = self.sql_connection.cursor(_sql.SQLTSCursor)
            self._unlink_ = self.sql_connection.close
            self.db_attached = False
            self.db_in_mem = True
        else:
            self.db_in_mem = False
            self.db_attached = False
            with _sql.DATABASE_FILES_ERROR_SUIT:
                if path := _sql.path_from_uri(db_path):
                    db_path = path[0]
                    if path[1]:
                        self.db_in_mem = True
                    elif Path(path[0]).exists():
                        raise DatabaseFilesError("file exists: ", db_path)
                elif Path(db_path).exists():
                    raise DatabaseFilesError("file exists: ", db_path)
            if self.db_in_mem:
                self._unlink_ = self.sql_connection.close
            else:
                def _unlink():
                    self.sql_connection.close()
                    for f in (db_path, db_path + '-journal', db_path + '-shm', db_path + '-wal'):
                        try:
                            unlink(f)
                        except FileNotFoundError:
                            pass

                self._unlink_ = _unlink

            self.sql_connection = sql_connect(self.db_path, check_same_thread=False, uri=True)
            self.sql_cursor = self.sql_connection.cursor(_sql.SQLTSCursor)

        self._dump_auto_commit_ = self.sql_connection.commit
        with _sql.DATABASE_TABLE_ERROR_SUIT:
            try:
                self.sql_cursor.executescript('''
                CREATE TABLE swap_chunk_index (
                slot INT,
                start_data INT,
                start_content INT,
                start_row INT,
                start_linenum INT,
                nrows INT,
                nnl INT
                );
                CREATE TABLE swap_rows (
                slot INT,
                content TEXT,
                end INT
                );
                CREATE TABLE swap_metas (
                cur_ids TEXT,
                slot_count INT,
                slot_index_key INT,
                slot_index_val INT
                );
                CREATE INDEX swap_rows_slot_index ON swap_rows (slot);
                ''')
            except SQLOperationalError as e:
                raise DatabaseTableError(*e.args)
        if from_db:
            def close():
                pass

            if isinstance(from_db, str):
                from_db = sql_connect(from_db, check_same_thread=False, uri=True)
                close = from_db.close

            # from_db.backup(self.connection)  # Availability: SQLite 3.6.11 or higher
            from_db_cur = from_db.cursor()
            self.__meta_index__ = _MetaIndex(
                self,
                ((row[0], ChunkMetaItem(*row[1:])) for row in from_db_cur.execute('SELECT * FROM swap_chunk_index')))
            self.sql_cursor.executemany('INSERT INTO swap_rows VALUES (?, ?, ?)',
                                        from_db_cur.execute('SELECT * FROM swap_rows'))
            metas = from_db_cur.execute('SELECT * FROM swap_metas')
            self.current_chunk_ids, self._slot_count, _, _ = metas.fetchone()
            self.current_chunk_ids: str
            self.current_chunk_ids = literal_eval(self.current_chunk_ids)
            self.__slot_index__ = {k: v for _, _, k, v in metas.fetchall()}
            close()

        if unlink_atexit:
            atexit.register(self.unlink)

        self.sql_connection.commit()

    @overload
    def __new_db__(self, *,
                   __buffer__: TextBuffer = ...,
                   db_path: str | Literal[':memory:', ':history:', 'file:...<uri>'] = ...,
                   from_db: str | SQLConnection | None | Literal['file:...<uri>'] = ...,
                   unlink_atexit: bool = ...,
                   rows_maximal: int = ...,
                   keep_first_row_size: bool = ...,
                   load_distance: int = ...) -> _Swap:
        ...

    def __new_db__(self, **kwargs) -> _Swap:
        """
        Create a new ``_Swap`` with the same parameters, except `from_db` is set to ``None`` by default.
        Parameters can be overwritten via `kwargs`.
        
        :raises ConfigurationError: if ":history:" is used and there is no connection to a database in `__local_history__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        return self.__class__(**(self.__params__ | {'from_db': None} | kwargs))

    def _new_slot(self, side: Literal[0, 1]) -> int:
        """Return a new slot number and sort it into the index depending on the side."""
        self._slot_count += 1
        if side == 0:
            self.current_chunk_ids[0] -= 1
            self.__slot_index__[self.current_chunk_ids[0]] = self._slot_count
        else:
            self.current_chunk_ids[1] += 1
            self.__slot_index__[self.current_chunk_ids[1]] = self._slot_count
        return self._slot_count

    def _dump_to_slot(self, slot: int, chunk: DumpData) -> None:
        """Dump a `chunk` to db/meta-`slot`."""
        nnl = 0
        for row in (rows := chunk.db_rows()):
            self.sql_cursor.execute('INSERT INTO swap_rows VALUES (?, ?, ?)', (slot, row[0], row[1]))
            nnl += bool(row[1])
        self.__meta_index__._insert(slot, chunk, len(rows), nnl)

    def _dump_chunk(self, chunk: DumpData) -> None:
        """Dump :class:`DumpData` (commit via ``self._dump_auto_commit_()``)."""
        slot = self._new_slot(chunk.side)
        self._dump_to_slot(slot, chunk)
        self._dump_auto_commit_()

    def remove_chunk_positions(self, *position_ids: int) -> None:
        """
        Irretrievably remove chunks from swap based on position numbers and adjust positioning addressing.

        **WARNING:** May disturb the stability of _Swap and TextBuffer if non-empty chunks are removed and the
        metadata index is not recalculated or adjusted.
        """
        top_ids = []
        bottom_ids = []
        for pos in position_ids:
            slot = self.__slot_index__.pop(pos)
            self._del_chunk(slot)
            if pos < 0:
                top_ids.append(pos)
            else:
                bottom_ids.append(pos)
        top_ids.sort(reverse=True)
        bottom_ids.sort()
        i = 0
        for tid in top_ids:
            _tid = tid + i
            self.current_chunk_ids[0] += 1
            new_index = {}
            for _pos in self.__slot_index__:
                if 0 > _pos < _tid:
                    new_index[_pos + 1] = self.__slot_index__[_pos]
                else:
                    new_index[_pos] = self.__slot_index__[_pos]
            i += 1
            self.__slot_index__ = new_index
        i = 0
        for bid in bottom_ids:
            _bid = bid - i
            self.current_chunk_ids[1] -= 1
            new_index = {}
            for _pos in self.__slot_index__:
                if 0 < _pos > _bid:
                    new_index[_pos - 1] = self.__slot_index__[_pos]
                else:
                    new_index[_pos] = self.__slot_index__[_pos]
            i += 1
            self.__slot_index__ = new_index

    def slot(self, position_id: int) -> int:
        """
        Return the slot number for `position_id`.

        :raises KeyError: if the position is not present.
        """
        return self.__slot_index__[position_id]

    def get_by_slot(self, slot: int) -> ChunkData:
        """
        Return the chunk of `slot` from the swap.

        Returns: :class:`ChunkData`
        """
        return ChunkData(
            slot,
            *self.__meta_index__.__getitem__(slot),
            rows=self.sql_cursor.execute('SELECT content, end FROM swap_rows WHERE slot = ?', (slot,)).fetchall())

    def get_chunk(self, position_id: int) -> ChunkData:
        """
        Read and return the chunk of the `position_id` from the swap.

        Returns: :class:`ChunkData`

        :raises KeyError: if the position is not present.
        """
        return self.get_by_slot(self.slot(position_id))

    def chunk_buffer(self, position_id: int, *, sandbox: bool = False, delete_empty: bool = False) -> ChunkBuffer:
        """
        Fabricate an :class:`ChunkBuffer`.
        Use the sandbox mode and do not overwrite the actual data if `sandbox` is ``True``.
        Delete the entry of the chunk in the swap if the chunk became empty due to an edit of the ChunkBuffer
        and `delete_empty` is set to ``True`` (is ignored in `sandbox` mode).
        """
        return self.__buffer__.ChunkBuffer(self.__buffer__, position_id, sandbox, delete_empty)

    def _del_chunk(self, slot: int) -> None:
        """Delete the chunk in `slot` and do commit."""
        self.__meta_index__.pop_by_slot(slot)
        self.sql_cursor.execute('DELETE FROM swap_rows WHERE slot = ?', (slot,))
        self.sql_connection.commit()

    def _pop_current(self, side: Literal[0, 1]) -> ChunkData:
        """
        Remove the next chunk of `side` from the swap and return the :class:`ChunkData`.

        :raises KeyError: no chunk on this site.
        """
        if side:
            chunk = self.get_chunk(self.current_chunk_ids[1])
            slot = self.__slot_index__.pop(self.current_chunk_ids[1])
            self._del_chunk(slot)
            self.current_chunk_ids[1] -= 1
        else:
            chunk = self.get_chunk(self.current_chunk_ids[0])
            slot = self.__slot_index__.pop(self.current_chunk_ids[0])
            self._del_chunk(slot)
            self.current_chunk_ids[0] += 1
        return chunk

    def _pop_specific(self, position_id: int) -> ChunkData:
        """
        Remove a specific chunk from the swap and return the :class:`ChunkData`.

        :raises IndexError: if the position is not present.
        """
        if (not position_id) or (position_id < self.current_chunk_ids[0] or position_id >
                                 self.current_chunk_ids[1]):
            raise IndexError(f'{position_id=} / {self.current_chunk_ids=}')
        if position_id < 0:
            for _id in range(self.current_chunk_ids[0], position_id):
                self.current_chunk_ids[1] += 1
                self.current_chunk_ids[0] += 1
                self.__slot_index__[self.current_chunk_ids[1]] = self.__slot_index__.pop(_id)
            self.current_chunk_ids[0] += 1
        else:
            for _id in range(self.current_chunk_ids[1], position_id, -1):
                self.current_chunk_ids[0] -= 1
                self.current_chunk_ids[1] -= 1
                self.__slot_index__[self.current_chunk_ids[0]] = self.__slot_index__.pop(_id)
            self.current_chunk_ids[1] -= 1
        chunk = self.get_chunk(position_id)
        slot = self.__slot_index__.pop(position_id)
        self._del_chunk(slot)
        return chunk

    def dump_metas(self, index_too: bool = True) -> None:
        """
        Dump the metadata of the :class:`_Swap` into the database and do commit.
        Include the :class:`_MetaIndex` if `index_too` is ``True``.
        """
        self.sql_cursor.execute('DELETE FROM swap_metas')
        self.sql_cursor.execute('INSERT INTO swap_metas (cur_ids, slot_count) VALUES (?, ?)',
                                (repr(self.current_chunk_ids), self._slot_count))
        items: Iterable = self.__slot_index__.items()
        self.sql_cursor.executemany(
            'INSERT INTO swap_metas (slot_index_key, slot_index_val) VALUES (?, ?)', items)
        self.sql_cursor.execute('DELETE FROM swap_chunk_index')
        if index_too:
            self.sql_cursor.executemany(
                'INSERT INTO swap_chunk_index VALUES (?, ?, ?, ?, ?, ?, ?)',
                ((slot,) + tuple(item) for slot, item in self.__meta_index__.items()))
        self.sql_connection.commit()

    def backup(self, dst: str | SQLConnection | Literal['file:...<uri>']) -> None:
        """
        Clones all chunks in the swap, the metadata of the :class:`_Swap`, the :class:`_MetaIndex` and the currently
        loaded buffer in `dst`. Close the connection to the backup-db if `dst` is defined as path or URI.

        :raises ConfigurationError: if ":history:" or ":memory:" is used as `dst`.
        :raises DatabaseFilesError: `dst` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        if dst in (':memory:', ':history:'):
            raise ValueError('":history:" or ":memory:" is not designated as a destination.')
        self.dump_metas()
        db = self.__new_db__(db_path=dst, from_db=self.sql_connection, unlink_atexit=False)
        db._dump_current_buffer(0)
        db.dump_metas()
        if isinstance(dst, str):
            db.sql_connection.close()
        del db

    def unlink(self) -> None:
        """
        Execute the unlink function, depending on where the database is located, and remove the execution entry when 
        exiting the Python interpreter. It can be assumed that the database will no longer exist and will be deleted
        (even if the database is on the disk as files).

        ==============  ===================================
        db origin       unlink
        ==============  ===================================
        Filepath         \\- > Connection.close ; os.unlink
        \\:memory:       \\- > Connection.close
        \\:history:      \\- > dropall
        SQL-Connection   \\- > Connection.close
        ==============  ===================================
        """
        atexit.unregister(self.unlink)
        self._unlink_()

    def dropall(self) -> None:
        """Delete all entries in the tables of the database and discard the indexes."""
        self.sql_cursor.executescript('''
                    DELETE FROM swap_chunk_index;
                    DELETE FROM swap_rows;
                    DELETE FROM swap_metas;
                    DROP INDEX swap_rows_slot_index;
                    ''')

    @overload
    def clone(self,
              to_db: str | Literal[':memory:', ':history:', 'file:...<uri>'] | SQLConnection,
              with_current_buffer: bool = False, unlink_origin: bool = False,
              *,
              unlink_atexit: bool = ...,
              rows_maximal: int = ...,
              keep_first_row_size: bool = ...,
              load_distance: int = ...) -> _Swap:
        ...

    def clone(self,
              to_db: str | Literal[':memory:', ':history:', 'file:...<uri>'] | SQLConnection,
              with_current_buffer: bool = False, unlink_origin: bool = False,
              **kwargs) -> _Swap:
        """
        Clone the database and metadata into a new ``_Swap`` object, and include the currently loaded chunks in
        ``TextBuffer`` if `with_current_buffer` is set to ``True``.
        The standard parameterization is the same as the original and can be overridden via keyword arguments.
        If `unlink_origin` is set to ``True``, the existing database is deleted depending on its location:

        ==============  ===================================
        db origin       unlink
        ==============  ===================================
        Filepath         \\- > Connection.close ; os.unlink
        \\:memory:       \\- > Connection.close
        \\:history:      \\- > dropall
        SQL-Connection   \\- > Connection.close
        ==============  ===================================

        - Returns the new ``_Swap`` object.

        :raises ConfigurationError: if ":history:" is used and there is no connection to a database in `__local_history__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        self.dump_metas(index_too=False)
        db = self.__new_db__(db_path=to_db, from_db=self.sql_connection, **kwargs)
        db.__meta_index__ = self.__meta_index__.copy()
        if with_current_buffer:
            db._dump_current_buffer(0)
        if unlink_origin:
            self.unlink()
        return db

    def _dump_current_buffer(self, to_side: Literal[0, 1]) -> None:
        """Dump the currently buffer `to_side` into the swap."""
        self._dump_chunk(DumpData(
            to_side,
            self.__buffer__.rows[0].__data_start__,
            self.__buffer__.rows[0].__content_start__,
            self.__buffer__.rows[0].__row_num__,
            self.__buffer__.rows[0].__line_num__,
            self.__buffer__.rows))
        if ids := self.positions_bottom_ids[to_side:]:
            self.__meta_index__.adjust_by_adjacent(ids, *self.__buffer__.indexing())

    def _load_chunk(self, to_side: Literal[0, 1] | int, chunk: ChunkData) -> None:
        """
        Add a `chunk` `to_side` of the ``TextBuffer``.

        [+] __marker__.adjust [+] __glob_cursor__.adjust
        """

        _chunk = list()
        for row in chunk.rows:
            _chunk.append(
                rowbuffer := _Row.__newrow__(self.__buffer__._future_baserow))
            row_content = row[0]
            while of := rowbuffer._write_line(row_content)[0]:
                _chunk.append(rowbuffer := _Row.__newrow__(self.__buffer__._future_baserow))
                row_content = of[0]
            with rowbuffer:
                if row[1] == 1:
                    rowbuffer.end = '\n'
                elif row[1] == 2:
                    rowbuffer.end = ''

        if to_side > 0:
            self.__buffer__.__display__.__highlighter__._prepare_by_writeitem(
                self.__buffer__.rows[-1].__row_num__, gt_too=True)
            if not self.__buffer__.rows[-1]:
                self.__buffer__.rows.pop(-1)
            if _chunk[-1].end is not None:
                _chunk.append(_Row.__newrow__(self.__buffer__._future_baserow))
            self.__buffer__.rows += _chunk
            if self._keep_top_row_size or not self.current_chunk_ids[0]:
                self.__buffer__.rows[0]._resize_bybaserow(self.__buffer__._top_baserow)
        else:
            self.__buffer__.__start_point_data__ = chunk.start_point_data
            self.__buffer__.__start_point_content__ = chunk.start_point_content
            self.__buffer__.__start_point_row_num__ = chunk.start_point_row
            self.__buffer__.__start_point_line_num__ = chunk.start_point_linenum
            if self._keep_top_row_size or not self.current_chunk_ids[0]:
                _chunk[0]._resize_bybaserow(self.__buffer__._top_baserow)
                self.__buffer__.rows[0]._resize_bybaserow(self.__buffer__._future_baserow)
            self.__buffer__.rows = _chunk + self.__buffer__.rows

        self.__buffer__._adjust_rows(0, endings=True)

    def load(self, side: Literal[0, 1], goto: int) -> bool:
        """
        Load the next chunk of side `side` to the ``TextBuffer``. Then set the cursor to the data point `goto`.
        Return ``False`` if no chunk of the side is present, otherwise ``True``.
        """
        if self.current_chunk_ids[side]:
            self._load_chunk(side, self._pop_current(side))
            self.__buffer__._goto_data(goto)
            return True
        return False

    def auto_fill(self) -> tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]:
        """
        Fill the buffer with chunks up to the upper limit. Then remove the overhang.

        [+] __trimmer__.trim

        Returns: (
            - `<`:class:`_Row`\\ `chunk's cut from top>` | ``None``,
            - `<`:class:`_Row`\\ `chunk's cut from bottom>` | ``None``,
            - `<n loaded chunks from top>` | ``None``,
            - `<n loaded chunks from bottom>` | ``None``
        )
        """
        loadtop = loadbottom = 0
        goto = self.__buffer__.current_row.cursors.data_cursor

        def fin():
            if cut := self.__buffer__.__trimmer__.__call__():
                return cut[0], cut[1], loadtop, loadbottom
            if len(self.__buffer__.rows) >= self._rows_max:
                return (None, None, loadtop, loadbottom) if loadtop or loadbottom else (None, None, None, None)

        if _fin := fin():
            return _fin

        if (s := self.__buffer__.current_row_idx - self._load_distance) <= 0:
            flag = len(self.__buffer__.rows) + abs(s) + self.__buffer__.__trimmer__._spec_size_arg
            while len(self.__buffer__.rows) < flag and self.load(0, goto):
                loadtop += 1
            if self.__buffer__.current_row_idx + self._load_distance >= len(self.__buffer__.rows) - 1:
                flag = len(self.__buffer__.rows) + self.__buffer__.__trimmer__._spec_size_arg
                while len(self.__buffer__.rows) < flag and self.load(1, goto):
                    loadbottom += 1
            if _fin := fin():
                return _fin
            while self.load(1, goto):
                loadbottom += 1
                if _fin := fin():
                    return _fin
        elif self.__buffer__.current_row_idx + self._load_distance >= len(self.__buffer__.rows) - 1:
            while self.load(1, goto):
                loadbottom += 1
                if _fin := fin():
                    return _fin

        if self.__buffer__.current_row_idx >= (len(self.__buffer__.rows) // 2):
            while self.load(1, goto):
                loadbottom += 1
                if _fin := fin():
                    return _fin
        while self.load(0, goto):
            loadtop += 1
            if _fin := fin():
                return _fin
        ct, cb = self.__buffer__.__trimmer__.__call__() or (None, None)
        return (ct, cb, loadtop, loadbottom) if loadtop or loadbottom else (ct, cb, None, None)

    def __call__(self) -> tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]:
        """
        Automation. Load the next chunk when the cursor is in the load distance.

        [+] __trimmer__.trim

        Returns: (
            - `<`:class:`_Row`\\ `chunk's cut from top>` | ``None``,
            - `<`:class:`_Row`\\ `chunk's cut from bottom>` | ``None``,
            - `<n loaded chunks from top>` | ``None``,
            - `<n loaded chunks from bottom>` | ``None``
        )
        """
        loadtop = loadbottom = 0
        goto = self.__buffer__.current_row.cursors.data_cursor
        if self.__buffer__.current_row_idx - self._load_distance <= 0:
            while self.load(0, goto):
                loadtop += 1
                if cut := self.__buffer__.__trimmer__.__call__():
                    return cut[0], cut[1], loadtop, loadbottom
                if len(self.__buffer__.rows) >= self._rows_max:
                    return None, None, loadtop, loadbottom
        if self.__buffer__.current_row_idx + self._load_distance >= len(self.__buffer__.rows) - 1:
            while self.load(1, goto):
                loadbottom += 1
                if cut := self.__buffer__.__trimmer__.__call__():
                    return cut[0], cut[1], loadtop, loadbottom
                if len(self.__buffer__.rows) >= self._rows_max:
                    return None, None, loadtop, loadbottom
        return (None, None, loadtop, loadbottom) if loadtop or loadbottom else (None, None, None, None)

    def suit(self, mode: Literal['commit', 'fill', '_metas'] = 'commit', leave_active: bool = False
             ) -> _Suit[_Swap] | _Suit[_Trimmer]:
        """
        Return a suit depending on mode.

        (when entering ``__swap__`` is returned)

        >>> with __swap__.suit(<mode>)[ as swap]:
        >>>     ...

        Modes:
            - ``"commit"`` :
                Commit when exiting the suit instead of after each dump.
            - ``"fill"`` :
                Disable automatic filling with chunks over ``__call__`` and ``auto_fill`` within the suit.
            - ``"_metas"`` :
                Bypasses the adjustment of metadata for actions on the swap and writes the differences separately.
                The final adjustment of the metadata is then done only after leaving the suit. **SPECIAL Usage**

        If a suit is active and `leave_active` is ``True``,
        ``__exit__`` of the active suit is executed and a new one is created, otherwise a dummy is returned.
        """
        if mode[0] == 'c':
            if self._active_suits[0]:
                if leave_active:
                    self._active_suits[0].__exit__(None, None, None)
                else:
                    return _Suit(lambda *_: self, lambda *_: None)

            def enter(suit: _Suit):
                self._active_suits[0] = suit
                self._dump_auto_commit_ = lambda: None
                return self

            def exit_(*_):
                self.sql_connection.commit()
                self._dump_auto_commit_ = self.sql_connection.commit
                self._active_suits[0] = None

        elif mode[0] == '_':
            if self._active_suits[1]:
                if leave_active:
                    self._active_suits[1].__exit__(None, None, None)
                else:
                    return _Suit(lambda *_: self, lambda *_: None)

            def enter(suit: _Suit):
                self._active_suits[1] = suit
                self.__meta_index__.__enter__()
                return self

            def exit_(*_):
                self.__meta_index__.__exit__(*_)
                self._active_suits[1] = None

        else:
            return self.__buffer__.__trimmer__.suit(_poll=False, _dmnd=False, leave_active=leave_active)

        return _Suit(enter, exit_)


class _MetaIndex(dict[int, ChunkMetaItem], ContextManager):
    """
    An index for storing, processing, and adjusting metadata associated with chunks.
    The metadata is stored as :class:`ChunkMetaItem` at the slot number.

    Handling is ensured by the methods in the :class:`TextBuffer` and its components when swap is active.

    The shadow-mode:
        For a special usage, the object can be used as a contextmanager/suit to register inplace edits of chunks
        separately without direct adjustment of the index. This allows a sequential processing of several chunks
        without changing the original data points (see also :class:`ChunkIter`), only when leaving the differences
        resulting from the editing are processed and the index is adjusted.
    """
    __swap__: _Swap
    _ins_: Callable[[int, DumpData, int, int], None]
    _pop_: Callable[[int], ChunkMetaItem]
    _remake_: Callable[[...], None]
    _adjust_by_position_: Callable[[int | None, int, int, int, int], None]
    _adjust_by_sequence_: Callable[[Sequence[int], int, int, int, int], None]
    __shadow_diffs__: dict[int | None, tuple[int, int, int, int]]
    __shadow_ln_count__: dict[int, tuple[int, int]]

    __slots__ = (
        '__swap__', '_ins_', '_pop_', '_remake_', '_adjust_by_position_', '_adjust_by_sequence_',
        '__shadow_diffs__', '__shadow_ln_count__')

    def __init__(self, __swap__: _Swap,
                 iterable: Iterable[tuple[int, ChunkMetaItem]] = None):
        if iterable:
            dict.__init__(self, iterable)
        else:
            dict.__init__(self)
        self.__swap__ = __swap__
        self._adjust_by_sequence_ = self._adjust_by_sequence
        self._adjust_by_position_ = self._adjust_by_position
        self._remake_ = self._remake
        self._ins_ = self._ins
        self._pop_ = self.pop

    def _ins(self,
             slot: int,
             chunk: DumpData,
             nrows: int, nnl: int) -> None:
        """
        The original insertion method.

        Create an :class:`ChunkMetaItem` and store it in the index under the `slot` number,
        then adjust the entries below by the differences.

        Overwritten when shadow mode is active.
        """
        self[slot] = ChunkMetaItem(chunk.start_point_data,
                                   chunk.start_point_content,
                                   chunk.start_point_row,
                                   chunk.start_point_linenum,
                                   nrows, nnl)
        if chunk.side:
            self.adjust_by_position(self.__swap__.current_chunk_ids[1],
                                    (row := chunk.rows[-1]).__next_data__,
                                    row.__next_content__,
                                    row.__next_row_num__,
                                    row.__next_line_num__)

    def _insert(self,
                slot: int,
                chunk: DumpData,
                nrows: int, nnl: int) -> None:
        """The interface method for inserting metadata."""
        return self._ins_(slot, chunk, nrows, nnl)

    @overload
    def _set(self,
             slot: int, *,
             start_point_data: int = ...,
             start_point_content: int = ...,
             start_point_row: int = ...,
             start_point_linenum: int = ...,
             nrows: int = ..., nnl: int = ...) -> None:
        ...

    def _set(self, slot: int, **kwargs) -> None:
        """Modify the item on `slot`."""
        self[slot].set(**kwargs)

    def get_by_slot(self, slot: int) -> ChunkMetaItem:
        """Return the :class:`ChunkMetaItem` on `slot`"""
        return self[slot]

    def get_metaitem(self, position_id: int) -> ChunkMetaItem:
        """Return the :class:`ChunkMetaItem` for `position_id`"""
        return self[self.__swap__.slot(position_id)]

    def pop(self, slot: int) -> ChunkMetaItem:
        """
        The original pop method.

        Remove :class:`ChunkMetaItem` on `slot` from the index and return it.

        Overwritten when shadow mode is active.
        """
        return super().pop(slot)

    def pop_by_slot(self, slot: int) -> ChunkMetaItem:
        """The interface method to pop :class:`ChunkMetaItem`'s by the `slot`-number."""
        return self._pop_(slot)

    def pop_metaitem(self, position_id: int) -> ChunkMetaItem:
        """The interface method to pop :class:`ChunkMetaItem`'s by the `position_id`."""
        return self._pop_(self.__swap__.slot(position_id))

    def _adjust_buffer(self, dif_dat: int, dif_cnt: int, dif_row: int, dif_lin: int) -> None:
        """Adjust the data start points in the :class:`TextBuffer` by the differences."""
        self.__swap__.__buffer__.__start_point_data__ += dif_dat
        self.__swap__.__buffer__.__start_point_content__ += dif_cnt
        self.__swap__.__buffer__.__start_point_row_num__ += dif_row
        self.__swap__.__buffer__.__start_point_line_num__ += dif_lin

    def _adjust_by_sequence(
            self, adjacent_pos_ids: Sequence[int], dif_dat: int, dif_cnt: int, dif_row: int, dif_lin: int
    ) -> None:
        """
        The original adjust-by-sequence method.

        Adjust the :class:`ChunkMetaItem`'s of the `adjacent_pos_ids` by the differences.

        Overwritten when shadow mode is active.
        """
        for _id in adjacent_pos_ids:
            chunk = self[self.__swap__.slot(_id)]
            chunk.start_point_data += dif_dat
            chunk.start_point_content += dif_cnt
            chunk.start_point_row += dif_row
            chunk.start_point_linenum += dif_lin

    def diff_by_adjacent(
            self, adjacent_pos_ids: Sequence[int],
            next_abs_dat: int, next_abs_cnt: int, next_row_num: int, next_lin_num: int
    ) -> tuple[int, int, int, int]:
        """
        Calculate the differences with the data start points of the meta item for the first entry in
        `adjacent_pos_ids` and the data end points from the chunk before it.

        :return: ( dif_dat, dif_cnt, dif_row, dif_lin )
        """
        chunk = self[self.__swap__.__slot_index__[adjacent_pos_ids[0]]]
        return (next_abs_dat - chunk.start_point_data,
                next_abs_cnt - chunk.start_point_content,
                next_row_num - chunk.start_point_row,
                next_lin_num - chunk.start_point_linenum)

    def adjust_by_adjacent(
            self,
            adjacent_pos_ids: Sequence[int],
            next_abs_dat: int,
            next_abs_cnt: int,
            next_row_num: int,
            next_lin_num: int
    ) -> tuple[int, int, int, int]:
        """
        Calculate the differences with the data start points of the meta item for the first entry in
        `adjacent_pos_ids` and the data end points from the chunk before it.

        Then call the interface to adjust the sequence of :class:`ChunkMetaItem`'s by the differences.

        :return: ( dif_dat, dif_cnt, dif_row, dif_lin )
        """
        dif_dat, dif_cnt, dif_row, dif_lin = self.diff_by_adjacent(adjacent_pos_ids,
                                                                   next_abs_dat,
                                                                   next_abs_cnt,
                                                                   next_row_num,
                                                                   next_lin_num)
        if dif_dat or dif_cnt or dif_row or dif_lin:
            self._adjust_by_sequence_(adjacent_pos_ids, dif_dat, dif_cnt, dif_row, dif_lin)
        return dif_dat, dif_cnt, dif_row, dif_lin

    def adjust_bottom_auto(self) -> tuple[int, int, int, int] | None:
        """Automatically adjust the items below the :class:`TextBuffer`."""
        if ids := self.__swap__.positions_bottom_ids:
            return self.adjust_by_adjacent(ids, *self.__swap__.__buffer__.indexing())

    def _adjust_by_position(
            self, origin_position: int | None, dif_dat: int, dif_cnt: int, dif_row: int, dif_lin: int
    ) -> None:
        """
        The original adjust-by-position method.

        Adjust the `origin_position` following :class:`ChunkMetaItem`'s [ and :class:`TextBuffer` ] by the differences.

        Overwritten when shadow mode is active.
        """
        if not origin_position:
            if ids := self.__swap__.positions_bottom_ids:
                if dif_row or dif_cnt or dif_dat or dif_lin:
                    self._adjust_by_sequence(ids, dif_dat, dif_cnt, dif_row, dif_lin)
        elif origin_position == self.__swap__.current_chunk_ids[0]:
            ids = self.__swap__.positions_bottom_ids
            if dif_row or dif_cnt or dif_dat or dif_lin:
                self._adjust_buffer(dif_dat, dif_cnt, dif_row, dif_lin)
                self._adjust_by_sequence(ids, dif_dat, dif_cnt, dif_row, dif_lin)
        else:
            ids = self.__swap__.positions_ids
            if ids := ids[ids.index(origin_position) + 1:]:
                if dif_row or dif_cnt or dif_dat or dif_lin:
                    self._adjust_by_sequence(ids, dif_dat, dif_cnt, dif_row, dif_lin)
                    if origin_position < 0:
                        self._adjust_buffer(dif_dat, dif_cnt, dif_row, dif_lin)

    def diff_by_position(
            self, origin_position: int | None,
            next_abs_dat: int, next_abs_cnt: int, next_row_num: int, next_lin_num: int
    ) -> tuple[int, int, int, int]:
        """
        Calculate the differences with the data start points of item adjacent to `origin_position`
        and the data end points from the `origin_position`.

        :return: ( dif_dat, dif_cnt, dif_row, dif_lin )
        """
        if not origin_position:
            if ids := self.__swap__.positions_bottom_ids:
                meta = self[self.__swap__.__slot_index__[ids[0]]]
                next_abs_dat -= meta.start_point_data
                next_abs_cnt -= meta.start_point_content
                next_row_num -= meta.start_point_row
                next_lin_num -= meta.start_point_linenum
            else:
                next_abs_dat = next_abs_cnt = next_row_num = next_lin_num = 0
        elif origin_position == self.__swap__.current_chunk_ids[0]:
            next_row_num -= self.__swap__.__buffer__.__start_point_row_num__
            next_abs_cnt -= self.__swap__.__buffer__.__start_point_content__
            next_abs_dat -= self.__swap__.__buffer__.__start_point_data__
            next_lin_num -= self.__swap__.__buffer__.__start_point_line_num__
        else:
            ids = self.__swap__.positions_ids
            if ids := ids[ids.index(origin_position) + 1:]:
                meta = self[self.__swap__.__slot_index__[ids[0]]]
                next_abs_dat -= meta.start_point_data
                next_abs_cnt -= meta.start_point_content
                next_row_num -= meta.start_point_row
                next_lin_num -= meta.start_point_linenum
            else:
                next_abs_dat = next_abs_cnt = next_row_num = next_lin_num = 0
        return next_abs_dat, next_abs_cnt, next_row_num, next_lin_num

    def adjust_by_position(
            self,
            origin_position: int | None,
            next_abs_dat: int,
            next_abs_cnt: int,
            next_row_num: int,
            next_lin_num: int
    ) -> tuple[int, int, int, int]:
        """
        Calculate the differences with the data start points of item adjacent to `origin_position`
        and the data end points from the `origin_position`.

        Then call the interface to adjust the `origin_position` following :class:`ChunkMetaItem`'s
        [ and :class:`TextBuffer` ] by the differences.

        :return: ( dif_dat, dif_cnt, dif_row, dif_lin )
        """
        dif_dat, dif_cnt, dif_row, dif_lin = self.diff_by_position(origin_position,
                                                                   next_abs_dat,
                                                                   next_abs_cnt,
                                                                   next_row_num,
                                                                   next_lin_num)
        if dif_dat or dif_cnt or dif_row or dif_lin:
            self._adjust_by_position_(origin_position, dif_dat, dif_cnt, dif_row, dif_lin)
        return dif_dat, dif_cnt, dif_row, dif_lin

    def _remake(self, *, bottom_too: bool = True, bottom_only: bool = False) -> None:
        """
        Original method of recalculation of the index.

        Overwritten when shadow mode is active.
        """
        def make():
            nonlocal next_abs_dat, next_abs_cnt, next_row_num, next_lin_num
            buffer = self.__swap__.__buffer__.ChunkBuffer(self.__swap__.__buffer__, posid, True, False)
            self[buffer.__chunk_slot__].set(start_point_data=next_abs_dat,
                                            start_point_content=next_abs_cnt,
                                            start_point_row=next_row_num,
                                            start_point_linenum=next_lin_num)
            buffer.__start_point_row_num__ = next_row_num
            buffer.__start_point_content__ = next_abs_cnt
            buffer.__start_point_data__ = next_abs_dat
            buffer.__start_point_line_num__ = next_lin_num
            next_abs_dat, next_abs_cnt, next_row_num, next_lin_num = buffer.indexing()

        if bottom_only:
            next_abs_dat, next_abs_cnt, next_row_num, next_lin_num = self.__swap__.__buffer__.indexing()
            for posid in self.__swap__.positions_bottom_ids:
                make()
        else:
            next_abs_dat = next_abs_cnt = next_row_num = next_lin_num = 0
            for posid in self.__swap__.positions_top_ids:
                make()
            self.__swap__.__buffer__.__start_point_data__ = next_abs_dat
            self.__swap__.__buffer__.__start_point_row_num__ = next_row_num
            self.__swap__.__buffer__.__start_point_content__ = next_abs_cnt
            self.__swap__.__buffer__.__start_point_line_num__ = next_lin_num
            next_abs_dat, next_abs_cnt, next_row_num, next_lin_num = self.__swap__.__buffer__.indexing()
            if bottom_too:
                for posid in self.__swap__.positions_bottom_ids:
                    make()

    def remake(self, *, bottom_too: bool = True, bottom_only: bool = False) -> None:
        """Recalculate the metaindex by reading all chunks."""
        return self._remake_(bottom_too=bottom_too, bottom_only=bottom_only)

    def get_meta_indices(self) -> tuple[tuple[int | None], dict[int | None, tuple[int, int, int, int, int, int]]]:
        """
        Create an index of the meta start points for each chunk.

        Return a top-down sorted sequence of position numbers at index ``0``:
            ``(-1, -2, -3, -4, None, 2, 1)``

        and an unordered dictionary at index ``1``:
            ``{ -3: (`` `<data start>, <content start>, <row start>, <line start>, <n rows>, <n newlines>` ``), ... }``

        The currently loaded chunks in the buffer are indicated by key ``None``.
        """
        chunk_top_ids = self.__swap__.positions_top_ids
        chunk_bottom_ids = self.__swap__.positions_bottom_ids
        return chunk_top_ids + (None,) + chunk_bottom_ids, {
            id_: tuple(self[self.__swap__.slot(id_)]) for id_ in chunk_top_ids} | {
                   None: (self.__swap__.__buffer__.__start_point_data__,
                          self.__swap__.__buffer__.__start_point_content__,
                          self.__swap__.__buffer__.__start_point_row_num__,
                          self.__swap__.__buffer__.__start_point_line_num__,
                          self.__swap__.__buffer__.__n_rows__,
                          self.__swap__.__buffer__.__n_newlines__)} | {
                   id_: tuple(self[self.__swap__.slot(id_)]) for id_ in chunk_bottom_ids}

    def copy(self) -> _MetaIndex:
        """Create a deepcopy and return a new ``_MetaIndex``"""
        return self.__class__(self.__swap__, ((slot, self[slot].copy()) for slot in self))

    def shadow_start(self) -> None:
        """
        Start the shadow adjustment of the MetaIndex.

        The following adjustments to the index are saved separately and are only finally performed when
        ``shadow_commit`` is executed.

        Overwrites the core methods for the adjustments, the ``remake`` method and the execution of ``pop_*``.
        """
        self.__shadow_diffs__ = dict()
        self.__shadow_ln_count__ = dict()

        def adj_by_pos(origin_position: int | None, *diffs: int):
            self.__shadow_diffs__[origin_position] = diffs

        def adj_by_seq(seq: Sequence, *diffs: int):
            if seq[0] == self.__swap__.positions_bottom_ids[0]:
                self.__shadow_diffs__[None] = diffs
            else:
                self.__shadow_diffs__[seq[0] + 1] = diffs

        self._adjust_by_position_ = adj_by_pos
        self._adjust_by_sequence_ = adj_by_seq

        self._remake_ = lambda *_, **__: None

        def ins(slot: int, _, nrows: int, nnl: int):  # set by ...dump_to_chunk
            self.__shadow_ln_count__[slot] = (nrows, nnl)

        self._ins_ = ins
        self._pop_ = self.get

    def shadow_commit(self) -> None:
        """
        Finish the shadow adjustment of the MetaIndex and perform the adjustments.

        Resets the core methods for the adjustment, the ``remake`` method and the execution of ``pop_*`` to the
        original functions.
        """
        top_items = []
        bottom_items = []
        cur_buffer_item = None
        for pos, diffs in self.__shadow_diffs__.items():
            if not pos:
                cur_buffer_item = diffs
            elif pos < 0:
                top_items.append((pos, diffs))
            else:
                bottom_items.append((pos, diffs))

        bottom_items.sort(reverse=True)
        top_items.sort(reverse=True)
        if cur_buffer_item:
            bottom_items.append((None, cur_buffer_item))

        for pos, diffs in bottom_items + top_items:
            self._adjust_by_position(pos, *diffs)

        for slot, itm in self.__shadow_ln_count__.items():
            self[slot].set(nrows=itm[0], nnl=itm[1])

        self.__swap__.__buffer__.indexing()

        self._adjust_by_position_ = self._adjust_by_position
        self._adjust_by_sequence_ = self._adjust_by_sequence
        self._remake_ = self._remake
        self._ins_ = self._ins
        self._pop_ = self.pop

        self.__shadow_diffs__.clear()
        self.__shadow_ln_count__.clear()

    def __enter__(self) -> None:
        """
        Start the shadow adjustment of the MetaIndex.

        The following adjustments to the index are saved separately and are only finally performed when
        ``shadow_commit`` is executed.

        Overwrites the core methods for the adjustments, the ``remake`` method and the execution of ``pop_*``.
        """
        self.shadow_start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Finish the shadow adjustment of the MetaIndex and perform the adjustments.

        Resets the core methods for the adjustment, the ``remake`` method and the execution of ``pop_*`` to the
        original functions.
        """
        self.shadow_commit()
