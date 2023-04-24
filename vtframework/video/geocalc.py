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

from typing import overload, Callable, Literal


class GeoCalculator:
    """
    The object is passed per axis to cells for calculation of their size.

    The basic calculation can be defined in different ways:

        - `base_spec`: ``int``
            If an integer is passed, it will be returned unchanged when the calculation is retrieved.

        - `base_spec`: ``float``
            A calculation of the size as a percentage of the total size passed in the calculation can be specified
            via floating numbers (``0.325`` == 32,5 %; ``1.0`` == 100 %).
            
            Additional parameterization of the percentage calculation are:
                - `perc_spec_range_rule`: ``range``
                    This can be used to adjust the calculated result to a specific range.
                    If the calculated value is greater than or equal to the stop value, the (stop value - 1) is
                    returned; if a start value is defined and the calculated value is smaller, the start value is
                    returned; if a step value is defined, the value is rounded down to the next lower step if the step
                    value is negative, otherwise to the next higher step. If the rule is combined with
                    `perc_spec_adjustment`, the order of the parameterization represents the order
                    of the working steps.

                - `perc_spec_adjustment`: ``int``
                    This adjustment is added to the calculated result. If the rule is combined with
                    `perc_spec_range_rule`, the order of the parameterization represents the order
                    of the working steps.

                - `perc_spec_round`: ``bool``
                    Specifies whether the calculated fraction is to be rounded true or rounded down.
            

        - `base_spec`: ``None``
            If ``None`` is passed, the total size passed is returned during the calculation.

        - `base_spec`: ``Callable[[int], int]``
            Own functions for the calculation can be passed as executable object, this receives the total size
            during the call and must return the calculated size.

    After the basic calculation is completed, the result is compared with the value of the remaining space.
    The algorithm can be optionally created by conditions and actions in a string or strings in a tuple.

    Available conditions/statements are:
        - ``"if val > remain"``
        - ``"if val < remain"``
        - ``"if val == remain"``
        - ``"if remain <= 0"``
        - ``"always"``

    Available actions are:
        - ``"use remain"``
        - ``"set 0"``
        - ``"use val"``

    If the code is passed summarized in a string, condition-action pairs must be written separated by colon,
    condition and action are also separated by colon.

    A more extensive algorithm can be passed through a callable object.
    The object receives the calculated size and the size of the remaining space when called and must return a
    numerical value.

    The order of querying GeoCalculator's of an axis is defined by the priority list in the grid.

    Tip: Instead of trying to divide the entire size in percentages, parameterize the last GeoCalculator in the
    priority list as follows:

    >>> GeoCalculator(None, comp_remain="always:use remain")
    """

    # :    x  |      (%, round up) |       (%, round up, range, adj) |       (%, round up, adj, range) |       (%, round up, adj) |       (%, round up, range)  |          size -> x   | 100%
    spec: int | tuple[float, float] | tuple[float, float, range, int] | tuple[float, float, int, range] | tuple[float, float, int] | tuple[float, float, range] | Callable[[int], int] | None
    sizing: Callable[[int], int]
    comp_remain: tuple[Callable[[int, int], int | None], ...]
    size: int

    __grid_char_range__: tuple[int, int]
    __axis_index__: int

    @overload
    def __init__(self,
                 base_spec: int | float | Callable[[int], int] | None,
                 /, *,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] = None
                 ):
        ...

    @overload
    def __init__(self,
                 base_spec: float,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] = None
                 ):
        ...

    @overload
    def __init__(self,
                 base_spec: float,
                 perc_spec_range_rule: range,
                 perc_spec_adjustment: int,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] = None
                 ):
        ...

    @overload
    def __init__(self,
                 base_spec: float,
                 perc_spec_adjustment: int,
                 perc_spec_range_rule: range,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] = None
                 ):
        ...

    @overload
    def __init__(self,
                 base_spec: float,
                 perc_spec_range_rule: range,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] = None
                 ):
        ...

    @overload
    def __init__(self,
                 base_spec: float,
                 perc_spec_adjustment: int,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] = None
                 ):
        ...

    def __init__(self,
                 *args,
                 **kwargs
                 ):
        self.settings(*args, **dict(perc_spec_round=False, comp_remain=None,) | kwargs)

    @overload
    def settings(self,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] | None = ...
                 ):
        ...
    
    @overload
    def settings(self,
                 base_spec: int | float | Callable[[int], int] | None,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] | None = ...
                 ):
        ...

    @overload
    def settings(self,
                 base_spec: float,
                 perc_spec_range_rule: range,
                 perc_spec_adjustment: int,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] | None = ...
                 ):
        ...

    @overload
    def settings(self,
                 base_spec: float,
                 perc_spec_adjustment: int,
                 perc_spec_range_rule: range,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] | None = ...
                 ):
        ...

    @overload
    def settings(self,
                 base_spec: float,
                 perc_spec_range_rule: range,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] | None = ...
                 ):
        ...

    @overload
    def settings(self,
                 base_spec: float,
                 perc_spec_adjustment: int,
                 /, *,
                 perc_spec_round: bool = False,
                 comp_remain: Callable[[int, int], int] | tuple[str | Literal[
                     "if val > remain",
                     "if val < remain",
                     "if val == remain",
                     "if remain <= 0",
                     "always",
                     "use remain",
                     "set 0",
                     "use val"
                 ], ...] | str | Literal["condition:action:condition:action..."] | None = ...
                 ):
        ...

    def settings(self, *args, **kwargs) -> None:
        """
        Change the parameterization of the :class:`GeoCalculator`.
        """
        try:
            comp_remain = kwargs.pop('comp_remain')
        except KeyError:
            if not hasattr(self, 'comp_remain'):
                self.comp_remain = ((lambda x, r: x),)
        else:
            if callable(comp_remain):
                self.comp_remain = (comp_remain,)
            elif comp_remain is None:
                self.comp_remain = ((lambda x, r: x),)
            else:
                comp_remain: tuple | str
                if isinstance(comp_remain, str):
                    comp_remain = tuple(s.strip() for s in comp_remain.split(":"))
                try:
                    i = comp_remain.index("if remain <= 0")
                    comp_remain = comp_remain[i:i + 2] + comp_remain[:i] + comp_remain[i + 2:]
                except ValueError:
                    pass
                func = {
                    "always": lambda x, r: True,
                    "if val > remain": lambda x, r: x > r,
                    "if val < remain": lambda x, r: x < r,
                    "if val == remain": lambda x, r: x == r,
                    "if remain <= 0": lambda x, r: r <= 0,
                    "use remain": lambda x, r: r,
                    "set 0": lambda x, r: 0,
                    "use val": lambda x, r: x
                }
                try:
                    funcs = tuple(func[f] for f in comp_remain)
                except KeyError as e:
                    raise KeyError(f"Unknown comparison rule {e} ")
                self.comp_remain = tuple(lambda x, r: (funcs[i + 1](x, r) if funcs[i](x, r) else None) for i in range(0, len(comp_remain), 2))
        if args:
            spec = args[0]
            
            if spec is None:
                self.spec = spec

                def sizing(_size):
                    return _size

            elif callable(spec):
                self.spec = spec

                sizing = spec

            elif isinstance(spec, int):
                self.spec = spec

                def sizing(_size):
                    return spec
                
            else:
                _round = 0
                try:
                    if kwargs.pop('perc_spec_round'):
                        _round = .5
                except KeyError:
                    try:
                        if isinstance(self.spec, tuple):
                            _round = self.spec[1]
                    except AttributeError:
                        pass

                largs = len(args)
                if largs == 1:
                    self.spec = (spec, _round)

                    def sizing(_size):
                        return int(_size * spec + _round)
                elif largs == 2 and isinstance(args[1], int):
                    self.spec = (spec, _round, args[1])

                    def sizing(_size):
                        return int(_size * spec + _round + args[1])
                else:
                    if largs == 3:
                        self.spec = (spec, _round, args[1], args[2])
                        if isinstance(args[1], int):
                            # tuple[float, int, range]
                            perc, add_before_rancheck, ran = args
                            add_after_rancheck = 0
                        else:
                            # tuple[float, range, int]
                            perc, ran, add_after_rancheck = args
                            add_before_rancheck = 0
                    else:
                        # tuple[float, range]
                        self.spec = (spec, _round, args[1])
                        perc, ran = args
                        add_before_rancheck = add_after_rancheck = 0

                    if ran.step > 0:
                        add_step = ran.step
                    else:
                        add_step = 0
                    abs_step = abs(ran.step)

                    def sizing(_size):
                        if (_val := (int(_size * perc + _round + add_before_rancheck))) not in ran:
                            if _val >= ran.stop:
                                return (ran.stop - 1) + add_after_rancheck
                            if ran.start is not None and _val < ran.start:
                                return ran.start + add_after_rancheck
                            if m_step := _val % abs_step:
                                _add_step = add_step
                            else:
                                _add_step = 0
                            return (_val - m_step) + add_after_rancheck + _add_step
                        return _val + add_after_rancheck

            self.sizing = sizing

    def __call__(self, _size: int, _remain: int) -> int:
        size = self.sizing(_size)
        for comp in self.comp_remain:
            if (_size := comp(size, _remain)) is not None:
                size = _size
                break
        self.size = size
        return self.size

    def __int__(self) -> int:
        return self.size
