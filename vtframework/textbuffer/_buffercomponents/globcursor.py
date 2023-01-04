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

from typing import Literal

try:
    from ..buffer import TextBuffer
    from .items import ChunkLoad
    from .localhistory import _LocalHistory
    __4doc1 = _LocalHistory
except ImportError:
    pass


class _GlobCursor:
    """
    Buffer Component as memory and handler for the global cursor position on the x-axis and cursor anchors.

    >>> # From here█ the cusror is moved down twice (on the y axis).
    >>> # line█
    >>> # As long a█ the cursor is not moved on the x-axis, it will be tried to set it on the last x position.

    Anchors are not fully :class:`_LocalHistory` compatible and will be deleted irreversibly on range removal,
    if there is an anchor in the range.
    """
    glob_column_change: bool
    glob_column_val: int

    cursor_anchors: list[tuple[int | str, int]]
    __buffer__: TextBuffer

    __slots__ = ('glob_column_change', 'glob_column_val', 'cursor_anchors', '__buffer__')

    def __init__(self, __buffer__: TextBuffer):
        self.glob_column_change = False
        self.glob_column_val = 0
        self.cursor_anchors = list()
        self.__buffer__ = __buffer__

    def _adjust_anchors(self, start: int, diff: int, _rm_area_end: int | Literal[False] = None) -> None:
        """
        Adjust the cursor anchors by `diff` starting from `start`.
        Remove applicable anchors irreversibly from `start` to `_rm_area_end`;
        if `_rm_area_end` is ``False`` remove all markers starting from `start`.
        """
        i = 0
        try:
            while True:
                if self.cursor_anchors[i][1] >= start + 1:
                    break
                i += 1
            if _rm_area_end is not None:
                if _rm_area_end is False:
                    self.cursor_anchors = self.cursor_anchors[:i]
                else:
                    while self.cursor_anchors[i][1] < _rm_area_end:
                        self.cursor_anchors.pop(i)
                    while True:
                        self.cursor_anchors[i] = (self.cursor_anchors[i][0], self.cursor_anchors[i][1] + diff)
                        i += 1
            else:
                while True:
                    self.cursor_anchors[i] = (self.cursor_anchors[i][0], self.cursor_anchors[i][1] + diff)
                    i += 1
        except IndexError:
            pass

    def _get_anchor_i(self, key: int | str) -> int:
        """
        Return the index position of the anchor with `key` in memory.

        :raises KeyError(key): if key is not present.
        """
        for i, anc in enumerate(self.cursor_anchors):
            if anc[0] == key:
                return i
        raise KeyError(key)

    def get_anchor(self, key: int | str) -> tuple[int | str, int]:
        """
        Return the anchor item with `key`.

        :raises KeyError(key): if key is not present.
        """
        return self.cursor_anchors[self._get_anchor_i(key)]

    def pop_anchor(self, key: int | str) -> tuple[int | str, int]:
        """
        Return the anchor item with `key` and pop them from cache.

        :raises KeyError(key): if key is not present.
        """
        return self.cursor_anchors.pop(self._get_anchor_i(key))

    def _get_anchor_i_by_position(self, position: int) -> int:
        """
        Return the index position of the anchor with `position` in memory.

        :raises KeyError(position): if anchor with position is not present.
        """
        for i, anc in enumerate(self.cursor_anchors):
            if anc[1] == position:
                return i
        raise KeyError(position)

    def get_anchor_by_position(self, position: int = None) -> tuple[int | str, int]:
        """
        Return the anchor item with `position`.

        :raises KeyError(position): if anchor with position is not present.
        """
        position = (self.__buffer__.current_row.cursors.data_cursor if position is None else position)
        return self.cursor_anchors[self._get_anchor_i_by_position(position)]

    def pop_anchor_by_position(self, position: int = None) -> tuple[int | str, int]:
        """
        Return the anchor item with `position` and pop them from cache.

        :raises KeyError(position): if anchor with position is not present.
        """
        position = (self.__buffer__.current_row.cursors.data_cursor if position is None else position)
        return self.cursor_anchors.pop(self._get_anchor_i_by_position(position))

    def goto_anchor(self, key: int | str) -> ChunkLoad:
        """
        Query the anchor with `key` and move the cursor there.

        :raises KeyError: if key is not present.

        :raises EOFError(0, msg): if n is not in the range of the currently loaded chunks and
          the chunks of the required side cannot be loaded completely/are not available.
        :raises EOFError(1, msg): Chunks of the required side could not be loaded sufficiently.
          The closest chunk was loaded and the cursor was placed at the beginning of the first row.
        :raises EOFError(2, msg): if an error occurs during the final setting of the cursor
          (indicator of too high value). The cursor was set to the next possible position.

        :raises AssertionError: __local_history__ lock is engaged.
        """
        return self.__buffer__.goto_data(self.cursor_anchors[self._get_anchor_i(key)][1])

    def add_anchor(self, key: int | str, anchor: int = None) -> None:
        """
        Add `anchor` (by default the current cursor position) under `key` to the memory.

        **The plausibility of** `anchor` **compared to the existing data is not checked**

        :raises KeyError: if the key is already assigned. The error can be processed by `add_anchor_by_err`.
        """
        anchor = (self.__buffer__.current_row.cursors.data_cursor if anchor is None else anchor)
        p = None
        for i, anc in enumerate(self.cursor_anchors):
            if anc[1] > anchor:
                p = i
            if anc[0] == key:
                raise KeyError(
                    "new anchor:", (key, anchor),
                    "found order position:", p,
                    "key present at index:", i,
                    "in anchor:", anc)
        if p is not None:
            self.cursor_anchors.insert(p, (key, anchor))
        else:
            self.cursor_anchors.append((key, anchor))

    def add_anchor_by_err(self, error: KeyError) -> None:
        """Set an `anchor` by the `error` from `add_anchor`."""
        _, new_anc, _, p, _, i, _, anc = error.args
        self.cursor_anchors.pop(i)
        if p is None:
            for _i, _anc in enumerate(self.cursor_anchors[i:]):
                if _anc[1] > new_anc[1]:
                    self.cursor_anchors.insert(i + _i, new_anc)
                    break
            else:
                self.cursor_anchors.append(new_anc)
        else:
            self.cursor_anchors.insert(p, new_anc)

    def purge_anchors(self) -> list[tuple[int | str, int]]:
        """Clear and return the anchor memory."""
        anchors = self.cursor_anchors
        self.cursor_anchors = list()
        return anchors

    def note_globc(self) -> None:
        """Change the global x-position on the next query."""
        self.glob_column_change = True

    def get_globc(self, __new: int) -> int:
        """Query the global x-position, set it to `new` before if flagged for change."""
        if self.glob_column_change:
            self.glob_column_val = __new
        self.glob_column_change = False
        return self.glob_column_val

    def set_globc(self, __n: int) -> None:
        """Set the global x-position."""
        self.glob_column_change = False
        self.glob_column_val = __n
