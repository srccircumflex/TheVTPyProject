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

from typing import Callable, Any, ContextManager, TypeVar, Generic

_T = TypeVar('_T')


class _Suit(ContextManager, Generic[_T]):
    """Contextmanager for special operations on the ``TextBuffer``."""

    _enter_: Callable[[_Suit], _T]
    _exit_: Callable[[Any, Any, Any], Any]

    __slots__ = ('_enter_', '_exit_')

    def __init__(self,
                 enter: Callable[[_Suit], _T],
                 exit_: Callable[[Any, Any, Any], Any]):

        self._enter_, self._exit_ = enter, exit_

    def __enter__(self) -> _T:
        return self._enter_(self)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._exit_(exc_type, exc_val, exc_tb)
