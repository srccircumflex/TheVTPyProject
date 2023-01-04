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
from typing import Union, NamedTuple, Generator, Literal, Type
from re import search

_MOD_COLLECTION: dict[int, tuple[int, ...]] = {
    4: (4, 12, 20, 28),
    8: (8, 12, 24, 28),
    16: (16, 20, 24, 28)
}


class _MOD(int):

    def __and__(self, other: _MOD):
        return _MOD(self + other)

    def __contains__(self, item: Literal[4, 8, 16] | _MOD):
        return self in _MOD_COLLECTION[item]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"


class _BUTTONS(NamedTuple):
    """
    - ``L_*`` : Left-
    - ``M_*`` : Middle-
    - ``R_*`` : Right-
    - ``U_*``/``D_*`` : Up/Down
    ``L_PRESS = 0 M_PRESS = 1 R_PRESS = 2 RELEASE = 3 L_MOVE = 32
    M_MOVE = 33 R_MOVE = 34 MOVE = 35 U_WHEEL = 64 D_WHEEL = 65``
    """
    L_PRESS: int = 0
    M_PRESS: int = 1
    R_PRESS: int = 2
    RELEASE: int = 3
    L_MOVE: int = 32
    M_MOVE: int = 33
    R_MOVE: int = 34
    MOVE: int = 35
    U_WHEEL: int = 64
    D_WHEEL: int = 65


class _MODI(NamedTuple):
    """Mouse Modification values.

    Supports the ``&`` operator to present combined keystrokes.

    ``SHIFT = 4 ALT = 8 META = 8 CTRL = 16``"""
    SHIFT: _MOD = _MOD(4)
    ALT: _MOD = _MOD(8)
    META: _MOD = _MOD(8)
    CTRL: _MOD = _MOD(16)


MOD_VALUES = _MODI()
BUTTON_VALUES = _BUTTONS()


class _MARGStypeHints:
    range = tuple[int, int]
    exact = int
    skip = None

    t_comp = Union[range, exact, skip]
    T_comp = tuple[t_comp, t_comp, t_comp]

    comp = Union[t_comp, T_comp, skip]

    t_val = int
    T_val = tuple[int, int, int]

    t = Union[t_val, t_comp]
    T = Union[T_val, T_comp]

    POS = Union[
        tuple[t_val, t_val],
        tuple[T_val, T_val],
        tuple[t_comp, t_comp],
        tuple[T_comp, T_comp],
        skip
    ]


