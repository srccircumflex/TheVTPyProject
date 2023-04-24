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

from typing import Literal, overload, Callable

from vtframework.video.exceptions import GeometrieError
from vtframework.video.geocalc import GeoCalculator
from vtframework.iodata.esccontainer import EscString

try:
    from vtframework.video.grid import Cell
    __4doc = Cell
except ImportError:
    pass


class FramePadding:
    """
    This widget frame definition object can be passed to a :class:`Cell`.

    Frame width and pattern is defined sweepingly by the length and composition of the strings at `N`, `O`, `S`, `E`,
    `NE`, `NO`, `SE`, `SO`. Thereby the name of the parameter corresponds to the cardinal direction and the characters
    are always arranged starting from the widget border. In addition, the default character can be passed in the second
    position of a tuple (``<NBSP>`` by default), this is used to fill remaining space. The passing of ``None`` is
    equivalent to ``("", <NBSP>)``.

    In order to grant the frame also accordingly place, the parameters `widget_x_calc`, and/or `widget_y_calc` must be
    defined compellingly by a :class:`GeoCalculator` object. These Calculate the size of the widget based on the
    height/width of the cell, the remaining space available for the frame is the difference. Tip:

    >>> widget_x_calc=GeoCalculator(base_spec=1.0, perc_spec_adjustment= -(len(E) + len(O)) )
    >>> widget_y_calc=GeoCalculator(base_spec=1.0, perc_spec_adjustment= -(len(N) + len(S)) ),

    If the orientation of the widget is specified via `widget_orient`, the widths of the frame sides are not adjusted
    according to the space, instead the opposite side(s) are extended as far as possible and if necessary the frames of
    the defined cardinal direction are shortened.
    Shortening of the frame definitions can generally be allowed via `mutable`. If ``"in"`` is passed, shortening is
    determined from the characters located at the widget onwards, via ``"out"`` the shortening is determined starting
    from the cell border.

    >>> frame = FramePadding(
    ...     NE="⁴4K",        N="nŋN",        NO="¹1I",
    ...     E=("e€E", "×"),                  O="oøO",
    ...     SE=("³3M", "/"), S=("sſS", "$"), SO="²2U",
    ...
    ...     widget_orient="NO",
    ...     mutable="out",
    ...     fold_mutable="in"
    ... )
    >>> frame.resize(widget_size=(10, 3), cell_size=(25, 11))
    ... ×××××××××KNNNNNNNNNNNNNNI
    ... ×××××××××E4ŋŋŋŋŋŋŋŋŋŋŋŋ1O
    ... ×××××××××E€⁴nnnnnnnnnn¹øO
    ... ×××××××××E€e          oøO
    ... ×××××××××E€e          oøO
    ... ×××××××××E€e          oøO
    ... ×××××××××E€³ssssssssss²øO
    ... ×××××××××E3ſſſſſſſſſſſſ2O
    ... ×××××××××MSSSSSSSSSSSSSSU
    ... ××××××××/$$$$$$$$$$$$$$$$
    ... ×××××××/$$$$$$$$$$$$$$$$$
    >>> frame.resize(widget_size=(10, 3), cell_size=(15, 8))
    ... EKŋŋŋŋŋŋŋŋŋŋŋŋI
    ... E€4nnnnnnnnnn1ø
    ... E€e          oø
    ... E€e          oø
    ... E€e          oø
    ... E€³ssssssssss2ø
    ... E3ſſſſſſſſſſſſU
    ... MSSSSSSSSSSSSSS

    The object is further treated via the :class:`Cell`.
    """
    _N: tuple[str, str]
    _O: tuple[str, str]
    _S: tuple[str, str]
    _E: tuple[str, str]
    _NO: tuple[str, str]
    _NE: tuple[str, str]
    _SO: tuple[str, str]
    _SE: tuple[str, str]

    widget_x_calc: GeoCalculator
    widget_y_calc: GeoCalculator

    mutable: bool
    _mutable: Callable[[int], slice] | None
    _fold_mutable: Callable[[int], slice]

    widget_orient: Literal["N", "O", "S", "E", "NO", "NE", "SO", "SE", ""]
    widget_size: tuple[int, int]
    cell_size: tuple[int, int]

    expanse_N: int
    expanse_O: int
    expanse_S: int
    expanse_E: int

    N: list[str]
    O: list[str]
    S: list[str]
    E: list[str]

    __slots__ = ('_N', '_O', '_S', '_E', '_NO', '_NE', '_SO', '_SE',
                 'widget_x_calc', 'widget_y_calc',
                 '_fold_mutable', '_mutable', 'mutable',
                 'widget_orient', 'widget_size', 'cell_size',
                 'N', 'O', 'S', 'E',
                 'expanse_N', 'expanse_O', 'expanse_S', 'expanse_E',)

    def __init__(self,
                 # E="pad", O="pad" -> dap|widget|pad
                 # param="pad" | param=("pad", "<filler_chr>") | param=None=("", "<NBSP>")
                 N: str | tuple[str, str] | None = None,
                 O: str | tuple[str, str] | None = None,
                 S: str | tuple[str, str] | None = None,
                 E: str | tuple[str, str] | None = None,
                 NO: str | tuple[str, str] | None = None,
                 SO: str | tuple[str, str] | None = None,
                 SE: str | tuple[str, str] | None = None,
                 NE: str | tuple[str, str] | None = None,
                 widget_x_calc: GeoCalculator = None,
                 widget_y_calc: GeoCalculator = None,
                 widget_orient: Literal["N", "O", "S", "E", "NO", "NE", "SO", "SE", ""] = None,
                 mutable: Literal["in", "out"] | None = None,
                 fold_mutable: Literal["in", "out"] = "out"):
        self.widget_x_calc = widget_x_calc or GeoCalculator(None)
        self.widget_y_calc = widget_y_calc or GeoCalculator(None)
        self.settings(N=N, O=O, S=S, E=E, NO=NO, NE=NE, SO=SO, SE=SE,
                      widget_orient=widget_orient, mutable=mutable, fold_mutable=fold_mutable)

    @overload
    def settings(self, *,
                 N: str | tuple[str, str] | None = ...,
                 O: str | tuple[str, str] | None = ...,
                 S: str | tuple[str, str] | None = ...,
                 E: str | tuple[str, str] | None = ...,
                 NO: str | tuple[str, str] | None = ...,
                 SO: str | tuple[str, str] | None = ...,
                 SE: str | tuple[str, str] | None = ...,
                 NE: str | tuple[str, str] | None = ...,
                 widget_orient: Literal["N", "O", "S", "E", "NO", "NE", "SO", "SE", ""] | None = ...,
                 mutable: Literal["in", "out"] | None = ...,
                 fold_mutable: Literal["in", "out"] = ...) -> None:
        ...

    def settings(self, **kwargs) -> None:
        """
        Changes the size, composition and properties of the frame.
        """
        for attr in ('N', 'E', 'O', 'S', 'NO', 'SO', 'NE', 'SE'):
            try:
                if isinstance(o := kwargs.pop(attr), str):
                    setattr(self, '_' + attr, (EscString.new(o), EscString("\u00a0")))  # NBSP
                elif o:
                    setattr(self, '_' + attr, (EscString.new(o[0]), EscString.new(o[1])))
                else:
                    setattr(self, '_' + attr, (EscString(), EscString("\u00a0")))  # NBSP
            except KeyError:
                pass
        try:
            mutable = kwargs.pop('mutable')
        except KeyError:
            pass
        else:
            if mutable:
                self._mutable = {"in": lambda n: slice(abs(n), None), "out": lambda n: slice(n)}[mutable]
            else:
                self._mutable = None
            self.mutable = bool(self._mutable)
        try:
            fold_mutable = kwargs.pop('fold_mutable')
        except KeyError:
            pass
        else:
            self._fold_mutable = {"in": lambda n: slice(-n, None), "out": lambda n: slice(n)}[fold_mutable]
        try:
            self.widget_orient = kwargs.pop('widget_orient') or ""
        except KeyError:
            pass

        self.resize((1, 1))

        if kwargs:
            raise ValueError(kwargs)

        #                             w/x  h/y
    def resize(self, cell_size: tuple[int, int] = None) -> None:
        """
        Calculate the widget size based on the `cell_size` and build the frame.

        :raises GeometrieError: Remaining space not enough for frame and frame is not mutable.
        """
        self.cell_size = cell_size
        self.widget_size = (
            self.widget_x_calc(cell_size[0], 0),
            self.widget_y_calc(cell_size[1], 0)
        )

        padN = EscString.new(self._N[0])
        padO = EscString.new(self._O[0])
        padS = EscString.new(self._S[0])
        padE = EscString.new(self._E[0])

        lpadN = len(self._N[0])
        lpadO = len(self._O[0])
        lpadS = len(self._S[0])
        lpadE = len(self._E[0])

        if cell_size:
            remaining_width = cell_size[0] - self.widget_size[0]
            remaining_height = cell_size[1] - self.widget_size[1]

            if (mut := (remaining_height - (lpadN + lpadS))) < 0:
                if not self._mutable:
                    raise GeometrieError("Remaining height not enough for frame and frame is not mutable.")
                if "N" in self.widget_orient:
                    padN = padN[self._mutable(mut)]
                    if (mut := mut + lpadN) < 0:
                        padS = padS[self._mutable(mut)]
                        lpadS = len(padS)
                    lpadN = len(padN)
                elif "S" in self.widget_orient:
                    padS = padS[self._mutable(mut)]
                    if (mut := mut + lpadS) < 0:
                        padN = padN[self._mutable(mut)]
                        lpadN = len(padN)
                    lpadS = len(padS)
                else:
                    _mutN = mut + abs(_mutS := mut // 2)
                    if (_rmutS := _mutS + lpadS) < 0:
                        padS = EscString()
                        padN = padN[self._mutable(_mutN + _rmutS)]
                        lpadS = 0
                        lpadN = len(padN)
                    elif (_rmutN := _mutN + lpadN) < 0:
                        padN = EscString()
                        padS = padS[self._mutable(_mutS + _rmutN)]
                        lpadS = len(padS)
                        lpadN = 0
                    else:
                        padN = padN[self._mutable(_mutN)]
                        padS = padS[self._mutable(_mutS)]
                        lpadS = len(padS)
                        lpadN = len(padN)
            elif mut:
                if "N" in self.widget_orient:
                    padS += self._S[1] * mut
                elif "S" in self.widget_orient:
                    padN += self._N[1] * mut
                else:
                    _mutN = mut - (_mutS := abs(mut // 2))
                    padS += self._S[1] * _mutS
                    padN += self._N[1] * _mutN

            if (mut := (remaining_width - (lpadO + lpadE))) < 0:
                if not self._mutable:
                    raise GeometrieError("Remaining width not enough for frame and frame is not mutable.")
                if "O" in self.widget_orient:
                    padO = padO[self._mutable(mut)]
                    if (mut := mut + lpadO) < 0:
                        padE = padE[self._mutable(mut)]
                        lpadE = len(padE)
                    lpadO = len(padO)
                elif "E" in self.widget_orient:
                    padE = padE[self._mutable(mut)]
                    if (mut := mut + lpadE) < 0:
                        padO = padO[self._mutable(mut)]
                        lpadO = len(padO)
                    lpadE = len(padE)
                else:
                    _mutO = mut + abs(_mutE := mut // 2)
                    if (_rmutE := _mutE + lpadE) < 0:
                        padE = EscString()
                        padO = padO[self._mutable(_mutO + _rmutE)]
                        lpadE = 0
                        lpadO = len(padO)
                    elif (_rmutO := _mutO + lpadO) < 0:
                        padO = EscString()
                        padE = padE[self._mutable(_mutE + _rmutO)]
                        lpadE = len(padE)
                        lpadO = 0
                    else:
                        padO = padO[self._mutable(_mutO)]
                        padE = padE[self._mutable(_mutE)]
                        lpadE = len(padE)
                        lpadO = len(padO)
            elif mut:
                if "O" in self.widget_orient:
                    padE += self._E[1] * mut
                elif "E" in self.widget_orient:
                    padO += self._O[1] * mut
                else:
                    _mutE = mut - (_mutO := abs(mut // 2))
                    padO += self._O[1] * _mutO
                    padE += self._E[1] * _mutE

        self.N = [c * self.widget_size[0] for c in reversed(padN)]
        self.S = [c * self.widget_size[0] for c in padS]
        self.O = [padO for _ in range(self.widget_size[1])]
        self.E = [EscString().join(reversed(padE)) for _ in range(self.widget_size[1])]

        lN = len(self.N)
        lS = len(self.S)

        if self.E and (lE := len(self.E[0])):
            SE = self._SE[0][self._fold_mutable(min(lpadS, lpadE))] + self._SE[1] * min(len(padS), lpadE := len(padE))
            NE = self._NE[0][self._fold_mutable(min(lpadN, lpadE))] + self._NE[1] * min(len(padN), lpadE)
            if lpadN:
                def cascade():
                    return EscString().join(reversed(padE[nxt_i:]))
            else:
                def cascade():
                    return self._N[1] * (lpadE - nxt_i)
            try:
                for i in range(m := max(lN, lE)):
                    nxt_i = i + 1
                    neg_i = -nxt_i
                    self.N[neg_i] = NE[i] + (padN[i] * i) + self.N[neg_i]
                    self.E.insert(0, _cas := cascade())
                    if not _cas:
                        _r = nxt_i
                        for _i in range(_r, m):
                            _ni = -(_i + 1)
                            self.N[_ni] = (padN[_i] * _r) + self.N[_ni]
                            self.E.insert(0, EscString())
                        break
            except IndexError:
                pass
            if lpadS:
                def cascade():
                    return EscString().join(reversed(padE[nxt_i:]))
            else:
                def cascade():
                    return self._S[1] * (lpadE - nxt_i)
            try:
                for i in range(m := max(lS, lE)):
                    nxt_i = i + 1
                    self.S[i] = SE[i] + (padS[i] * i) + self.S[i]
                    self.E.append(_cas := cascade())
                    if not _cas:
                        _r = nxt_i
                        for _i in range(_r, m):
                            self.S[_i] = (padS[_i] * _r) + self.S[_i]
                            self.E.append(EscString())
                        break
            except IndexError:
                pass
        else:
            self.E.extend(EscString() for _ in range(lN + lS))
            lE = 0

        if self.O and (lO := len(self.O[0])):
            NO = self._NO[0][self._fold_mutable(min(lpadN, lpadO))] + self._NO[1] * min(len(padN), lpadO := len(padO))
            SO = self._SO[0][self._fold_mutable(min(lpadS, lpadO))] + self._SO[1] * min(len(padS), lpadO)
            if lpadN:
                def cascade():
                    return padO[nxt_i:]
            else:
                def cascade():
                    return self._N[1] * (lpadO - nxt_i)
            try:
                for i in range(m := max(lN, lO)):
                    nxt_i = i + 1
                    neg_i = -nxt_i
                    self.N[neg_i] += (padN[i] * i) + NO[i]
                    self.O.insert(0, _cas := cascade())
                    if not _cas:
                        _r = nxt_i
                        for _i in range(_r, m):
                            _ni = -(_i + 1)
                            self.N[_ni] += (padN[_i] * _r)
                            self.O.insert(0, EscString())
                        break
            except IndexError:
                pass
            if lpadS:
                def cascade():
                    return padO[nxt_i:]
            else:
                def cascade():
                    return self._S[1] * (lpadO - nxt_i)
            try:
                for i in range(m := max(lS, lO)):
                    nxt_i = i + 1
                    self.S[i] += (padS[i] * i) + SO[i]
                    self.O.append(_cas := cascade())
                    if not _cas:
                        _r = nxt_i
                        for _i in range(_r, m):
                            self.S[_i] += (padS[_i] * _r)
                            self.O.append(EscString())
                        break
            except IndexError:
                pass
        else:
            self.O.extend(EscString() for _ in range(lN + lS))
            lO = 0

        self.expanse_N = lN
        self.expanse_O = lO
        self.expanse_S = lS
        self.expanse_E = lE

    def __repr__(self) -> str:
        s = ""
        ii = 0
        for i in range(len(self.N)):
            s += self.E[i] + self.N[i] + self.O[i] + '\n'
            ii += 1
        for e, o in zip(self.E[ii:(-len(self.S) or None)], self.O[ii:(-len(self.S) or None)]):
            s += e + (' ' * self.widget_size[0]) + o + '\n'
            ii += 1
        for _i in range(len(self.S)):
            s += self.E[_i + ii] + self.S[_i] + self.O[_i + ii] + '\n'
        return s


# frame = FramePadding(
#     N="nŋN", O="oøO", S=("sſS", "$"), E=("e€E", "·"),
#     NO="¹1I", SO="²2U", SE=("³3M", "/"), NE="⁴4K",
#     widget_orient="NO",
#     mutable="in",
#     fold_mutable="in"
# )
# frame.settings()
# frame.resize(widget_size=(10, 3), cell_size=(25, 11))
# # ·········KNNNNNNNNNNNNNNI
# # ·········E4ŋŋŋŋŋŋŋŋŋŋŋŋ1O
# # ·········E€⁴nnnnnnnnnn¹øO
# # ·········E€e          oøO
# # ·········E€e          oøO
# # ·········E€e          oøO
# # ·········E€³ssssssssss²øO
# # ·········E3ſſſſſſſſſſſſ2O
# # ·········MSSSSSSSSSSSSSSU
# # ········/$$$$$$$$$$$$$$$$
# # ·······/$$$$$$$$$$$$$$$$$
# frame.resize(widget_size=(10, 3), cell_size=(15, 8))
# # EKŋŋŋŋŋŋŋŋŋŋŋŋI
# # E€4nnnnnnnnnn1ø
# # E€e          oø
# # E€e          oø
# # E€e          oø
# # E€³ssssssssss2ø
# # E3ſſſſſſſſſſſſU
# # MSSSSSSSSSSSSSS
