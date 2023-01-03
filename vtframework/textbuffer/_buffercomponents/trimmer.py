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

from ast import literal_eval
from typing import Callable, overload, Literal, Iterable, Sequence, Any

try:
    from ..buffer import TextBuffer
    from .row import _Row
    from .swap import _Swap
    __4doc1 = _Swap
    from .localhistory import _LocalHistory
    __4doc2 = _LocalHistory
    from .globcursor import _GlobCursor
    __4doc3 = _GlobCursor
    from .items import ChunkLoad
    __4doc4 = ChunkLoad
    from .marker import _Marker
    __4doc5 = _Marker
except ImportError:
    pass

from .items import DumpData, HistoryItem
from ._suit import _Suit
from ..exceptions import ConfigurationError


class _Trimmer:
    """
    Optional Buffer Component for limiting the number of :class:`_Row`'s in the :class:`TextBuffer`.

    General parameters:
        - `__buffer__`
            The ``TextBuffer`` for which the ``_Trimmer`` is created.
        - `rows_max`
            The maximum number of rows in a current buffer.

    Morphe:
        The morph of the ``_Trimmer`` and its actions can be defined analogously via the parameters during
        initialization.

        SWAP
            This morph of the ``_Trimmer`` correlates with :class:`_Swap` for data chunk management.
            When rows are cut from the buffer, they are passed as :class:`DumpData` to ``_Swap`` to be stored in a
            database. This allows the dynamic swapping of data to handle larger amounts of data.

            The side from which rows are cut from the ``TextBuffer`` is based on the current cursor position:
            If the trimming is executed, it is first queried whether the number of rows in the buffer has reached the
            upper limit, which is composed of the defined maximum value and one chunk size. Is this the case, rows of
            one chunk size are removed from the beginning of the buffer until the row of the current cursor position
            is in a range of two chunk sizes starting from the beginning of the buffer. Following this, the chunking
            of rows at the end of the buffer continues until the number of rows no longer exceeds the upper limit.

            Feeding chunks back from swap to the current buffer is done by interfaces in the ``_Trimmer`` to ``_Swap``
            methods and is done automatically by main methods in the :class:`TextBuffer`.

            Keyword parameters:
                - `swap__chunk_size`
                    The size of a chunk. The final upper limit of rows in the buffer is composed of this value and the
                    general parametrization.
                - `swap__keep_top_row_size`
                    Define the top row in the currently loaded buffer as the top row and apply the top row
                    parametrization in case of a trimming. If the parameter is ``False``, the top parametrization is
                    applied only to the real top row of the data (default).

        DROP
            A variation of the behavior of ``_Trimmer`` as if a swap were installed for chunk data management.

            As reaction to cut rows of the buffer, a function must be passed which receives the rows in a
            :class:`DumpData` item as parameter. The function is then called synchronously during trimming.

            The management of chunks to be reloaded into the buffer is realized in the ``_Trimmer`` morph SWAP by
            interfaces to :class:`_Swap` methods. For the DROP morph, these interfaces can be assigned differently,
            but they must adhere to the signature of the return values, since these are passed to the
            :class:`ChunkLoad` item.
            The `"poll"`-action is executed when the processing of the :class:`TextBuffer` data or cursor movement
            suggests that loading chunks into the buffer is necessary.
            The `"demand"`-action is the interface to the :class:`_Swap`'s ``auto_fill`` method in the SWAP morph,
            and is executed when extensive processing of the buffer data or cursor movement occurs.

            This morph of trimmer is NOT compatible with the :class:`_LocalHistory` component, but takes care of
            adjustment and removal of markings and cursor anchors (component :class:`_Marker` and
            :class:`_GlobCursor`). This morph is intended for use of the :class:`TextBuffer` as a simple
            screen-scroller and is not intended for dynamic editing of data.

            Keyword parameters:
                - `drop__chunk_size`
                    The size of a chunk. The final upper limit of rows in the buffer is composed of this value and the
                    general parametrization.
                - `drop__keep_top_row_size`
                    Define the top row in the currently loaded buffer as the top row and apply the top row
                    parametrization in case of a trimming. If the parameter is ``False``, the top parametrization is
                    applied only to the real top row of the data (default).
                - `drop__poll`
                    The `"poll"`-function.
                - `drop__demand`
                    The `"demand"`-function.

        RESTRICTIVE
            This design of the ``_Trimmer`` removes rows when the maximum value is reached from the end of the buffer
            and does not provide for any treatment of the removed data. Although the functionality of the
            :class:`_LocalHistory` component is extended:

            If the ``_LocalHistory`` component is installed, `"restrictively"` cut data is registered chronologically
            and when an action in the buffer is receded, it is appended to the buffer again. This morph also takes
            care of markings (component :class:`_Marker`), thus allowing full compatibility with :class:`_LocalHistory`.

            Keyword parameters:
                - `restrictive`
                    Must be explicitly set to ``True`` for the morph.
                - `restrictive__last_row_maxsize`
                    An optional deviation of the size of the final row in the buffer.
    """

    _trim_: Callable[[],
                     tuple[
                         list[list[_Row]],              # list of chunk rows cut from top
                         list[list[_Row]],              # list of chunk rows cut from bottom
                           ] | None
                     ]
    _sizing_: Callable[[bool], bool]
    _resize_: Callable[[int, int, bool], None]

    _dump_: Callable[[DumpData], None]
    _poll_: Callable[[],
                     tuple[
                         list[list[_Row]] | None,       # chunk rows cut from top
                         list[list[_Row]] | None,       # list of chunk rows cut from bottom
                         int | None,                    # number of loaded chunks to the top
                         int | None                     # number of loaded chunks to the bottom
                          ]
                     ]
    _demand_: Callable[[],
                       tuple[
                           list[list[_Row]] | None,       # chunk rows cut from top
                           list[list[_Row]] | None,       # list of chunk rows cut from bottom
                           int | None,                    # number of loaded chunks to the top
                           int | None                     # number of loaded chunks to the bottom
                            ]
                       ]

    _rows_max: int
    _dump_trigger: int
    _spec_size_arg: int
    _top_charge: int

    morph: Literal['swp', 'res', 'drp']

    __local_history__add_res_removemend__: Callable[
        [Sequence[Any, list[list[_Row]]] | None],
        None]
    __local_history__add_res_removemend_by_item__: Callable[
        [int, Iterable[list[str, Literal[False, "", "\n", None]]] | None], 
        None]
    __local_history__get_res_removemend_by_item__: Callable[
        [HistoryItem], 
        list[list[str, Literal[False, "", "\n", None]]]]
    __local_history__add_res_removemend_by_write__: Callable[
        [list[list[_Row]] | None],
        tuple[
            Callable[[], None],                                             # extend current item by res_removemend
            Callable[[], None],                                             # dump res_removemend direct
            Callable[[], bool],                                             # type(current_item.res_removemend) == type(res_removemend)
            list[list[str, str | None] | tuple[str, str | None]] | None     # res_removemend history item format
        ]]

    _active_suit: _Suit | None

    __slots__ = ('_trim_', '_sizing_', '_resize_', '_dump_', '_poll_', '_demand_', '_rows_max', '_spec_size_arg',
                 '_dump_trigger', '_top_charge', 'morph', '_active_suit',
                 '__local_history__add_res_removemend__', '__local_history__add_res_removemend_by_item__',
                 '__local_history__get_res_removemend_by_item__', '__local_history__add_res_removemend_by_write__')

    @overload
    def __init__(self, __buffer__: TextBuffer, rows_max: int, *,
                 drop__dump: Callable[[DumpData], None],
                 drop__chunk_size: int, drop__keep_top_row_size: bool = False,
                 drop__poll: Callable[
                     [], tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]
                 ] = lambda: (None, None, None, None),
                 drop__demand: Callable[
                     [], tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]
                 ] = lambda: (None, None, None, None)):
        ...

    @overload
    def __init__(self, __buffer__: TextBuffer, rows_max: int, *,
                 restrictive: bool,
                 restrictive__last_row_maxsize: int = None):
        ...

    @overload
    def __init__(self, __buffer__: TextBuffer, rows_max: int, *,
                 swap__chunk_size: int, swap__keep_top_row_size: bool = False):
        ...

    def __init__(self, __buffer__: TextBuffer, rows_max: int, *,
                 drop__dump: Callable[[DumpData], None] = None,
                 drop__chunk_size: int = None, drop__keep_top_row_size: bool = False,
                 drop__poll: Callable[
                     [], tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]
                 ] = lambda: (None, None, None, None),
                 drop__demand: Callable[
                     [], tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]
                 ] = lambda: (None, None, None, None),
                 restrictive: bool = None,
                 restrictive__last_row_maxsize: int = None,
                 swap__chunk_size: int = None, swap__keep_top_row_size: bool = None):

        self._active_suit = None

        if restrictive:

            self.morph = 'res'

            def _sizing(adjust=True) -> bool:
                __buffer__.rows[0]._resize_bybaserow(__buffer__._top_baserow)
                if (_l := len(__buffer__.rows)) != 1:
                    if adjust:
                        __buffer__._adjust_rows(0, 0, endings=True)
                    try:
                        finidx = self._rows_max - 1
                        __buffer__.rows[finidx]._resize_bybaserow(__buffer__._last_baserow)
                        if adjust:
                            __buffer__._adjust_rows(finidx, None)
                    except IndexError:
                        pass
                    return True

            def _resize(rows_max_: int, last_row_maxsize: int, adjust=True):
                self._rows_max = rows_max_
                self._spec_size_arg = last_row_maxsize

                __buffer__._last_baserow._resize(self._spec_size_arg)

                if self._rows_max == 1:
                    __buffer__._top_baserow._resize(self._spec_size_arg)
                    __buffer__._future_baserow._resize(self._spec_size_arg)

                _sizing(adjust)

                goto = __buffer__.current_row.cursors.data_cursor
                if __buffer__.rows[-1]._trim():
                    __buffer__._goto_data(min(goto, __buffer__.rows[-1].cursors.content_limit))

            _resize(rows_max, restrictive__last_row_maxsize or __buffer__._last_baserow.maxsize_param)

            def _trim() -> tuple[list[list[_Row]], list[list[_Row]]] | None:
                if len(__buffer__.rows) > self._rows_max:
                    goto = __buffer__.current_row.cursors.data_cursor

                    idx = self._rows_max - 1
                    __buffer__.rows[idx]._resize_bybaserow(__buffer__._last_baserow)
                    __buffer__._adjust_rows(idx, None)

                    cut = __buffer__.rows[self._rows_max:]
                    __buffer__.rows = __buffer__.rows[:self._rows_max]

                    if trim := __buffer__.rows[-1]._trim():
                        with _Row.__newrow__(__buffer__._future_baserow) as rowbuffer:
                            rowbuffer.content = trim[0]
                        cut.append(rowbuffer)

                    __buffer__._goto_data(min(goto, (lp := __buffer__.rows[-1].__next_data__ - 1)))

                    __buffer__.__marker__._adjust_markings(lp, 0, False)
                    __buffer__.__glob_cursor__._adjust_anchors(lp, 0, False)

                    return [], [cut]

            def _func(
            ) -> tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]:
                ct, cb = _trim() or (None, None)
                return ct, cb, None, None

            self._poll_ = _func
            self._demand_ = _func
            
            def __local_history__add_res_removemend_by_write__(resrem: list[list[_Row]] | None):
                if resrem:
                    restrict_removed: list[list[str, str | None] | tuple[str, str | None]] = [
                        row.read_row_content(0, None) for row in resrem[0]]

                    def resremexp():
                        nonlocal restrict_removed
                        restrict_removed += __buffer__.__local_history__._current_item.restrict_removed
                        __buffer__.__local_history__._current_item.restrict_removed.clear()
                        __buffer__.__local_history__._current_item.restrict_removed.extend(restrict_removed)

                    def dumpresrem():
                        __buffer__.__local_history__._dump(id_=__buffer__.__local_history__._get_id_(),
                                                           type_=HistoryItem.TYPES.RESTRICT_REMOVEMENT,
                                                           restrict_removed=restrict_removed,
                                                           order_=__buffer__.__local_history__._get_order_())
                else:
                    restrict_removed: None = None
                    
                    def resremexp():
                        pass
                    
                    def dumpresrem():
                        pass
                
                def curitemresremandresrem():
                    return type(__buffer__.__local_history__._current_item.restrict_removed) == type(resrem)
                
                return resremexp, dumpresrem, curitemresremandresrem, restrict_removed

            def __local_history__add_res_removemend__(resrem__i1: Sequence[Any, list[list[_Row]] | None] | None):
                if resrem__i1 and (resrem := resrem__i1[1]):
                    __buffer__.__local_history__.flush_redo()
                    if __buffer__.__local_history__._current_item:
                        __buffer__.__local_history__._dump_current_item()
                    if not (order := __buffer__.__local_history__._get_order_()):
                        order = -1
                        id_ = __buffer__.__local_history__._chronicle_progress_id
                    else:
                        id_ = __buffer__.__local_history__._get_id_()
                    if not id_:
                        return
                    __buffer__.__local_history__.sql_cursor.execute(
                        "INSERT INTO local_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (id_, HistoryItem.TYPES.RESTRICT_REMOVEMENT,
                         None, None, None, None,
                         repr([row.read_row_content(0, None) for row in resrem[0]]),
                         None,
                         order))
                    __buffer__.__local_history__.auto_commit()
            
            def __local_history__add_res_removemend_by_item__(
                    cron_id: int, resrem: list[list[str, Literal[False, "", "\n", None]]] | None):
                if resrem:
                    __buffer__.__local_history__.sql_cursor.execute(
                        "INSERT INTO local_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (cron_id, HistoryItem.TYPES.RESTRICT_REMOVEMENT,
                         None, None, None, None,
                         repr(resrem),
                         None,
                         __buffer__.__local_history__._get_order_() or -1))
            
            def __local_history__get_res_removemend_by_item__(item: HistoryItem):
                if item.restrict_removed:
                    return literal_eval(item.restrict_removed)
                elif item.id_ < 0:
                    if query := __buffer__.__local_history__.sql_cursor.execute(
                            "SELECT (restrict_removemend) FROM local_history "
                            "WHERE id_ = ? AND order_ = ?", (abs(item.id_), item.cursor)).fetchone():
                        return literal_eval(query[0])
                else:
                    return ()
            
        else:
            def __local_history__add_res_removemend_by_write__(resrem: list[list[_Row]] | None):
                return (lambda: None), (lambda: None), (lambda: True), (lambda: None)

            def __local_history__add_res_removemend__(
                    resrem__i1: Sequence[Any, list[list[_Row]]] | None):
                pass

            def __local_history__add_res_removemend_by_item__(
                    cron_id: int, resrem: list[list[str, Literal[False, "", "\n", None]]] | None):
                pass

            def __local_history__get_res_removemend_by_item__(item: HistoryItem):
                raise ConfigurationError(
                    "HistoryItem of type `RESTRICT_REMOVEMENT' occurred: "
                    "should not and must not be created with current morph of Trimmer.")

            if drop__dump:

                self.morph = 'drp'

                def _dump(dd: DumpData):
                    if dd.side:
                        __buffer__.__marker__._adjust_markings(__buffer__.__eof_data__ - 1, 0, False)
                        __buffer__.__glob_cursor__._adjust_anchors(__buffer__.__eof_data__ - 1, 0, False)
                    else:
                        __buffer__.__marker__._adjust_markings(0, -dd.start_point_data, dd.start_point_data)
                        __buffer__.__glob_cursor__._adjust_anchors(0, -dd.start_point_data, dd.start_point_data)

                    drop__dump(dd)

                self._dump_ = _dump
                self._poll_ = drop__poll
                self._demand_ = drop__demand

                keep_top_row_size = drop__keep_top_row_size
                chunk_size = drop__chunk_size

            elif swap__chunk_size:

                self.morph = 'swp'

                if not __buffer__.__swap__:
                    raise ConfigurationError('__swap__ not initialled')

                self._dump_ = lambda c: __buffer__.__swap__._dump_chunk(c)
                self._poll_ = lambda: __buffer__.__swap__.__call__()
                self._demand_ = lambda: __buffer__.__swap__.auto_fill()

                keep_top_row_size = swap__keep_top_row_size
                chunk_size = swap__chunk_size

            else:
                raise AttributeError('A morph must be specified using the keyword arguments.')

            if not keep_top_row_size:
                def _sizing(adjust=True) -> bool:
                    if __buffer__.rows[0].__row_num__ == 0:
                        __buffer__.rows[0]._resize_bybaserow(__buffer__._top_baserow)
                        if adjust:
                            __buffer__._adjust_rows(0, 0, endings=True)
                        return True
            else:
                def _sizing(adjust=True) -> bool:
                    __buffer__.rows[0]._resize_bybaserow(__buffer__._top_baserow)
                    if adjust:
                        __buffer__._adjust_rows(0, 0, endings=True)
                    return True

            def _resize(rows_max_: int, chunk_size: int, adjust=True):
                self._rows_max = rows_max_
                self._spec_size_arg = chunk_size
                self._top_charge = chunk_size * 2
                self._dump_trigger = self._rows_max + self._spec_size_arg
                _sizing(adjust)

            _resize(rows_max, chunk_size)

            def _trim() -> tuple[list[list[_Row]], list[list[_Row]], list[_Row] | None] | None:
                if len(__buffer__.rows) > self._dump_trigger:
                    __buffer__.indexing()
                    goto = __buffer__.current_row.cursors.data_cursor
                    cuttop = list()
                    while __buffer__.current_row_idx > self._top_charge:
                        __buffer__.current_row_idx -= self._spec_size_arg
                        chunk_rows, __buffer__.rows = (__buffer__.rows[:self._spec_size_arg],
                                                       __buffer__.rows[self._spec_size_arg:])
                        __buffer__.__start_point_data__ = __buffer__.rows[0].__data_start__
                        __buffer__.__start_point_content__ = __buffer__.rows[0].__content_start__
                        __buffer__.__start_point_row_num__ = __buffer__.rows[0].__row_num__
                        __buffer__.__start_point_line_num__ = __buffer__.rows[0].__line_num__
                        self._dump_(DumpData(
                            0,
                            chunk_rows[0].__data_start__,
                            chunk_rows[0].__content_start__,
                            chunk_rows[0].__row_num__,
                            chunk_rows[0].__line_num__,
                            chunk_rows
                        ))
                        cuttop.append(chunk_rows)
                    cutbottom = list()
                    while len(__buffer__.rows) > self._dump_trigger:
                        chunk_rows, __buffer__.rows = (__buffer__.rows[-self._spec_size_arg:],
                                                       __buffer__.rows[:-self._spec_size_arg])
                        self._dump_(DumpData(
                            1,
                            chunk_rows[0].__data_start__,
                            chunk_rows[0].__content_start__,
                            chunk_rows[0].__row_num__,
                            chunk_rows[0].__line_num__,
                            chunk_rows
                        ))
                        cutbottom.insert(0, chunk_rows)

                    if not _sizing():
                        __buffer__.indexing()

                    __buffer__._goto_data(goto)
                    return cuttop, cutbottom, None

        self._trim_ = _trim
        self._sizing_ = _sizing
        self._resize_ = _resize

        self.__local_history__add_res_removemend_by_write__ = __local_history__add_res_removemend_by_write__
        self.__local_history__add_res_removemend__ = __local_history__add_res_removemend__
        self.__local_history__add_res_removemend_by_item__ = __local_history__add_res_removemend_by_item__
        self.__local_history__get_res_removemend_by_item__ = __local_history__get_res_removemend_by_item__

    def __call__(self) -> tuple[list[list[_Row]], list[list[_Row]]] | None:
        """
        Automation. Execute the trim.

        Returns: ( 
            - `<`:class:`_Row`\\ `chunk's cut from top>` | ``None``, 
            - `<`:class:`_Row`\\ `chunk's cut from bottom>` | ``None``
        )  | ``None``
        """
        return self._trim_()

    def action__poll__(self) -> tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]:
        """
        Should return: (
            - `<`:class:`_Row`\\ `chunk's cut from top>` | ``None``,
            - `<`:class:`_Row`\\ `chunk's cut from bottom>` | ``None``,
            - `<n loaded chunks from top>` | ``None``,
            - `<n loaded chunks from bottom>` | ``None``
        )
        """
        return self._poll_()

    def action__demand__(self) -> tuple[list[list[_Row]] | None, list[list[_Row]] | None, int | None, int | None]:
        """
        Should return: (
            - `<`:class:`_Row`\\ `chunk's cut from top>` | ``None``,
            - `<`:class:`_Row`\\ `chunk's cut from bottom>` | ``None``,
            - `<n loaded chunks from top>` | ``None``,
            - `<n loaded chunks from bottom>` | ``None``
        )
        """
        return self._demand_()

    def sizing(self, *, adjust_buffer: bool = True) -> bool:
        """
        Perform the sizing for the special rows in the current buffer according to the parametrization.

        [+] __marker__.adjust [+] __glob_cursor__.adjust

        :return: True if the sizing is executed.
        """
        return self._sizing_(adjust_buffer)

    def _resize(self, rows_max: int = None, _spec_arg: int = None, adjust_buffer: bool = True) -> None:
        """
        Changes the size parameterization of the trimmer depending on parameterization.
        Will be applied immediately.
        """

        rows_max = rows_max or self._rows_max
        _spec_arg = _spec_arg or self._spec_size_arg
        self._resize_(rows_max, _spec_arg, adjust_buffer)

    def suit(self,
             all_: bool = True,
             *,
             _trim: bool = True,
             _poll: bool = True,
             _dmnd: bool = True,
             leave_active: bool = False) -> _Suit[_Trimmer]:
        """
        Create a context manager to disable trimmer interfaces within the suit.

        If a suit is active and `leave_active` is ``True``,
        ``__exit__`` of the active suit is executed and a new one is created, otherwise a dummy is returned.
        """

        if self._active_suit:
            if leave_active:
                self._active_suit.__exit__(None, None, None)
            else:
                return _Suit(lambda *_: self, lambda *_: None)

        if not all_:
            _trim = _poll = _dmnd = False
        elif all((_trim, _poll, _dmnd)):
            return _Suit(lambda *_: self, lambda *_: None)

        o_trim = self._trim_
        o_call = self._poll_
        o_fill = self._demand_

        def enter(suit):
            self._active_suit = suit
            self._trim_ = ((lambda *_: None) if not _trim else o_trim)
            self._poll_ = ((lambda *_: (None, None)) if not _poll else o_call)
            self._demand_ = ((lambda *_: (None, None)) if not _dmnd else o_fill)
            return self

        def exit_(*_):
            self._trim_ = o_trim
            self._poll_ = o_call
            self._demand_ = o_fill
            self._active_suit = None

        return _Suit(enter, exit_)
