# MIT License
#
# Copyright (c) 2022 Adrian F. Hoefflin [srccircumflex]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
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

try:
    from .buffer import TextBuffer
except ImportError:
    pass


# TODO

def reset_caches(buffer: TextBuffer) -> None:
    """
    Resets caches and metadata, indexes the buffer, sets the size configuration of the lines in the current
    buffer, adjusts the lines in the current buffer and moves the cursor to the previous position if possible.
    """
    try:
        goto = buffer.current_row.cursors.data_cursor
    except IndexError:
        goto = buffer.rows[0].cursors.data_cursor
    for row in buffer.rows:
        row.__exit__()
    buffer.__trimmer__.sizing(adjust_buffer=False)
    buffer._adjust_rows(0, endings=True)
    # todo: leave context managers
    buffer.__swap__.__meta_index__.remake()
    buffer._goto_data(min(goto, buffer.rows[-1].__data_start__))
    buffer._eof_metas._new_eof()
