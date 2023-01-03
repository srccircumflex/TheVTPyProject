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
from typing import Callable


class Gate:
    """
    A wrapper class for a decorator that executes the function or an alternative depending on ``self.status``
    (editable via ``enable`` | ``disable`` | ``destroy``).

    Statuses:
        - ``True`` : enabled
        - ``None`` : disabled
        - ``False`` : permanently disabled (destroyed)
    """

    state: bool | None

    def __init__(self):
        self.state = True

    def enable(self) -> bool:
        if self.state is False:
            return False
        self.state = True
        return True

    def disable(self) -> bool:
        if self.state is False:
            return False
        self.state = None
        return True

    def destroy(self) -> None:
        self.state = False

    def __bool__(self) -> bool:
        return bool(self.state)

    def __repr__(self):
        return {
            None: f"<{self.__class__.__name__} :: disable>",
            True: f"<{self.__class__.__name__} :: enabled>",
            False: f"<{self.__class__.__name__} :: permanently disabled>",
        }[self.state]

    def wrapper(self, alt=lambda cls, *args, **kwargs: str()) -> Callable[[...], ...]:
        def _wrapper(__f: Callable[[...], str]):
            def wrap(*args, **kwargs) -> str:
                if self.state:
                    return __f(*args, **kwargs)
                return alt(*args, **kwargs)
            return wrap
        return _wrapper

    def __call__(self, alt=lambda cls, *args, **kwargs: str()) -> Callable[[...], ...]:
        return self.wrapper(alt)


__STYLE_GATE__ = Gate()
__DECPM_GATE__ = Gate()
