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

from types import TracebackType
from typing import Iterable, Any, ContextManager, Type, Callable
from sqlite3 import Cursor
from threading import RLock
from re import search
from urllib.parse import unquote

try:
    from sqlite3 import Connection
    __4doc1 = Connection
    from .swap import _Swap
    __4doc2 = _Swap
    from .localhistory import _LocalHistory
    __4doc3 = _LocalHistory
except ImportError:
    pass


class SQLTSCursor(Cursor):
    """
    A thread-safe SQLite :class:`Cursor` object.

    Used inside the buffer components :class:`_LocalHistory` and :class:`_Swap` as the database cursor,
    since the property `check_same_thread` is disabled in the :class:`Connection`\\ s.

    Contains a :class:`RLock` which is used inside the ``execute*`` methods.
    """

    __lock__: RLock

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.__lock__ = RLock()
        super().__init__(*args, **kwargs)

    def execute(self, __sql: str, __parameters: Iterable[Any] = None) -> Cursor:
        try:
            self.__lock__.acquire()
            if __parameters:
                return super().execute(__sql, __parameters)
            else:
                return super().execute(__sql)
        finally:
            self.__lock__.release()

    def executemany(self, __sql: str, __seq_of_parameters: Iterable[Iterable[Any]]) -> Cursor:
        try:
            self.__lock__.acquire()
            return super().executemany(__sql, __seq_of_parameters)
        finally:
            self.__lock__.release()

    def executescript(self, __sql_script: bytes | str) -> Cursor:
        try:
            self.__lock__.acquire()
            return super().executescript(__sql_script)
        finally:
            self.__lock__.release()


def path_from_uri(uri: str) -> tuple[str, bool] | None:
    """
    Parse the file path from a `URI`, return ``None`` if the input is not a `URI`.

    Return a positive value as a tuple:
        ``(`` `<the file path | memory database name>`, `<whether memory mode is used>` ``)``
    """
    if m := search("(?<=^file:)[^?]+(?=#|\\?|$)", uri):
        return unquote(m.group()), bool(search("[?&]mode=memory", uri))


class _DBInitSuit(ContextManager):
    """
    A contextmanager/suit that is applied when a database is created.

    Allows to handle or ignore database errors during creation.

    For example, if a database is passed during parameterization whose files and tables already exist,
    this will normally cause an error. If these errors are to be avoided and the database is to be accepted 
    nevertheless, the method ``do_ignore`` can be executed over the global constants ``DATABASE_FILES_ERROR_SUIT`` 
    and ``DATABASE_TABLE_ERROR_SUIT`` of the module beforehand.
    """

    _handler: Callable[[Type[BaseException] | None, BaseException | None, TracebackType | None], bool | None]

    def __init__(self):
        self._handler = lambda *_: False

    def do_ignore(self) -> None:
        """Enable ignoring of all errors."""
        self._handler = lambda *_: True

    def do_raise(self) -> None:
        """Enable the raising of errors."""
        self._handler = lambda *_: False

    def set_handler(
            self,
            handler: Callable[[Type[BaseException] | None, BaseException | None, TracebackType | None], bool | None]
    ) -> None:
        """Set a custom handler for exiting."""
        self._handler = handler

    def __enter__(self) -> None:
        pass

    def __exit__(self, __exc_type: Type[BaseException] | None, __exc_value: BaseException | None,
                 __traceback: TracebackType | None) -> bool | None:
        return self._handler(__exc_type, __exc_value, __traceback)


DATABASE_FILES_ERROR_SUIT: _DBInitSuit = _DBInitSuit()
"""This context manager is used when checking whether the database file already exists."""

DATABASE_TABLE_ERROR_SUIT: _DBInitSuit = _DBInitSuit()
"""This context manager is used when creating the database tables."""

