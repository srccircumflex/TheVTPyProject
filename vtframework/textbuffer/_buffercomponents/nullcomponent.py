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

from typing import Any


# Python console of PyCharm could hang on chained call. (!)
#
# PyDev console: starting.
#
# Python 3.9.9 (main, Nov 10 2011, 15:00:00)
# [GCC 11.3.0] on linux
#
# >>> runfile(...
# >>> buffer = TextBuffer(...
# >>> buffer.__swap__
# <__main__.TextBuffer._NullComponent object at 0x>
# >>> buffer.__swap__.attr
# ..........
#
#
# October 2022


class _NullComponent:
    """
    This object is used as a NULL object if an optional component in the ``TextBuffer`` is not active.

    **INFO:** Python console of PyCharm could hang on chained call.
    """

    def __call__(self, *args, **kwargs) -> Any:
        return self

    def __setattr__(self, name: str, value: Any) -> None:
        pass

    def __delattr__(self, name: str) -> None:
        pass

    def __getattr__(self, item) -> Any:
        return self

    def __getattribute__(self, item) -> Any:
        return self

    def __getitem__(self, item) -> Any:
        return self

    def __contains__(self, item) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __len__(self) -> int:
        return 0

    def __abs__(self) -> int:
        return 0

    def __int__(self) -> int:
        return 0

    def __str__(self) -> str:
        return ''

    def __bytes__(self) -> bytes:
        return b''

    def __hash__(self) -> int:
        return 0

    def __eq__(self, o: object) -> bool:
        return False

    def __ne__(self, o: object) -> bool:
        return True

    def __lt__(self, other) -> bool:
        return False

    def __le__(self, other) -> bool:
        return False

    def __gt__(self, other) -> bool:
        return False

    def __ge__(self, other) -> bool:
        return False

    def __add__(self, other) -> Any:
        return other

    def __radd__(self, other) -> Any:
        return other

    def __sub__(self, other) -> Any:
        return other

    def __rsub__(self, other) -> Any:
        return other

    def __and__(self, other) -> Any:
        return other

    def __rand__(self, other) -> Any:
        return other

    def __or__(self, other) -> Any:
        return other

    def __ror__(self, other) -> Any:
        return other

    def __xor__(self, other) -> Any:
        return other

    def __rxor__(self, other) -> Any:
        return other

    def __iter__(self) -> Any:
        return self

    def __reversed__(self) -> Any:
        return self

    def __next__(self) -> None:
        raise StopIteration

    def __enter__(self) -> Any:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
