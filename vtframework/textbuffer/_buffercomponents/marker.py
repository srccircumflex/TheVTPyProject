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

from typing import Callable, Literal, Sequence, Generator, Iterable, Union

try:
    from ..buffer import TextBuffer
    from .items import ChunkLoad, WriteItem
except ImportError:
    pass

from ..bufferreader import Reader
from .items import HistoryItem


class _Marking(list):
    """
    The marking object implemented as a subclass of list: ``[`` `<start position>, <stop position>` ``]``
    """

    anchor: int
    trend: None | int

    __slots__ = ('anchor', 'trend')

    def __init__(self, anchor: int):
        self.anchor = anchor
        self.trend = None
        list.__init__(self, (self.anchor, self.anchor))

    def set(self, pos: int) -> None:
        """Set the second anchor."""
        if pos < self.anchor:
            if self.trend != 0:
                self.trend = 0
                self[0], self[1] = self.anchor, self.anchor
        elif pos > self.anchor:
            if self.trend != 1:
                self.trend = 1
                self[0], self[1] = self.anchor, self.anchor
        else:
            self[0], self[1] = self.anchor, self.anchor
            return

        self[self.trend] = pos

    def lapps(self, item: _Marking) -> bool:
        """Whether the markings overlap."""
        if not self:
            return item[0] < self[0] < item[1]
        else:
            return (item[0] < self[1] <= item[1] or
                    item[0] <= self[0] < item[1] or
                    self[0] < item[1] <= self[1] or
                    self[0] <= item[0] < self[1])

    @classmethod
    def make(cls, range_: Sequence[int, int]) -> _Marking:
        """Create a new marker from the sequence `range_`."""
        _cls = cls(range_[0])
        _cls.set(range_[1])
        return _cls

    def snap(self) -> list[int, int]:
        """Creates a new list from the current coordinates."""
        return list(self)

    def __bool__(self) -> bool:
        """Whether the anchors are unequal."""
        return self[0] != self[1]