class Mouse:
    """

    ---Mouse Tracking Object---

    Activated by one of:  (:class:`DECPrivateMode`)
        - [CSI ? 9 h]
        - [CSI ? 1000 h]
        - [CSI ? 1002 h]
        - [CSI ? 1003 h]

    Modified by one of:  (:class:`DECPrivateMode`)
        - [CSI ? 1006 h]
        - [CSI ? 1016 h]

    Values:

    - `BUTTON`: int
        Values for comparison in `B`:
            ``L_PRESS = 0
            M_PRESS = 1
            R_PRESS = 2
            RELEASE = 3
            L_MOVE = 32
            M_MOVE = 33
            R_MOVE = 34
            MOVE = 35
            U_WHEEL = 64
            D_WHEEL = 65``

            ## `Other buttons`_ (gt. 6) are initiated with the real value
            (button value + sum(modifications)) and `MOD` becomes -1. ##

    - `MOD`: int
        Values for comparison in `M`:
            ``SHIFT = 4
            ALT = 8
            META = 8
            CTRL = 16``
        Comparisons:
            - ``Mouse.M.SHIFT  in  Mouse(key)``
            - ``(Mouse.M.SHIFT, Mouse.M.CTRL)  in  Mouse(key)``  `(Combined modifications)`
            - ``Mouse.M.SHIFT & Mouse.M.CTRL  in  Mouse(key)``  `(Combined modifications)`

    - `POS`: tuple
        - ``POS[0]``: int = Pointer position on the x-axis
        - ``POS[1]``: int = Pointer position on the y-axis

        ## When `Highlight tracking`_ is enabled and x != y :
        ``POS[0]``: tuple = (start-x, end-x, mouse-x)
        ``POS[1]``: tuple = (start-y, end-y, mouse-y)
        ## untested ##

    ****

    # Resources:
     ; `xterm/Mouse-Tracking`_

    .. _`Other buttons`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Other-buttons
    .. _`Highlight tracking`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Highlight-tracking
    .. _`xterm/Mouse-Tracking`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Mouse-Tracking

    ****

    This object is created by the vtiinterpreter and also serves as a reference object,
    see for the documentation about the parameterization in __init__.

    :param x: The position of the pointer on the x-axis.
     Can be defined as a range by a tuple (start, stop).
     None skips the comparison of the parameter. For the untested Highlight mode the parameterization is more complex:
     (start-x, end-x, mouse-x). Each field of the three-tuple can be defined accordingly.
    :param y: The position of the pointer on the y-axis.
     Can be defined as a range by a tuple (start, stop).
     None skips the comparison of the parameter. For the untested Highlight mode the parameterization is more complex:
     (start-y, end-y, mouse-y). Each field of the three-tuple can be defined accordingly.
    :param button: The button should be selected from `Mouse.B`.
     None skips the comparison of the parameter.
    :param mod: Should be selected from `Mouse.M`.
     None skips the comparison of the parameter. The `&` operator can be used between the mods to display combinations
     ( e.g. ``Mouse(Mouse.B.L_PRESS, Mouse.M.SHIFT & Mouse.M.CTRL)`` ).
     If mod 0, no modification is explicitly expected.
    """

    BUTTON: int
    MOD: _MOD
    POS: _MARGStypeHints.POS
    B: _BUTTONS = BUTTON_VALUES
    M: _MODI = MOD_VALUES

    @property
    def __vtdtid__(self):
        return 3

    @__vtdtid__.setter
    def __vtdtid__(self, v):
        raise AttributeError("__vtdtid__ is not settable")

    @__vtdtid__.deleter
    def __vtdtid__(self):
        raise AttributeError("__vtdtid__ is not deletable")

    __slots__ = ('BUTTON', 'MOD', 'POS')

    def __init__(
            self,
            button: int | None = None,
            mod: int | None = 0,
            x: _MARGStypeHints.comp = None, y: _MARGStypeHints.comp = None
    ):
        self.BUTTON = button
        self.MOD = self._mod(mod)
        self.POS = (x, y)

    @staticmethod
    def _mod(mod: int | tuple | None) -> _MOD | None:
        if mod is None:
            return None
        if isinstance(mod, int):
            return _MOD(mod)
        return _MOD(sum(mod))

    def __contains__(self, item: int | tuple[int, ...] | None):
        r"""
        Return if the modification matches. Multiple keystrokes are queried via a tuple.
        Values should be chosen from `self.M`.

        ****

        ============= ========== ============= ========== ==================
         BUTTONS       SHIFT(4)   ALT/META(8)   CTRL(16)   [combined]
        ============= ========== ============= ========== ==================
         L_PRESS(0)       4           8           16       [12  20  24  28]
         M_PRESS(1)       5           9           17       [13  21  25  29]
         R_PRESS(2)       6          10           18       [14  22  26  30]
         RELEASE(3)       7          11           19       [15  23  27  31]
         L_MOVE(32)      36          40           48       [44  52  56  60]
         M_MOVE(33)      37          41           49       [45  53  57  61]
         R_MOVE(34)      38          42           50       [46  54  58  62]
         MOVE(35)        39          43           51       [47  55  59  63]
         U_WHEEL(64)     68          72           80       [76  84  88  92]
         D_WHEEL(65)     67          73           81       [77  85  89  93]
        ============= ========== ============= ========== ==================
        """
        return self.MOD is None or item is None or self.MOD == self._mod(item)

    def __eq__(self, other: Mouse):
        """Return whether `other` is the same kind of instance and the defined parameters of the
        reference object correlate with those of the `other` one."""

        def comp(_v: tuple | int | None, _r: tuple | int | None):
            if isinstance(_r, int):
                _v, _r = _r, _v
            if _r is None:
                return True
            if isinstance(_r, int):
                return _v == _r
            if isinstance(_r, tuple):
                try:
                    if len(_r) == 3:
                        # Highlight-T-Mode
                        return
                    return _r[0] <= _v <= _r[-1]
                except TypeError as e:
                    raise TypeError("faulty comparison", e.args)

        if not isinstance(self, other.__class__):
            return False

        if (self.BUTTON is None or self.BUTTON == other.BUTTON or other.BUTTON is None) and self.MOD in other:
            for ref, cmp in zip(self.POS, other.POS):
                if None not in (ref, cmp):
                    if isinstance(ref, tuple) and isinstance(cmp, tuple):
                        # Highlight-T-Mode
                        if len(ref) != len(cmp):
                            return False
                        for r, c in zip(ref, cmp):
                            if not comp(c, r):
                                return False
                    elif not comp(cmp, ref):
                        return False
            return True
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.BUTTON} {self.MOD} {self.POS}>"

    def __hash__(self) -> int:
        return hash(self.__repr__())

    def __int__(self) -> int:
        return self.BUTTON

    def __iter__(self) -> Generator[int | tuple[int, int, int]]:
        for p in self.POS:
            yield p

    @staticmethod
    def eval(x: str) -> Mouse:
        """Create a :class:`Mouse` instance from a representative sting of a :class:`Mouse` instance.

        :raise ValueError(exception): on errors with the original exception as argument."""
        try:
            mouse: Mouse = eval((m := search("(?<=<)\\w+", x)).group() + '()')
            mouse.BUTTON = eval((m := search("(?<= )\\S+", x[(s := m.end()):])).group())
            mouse.MOD = eval(search("(?<= )\\S+", x[s + m.end():]).group())
            mouse.POS = eval(search("(?<= )\\(.*\\)(?=>$)", x).group())
            return mouse
        except Exception as e:
            raise ValueError(e)


def Eval(x: str) -> Mouse | Type[Mouse]:
    """Return a :class:`Mouse` instance or type from a representative sting.

    :raise ValueError(exception): on errors with the original exception as argument."""
    try:
        if x.startswith('<class '):
            return eval(search("(?<=\\.)\\w+(?='>$)", x).group())
        else:
            return Mouse.eval(x)
    except Exception as e:
        raise ValueError(e)
