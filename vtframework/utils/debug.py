# MIT License
#
# Copyright (c) 2023 Adrian F. Hoefflin [srccircumflex]
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

from typing import Literal

try:
    from .buffer import TextBuffer
except ImportError:
    pass


def reset_buffer_caches(__buffer__: TextBuffer, fatal_error_act: Literal["raise", "ignore"] = "raise") -> None:
    """
    The function is for rough error recovery of a buffer object (:class:`TextBuffer`). Starting from the original
    state, the buffer may remain in an unstable state even if the function is successfully executed.

    THE FUNCTION SHOULD NEVER BE USED AND ONLY SUPPORTS FURTHER PROCESSING OR SAVING OF THE BUFFER IN CASE OF FATAL
    ERRORS.

    The parameter `fatal_error_act` specifies how to handle severe errors during recovery and can be
    ``"raise"`` or ``"ignore"``. If ``"raise"`` is passed, an ``AssertionError`` is raised for fatal errors,
    with the original error as argument.

    The processes of recovery:
        - Reset caches, metadata and indexes in the buffer.
        - Leave all active suits.
        - Set the size configuration of the rows.
        - Adjust the rows.
        - Remake the swap metaindex.
        - Move the cursor to the previous position if possible.
        - Calculate the data amount.
    """
    if fatal_error_act[0] == "i":
        def _raise(_e):
            pass
    else:
        def _raise(_e):
            raise _e
    try:
        goto = __buffer__.current_row.cursors.data_cursor
    except IndexError as e:
        try:
            goto = __buffer__.rows[0].cursors.data_cursor
        except IndexError as e:
            _raise(AssertionError("no rows in the buffer", e))
            goto = 0
    for row in __buffer__.rows:
        try:
            row.__exit__()
        except Exception as e:
            raise
    for suit in __buffer__.__swap__._active_suits + [__buffer__.__trimmer__._active_suit,
                                                     __buffer__.__swap__.__meta_index__,
                                                     __buffer__.__local_history__._active_suit]:
        try:
            suit.__exit__(None, None, None)
        except Exception:
            pass
    try:
        __buffer__.__trimmer__.sizing(adjust_buffer=False)
    except Exception as e:
        _raise(AssertionError("sizing of the rows failed", e))
    try:
        __buffer__._adjust_rows(0, endings=True)
    except Exception as e:
        _raise(AssertionError("adjustment of the rows failed", e))
    try:
        __buffer__.__swap__.__meta_index__.remake()
    except Exception as e:
        _raise(AssertionError("calculation of the swap metaindex failed", e))
    try:
        __buffer__._goto_data(max(__buffer__.__swap__.get_chunk(-1).start_point_data,
                                  min(goto, __buffer__.rows[-1].__data_start__)))
    except Exception:
        try:
            __buffer__._goto_data(max(__buffer__.rows[0].__data_start__,
                                      min(goto, __buffer__.rows[-1].__data_start__)))
        except Exception as e:
            _raise(AssertionError("moving the cursor to a valid position failed", e))
    try:
        __buffer__._eof_metas._new_eof()
    except Exception as e:
        _raise(AssertionError("calculation of the data amount failed", e))