class _Marker(Iterable[Union[_Marking, list[int, int]]]):
    """
    Optional Buffer Component for creating, editing and processing data markings in the buffer.
    This also extends the functionality of ``cursor_move`` in :class:`TextBuffer`.

    Markings are stored in the ``_Marker`` in a list of :class:`_Marking` objects (``markings``), in runtime they can 
    also change to ordinary lists: ``[`` `<start position>, <stop position>` ``]``

    When a new :class:`_Marking` is created by ``cursor_move`` or a method in ``_Marker``, it is attached to the list 
    ``markings`` and can be edited on index ``-1`` via ``cursor_move`` or methods in ``_Marker`` until ``_Marker`` is 
    notified that a marker is finished.
    Depending on the parametrization of ``multy_mode``, the marker is then sorted into the list or removed.
    If the marking is terminated by ``cursor_move``, the ``backjump_mode`` can be used to trigger the movement of the
    cursor to the relative beginning of the marking.
    If the ``multy_mode`` is set to ``True``, all markings are kept even after they have been ended and are adjusted
    to inputs in the buffer and handled (`sticky mode`).

    Currently implemented functions with markings:
        - Remove all or targeted marked data areas.
        - Remove or replace tab ranges in all or targeted marked ranges.
        - Shift or backshift all or targeted marked rows.
        - Read all or targeted marked data.
        - Cursor navigation to marked areas.
    """
    markings: list[_Marking | list[int, int]]
    _do_mark: bool
    _multy_mode: bool
    _backjump_mode: bool

    _current_pos_: Callable[[], int]
    _stop_: Callable[[], None]
    _get_backjump_val_: Callable[[int], int | None]

    __buffer__: TextBuffer

    __slots__ = ('markings', '_current_pos_', '_do_mark', '_multy_mode', '_backjump_mode',
                 '_get_backjump_val_', '_stop_', '__buffer__')

    @property
    def multy_mode(self) -> bool:
        return self._multy_mode
    
    @multy_mode.setter
    def multy_mode(self, __set: bool) -> None:
        self._multy_mode = __set
        if __set:
            def stop():
                if self.markings and self._do_mark:
                    if not self.markings[-1]:
                        self.markings.pop(-1)
                    else:
                        self._lisort(self.markings)
                self._do_mark = False
        else:
            def stop():
                if self.markings:
                    if not self.markings[-1]:
                        self.markings.pop(-1)  # avoidance of inclusion in __local_history__
                    else:
                        self.purge()
                self._do_mark = False
        self._stop_ = stop

    @property
    def backjump_mode(self) -> bool:
        return self._backjump_mode

    @backjump_mode.setter
    def backjump_mode(self, __set: bool) -> None:
        self._backjump_mode = __set
        if __set:
            def get_backjump_val(_stop_jump_trend):
                if _stop_jump_trend is not None:
                    if _stop_jump_trend > 0:
                        if self.markings[-1].trend == 0:
                            return self.markings[-1][1]
                    elif _stop_jump_trend < 0:
                        if self.markings[-1].trend == 1:
                            return self.markings[-1][0]

            self._get_backjump_val_ = get_backjump_val
        else:
            self._get_backjump_val_ = lambda _stop_jump_trend: None
        
    def __init__(self, __buffer__: TextBuffer, multy_mode: bool, backjump_mode: bool):
        """
        :param __buffer__:
        :param multy_mode: Allow multiple sticky marks.
        :param backjump_mode: Return the outermost position when the marker is stopped and the movement is opposite.
        """
        self.markings = list()
        self._do_mark = False
        self.multy_mode = multy_mode
        self.backjump_mode = backjump_mode
        self.__buffer__ = __buffer__
        self._current_pos_ = lambda: self.__buffer__.current_row.cursors.data_cursor

    def purge(self) -> list[list[int, int]]:
        """
        Delete all markings.

        [+] __local_history__ [+] __local_history__.lock

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__buffer__.__local_history__._lock_assert_()
        marks_p = self.markings.copy()
        self.__buffer__.__local_history__._add_marks(HistoryItem.TYPEVALS.MARKERCOMMENTS.PURGED, lambda: self._lisort(marks_p))
        self._do_mark = False
        self.markings.clear()
        return marks_p

    def add_new(self, anchor: int = None) -> bool:
        """
        Add a new marking if the current one is not stopped.
        `anchor` is a data position can be specified optionally, by default the current cursor position is used.

        [+] __local_history__ [+] __local_history__.lock

        :return: Whether a new mark has been added.
        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__buffer__.__local_history__._lock_assert_()
        if not self._do_mark:
            if anchor is None:
                anchor = self._current_pos_()
            self.__buffer__.__local_history__._add_marks(HistoryItem.TYPEVALS.MARKERCOMMENTS.NEW_MARKING, self.sorted_copy, anchor)
            self.markings.append(_Marking(anchor))
            self._do_mark = True
            return True
        else:
            return False

    def add_marks(self, *ranges: Sequence[int, int]) -> None:
        """
        Add complete markings. Remove overlapping markings with prioritization of the new ones to be added and
        sort the markings.

        [+] __local_history__ [+] __local_history__.lock

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.stop()
        self.__buffer__.__local_history__._add_marks(HistoryItem.TYPEVALS.MARKERCOMMENTS.EXTERNAL_ADDING, self.sorted_copy)
        for ran in ranges:
            self.markings.append(_Marking.make(ran))
            self._rm_lapp()
            self._lisort(self.markings)

    def ready(self, _do_mark: bool, _stop_jump_trend: int = None) -> int | None:
        """
        Automation for the cursor movement.

        Add a new or stop the current marking depending on `_do_mark`. Return the outermost position at stop if
        configured and the movement (`_stop_jump_trend`) is opposite.

        [+] __local_history__ [+] __local_history__.lock

        :raises AssertionError: __local_history__ lock is engaged.
        """
        if _do_mark:
            self.add_new()
        elif self._do_mark:
            try:
                return self._get_backjump_val_(_stop_jump_trend)
            finally:
                self.stop()

    def set(self, n: int) -> None:
        """
        Set the second anchor of the current active marking and remove overlapping markings.

        [+] __local_history__ [+] __local_history__.lock

        :raises AssertionError: __local_history__ lock is engaged.
        """
        if self._do_mark:
            self.__buffer__.__local_history__._lock_assert_()
            lh_async_marks_add = self.__buffer__.__local_history__._add_marks_async(HistoryItem.TYPEVALS.MARKERCOMMENTS.LAPPING, self.coord_snap).read_marks()
            pos_h = (mark[mark.trend] if (mark := self.markings[-1]).trend is not None else None)
            self.markings[-1].set(n)
            if self._rm_lapp():
                lh_async_marks_add.add_cursor(pos_h)

    def set_current(self, __do_mark: bool = True) -> None:
        """
        Set the second anchor of the current active marking to the current cursor position if `__do_mark` is ``True``.

        [+] __local_history__ [+] __local_history__.lock

        :raises AssertionError: __local_history__ lock is engaged.
        """
        if __do_mark:
            return self.set(self._current_pos_())

    @staticmethod
    def _lisort(markings: list[list[int, int]]) -> list[list[int, int]]:
        """Sort the last entry in the marking list (inplace)."""
        for i in range(len(markings) - 1):
            if markings[-1] < markings[i]:
                markings.insert(i, markings.pop(-1))
                break
        return markings

    def stop(self) -> None:
        """
        Stop the current active marking; clean or sort the marker (depending on `multy_marks`).

        [+] __local_history__ [+] __local_history__.lock

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__buffer__.__local_history__._lock_assert_()
        self._stop_()

    def _in_conflict(self, *, pos: int = None, rm__beside: int = 0, rm__eq_start: bool = False) -> bool:
        """
        Remove a marking if the following edit is in its range.

        The machining position is by default the current cursor position or can be specified explicitly via `pos`.
        For operations which affect the current position indirectly (like backspace) a deviation can be specified via
        `rm__beside`. If the position is exactly at the beginning of a marking, it will be removed if
        `rm__eq_start` is set to ``True``.

        [+] __local_history__ [+] __local_history__.lock

        :return: Whether something was removed.
        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.stop()
        lh_async_marks_add = self.__buffer__.__local_history__._add_marks_async(HistoryItem.TYPEVALS.MARKERCOMMENTS.INPUT_CONFLICT, self.markings.copy).read_marks()
        if m := self._rm_marking(_pos=(self._current_pos_() if pos is None else pos) + rm__beside,
                                 _eq_start=rm__eq_start):
            lh_async_marks_add.add_cursor(m[1]).defrag_dump()
            return True
        return False

    def _rm_lapp(self) -> bool:
        """
        Compare the last entry in the list of markings with the rest of the list and remove overlapping markers by
        prioritizing the last entry.

        :return: Whether an entry has been removed.
        """
        i = len(self.markings) - 1
        _index = 0
        match = False
        while i > 0:
            if self.markings[-1].lapps(self.markings[_index]):
                match = True
                self.markings.pop(_index)
            else:
                _index += 1
            i -= 1
        return match

    def get_aimed_mark(self, *, _pos: int = None, _get_index: bool = False,
                       _eq_start: bool = True, _eq_end: bool = False
                       ) -> _Marking | int | None:
        """
        Return the :class:`_Marking` if the position is in its range.

        By default, the current cursor position is used if `_pos` is not defined, then the currently active marking
        is also returned, even if it would normally not match; returns ``-1`` in that case if `_get_index` is ``True``.

        The rules `_eq_start` and `_eq_end` indicate whether the position also applies to a marking if the position
        is at the edge of the marking.

        If `_get_index` is ``True``, the index number of the marker object in the list of markings is returned
        instead of the marker object.

        :return: Marking or its index if the conditions are matched, otherwise None
        """
        if self._do_mark and _pos is None:
            return -1 if _get_index else self.markings[-1]
        _pos = (self._current_pos_() if _pos is None else _pos)
        comp_i0 = getattr(_pos, '__ge__' if _eq_start else '__gt__')
        comp_iN1 = getattr(_pos, '__le__' if _eq_end else '__lt__')
        for i, mark in enumerate(self.markings):
            if comp_i0(mark[0]) and comp_iN1(mark[1]):
                return i if _get_index else mark

    def pop_aimed_mark(self, *, _pos: int = None, _eq_start: bool = True, _eq_end: bool = False) -> _Marking | None:
        """
        Remove and return the :class:`_Marking` if the position is in its range.

        [+] __local_history__ [+] __local_history__.lock

        By default, the current cursor position is used if `_pos` is not defined, then the currently active marking
        is also returned, even if it would normally not match.

        The rules `_eq_start` and `_eq_end` indicate whether the position also applies to a marking if the position
        is at the edge of the marking.

        :return: Marking if the conditions are matched, otherwise None
        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__buffer__.__local_history__._lock_assert_()
        lh_async_marks_add = self.__buffer__.__local_history__._add_marks_async(HistoryItem.TYPEVALS.MARKERCOMMENTS.POP, self.markings.copy).read_marks()
        if (i := self.get_aimed_mark(_pos=_pos, _get_index=True, _eq_start=_eq_start, _eq_end=_eq_end)) is not None:
            m = self.markings.pop(i)
            self._do_mark = False
            lh_async_marks_add.add_cursor(m[1]).defrag_dump()
            return m

    def mark_jump_point(self, trend: int) -> int | None:
        """
        Returns the nearest boundary position of a marker, based on the current cursor position in the direction
        of the `trend` (positive = forward, negative = backward).

        :return: Position or None
        """
        if not self.markings:
            return None
        pos = self._current_pos_()
        markings = self.markings.copy()
        if self._do_mark:
            self._lisort(markings)
        if trend < 1:
            markings.reverse()
        if trend > 0:
            for mark in markings:
                if (begin := mark[0]) > pos:
                    return begin
                elif (end := mark[1]) > pos:
                    return end
        else:
            for mark in markings:
                if (end := mark[1]) < pos:
                    return end
                elif (begin := mark[0]) < pos:
                    return begin
        return None

    def _rm_marking(self, _pos: int = None, _eq_start: bool = True, _eq_end: bool = False) -> _Marking | None:
        """
        Remove and return the :class:`_Marking` if the position is in its range.

        By default, the current cursor position is used if `_pos` is not defined, then the currently active marking
        is also returned, even if it would normally not match.

        The rules `_eq_start` and `_eq_end` indicate whether the position also applies to a marking if the position
        is at the edge of the marking.

        :return: Marking if the conditions are matched, otherwise None
        """
        if (i := self.get_aimed_mark(_pos=_pos, _get_index=True, _eq_start=_eq_start, _eq_end=_eq_end)) is not None:
            m = self.markings.pop(i)
            self._do_mark = False
            return m

    def _adjust_markings(self, start: int, diff: int, _rm_area_end: int | Literal[False] = None) -> None:
        """
        Adjust the markings by `diff` starting from data `start` point.
        Remove applicable markers from `start` to `_rm_area_end`; if `_rm_area_end` is ``False`` remove all markings
        starting from `start`.

        [+] __local_history__ [+] __local_history__.lock

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.stop()
        lh_async_marks_add = self.__buffer__.__local_history__._add_marks_async(HistoryItem.TYPEVALS.MARKERCOMMENTS.REMOVED_BY_ADJUST, self.coord_snap).read_marks()
        i = 0
        rm = False
        try:
            try:
                while True:
                    if self.markings[i][0] >= start:
                        break
                    i += 1
            except IndexError:
                if _rm_area_end is not None:
                    i -= 1
                    if self.markings[i][1] > start:
                        pass
                    else:
                        raise
                else:
                    raise
            if _rm_area_end is not None:
                if _rm_area_end is False:
                    rm = self.markings[i:]
                    self.markings = self.markings[:i]
                else:
                    while self.markings[i][0] < _rm_area_end:
                        rm = [self.markings.pop(i)]
                    for mark in self.markings[i:]:
                        mark[0] += diff
                        mark[1] += diff
            else:
                for mark in self.markings[i:]:
                    mark[0] += diff
                    mark[1] += diff
        except IndexError:
            pass
        finally:
            if rm:
                lh_async_marks_add.add_cursor(rm[-1][1]).defrag_dump()

    def marked_remove(self, *,
                      aimed: bool | Literal['<', '>', '<>'] = False,
                      rows: bool = False
                      ) -> tuple[
                               list[tuple[int, list[tuple[list[str], str | Literal[False] | None]]]],
                               ChunkLoad
                           ] | None:
        r"""
        Remove and return marked data (records the markings in __local_history__ beforehand).

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust [+] __highlighter__.prep_by_chunkload

        Remove only the marked data of the current position instead of all when `aimed` is set.
        The parameterization via angle brackets defines the evaluation of the position of the cursor at the marking;
        if only the left angle bracket ``"<"`` is selected (default if ``True`` is set), the cursor hits the marking
        even if it is located at the beginning; if only the right angle bracket ``">"`` is passed, the cursor hits the
        marking even if it is located adjacent to the end, at the beginning of the marking the cursor must be clearly
        inside; the rules can be combined via ``"<>"``.

        Understand the marker coordinates as pointers to rows and remove entire rows if `rows` is ``True``.

        The return value is composed as follows:
            - At index 1 of the tuple is the :class:`ChunkLoad`.
            - At index 0 of the tuple there is a list of items of the removed data:
                - An item is composed of the starting point of the coordinate at index 0 and a list of row data at index 1:
                    Row data is a tuple of the remoted content data (tab-separated string of printable characters) at
                    index 0 and the remoted row end (can be ``"\n"`` for a line break, ``""`` for a non-breaking line
                    break, ``None`` if the row has no line break, or ``False`` as a non-removed end) at index 1.
        The total return value can be ``None`` if nothing was removed.

        Relevant :class:`ChunkLoad` Fields:
            - `edited_ran`
            - `spec_position`
            - `top_nload`
            - `btm_nload`
            - `top_cut`
            - `btm_cut`

        :return: ( [ ( coord start: int, removed rows: [ ( row raster: [str], row end: "" | "\n" | None | False ), ... ] ), ... ], final chunk load item)

        :raises AssertionError: __local_history__ lock is engaged.
        """
        self.__buffer__.__local_history__._lock_assert_()
        removed = None
        if aimed:
            if isinstance(aimed, str):
                _eq_start = aimed[0] == '<'
                _eq_end = aimed[-1] == '>'
            else:
                _eq_start = True
                _eq_end = False
            with self.__buffer__.__local_history__.suit():
                if mark := self.pop_aimed_mark(_eq_start=_eq_start, _eq_end=_eq_end):
                    if rows:
                        removed = self.__buffer__.remove([mark], 'p')
                    else:
                        removed = self.__buffer__.remove([mark], 'd')
        elif self.markings:
            if self._do_mark:
                self._lisort(self.markings)
                self._do_mark = False
            markings = self.markings.copy()
            with self.__buffer__.__local_history__.suit():
                self.purge()
                if rows:
                    removed = self.__buffer__.remove(markings, 'p')
                else:
                    removed = self.__buffer__.remove(markings, 'd')
        return removed

    def marked_shift(self, *,
                     aimed: bool | Literal['<', '>', '<>'] = False,
                     backshift: bool = False,
                     unique_rows: bool = True
                     ) -> tuple[
                              list[tuple[int, list[tuple[list[str], str | Literal[False] | None]]]],
                              ChunkLoad
                          ] | None:
        """
        Shift marked rows.

        >>> \\t foo bar
        >>>     foo bar
        origin
        >>> \\t\\t foo bar
        >>> \\t    foo bar
        shifted origin (`tab-to-blanks-mode` not configured)
        >>>  foo bar
        >>> foo bar
        backshifted origin

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust [+] __highlighter__.prep_by_chunkload

        Shift only the marked rows of the current position instead of all when `aimed` is set.
        The parameterization via angle brackets defines the evaluation of the position of the cursor at the marking;
        if only the left angle bracket ``"<"`` is selected (default if ``True`` is set), the cursor hits the marking
        even if it is located at the beginning; if only the right angle bracket ``">"`` is passed, the cursor hits the
        marking even if it is located adjacent to the end, at the beginning of the marking the cursor must be clearly
        inside; the rules can be combined via ``"<>"``.

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
        self.__buffer__.__local_history__._lock_assert_()
        _worked = None
        if aimed:
            if isinstance(aimed, str):
                _eq_start = aimed[0] == '<'
                _eq_end = aimed[-1] == '>'
            else:
                _eq_start = True
                _eq_end = False
            if (i := self.get_aimed_mark(_get_index=True, _eq_start=_eq_start, _eq_end=_eq_end)) is not None:
                _markings = self.markings.copy()
                with self.__buffer__.__local_history__.suit():
                    post_un = self.__buffer__.__local_history__._add_marks_async(HistoryItem.TYPEVALS.MARKERCOMMENTS.POP, self.coord_snap).read_marks()
                    post_un.add_cursor((mark := self.markings.pop(i).copy())[1])
                    post_un.read_order_id()
                    with self.__buffer__.__trimmer__.suit(all_=False):
                        if _worked := self.__buffer__.shift_rows([mark], 'p', backshift=backshift, unique_rows=unique_rows):
                            worked = _worked[0]
                            post_un.flush().read_chronological_id().dump()
                            for i in range(_l := len(worked[0][1])):
                                if wi := worked[0][1][i]:
                                    mark[0] = min(mark[0], wi.begin)
                                    mark[1] += sum(wi.diff for _i in range(i, _l) if (wi := worked[0][1][_i]))
                                    break
                            if mark[0] != mark[1]:
                                self.markings.append(_Marking.make(mark))
                                self._rm_lapp()
                                self._lisort(self.markings)
                            self._do_mark = False
                        else:
                            self.markings = _markings
                            post_un.unread_order_id()
                    cut = self.__buffer__.__trimmer__.__call__()
                    if _worked:
                        self.__buffer__.__local_history__._add_resremove(cut)
        elif self.markings:
            _markings = self.markings.copy()
            markings = self.coord_snap()
            self.markings.clear()
            with self.__buffer__.__local_history__.suit():
                post_un = self.__buffer__.__local_history__._add_marks_async(
                    HistoryItem.TYPEVALS.MARKERCOMMENTS.PURGED, lambda: (self._lisort(_markings) if self._do_mark else _markings)).read_marks()
                post_un.read_order_id()
                with self.__buffer__.__trimmer__.suit(all_=False):
                    if _worked := self.__buffer__.shift_rows(markings, 'p', backshift=backshift, unique_rows=unique_rows):
                        worked = _worked[0]
                        post_un.flush().read_chronological_id().dump()
                        diff = 0
                        markings = []
                        for mark, items in reversed(worked):
                            mark = mark.copy()
                            for i in range(_l := len(items)):
                                if wi := items[i]:
                                    mark[0] = min(mark[0], wi.begin) + diff
                                    diff += sum(wi.diff for _i in range(i, _l) if (wi := items[_i]))
                                    mark[1] += diff
                                    break
                            else:
                                mark[0] += diff
                                mark[1] += diff
                            if mark[0] != mark[1]:
                                markings.append(mark)
                        i = len(markings) - 1
                        try:
                            while i > 0:
                                while markings[i][0] <= markings[i - 1][0]:
                                    markings.pop(i - 1)
                                    if not (i := i - 1):
                                        break
                                i -= 1
                        except IndexError:
                            pass
                        finally:
                            for i in range(len(markings) - 1):
                                markings[i][1] = min(markings[i][1], markings[i + 1][0])
                            self.markings = markings
                        self._do_mark = False
                    else:
                        self.markings = _markings
                        post_un.unread_order_id()
                cut = self.__buffer__.__trimmer__.__call__()
                if _worked:
                    self.__buffer__.__local_history__._add_resremove(cut)
        return _worked

    def marked_tab_replace(self, *,
                           aimed: bool | Literal['<', '>', '<>'] = False,
                           row_pointing: bool = True,
                           to_chr: str = " "
                           ) -> tuple[
                                    list[tuple[int, list[tuple[list[str], str | Literal[False] | None]]]],
                                    ChunkLoad
                                ] | None:
        """
        Replace marked tab spaces `to_chr` (default is to blanks).

        [+] __local_history__ [+] __local_history__.lock [+] __swap__.adjust [+] __swap__.fill [+] __trimmer__.trim
        [+] __marker__.adjust [+] __glob_cursor__.adjust [+] __highlighter__.prep_by_chunkload

        Replace only the marked tab spaces of the current position instead of all when `aimed` is set.
        The parameterization via angle brackets defines the evaluation of the position of the cursor at the marking;
        if only the left angle bracket ``"<"`` is selected (default if ``True`` is set), the cursor hits the marking
        even if it is located at the beginning; if only the right angle bracket ``">"`` is passed, the cursor hits the
        marking even if it is located adjacent to the end, at the beginning of the marking the cursor must be clearly
        inside; the rules can be combined via ``"<>"``.

        Understand the marker coordinates as pointers to rows and replace tab spaces in entire rows if 
        `row_pointing` is ``True``.

        The cursor position is adjusted and markers are shortened or extended accordingly, in
        `row_pointing` mode the end of a marker is adjusted to the end of the last edited row.

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
        self.__buffer__.__local_history__._lock_assert_()
        _worked = None
        if aimed:
            if isinstance(aimed, str):
                _eq_start = aimed[0] == '<'
                _eq_end = aimed[-1] == '>'
            else:
                _eq_start = True
                _eq_end = False
            if (i := self.get_aimed_mark(_get_index=True, _eq_start=_eq_start, _eq_end=_eq_end)) is not None:
                _markings = self.markings.copy()
                with self.__buffer__.__local_history__.suit():
                    post_un = self.__buffer__.__local_history__._add_marks_async(HistoryItem.TYPEVALS.MARKERCOMMENTS.POP, self.coord_snap).read_marks()
                    post_un.add_cursor((mark := self.markings.pop(i).copy())[1])
                    post_un.read_order_id()
                    with self.__buffer__.__trimmer__.suit(all_=False):
                        if row_pointing:
                            if _worked := self.__buffer__.tab_replace([mark], 'p', to_char=to_chr):
                                worked = _worked[0]
                                for i in range(_l := len(worked[0][1])):
                                    if wi := worked[0][1][i]:
                                        mark[0] = min(mark[0], wi.begin)
                                        diff = sum(
                                            (last_wi := wi).diff for _i in range(i, _l) if (wi := worked[0][1][_i]))
                                        mark[1] = last_wi.begin + diff + last_wi.write - last_wi.diff
                                        break
                        elif _worked := self.__buffer__.tab_replace([mark], 'd', to_char=to_chr):
                            worked = _worked[0]
                            mark[1] += sum(wi.diff for wi in worked[0][1] if wi)
                    if _worked:
                        post_un.flush().read_chronological_id().dump()
                        self._do_mark = False
                        if mark[0] != mark[1]:
                            self.markings.append(_Marking.make(mark))
                            self._rm_lapp()
                            self._lisort(self.markings)
                        self.__buffer__.__local_history__._add_resremove(self.__buffer__.__trimmer__.__call__())
                    else:
                        post_un.unread_order_id()
                        self.markings = _markings
                        self.__buffer__.__trimmer__.__call__()

        elif self.markings:
            _markings = self.markings.copy()
            markings = self.coord_snap()
            self.markings.clear()
            with self.__buffer__.__local_history__.suit():
                post_un = self.__buffer__.__local_history__._add_marks_async(
                    HistoryItem.TYPEVALS.MARKERCOMMENTS.PURGED, lambda: (self._lisort(_markings) if self._do_mark else _markings)).read_marks()
                post_un.read_order_id()
                with self.__buffer__.__trimmer__.suit(all_=False):
                    if row_pointing:
                        if _worked := self.__buffer__.tab_replace(markings, 'p', to_char=to_chr):
                            worked = _worked[0]
                            diff = 0
                            markings = []
                            for mark, items in reversed(worked):
                                mark = mark.copy()
                                for i in range(_l := len(items)):
                                    if wi := items[i]:
                                        mark[0] = min(mark[0], wi.begin) + diff
                                        diff += sum((last_wi := wi).diff for _i in range(i, _l) if (wi := items[_i]))
                                        mark[1] = last_wi.begin + diff + last_wi.write - last_wi.diff
                                        break
                                else:
                                    mark[0] += diff
                                    mark[1] += diff
                                if mark[0] != mark[1]:
                                    markings.append(mark)

                            i = len(markings) - 1
                            try:
                                while i > 0:
                                    while markings[i][0] <= markings[i - 1][0]:
                                        markings.pop(i - 1)
                                        if not (i := i - 1):
                                            break
                                    i -= 1
                            except IndexError:
                                pass
                            for i in range(len(markings) - 1):
                                markings[i][1] = min(markings[i][1], markings[i + 1][0])
                            self.markings = markings
                            self._do_mark = False
                        else:
                            self.markings = _markings
                    elif _worked := self.__buffer__.tab_replace(markings, 'd', to_char=to_chr):
                        worked = _worked[0]
                        diff = 0
                        for mark, items in reversed(worked):
                            mark = mark.copy()
                            mark[0] += diff
                            diff += sum(wi.diff for wi in items if wi)
                            mark[1] += diff
                            if mark[0] != mark[1]:
                                self.markings.append(mark)
                    else:
                        self.markings = _markings
                cut = self.__buffer__.__trimmer__.__call__()
                if _worked:
                    post_un.flush().read_chronological_id().dump()
                    self.__buffer__.__local_history__._add_resremove(cut)
                else:
                    post_un.unread_order_id()
        return _worked

    def coord_snap(self) -> list[list[int, int]]:
        """New sorted list from snapped (copied) coordinates."""
        markings = [list(mark) for mark in self.markings]
        if self._do_mark:
            self._lisort(markings)
        return markings

    def sorted_copy(self) -> list[_Marking | list[int, int]]:
        """Sorted copy of the main list."""
        markings = self.markings.copy()
        if self._do_mark:
            self._lisort(markings)
        return markings

    def reader(self,
               *,
               aimed: bool | Literal['<', '>', '<>'] = False,
               bin_mode: bool | str = False,
               endings: dict[Literal['', '\n'] | None, bytes] = None,
               tabs_to_blanks: int | bool = False,
               replace_tabs: bytes = None) -> Reader | None:
        """
        Factory method for the :class:`Reader` of the marked areas.
        
        Read only the marked rows of the current position instead of all when `aimed` is set.
        The parameterization via angle brackets defines the evaluation of the position of the cursor at the marking;
        if only the left angle bracket ``"<"`` is selected (default if ``True`` is set), the cursor hits the marking
        even if it is located at the beginning; if only the right angle bracket ``">"`` is passed, the cursor hits the
        marking even if it is located adjacent to the end, at the beginning of the marking the cursor must be clearly
        inside; the rules can be combined via ``"<>"``.

        To read the data in bytes, `bin_mode` must be ``True`` (UTF-8 encoding) or an encoding.

        The association of the row-ends can be defined as dict over `endings`, the keys must consist of
        ``None`` (no ending), ``"\\n"`` (newline) and ``""`` (unbroken newline), the parameter value is specified in
        bytes.

        Tabs can be converted by `tabs_to_blanks` to blanks relative to space; if ``True`` is chosen, the
        size is taken from the buffer, otherwise a different size can be specified as an integer.

        An ordinal replacement of tabs can be parameterized via `replace_tabs` with bytes.

        :return: Reader object.
        """
        if aimed:
            if isinstance(aimed, str):
                _eq_start = aimed[0] == '<'
                _eq_end = aimed[-1] == '>'
            else:
                _eq_start = True
                _eq_end = False
            dran = self.get_aimed_mark(_eq_start=_eq_start, _eq_end=_eq_end)
        elif self._do_mark:
            dran = self.sorted_copy()
        else:
            dran = self.markings
        if dran:
            return Reader(self.__buffer__, bin_mode=bin_mode, endings=endings, tabs_to_blanks=tabs_to_blanks,
                          replace_tabs=replace_tabs, dat_ranges=dran)

    def __iter__(self) -> Generator[_Marking | list[int, int]]:
        return (mark for mark in self.markings)
