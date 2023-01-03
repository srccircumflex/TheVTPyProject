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

from typing import Type

from vtframework.iodata.keys import NavKey
from vtframework.iodata.chars import Char, Eval as _ceval
from vtframework.iodata.keys import Key, Eval as _keval
from vtframework.iodata.mouse import Mouse, Eval as _meval
from vtframework.iodata.replies import Reply, Eval as _reval


def Eval(x: str) -> Char | Key | Mouse | Reply | Type[Char | Key | Mouse | Reply]:
    """
    The central Eval function.
    Returns the input type or the instance from a representational string.

    :raise ValueError: if the repr-string cannot be associated.
    """
    for evl in (_ceval, _keval, _meval, _reval):
        try:
            return evl(x)
        except ValueError:
            pass
    raise ValueError(f"cannot be associated: {repr(x)}")


class BasicKeyComp:

    class NavKeys:

        arrow_lr: tuple[NavKey, NavKey] = (NavKey(NavKey.K.A_LEFT, None), NavKey(NavKey.K.A_RIGHT, None))
        arrow_ud: tuple[NavKey, NavKey] = (NavKey(NavKey.K.A_UP, None), NavKey(NavKey.K.A_DOWN, None))
        border: tuple[NavKey, NavKey, NavKey] = (
            NavKey(NavKey.K.C_BEGIN, None), NavKey(NavKey.K.C_END, None), NavKey(NavKey.K.C_HOME, None)
        )
        page_ud: tuple[NavKey, NavKey] = (NavKey(NavKey.K.P_UP, None), NavKey(NavKey.K.P_DOWN, None))
