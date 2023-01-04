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
from typing import Callable

try:
    from ..buffer import TextBuffer
except ImportError:
    pass


class _EOFMetas:
    """
    Buffer Component for metadata about the size of the data stored in the buffer.
    The calculations are performed only when retrieved.
    """

    _rows_changed: bool
    _data_changed: bool
    _changed_rows_: Callable[[], None]
    _changed_data_: Callable[[], None]
    _eof_dat: int
    _eof_cnt: int
    _eof_row: int
    _eof_lin: int
    __buffer__: TextBuffer

    @property
    def eof_data(self) -> int:
        if self._data_changed:
            self._new_eof()
        return self._eof_dat

    @property
    def eof_content(self) -> int:
        if self._data_changed:
            self._new_eof()
        return self._eof_cnt

    @property
    def eof_row_num(self) -> int:
        if self._rows_changed:
            self._new_eof()
        return self._eof_row

    @property
    def eof_line_num(self) -> int:
        if self._rows_changed:
            self._new_eof()
        return self._eof_lin

    def __init__(self, __buffer__: TextBuffer):
        self._data_changed = self._rows_changed = False
        if (__buffer__._top_baserow.maxsize_param or
            __buffer__._future_baserow.maxsize_param or
            __buffer__._last_baserow.maxsize_param):

            def _changed_data():
                self._rows_changed = self._data_changed = True

        else:
            def _changed_data():
                self._data_changed = True

        def _changed_rows():
            self._rows_changed = self._data_changed = True

        self._changed_data_ = _changed_data
        self._changed_rows_ = _changed_rows

        self._eof_dat = self._eof_cnt = self._eof_lin = self._eof_row = 0
        self.__buffer__ = __buffer__

    def _new_eof(self) -> None:
        if self.__buffer__.__swap__.current_chunk_ids[1]:
            self.__buffer__.__swap__.__meta_index__.adjust_bottom_auto()
            self._eof_dat, self._eof_cnt, self._eof_row, self._eof_lin = self.__buffer__.__swap__.chunk_buffer(
                1, sandbox=True).indexing()
        else:
            self._eof_dat, self._eof_cnt, self._eof_row, self._eof_lin = self.__buffer__.indexing()
        self._rows_changed = self._data_changed = False

    def __repr__(self) -> str:
        return repr((self.eof_data, self.eof_content, self.eof_row_num, self.eof_line_num))
