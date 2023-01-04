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

from typing import Callable, Literal, Any, Iterable, overload, Sequence
from ast import literal_eval
from os import unlink
from pathlib import Path
import atexit
from sqlite3 import (connect as sql_connect, 
                     Connection as SQLConnection, 
                     ProgrammingError as SQLProgrammingError, 
                     OperationalError as SQLOperationalError)

try:
    from ..buffer import TextBuffer
    from .items import WriteItem
    from .marker import _Marker
    _ = _Marker
    from .swap import _Swap
    _ = _Swap
except ImportError:
    pass

from .items import HistoryItem, ChunkLoad
from .row import _Row
from ._suit import _Suit
from . import _sql
from ..exceptions import DatabaseFilesError, DatabaseTableError, DatabaseCorruptedError, ConfigurationError


class _LocalHistory:
    """
    Optional Buffer Component to support features around chronological progress of edits in the :class:`TextBuffer`.

    If active, all edits to the TextBuffer's data via its main methods are registered and held for an extension or
    direckt written to an SQL database, as well as the related markings or edits to markings via TextBuffer's or
    :class:`_Marker`'s main methods. In addition, the special cursor movements are registered via TextBuffer's methods
    with ``goto_`` prefix and the movement by the `backjumpmode` of the :class:`_Marker`.
    Internally, the chronological steps of the editing are processed with :class:`HistoryItem`'s.

    When ``undo`` is executed later, opposite entries for ``redo`` are generated. For a more comprehensive nature of
    the ordinary undo and redo properties of a text editing program, this object provides two additional ways to
    specify or manage the undo/redo actions.

    First, the use of a lock on undo actions can be specified at initialization. An execution of ``undo`` will then
    lock subsequent edits of the buffer via raising an ``AssertionError``; only when the lock is released the buffer
    can be further edited.
    This property is intended to prevent the accidental deletion of redo entries after undo actions.

    On the other hand, the creation of a ``branch_fork`` in sequence of an edit after ``undo``/``redo`` actions can
    be set. This allows jumping between two edit branches until the next creation of a branch.
    Like the lock, this feature provides the possibility to handle the accidental deletion of redo entries,
    only with an extended functionality:

    >>> # o - o - o - | - u - u - u
    >>>
    History entries were registered (`o') and a few edits were undone (`u') (`|' marks the current position in the timeline).

    >>> #               o - o - o - o - o - o - |
    >>> #              /
    >>> # o - o - o - o
    >>> #              \\
    >>> #               o - u - u - u
    After the undo, the buffer was edited next.

    >>> #               o - u - u - u - u - u - u
    >>> #              /
    >>> # o - o - o - o
    >>> #              \\
    >>> #               o - o - o - o - | - u - u
    The editing branch was changed, then the buffer was edited further and then entries were undone again.

    >>> #                                   o - o - |
    >>> #                                  /
    >>> # o - o - o - o - o - o - o - o - o
    >>> #                                  \\
    >>> #                                   o - u - u
    The buffer was edited some more.
    
    The component can also set a "chronological progress clamp", which can then be used as a comparison to the current
    "chronological progress identification number" to detect a changed buffer.


    **WARNING**: the connection of the SQL Database is NOT threadsave, but the cursor (:class:`_sql.SQLTSCursor`).
    """

    __buffer__: TextBuffer
    __params__: dict

    db_path: str | Literal[':memory:', ':swap:', 'file:...<uri>']
    db_attached: bool
    db_in_mem: bool
    sql_connection: SQLConnection
    sql_cursor: _sql.SQLTSCursor
    _unlink_: Callable[[], None]

    _current_item: None | HistoryItem               # held item

    _chronicle_progress_id: int                     # counter for chronological entries
    _chronicle_redo_id: int | None                  # neg. counter, used within undo sequences
    _chronicle_cursor: int | None                   # used within undo/redo sequences
    _get_id_: Callable[[], int]                     # returns the next _chronicle_progress_id or the _unification_id

    _unification_id: int | None                     # static id for chronological entries, used within unification
    _order_id: int | None                           # neg. counter, used within unification
    _get_order_: Callable[[], int | Literal[0]]     # returns the next _order_id or 0

    _chronicle_clamp: int
    _fork_chronicle_clamp: int                      # the _chronicle_clamp of the other branch,
    # can be reassigned as the current clamp if no new fork has been created and the branch is changed back.

    _islocked: bool
    _lock_acquire_: Callable[[], None]
    _lock_assert_: Callable[[], None]

    _branch_fork_mode: bool
    _fork_id: int
    _forked: bool | None

    _items_max_action_: Callable[[], None]

    _active_suit: _Suit | None
    _processing: bool

    __commit_quotient__: int                        # commit automatically after n entries. (default = 10)

    __slots__ = ('__buffer__', '__params__', 'db_path', 'sql_connection', 'sql_cursor', '_current_item',
                 '_chronicle_progress_id', '_chronicle_redo_id', '_unification_id', '_chronicle_clamp', '_get_id_',
                 '_get_order_', '_chronicle_cursor', '_order_id', '_processing', '_islocked', '_lock_acquire_',
                 '_lock_assert_', '_branch_fork_mode', '_fork_id', '_forked', '_items_max_action_', '_unlink_',
                 '_active_suit', '_fork_chronicle_clamp', 'db_attached', 'db_in_mem', '__commit_quotient__')

    @property
    def lock(self) -> bool:
        """whether the lock is engaged"""
        return self._islocked

    @lock.setter
    def lock(self, __val: bool) -> None:
        """Set the undo lock. Flush the redo memory when releasing the lock."""
        if not __val:
            self.flush_redo()
        self._islocked = __val

    @overload
    def __init__(self, *,
                 __buffer__: TextBuffer,
                 db_path: str | Literal[':memory:', ':swap:', 'file:...<uri>'],
                 from_db: str | SQLConnection | None | Literal['file:...<uri>'], unlink_atexit: bool,
                 undo_lock: bool, branch_forks: bool,
                 maximal_items: int | None, items_chunk_size: int, maximal_items_action: Callable[[], Any]):
        ...
    
    def __init__(self, **kwargs):
        """
        Create a new LocalHistory object.
        
        Keyword parameter:
            - `__buffer__`
                The :class:`TextBuffer` object for which LocalHistory is created.
            - `db_path`
                The location of the database can be specified as a filepath using an ordinal or
                `"Uniform Resource Identifier"`_ (URI) string;
                to create the database temporarily in RAM, the expression ``":memory:"`` can be used;
                another special expression is ``":swap:"`` to create the database in the same location of the database
                in :class:`_Swap`.
            - `from_db`
                To build the database and the object from an existing database, the origin can be passed as an ordinal
                path, a URI, or an existing SQL connection. The connection will be closed automatically afterwards,
                unless an SQL connection was passed.
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

        :raises ConfigurationError: if ":swap:" is used and there is no connection to a database in `__swap__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        __buffer__ = kwargs['__buffer__']
        db_path = kwargs['db_path']
        from_db = kwargs['from_db']
        unlink_atexit = kwargs['unlink_atexit']
        undo_lock = kwargs['undo_lock']
        branch_forks = kwargs['branch_forks']
        items_max = kwargs['maximal_items']
        items_max_chunk_size = kwargs['items_chunk_size']
        items_max_action = kwargs['maximal_items_action']
        
        self.__params__ = kwargs
        self.__buffer__ = __buffer__
        self._current_item = None
        self._chronicle_progress_id = 0
        self._chronicle_redo_id = None
        self._chronicle_cursor = None
        self._unification_id = None
        self._order_id = None
        self._processing = False
        self._islocked = False
        self._forked = None
        self._active_suit = None
        self.__commit_quotient__ = 10

        if undo_lock:
            def lock():
                self._islocked = True

            def lock_assert():
                assert not (not self._processing and self._islocked), 'undo lock is engaged'
        else:
            def lock():
                pass

            def lock_assert():
                pass

        self._lock_assert_ = lock_assert
        self._lock_acquire_ = lock
        self._branch_fork_mode = branch_forks
        self._fork_id = 0

        def get_id() -> int:
            self._chronicle_progress_id += 1
            return self._chronicle_progress_id

        self._get_id_ = get_id

        self._get_order_ = lambda: 0

        self.db_path = db_path

        if isinstance(db_path, SQLConnection):
            self.sql_connection = db_path
            self.sql_cursor = self.sql_connection.cursor(_sql.SQLTSCursor)
            self._unlink_ = self.sql_connection.close
            self.db_attached = True
        elif db_path == ':swap:':
            if not __buffer__.__swap__.sql_connection:
                raise ConfigurationError('__swap__: no db connection')
            self.sql_connection = __buffer__.__swap__.sql_connection
            self.sql_cursor = __buffer__.__swap__.sql_cursor
            self.db_attached = True
            self.db_in_mem = __buffer__.__swap__.db_in_mem

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

        with _sql.DATABASE_TABLE_ERROR_SUIT:
            try:
                self.sql_cursor.executescript('''
                CREATE TABLE local_history (
                id_ INT,
                type_ INT,
                typeval INT,
                work_row INT,
                coord TEXT,
                removed TEXT,
                restrict_removemend TEXT,
                cursor INT,
                order_ INT
                );
                CREATE TABLE local_history_branch (
                fork_id INT, 
                id_ INT,
                type_ INT,
                typeval INT,
                work_row INT,
                coord TEXT,
                removed TEXT,
                restrict_removemend TEXT,
                cursor INT,
                order_ INT
                );
                CREATE TABLE local_history_metas (
                undo_id INT,
                fork_id INT
                );
                CREATE INDEX local_history_main_ids_index ON local_history (id_);
                CREATE INDEX local_history_main_branch_ids_index ON local_history_branch (id_);
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
            query = from_db_cur.execute('SELECT * FROM local_history')
            while (row := query.fetchone()) is not None:
                self.sql_cursor.execute('INSERT INTO local_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', row)
            query = from_db_cur.execute('SELECT * FROM local_history_branch')
            while (row := query.fetchone()) is not None:
                self.sql_cursor.execute('INSERT INTO local_history_branch VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', row)
            self._chronicle_progress_id, self._fork_id = from_db_cur.execute('SELECT * FROM local_history_metas').fetchone()
            close()
            self.sql_connection.commit()

        self._chronicle_clamp = self._fork_chronicle_clamp = self._chronicle_progress_id

        if unlink_atexit:
            atexit.register(self.unlink)
        self.sql_connection.commit()

        if items_max is None:
            self._items_max_action_ = lambda: None
        else:
            maximal = items_max + items_max_chunk_size

            def _items_max_act():
                if self._chronicle_progress_id > maximal:

                    self.sql_connection.commit()

                    items_max_action()

                    self.sql_cursor.execute('DELETE FROM local_history WHERE 0 < id_ AND id_ <= ?', (items_max_chunk_size,))
                    self.sql_cursor.execute('DELETE FROM local_history_branch WHERE ABS(id_) <= ?', (items_max_chunk_size,))

                    '''self.sql_cursor.execute(
                        'DELETE FROM local_history_branch WHERE 0 < id_ AND id_ <= ?', (items_max_chunk_size,))
                    self.sql_cursor.execute(
                        'DELETE FROM local_history_branch WHERE 0 > id_ AND id_ >= ?', (-items_max_chunk_size,))'''

                    self.sql_cursor.executemany('UPDATE local_history SET id_ = ? WHERE id_ = ?',
                                                zip(range(1, self._chronicle_progress_id + 1),
                                                    range(items_max_chunk_size + 1, self._chronicle_progress_id + 1)))
                    self.sql_cursor.executemany('UPDATE local_history_branch SET id_ = ? WHERE id_ = ?',
                                                zip(range(1, self._chronicle_progress_id + 1),
                                                    range(items_max_chunk_size + 1, self._chronicle_progress_id + 1)))
                    self.sql_cursor.executemany('UPDATE local_history_branch SET id_ = -? WHERE id_ = -?',
                                                zip(range(1, self._chronicle_progress_id + 1),
                                                    range(items_max_chunk_size + 1, self._chronicle_progress_id + 1)))

                    # branch metas
                    for id_, coord, cur, ord_ in self.sql_cursor.execute(
                            'SELECT fork_id, coord, cursor, order_ FROM local_history_branch WHERE id_ = 0'
                    ).fetchall():
                        if (ord_ := ord_ - items_max_chunk_size) < 1:
                            self._forked = False
                            self.sql_cursor.execute('DELETE FROM local_history_branch WHERE fork_id = ?', (id_,))
                        else:
                            self.sql_cursor.execute(
                                'UPDATE local_history_branch SET '
                                'coord = ?, '
                                'cursor = ?, '
                                'order_ = ? '
                                'WHERE id_ = 0 AND fork_id = ?',
                                (repr([x - items_max_chunk_size for x in literal_eval(coord)]),
                                 cur - items_max_chunk_size, ord_, id_))

                    self.sql_connection.commit()

                    self._chronicle_progress_id -= items_max_chunk_size

                    self._chronicle_clamp = max(0, self._chronicle_clamp - items_max_chunk_size) or -2

            self._items_max_action_ = _items_max_act

    @overload
    def __new_db__(self, *,
                   __buffer__: TextBuffer = ...,
                   db_path: str | Literal[':memory:', ':swap:', 'file:...<uri>'] = ...,
                   from_db: str | SQLConnection | None | Literal['file:...<uri>'] = ...,
                   unlink_atexit: bool = ...,
                   undo_lock: bool = ...,
                   branch_forks: bool = ...,
                   maximal_items: int | None = ...,
                   items_chunk_size: int = ...,
                   maximal_items_action: Callable[[], Any] = ...) -> _LocalHistory:
        ...

    def __new_db__(self, **kwargs) -> _LocalHistory:
        """
        Create a new ``_LocalHistory`` with the same parameters, except `from_db` is set to ``None`` by default.
        Parameters can be overwritten via `kwargs`.

        :raises ConfigurationError: if ":swap:" is used and there is no connection to a database in `__swap__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        return self.__class__(**(self.__params__ | {'from_db': None} | kwargs))

    def auto_commit(self) -> None:
        """
        Commit the connection if the chronological number of the last entry can be divided restless by
        ``__commit_quotient__`` (default = 10).
        """
        if not self._chronicle_progress_id % self.__commit_quotient__:
            self.sql_connection.commit()

    def clamp_is_diff(self) -> bool:
        """
        Returns whether the set id clamp is different from the chronological progress.
        """
        if self._current_item:
            return True
        elif self._chronicle_cursor is not None:
            return self._chronicle_clamp != self._chronicle_cursor - 1
        else:
            return self._chronicle_clamp != self._chronicle_progress_id

    def clamp_in_past(self) -> bool:
        """
        Returns whether the set id clamp is less than the chronological progress.
        """
        if self._chronicle_cursor is not None:
            return self._chronicle_clamp < self._chronicle_cursor - 1
        else:
            return self._chronicle_clamp < self._chronicle_progress_id + bool(self._current_item)

    def clamp_diff(self) -> int:
        """
        Returns the difference between the set id clamp and the chronological progress as an absolute integer.
        """
        if self._chronicle_cursor is not None:
            return abs(self._chronicle_clamp - (self._chronicle_cursor - 1))
        else:
            return abs(self._chronicle_clamp - (self._chronicle_progress_id + bool(self._current_item)))

    def clamp_is_reachable(self) -> Literal[0, 1, 2]:
        """
        Returns whether the chronological id clamp is reachable.

        returns:
         - ``0``: not reachable (the clamp was lost during -- trimming after the maximum number of items was reached;
           branching after the branch was changed; flushing redo items after undo and branch forks are not supported).
         - ``1``: reachable by ``undo``/``redo`` or the current id is equal to the clamp.
         - ``2``: reachable by ``branch_fork`` [+ ``redo``].
        """
        if self._chronicle_clamp in (-2, -3):
            return 0
        elif self._chronicle_clamp == -1:
            return 2
        else:
            return 1

    def clamp_set(self, *, dump_current: bool = True) -> None:
        """
        Sets the current chronological process id, for the comparison in ``clamp_is_diff``.
        Dumps the current history item if present and `dump_current` is ``True`` (default).
        """
        if self._current_item and dump_current:
            self._dump_current_item()
        if self._chronicle_cursor is not None:
            self._chronicle_clamp = self._chronicle_cursor
        else:
            self._chronicle_clamp = self._chronicle_progress_id

    def dump_metas(self) -> None:
        """Dump the metadata into the database and do commit."""
        self.sql_cursor.execute('DELETE FROM local_history_metas')
        self.sql_cursor.execute('INSERT INTO local_history_metas VALUES (?, ?)', (self._chronicle_progress_id, self._fork_id))
        self.sql_connection.commit()

    def backup(self, dst: str | SQLConnection | Literal['file:...<uri>']) -> None:
        """
        Dump the currently held item, then clone all items and metadata into `dst`.
        Close the connection to the backup-db if `dst` is defined as path or URI.

        :raises ValueError: if ":swap:" or ":memory:" is used as `dst`.
        :raises DatabaseFilesError: `dst` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        if dst in (':memory:', ':swap:'):
            raise ValueError('":swap:" or ":memory:" is not designated as a destination.')
        if self._current_item:
            self._dump_current_item()
        self.flush_redo()
        self.dump_metas()
        db = self.__new_db__(db_path=dst, from_db=self.sql_connection, unlink_atexit=False)
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
        \\:swap:         \\- > dropall
        SQL-Connection   \\- > Connection.close
        ==============  ===================================
        """
        atexit.unregister(self.unlink)
        self._unlink_()

    def dropall(self) -> None:
        """Delete all entries in the tables of the database and discard the indexes."""
        self.sql_cursor.executescript('''
                    DELETE FROM local_history;
                    DELETE FROM local_history_branch;
                    DELETE FROM local_history_metas;
                    DROP INDEX local_history_main_ids_index;
                    DROP INDEX local_history_main_branch_ids_index;
                    ''')
    
    @overload
    def clone(self,
              to_db: str | Literal[':memory:', ':swap:', 'file:...<uri>'] | SQLConnection,
              unlink_origin: bool = False,
              *,
              unlink_atexit: bool = ...,
              undo_lock: bool = ...,
              branch_forks: bool = ...,
              maximal_items: int | None = ...,
              items_chunk_size: int = ...,
              maximal_items_action: Callable[[], Any] = ...) -> _LocalHistory:
        ...

    def clone(self,
              to_db: str | Literal[':memory:', ':swap:', 'file:...<uri>'] | SQLConnection,
              unlink_origin: bool = False,
              **kwargs) -> _LocalHistory:
        """
        Clone the database and metadata into a new ``_LocalHistory`` object. 
        The standard parameterization is the same as the original and can be overridden via keyword arguments.
        If `unlink_origin` is set to ``True``, the existing database is deleted depending on its location:

        ==============  ===================================
        db origin       unlink
        ==============  ===================================
        Filepath         \\- > Connection.close ; os.unlink
        \\:memory:       \\- > Connection.close
        \\:swap:         \\- > dropall
        SQL-Connection   \\- > Connection.close
        ==============  ===================================
        
        - Returns the new ``_LocalHistory`` object.

        :raises ConfigurationError: if ":swap:" is used and there is no connection to a database in `__swap__`.
        :raises DatabaseFilesError: `db_path` already exists.
        :raises DatabaseTableError: if the database tables already exist in the destination.
        """
        if self._current_item:
            self._dump_current_item()
        self.flush_redo()
        self.dump_metas()
        db = self.__new_db__(db_path=to_db, from_db=self.sql_connection, **kwargs)
        if unlink_origin:
            self.unlink()
        return db
    
    def _dump(self,
              id_: int,
              __itm_id_: int = None,
              type_: int = None,
              typeval: int = None,
              work_row: int = None,
              coord: list = None,
              removed: list = None,
              restrict_removed: list = None,
              cursor: int = None,
              __itm_order_: int = None,
              order_: int = None) -> None:
        """
        Write a new :class:`HistoryItem` entry in the database (Bypassed when `id_` is 0).
        Delete entries when the upper limit is reached, and it is configured."""
        if not id_:
            return
        self.sql_cursor.execute("INSERT INTO local_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (id_,
                                 type_,
                                 typeval,
                                 work_row,
                                 (repr(coord) if coord is not None else None),
                                 (repr(removed) if removed is not None else None),
                                 None,
                                 cursor,
                                 order_))
        self.__buffer__.__trimmer__.__local_history__add_res_removemend_by_item__(id_, restrict_removed)
        self.auto_commit()
        self._items_max_action_()

    def _dump_current_item(self) -> None:
        """Dump the currently held item."""
        self._dump(self._get_id_(), *self._current_item, order_=self._get_order_())
        self._current_item = None

    def dump_current_item(self) -> bool:
        """
        Dump the currently held item if present.

        :return: whether an item was dumped
        """
        if self._current_item:
            self._dump_current_item()
            return True
        return False

    def _unite(self, _dedicated_id: int = None) -> Callable[[], None]:
        """
        Starts the unification of the following actions. Returns the reset function.
        Generates a new history id when `_dedicated_id` is None.
        `_dedicated_id` is intended for internal use within undo.
        """
        if self._order_id is None:

            if self._current_item:
                self._dump_current_item()

            if _dedicated_id is None:
                self.flush_redo()
                self._unification_id = self._get_id_()
            else:
                self._unification_id = _dedicated_id

            self._order_id = 0

            def get_id() -> int:
                return self._unification_id

            def get_order() -> int:
                self._order_id -= 1
                return self._order_id

            self._get_id_ = get_id
            self._get_order_ = get_order

            def reset():

                if self._current_item:
                    self._dump_current_item()

                if not self._order_id and _dedicated_id is None:
                    self._chronicle_progress_id -= 1

                self._unification_id = None
                self._order_id = None

                def get_id() -> int:
                    self._chronicle_progress_id += 1
                    return self._chronicle_progress_id

                self._get_id_ = get_id
                self._get_order_ = lambda: 0

            return reset
        elif _dedicated_id is None:  # nested unite
            return lambda: None
        else:
            raise RuntimeError('undo/redo while uniting')

    def _add_removed(self, removed: Iterable[tuple[int, list[tuple[str, str | bool | None]]]]) -> None:
        """Create and add a history item for removed data ranges."""
        self.flush_redo()
        if self._current_item:
            self._dump_current_item()

        reset_unite = self._unite()
        for item in removed:
            self._dump(
                id_=self._get_id_(),
                type_=HistoryItem.TYPES.REMOVE_RANGE,
                removed=item[1],
                cursor=item[0],
                order_=self._get_order_()
            )

        reset_unite()

    def _add_marks(self, typeval: int, get_marks: Callable[[], list[list[int, int]]], cursor: int = None) -> None:
        self.flush_redo()
        if self._current_item:
            self._dump_current_item()

        self._dump(
            id_=self._get_id_(),
            type_=HistoryItem.TYPES.MARKS,
            typeval=typeval,
            coord=get_marks(),
            cursor=cursor,
            order_=self._get_order_()
        )

    def _add_marks_async(self, h_comment: int, mark_reader: Callable[[], list[list[int, int]]]) -> _AddMarksASync:
        return _AddMarksASync(self, h_comment, mark_reader)

    def _add_rmchr(self,
                   typeval: int,
                   write_item: WriteItem,
                   end: str | bool) -> None:
        """
        Create and add a history item for single removals.
        Hold the item to expand it with the following similar actions.
        """
        self.flush_redo()
        if self._current_item:
            if self._current_item.type_ == HistoryItem.TYPES.REMOVE:
                if (HistoryItem.TYPEVALS.DELETE == self._current_item.typeval == typeval) and \
                        self._current_item.coord[0] == write_item.begin:
                    self._current_item.removed[0][0] += write_item.removed
                    return
                elif (HistoryItem.TYPEVALS.BACKSPACE == self._current_item.typeval == typeval) and \
                        self._current_item.coord[0] - 1 == write_item.begin:
                    self._current_item.coord[0] = write_item.begin
                    self._current_item.removed[0][0] = write_item.removed + self._current_item.removed[0][0]
                    self._current_item.coord[0] = write_item.begin
                    return
                elif (HistoryItem.TYPEVALS.DELETED_NEWLINE == self._current_item.typeval == typeval) and \
                        self._current_item.coord[0] == write_item.begin:
                    self._current_item.removed.append([write_item.removed, end])
                    return
                elif (HistoryItem.TYPEVALS.BACKSPACED_NEWLINE == self._current_item.typeval == typeval) and \
                        self._current_item.coord[0] - 1 == write_item.begin:
                    self._current_item.removed.insert(0, [write_item.removed, end])
                    self._current_item.coord[0] = write_item.begin
                    return

            self._dump_current_item()

        cur = [write_item.begin]
        removed = [[write_item.removed, end]]

        self._current_item = HistoryItem(
            type_=HistoryItem.TYPES.REMOVE,
            typeval=typeval,
            coord=cur,
            removed=removed,
            work_row=write_item.work_row
        )

    def _add_resremove(self, resrem__i1: Sequence[Any, list[list[_Row]]] | None) -> None:
        self.__buffer__.__trimmer__.__local_history__add_res_removemend__(resrem__i1)

    def _add_iterwork(self, worked: list[tuple[list[int, int] | int, list[WriteItem | None]]]) -> None:
        """
        Add unified history items for the editing via rowwork.
        """
        diffs = list()
        diff = 0
        for coord, items in reversed(worked):
            diffs.insert(0, list())
            for item in items:
                diffs[0].insert(0, diff)
                if item:
                    diff += item.diff

        # unite-suit in TextBuffer.rowwork
        for work, _diffs in zip(worked, diffs):
            coord, items = work
            for n, item in enumerate(reversed(items)):
                if item:
                    self._add_write(item, None, False, None, _diffs[n])
        self.dump_current_item()

    def _add_write(self,
                   write_item: WriteItem,
                   overflow_removed: list[tuple[str, str | bool | None]] | None,
                   line_insert: bool,
                   btm_cut: list[list[_Row]] | None,
                   shadow_diff: int = 0) -> None:
        """
        Create and add a history item for written data.
        Hold the item to expand it with the following similar actions.
        """
        self.flush_redo()

        (_resremexp, _dumpresrem, _curitemresremandresrem, restrict_removed
         ) = self.__buffer__.__trimmer__.__local_history__add_res_removemend_by_write__(btm_cut)

        if self._current_item:

            if _curitemresremandresrem():

                if self._current_item.type_ == HistoryItem.TYPES.WRITE and write_item.write == 1:
                    if not (line_insert and write_item.removed) and not overflow_removed:
                        if (
                                write_item.removed and
                                self._current_item.typeval == HistoryItem.TYPEVALS.SUBSTITUTED and
                                self._current_item.coord[1] == write_item.begin and
                                self._current_item.work_row == write_item.work_row
                        ):
                            _resremexp()
                            self._current_item.coord[1] += 1
                            self._current_item.removed[0][0] += write_item.removed
                            return
                        elif (
                                write_item.newlines and
                                self._current_item.typeval == HistoryItem.TYPEVALS.W_HAS_NEWLINE and
                                self._current_item.coord[1] == write_item.begin
                        ):
                            _resremexp()
                            self._current_item.coord[1] += 1
                            return
                        elif (
                                self._current_item.typeval == HistoryItem.TYPEVALS.WRITE and
                                self._current_item.coord[1] == write_item.begin and
                                self._current_item.work_row == write_item.work_row
                        ):
                            _resremexp()
                            self._current_item.coord[1] += 1
                            return

            self._dump_current_item()

        if line_insert and (write_item.removed or overflow_removed):
            if write_item.removed:
                removed = [[write_item.removed, write_item.removed_end]]
                if overflow_removed:
                    removed += overflow_removed
            else:
                removed = overflow_removed
            reset_unite = self._unite()
            self._dump(
                id_=self._get_id_(),
                type_=HistoryItem.TYPES.WRITE,
                typeval=HistoryItem.TYPEVALS.LINE_SUBSTITUTED,
                coord=[write_item.begin, write_item.begin + write_item.write],
                removed=removed,
                work_row=write_item.work_row,
                order_=self._get_order_()
            )
            _dumpresrem()
            reset_unite()

        elif write_item.removed:
            removed: list[list[str | bool] | tuple[str, str | bool | None]] = [[write_item.removed, False]]
            if overflow_removed:
                reset_unite = self._unite()
                self._dump(
                    id_=self._get_id_(),
                    type_=HistoryItem.TYPES.WRITE,
                    typeval=HistoryItem.TYPEVALS.SUBSTITUTED,
                    coord=[write_item.begin, write_item.begin + write_item.write],
                    removed=removed + overflow_removed,
                    work_row=write_item.work_row,
                    order_=self._get_order_()
                )
                _dumpresrem()
                reset_unite()

            elif write_item.write:
                self._current_item = HistoryItem(
                    type_=HistoryItem.TYPES.WRITE,
                    typeval=HistoryItem.TYPEVALS.SUBSTITUTED,
                    coord=[write_item.begin, write_item.begin + write_item.write],
                    removed=removed,
                    restrict_removed=restrict_removed,
                    work_row=write_item.work_row
                )
            else:
                reset_unite = self._unite()
                self._dump(
                    id_=self._get_id_(),
                    type_=HistoryItem.TYPES.WRITE,
                    typeval=HistoryItem.TYPEVALS.W_REMOVE,
                    coord=[write_item.begin],
                    removed=removed,
                    work_row=write_item.work_row,
                    order_=self._get_order_()
                )
                _dumpresrem()
                reset_unite()

        elif write_item.newlines:
            self._current_item = HistoryItem(
                type_=HistoryItem.TYPES.WRITE,
                typeval=HistoryItem.TYPEVALS.W_HAS_NEWLINE,
                coord=[(b := write_item.begin + shadow_diff), b + write_item.write],
                restrict_removed=restrict_removed,
                work_row=write_item.work_row,
            )
        else:
            self._current_item = HistoryItem(
                type_=HistoryItem.TYPES.WRITE,
                typeval=HistoryItem.TYPEVALS.WRITE,
                coord=[(b := write_item.begin + shadow_diff), b + write_item.write],
                restrict_removed=restrict_removed,
                work_row=write_item.work_row,
            )

    def _add_cursor(self, cursor: Callable[[], int]) -> None:
        """Create and add a history item for cursor positions."""
        self.flush_redo()
        if self._current_item:
            self._dump_current_item()
        self._dump(
            id_=self._get_id_(),
            type_=HistoryItem.TYPES.CURSOR,
            typeval=HistoryItem.TYPEVALS.POSITION,
            cursor=cursor(),
            order_=self._get_order_()
        )

    def _do(self, items: list[HistoryItem], _dedicated_id: int
            ) -> ChunkLoad:
        """
        Process history items, create the respective counterparts under the `_dedicated_id`.

        [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.sizing [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust
        [+] __local_history__ [+] __highlighter__.prep_by_chunkload
        """
        def _rewrite(_cur: int, removed: list[list[str, str | bool | None]]):
            self.__buffer__.__display__.__highlighter__._prepare_by_chunkload(
                ChunkLoad(
                    self.__buffer__.__swap__.current_chunk_ids[0],
                    self.__buffer__.__swap__.current_chunk_ids[1],
                    spec_position=self.__buffer__.goto_data(_cur).spec_position))
            _ran = 0
            after_row = (row := self.__buffer__.current_row)._remove_area(row.cursors.content, None)
            after_rows = self.__buffer__.rows[row.__row_index__ + 1:]
            self.__buffer__.rows = self.__buffer__.rows[:row.__row_index__ + 1]
            self.__buffer__.__display__.__highlighter__._prepare_by_writeitem(self.__buffer__.rows[-1].__row_num__, gt_too=True)
            for rrow in removed:
                self.__buffer__.rows.append(
                    rowbuffer := _Row.__newrow__(self.__buffer__._future_baserow))
                row_content, end = rrow
                _ran += len(row_content) + (hasend := isinstance(end, str))
                while of := rowbuffer._write_line(row_content)[0]:
                    row_content = of[0]
                    self.__buffer__.rows.append(rowbuffer := _Row.__newrow__(self.__buffer__._future_baserow))
                if hasend:
                    with rowbuffer:
                        rowbuffer.end = end
            self.__buffer__.rows.append(
                rowbuffer := _Row.__newrow__(self.__buffer__._future_baserow))
            rowbuffer._write_line(after_row[0])
            with rowbuffer:
                rowbuffer.end = after_row[1]

            self.__buffer__.rows += after_rows

            self.__buffer__._adjust_rows(0, endings=True, dat_start=_cur, diff=_ran)
            self.__buffer__.__swap__.__meta_index__.adjust_bottom_auto()

            return _ran

        reset_unite = self._unite(_dedicated_id)
        self._processing = True
        resrem_cursor = goto = None
        try:
            with self.__buffer__.__display__.__highlighter__.suit('sum'):
                with self.__buffer__.__trimmer__.suit(all_=False, _trim=False, _poll=False, _dmnd=False):
                    try:
                        __item = items.pop(0)
                        while True:
                            if __item.type_ == HistoryItem.TYPES.WRITE:
                                if __item.typeval in (HistoryItem.TYPEVALS.SUBSTITUTED,
                                                      HistoryItem.TYPEVALS.LINE_SUBSTITUTED):
                                    self.__buffer__.remove([__item.coord], 'd')
                                    ran = _rewrite(__item.coord[0], __item.removed)
                                    self._dump(
                                        id_=self._get_id_(),
                                        type_=HistoryItem.TYPES.RE_WRITE,
                                        typeval=HistoryItem.TYPEVALS.RE_SUBSTITUTION,
                                        coord=[__item.coord[0], (goto := __item.coord[0]) + ran],
                                        order_=self._get_order_(),
                                        work_row=__item.work_row
                                    )
                                elif __item.typeval == HistoryItem.TYPEVALS.W_REMOVE:
                                    ran = _rewrite(__item.coord[0], __item.removed)
                                    self._dump(
                                        id_=self._get_id_(),
                                        type_=HistoryItem.TYPES.RE_WRITE,
                                        typeval=HistoryItem.TYPEVALS.RE_WRITE,
                                        coord=[__item.coord[0], (goto := __item.coord[0]) + ran],
                                        order_=self._get_order_(),
                                        work_row=__item.work_row
                                    )
                                else:  # self.HistoryItem.TYPEVALS.WRITE or self.HistoryItem.TYPEVALS.W_HAS_NEWLINE
                                    coords = [__item.coord]
                                    try:
                                        while (__item := items.pop(0)).typeval in (HistoryItem.TYPEVALS.WRITE,
                                                                                   HistoryItem.TYPEVALS.W_HAS_NEWLINE):
                                            coords.append(__item.coord)
                                    except IndexError:
                                        goto = coords[0][0]
                                        self.__buffer__.remove(coords, 'd')
                                        raise IndexError
                                    else:
                                        goto = coords[0][0]
                                        self.__buffer__.remove(coords, 'd')
                                        continue
                            elif __item.type_ == HistoryItem.TYPES.RESTRICT_REMOVEMENT:
                                idx = self.__buffer__.rows[-1].__row_index__
                                for row_content, end in self.__buffer__.__trimmer__.__local_history__get_res_removemend_by_item__(__item):
                                    self.__buffer__.rows.append(
                                        rowbuffer := _Row.__newrow__(self.__buffer__._future_baserow))
                                    while of := rowbuffer._write_line(row_content)[0]:
                                        row_content = of[0]
                                        self.__buffer__.rows.append(
                                            rowbuffer := _Row.__newrow__(self.__buffer__._future_baserow))
                                    if isinstance(end, str):
                                        with rowbuffer:
                                            rowbuffer.end = end
                                self.__buffer__.indexing(idx)
                                if resrem_cursor:
                                    self.sql_cursor.execute(
                                        "INSERT INTO local_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                        (self._get_id_(), HistoryItem.TYPES.RESTRICT_REMOVEMENT,
                                         None, None, None, None, None, resrem_cursor, self._get_order_()))
                                    self.auto_commit()
                                resrem_cursor = __item.order_
                            elif __item.type_ == HistoryItem.TYPES.REMOVE:
                                ran = _rewrite(__item.coord[0], __item.removed)
                                self._dump(
                                    id_=self._get_id_(),
                                    type_=HistoryItem.TYPES.RE_WRITE,
                                    typeval=HistoryItem.TYPEVALS.RE_WRITE,
                                    coord=[__item.coord[0], (goto := __item.coord[0]) + ran],
                                    order_=self._get_order_(),
                                    work_row=__item.work_row
                                )
                            elif __item.type_ == HistoryItem.TYPES.CURSOR:
                                self.__buffer__.goto_data(__item.cursor)
                                goto = None
                            elif __item.type_ == HistoryItem.TYPES.MARKS:
                                cur_marks = self.__buffer__.__marker__.sorted_copy()
                                if (_goto := __item.cursor) is None:
                                    if diff := [coord for coord in cur_marks if coord not in __item.coord]:
                                        cur = diff[-1][1]
                                    else:
                                        cur = None
                                else:
                                    goto = _goto
                                    cur = self.__buffer__.current_row.cursors.data_cursor
                                self._dump(
                                    id_=self._get_id_(),
                                    type_=HistoryItem.TYPES.MARKS,
                                    typeval=HistoryItem.TYPEVALS.MARKERCOMMENTS.UNDO_REDO,
                                    coord=cur_marks,
                                    cursor=cur,
                                    order_=self._get_order_()
                                )
                                self.__buffer__.__marker__.markings = __item.coord
                            elif __item.type_ == HistoryItem.TYPES.REMOVE_RANGE:
                                ran = _rewrite(__item.cursor, __item.removed)
                                self._dump(
                                    id_=self._get_id_(),
                                    type_=HistoryItem.TYPES.RE_WRITE,
                                    typeval=HistoryItem.TYPEVALS.RE_WRITE,
                                    coord=[__item.cursor, (goto := __item.cursor + ran)],
                                    order_=self._get_order_()
                                )
                            elif __item.type_ == HistoryItem.TYPES.RE_WRITE:
                                if __item.typeval == HistoryItem.TYPEVALS.RE_WRITE:
                                    coords = [__item.coord]
                                    try:
                                        while (__item := items.pop(0)).typeval == HistoryItem.TYPEVALS.RE_WRITE:
                                            coords.append(__item.coord)
                                    except IndexError:
                                        coords.reverse()
                                        self.__buffer__.remove(coords, 'd')
                                        raise IndexError
                                    else:
                                        coords.reverse()
                                        self.__buffer__.remove(coords, 'd')
                                        continue
                                else:  # item.typeval == self.Item.TYPEVALS.RANGE_INSERTION:
                                    self.__buffer__.remove([__item.coord], 'd')
                            else:
                                raise AttributeError(f'{__item.type_=}')

                            __item = items.pop(0)

                    except IndexError:
                        pass

                if resrem_cursor:
                    self.sql_cursor.execute(
                        "INSERT INTO local_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (self._get_id_(), HistoryItem.TYPES.RESTRICT_REMOVEMENT,
                         None, None, None, None, None, resrem_cursor, self._get_order_()))
                    self.auto_commit()

                if goto is not None:
                    spec_pos = self.__buffer__._goto_data(goto)
                    cl = ChunkLoad(
                        self.__buffer__.__swap__.current_chunk_ids[0], self.__buffer__.__swap__.current_chunk_ids[1],
                        *self.__buffer__.__trimmer__.action__demand__(),
                        spec_position=spec_pos)
                else:
                    cl = ChunkLoad(
                        self.__buffer__.__swap__.current_chunk_ids[0], self.__buffer__.__swap__.current_chunk_ids[1],
                        *self.__buffer__.__trimmer__.action__demand__())

                self.__buffer__.__display__.__highlighter__._prepare_by_chunkload(cl)

        finally:
            reset_unite()
            self._processing = False

        return cl

    def undo(self) -> tuple[list[HistoryItem], ChunkLoad] | None:
        """
        Undo the last edit in the buffer and create counterparts to the undo action for ``redo``.
        Can be executed in sequence.

        [+] __swap__.adjust [+] __swap__.fill [+] __swap__.suit [+] __trimmer__.sizing [+] __trimmer__.trim
        [+] __highlighter__.prep_by_undoredo [+] __marker__.adjust [+] __glob_cursor__.adjust

        Returns: ( [`<`\\ :class:`HistoryItem` `per action>`, ...], `<final` :class:`ChunkLoad`\\ `>` )
        or ``None`` when nothing has been processed.
        """
        if self._current_item:
            self._dump_current_item()
        if not self._chronicle_progress_id:
            return
        if self._chronicle_cursor is None:
            self.__buffer__.__marker__.stop()
            self._lock_acquire_()
            self._chronicle_cursor = self._chronicle_redo_id = self._chronicle_progress_id
            _dedicated_id = -self._chronicle_cursor
        else:
            if not self._chronicle_cursor:
                return
            self._chronicle_cursor -= 1
            if not self._chronicle_cursor:
                return
            if self._chronicle_cursor == self._chronicle_redo_id:
                _dedicated_id = 0
            elif self._chronicle_cursor < self._chronicle_redo_id:
                self._chronicle_redo_id -= 1
                _dedicated_id = -self._chronicle_cursor
            else:
                _dedicated_id = 0

        hitems = [HistoryItem.from_db(row) for row in self.sql_cursor.execute(
            "SELECT * FROM local_history WHERE id_ = ?", (self._chronicle_cursor,)).fetchall()]
        hitems.sort(key=lambda itm: itm.order_)

        return hitems, self._do(hitems.copy(), _dedicated_id)

    def redo(self) -> tuple[list[HistoryItem], ChunkLoad] | None:
        """
        Redo the last undone action in the buffer and create counterparts to the redo action for ``undo``.
        Can be executed in sequence.

        [+] __swap__.adjust [+] __swap__.fill [+] __swap__.suit [+] __trimmer__.sizing [+] __trimmer__.trim
        [+] __highlighter__.prep_by_undoredo [+] __marker__.adjust [+] __glob_cursor__.adjust

        Returns: ( [`<`\\ :class:`HistoryItem` `per action>`, ...], `<final` :class:`ChunkLoad`\\ `>` )
        or ``None`` when nothing has been processed.
        """
        if self._chronicle_cursor is None or self._chronicle_cursor > self._chronicle_progress_id:
            return
        hitems = [HistoryItem.from_db(row) for row in self.sql_cursor.execute(
            "SELECT * FROM local_history WHERE id_ = ?", (-self._chronicle_cursor,)).fetchall()]
        hitems.sort(key=lambda itm: itm.order_)

        self._chronicle_cursor += 1

        return hitems, self._do(hitems.copy(), 0)

    def branch_fork(
            self, __redo_hint: int | Literal['all'] = 0
    ) -> ChunkLoad | None:
        """
        Switch the branch fork.
        Execute ``redo`` `n` times or as many times as possible if the parameterization is
        ``"all"``. Set the clamp to ``-1``,so that future execution of ``clamp_is_diff`` returns ``True`` until
        a new clamp is set or the branch is changed back.

        [+] __swap__.adjust [+] __swap__.fill [+] __swap__.suit [+] __trimmer__.sizing [+] __trimmer__.trim
        [+] __highlighter__.prep_by_bypass [+] __marker__.adjust [+] __glob_cursor__.adjust

        :raises ConfigurationError: branch forks not configured.
        :raises DatabaseCorruptedError: Programming Error | Corrupted Data
        """
        if not self._branch_fork_mode:
            raise ConfigurationError('branch forks not configured')
        if not self._forked:
            return
        if meta := self.sql_cursor.execute(
                "SELECT coord, cursor, order_ FROM local_history_branch WHERE fork_id = ? AND id_ = 0",
                (fork_id := (self._fork_id ^ 1),)
        ).fetchone():

            self._forked = True
            _id_clamp = self._chronicle_clamp

            if self._current_item:
                self._dump_current_item()

            with self.__buffer__.__trimmer__.suit(all_=False, _trim=False, _poll=False, _dmnd=False), self.__buffer__.__display__.__highlighter__.suit('null'):

                if self._chronicle_cursor is not None:
                    while self._chronicle_cursor < meta[1]:
                        if not self.redo():
                            raise DatabaseCorruptedError('# Programming Error | Corrupted Data')
                    while self._chronicle_cursor > meta[1]:
                        if not self.undo():
                            raise DatabaseCorruptedError('# Programming Error | Corrupted Data')

                elif self._chronicle_progress_id > meta[2]:
                    if not self.undo():
                        raise DatabaseCorruptedError('# Programming Error | Corrupted Data')
                    while meta[1] < self._chronicle_cursor:
                        if not self.undo():
                            raise DatabaseCorruptedError('# Programming Error | Corrupted Data')

                self.flush_redo()

                for id_ in self.sql_cursor.execute(
                        "SELECT id_ FROM local_history_branch WHERE fork_id = ? AND NOT id_ = 0",
                        (fork_id,)).fetchall():

                    self.sql_cursor.execute("DELETE FROM local_history WHERE id_ = ?", id_)
                    for row in self.sql_cursor.execute("SELECT * FROM local_history_branch "
                                                       "WHERE fork_id = ? AND id_ = ?",
                                                       (fork_id, id_[0])).fetchall():
                        self.sql_cursor.execute("INSERT INTO local_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row[1:])

                self._chronicle_progress_id, self._chronicle_redo_id = literal_eval(meta[0])
                self._chronicle_cursor = meta[1]

                self.sql_connection.commit()

                if __redo_hint == 'all':
                    while self.redo():
                        pass
                else:
                    for _ in range(__redo_hint):
                        if not self.redo():
                            break

                self._fork_id = fork_id

                if _id_clamp == -1:
                    self._chronicle_clamp = self._fork_chronicle_clamp

            return ChunkLoad(self.__buffer__.__swap__.current_chunk_ids[0],
                             self.__buffer__.__swap__.current_chunk_ids[1],
                             *self.__buffer__.__trimmer__.action__demand__())

    def flush_redo(self) -> None:
        """Flush the redo memory [ and create a branch fork if configured ]."""
        if not self._processing and self._chronicle_cursor is not None:

            _undo_id = max(0, self._chronicle_cursor - 1)

            if self._branch_fork_mode:

                if self._chronicle_clamp == -1:
                    self._chronicle_clamp = -3
                elif self._chronicle_clamp > _undo_id:
                    self._fork_chronicle_clamp = self._chronicle_clamp
                    self._chronicle_clamp = -1

                self.sql_cursor.execute("DELETE FROM local_history_branch WHERE fork_id = ?", (self._fork_id,))

                self.sql_cursor.execute(
                    "INSERT INTO local_history_branch (fork_id, id_, type_, coord, cursor, order_) "
                    "VALUES (?, 0, ?, ?, ?, ?)", (self._fork_id, HistoryItem.TYPES.BRANCH_METADATA,
                                                  f"[{self._chronicle_progress_id}, {self._chronicle_redo_id}]",
                                                  self._chronicle_cursor,
                                                  _undo_id))

                min_id = self.sql_cursor.execute("SELECT MIN(id_) FROM local_history").fetchone()[0]
                max_id = self.sql_cursor.execute(
                    "SELECT MAX(id_) FROM local_history WHERE id_ > ?", (_undo_id,)).fetchone()[0] or 0
                for ids in (range(min_id, 0), range(_undo_id + 1, max_id + 1)):
                    for id_ in ids:
                        if query := self.sql_cursor.execute("SELECT * FROM local_history WHERE id_ = ?",
                                                            (id_,)).fetchall():
                            for row in query:
                                self.sql_cursor.execute("INSERT INTO local_history_branch VALUES "
                                                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (self._fork_id,) + row)

                # query = self.cursor.execute("SELECT * FROM __local_history__ WHERE id < 0 OR id > ?", (self._undo_id,))
                # while (row := query.fetchone()) is not None:
                #    self.cursor.execute("INSERT INTO local_history_branch VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
                # # DBMS probably changes the addresses after the first write access,
                # # so fetchone raises an error or returns None.

                self._fork_id ^= 1
                self._forked = True

            elif self._chronicle_clamp > _undo_id:
                self._chronicle_clamp = -3

            self.sql_cursor.execute("DELETE FROM local_history WHERE id_ < 0 OR id_ > ?", (_undo_id,))
            self.sql_connection.commit()

            self._chronicle_progress_id = _undo_id
            self._chronicle_redo_id = None
            self._chronicle_cursor = None

    def lock_release(self) -> None:
        """Set the undo lock. Flush the redo memory when releasing the lock."""
        self.flush_redo()
        self._islocked = False

    def suit(self, mode: Literal['_ignore', 'unite'] = 'unite', leave_active: bool = False) -> _Suit[_LocalHistory]:
        """
        Dump a held history item if available. Then return a suit depending on mode.

        (when entering, ``__local_history__`` is returned)

        >>> with __local_history__.suit(<mode>)[ as local_history]:
        >>>     ...

        Modes:
            - ``"unite"`` :
                Unite the actions inside the suit into one chronological action.
            - ``"_ignore"`` :
                Disable the following dump of history items, but not the creation of held items.
                **WARNING**: May disturb the stability of local history and the buffer
                when edits to the data is skipped.

        If a suit is active and `leave_active` is ``True``, ``__exit__`` of the active suit is executed and a
        new one is created, otherwise a dummy is returned.
        """
        if self._active_suit:
            if leave_active:
                self._active_suit.__exit__(None, None, None)
            else:
                return _Suit(lambda *_: self, lambda *_: None)

        if self._current_item:
            self._dump_current_item()

        if mode[0] == '_':
            def enter(suit) -> _LocalHistory:
                self._active_suit = suit
                self._get_id_ = lambda: 0
                return self

            def exit_(*_):
                def get_id() -> int:
                    self._chronicle_progress_id += 1
                    return self._chronicle_progress_id

                self._get_id_ = get_id
                self._active_suit = None

        else:
            resetunite: Callable

            def enter(suit) -> _LocalHistory:
                nonlocal resetunite
                self._active_suit = suit
                resetunite = self._unite()
                return self

            def exit_(*_):
                resetunite()
                self._active_suit = None

        return _Suit(enter, exit_)


class _AddMarksASync:

    __local_history__: _LocalHistory
    h_comment: int
    mark_reader: Callable[[], list[list[int, int]]]
    marks: list[list[int, int]]
    cursor: int | None
    chronological_id: int
    order_id: int

    __slots__ = ('__local_history__', 'h_comment', 'mark_reader', 'marks', 'cursor', 'chronological_id', 'order_id')

    def __init__(self, __local_history__: _LocalHistory,
                 h_comment: int, mark_reader: Callable[[], list[list[int, int]]]):
        self.__local_history__ = __local_history__
        self.h_comment = h_comment
        self.mark_reader = mark_reader
        self.cursor = None

    def read_marks(self) -> _AddMarksASync:
        self.marks = self.mark_reader()
        return self

    def add_cursor(self, cursor: int | None) -> _AddMarksASync:
        self.cursor = cursor
        return self

    def flush(self) -> _AddMarksASync:
        self.__local_history__.flush_redo()
        if self.__local_history__._current_item:
            self.__local_history__._dump_current_item()
        return self

    def read_chronological_id(self) -> _AddMarksASync:
        self.chronological_id = self.__local_history__._get_id_()
        return self

    def read_order_id(self) -> _AddMarksASync:
        self.order_id = self.__local_history__._get_order_()
        return self

    def dump(self) -> None:
        self.__local_history__._dump(
            id_=self.chronological_id,
            type_=HistoryItem.TYPES.MARKS,
            typeval=self.h_comment,
            coord=self.marks,
            cursor=self.cursor,
            order_=self.order_id
        )

    def defrag_dump(self) -> None:
        self.flush()
        self.read_chronological_id()
        self.read_order_id()
        self.dump()

    def unread_order_id(self) -> _AddMarksASync:
        self.__local_history__._order_id += 1
        return self
