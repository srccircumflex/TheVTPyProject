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
from typing import Generator, NamedTuple, Callable, Any, overload, TextIO
from re import search, compile
from sys import stdout

try:
    from .c1ctrl import FsFpnF, Fe, UnknownESC, ManualESC
    __4doc1 = FsFpnF
    __4doc2 = Fe
    __4doc3 = UnknownESC
    __4doc4 = ManualESC
except ImportError:
    pass


_PRINTF_RE = compile('(?<!%)(%(\\((\\w+)\\)|)([\\s+#0-]*)(\\d*)([bidouxXeEfFgGcrsa])|((%%)+))')


def _slicei(item: int | tuple | slice, _max: int) -> tuple[int, int]:
    """
    :raise IndexError: if _i is int (eq. m)
    :raise ValueError: fault indexing
    :raise AttributeError: slice with steps
    :raise EOFError: _T[slice] -> ""
    """
    try:
        if isinstance(item, int):
            start, stop = item, item + 1
            if start < 0:
                if (start := start + _max) < 0:
                    raise IndexError(f"{start=} !< {_max=}")
                stop = start + 1
            elif start >= _max:
                raise IndexError(f"{start=} !< {_max=}")
            return start, stop
        elif isinstance(item, tuple):
            start, stop = item
        elif isinstance(item, slice):
            if item.step:
                raise AttributeError(f"Steps not supported : {item}")
            start, stop = item.start, item.stop
        else:
            raise ValueError

        if not _max:
            raise EOFError
        elif start is not None:
            if start < 0:
                if (start := start + _max) < 0:
                    raise EOFError
            elif start >= _max:
                raise EOFError
        else:
            start = 0
        if stop is not None:
            if stop < 0:
                stop += _max
        else:
            stop = _max
        if stop <= start:
            raise EOFError

    except ValueError:
        raise ValueError(f"Invalid indexing : {item}")

    return start, stop


def _nfibidx(_ran: int) -> Generator[tuple[int, int]]:
    """:return: (0, 1), (1, 2), (2, 3) ..."""
    for _t in zip(range(_ran - 1), range(1, _ran)):
        yield _t


def _shiftidx(_idx: list) -> int:
    """[(2, 4), (4, 7), (7, 11), ...] -> [(0, 2), (2, 5), (5, 9), ...] -> returns: diff = 2"""
    diff = _idx[0][0]
    p = 0
    for i in range(len(_idx)):
        _idx[i] = (p, (p := _idx[i][1] - diff))
    return diff


class EscSegment(str):
    """
    Data type for escape sequences. Subclass of string.

    Structure: "<introducing escape sequence><printable string><terminating escape sequence>"

    The default ``EscSegment("string")`` initialization only provides for the creation of an EscSegment with the
    string field. Escape sequences can be assigned already with the creation via class methods with ``new`` -prefix.

    Unique features:
        - ``len(eseg)``
            returns the length of the printable string (excl. escape sequences).
        - ``int(eseg)``
            returns the length of the escape sequences.
        - ``abs(eseg)``
            returns the real data length (including escape sequences).
        - ``eseg + str | EscSegment | EscContainer``
            returns an :class:`EscContainer`.
        - ``eseg & str``
            appends to the printable string and returns a new EscSegment.
        - ``eseg << str``
            appends the intro escape sequence to `str` and returns a new EscSegment.
        - ``eseg >> str``
            appends to the outro escape sequence and returns a new EscSegment.
        - ``econt % eseg | econt2``
            considers the real length of ``eseg`` | ``econt2`` when formatting fstring arguments like `'%-4s'` or
            `'%+2s'` and extends the parameterization. So the entered parameterization corresponds to the final one
            after printing. Also supports any other fstring parameterization and argumentation, and behaves similarly for
            exceptions. Differently, SyntaxError is raised if a fstring flag or conversion for an EscSegment/EscContainer
            is not supported (Supported flags: `-` and `+` only; Supported conversion: `s` only).
        - ``eseg[0] | eseg[1:4] | eseg[(4, 7)]``
            relates to and is oriented to the string field.

    The base class for escape sequences.

    Derivatives:
        - :class:`FsFpnF`
        - :class:`Fe`
        - :class:`UnknownESC`
        - :class:`ManualESC`

    ****

    **Note:** The data type is fully implemented in Python, which combined with the complexity of its properties makes
    it a "heavy object". Especially frequently concatenation and slicing can slow down the program significantly.
    To reduce the computational cost of slicing or formatting, method ``assimilate()`` can be used for concatenation;
    this tries to merge the segments at the intersections and ignores irrelevant ones, minimizing the likelihood of a
    high number of segments (but also not recommended for concatenation of many diverse sequences, since it is more
    computationally intensive than ``__add__()``).
    Practically, its use should be avoided as far as possible.
    """
    intro: str
    string: str
    outro: str
    len: int
    esc_len: int

    @property
    def __vtdtid__(self):
        return 1

    @__vtdtid__.setter
    def __vtdtid__(self, v):
        raise AttributeError("__vtdtid__ is not settable")

    @__vtdtid__.deleter
    def __vtdtid__(self):
        raise AttributeError("__vtdtid__ is not deletable")

    __slots__ = ('intro', 'string', 'outro', 'len', 'esc_len')

    def __new__(cls, string: str) -> EscSegment:
        return cls.new(string=string)

    @classmethod
    def new(cls, intro: str = '', string: str = '', outro: str = '') -> EscSegment:
        """Creates a new EscSegment. Each field can be assigned."""
        new = str.__new__(cls, intro + string + outro)
        new.intro = str(intro)
        new.string = str(string)
        new.outro = str(outro)
        new.len = len(new.string)
        new.esc_len = len(new.intro) + len(new.outro)
        return new

    @classmethod
    def new_esc(cls, *params: str, string: str = '', outro: str = '') -> EscSegment:
        """Creates an escape sequence from `params` (puts ESC in front of it) and puts it into the intro field."""
        return cls.new(EscSegment.new_raw(*params), string, outro)

    @staticmethod
    def new_nul(*_, **__) -> EscSegment:
        """Creates an EscSegment with the values `('', '', '')`."""
        return EscSegment.new()

    @classmethod
    def new_pur(cls, esc: str = '', esc_string: str = '', term: str = '') -> EscSegment:
        """Intended for terminated string escapes. Ignores the length of the string."""
        new = str.__new__(cls, esc + esc_string + term)
        new.intro = str(esc)
        new.string = str(esc_string)
        new.outro = str(term)
        new.len = 0
        new.esc_len = len(new.intro) + len(new.string) + len(new.outro)
        new.new = new.new_pur
        return new

    @staticmethod
    def new_raw(*params: str) -> str:
        """Creates a new escape sequence (datatype str) from `params`. Prepends the ESC character."""
        return '\x1b' + str().join(params)

    def wrap(self, sufseq: str, preseq: str, *, inner: bool = False, cellular: bool = False) -> EscSegment:
        """
        Extends the intro and outro sequence depending on `inner`:

        wrap:
            -> EscSegment(sufseq + self.intro, self.string, self.outro + preseq)

        inner-wrap:
            -> EscSegment(self.intro + sufseq, self.string, preseq + self.outro)

        `cellular` is duck typing, takes effect only in :class:`EscContainer`. *
        """
        if inner:
            return self.new(self.intro + str(sufseq), self.string, str(preseq) + self.outro)
        return self.new(str(sufseq) + self.intro, self.string, self.outro + str(preseq))

    def _formatting(self,
                    *,
                    kw_args: dict[str, Any] = None,
                    callable_args: Callable[[], Any] = None,
                    _find_esc: bool = False,
                    _return_str: bool = False) -> str | EscSegment | tuple[str | EscSegment, bool]:
        """
        :raise SyntaxError(unsupported flag or conversion for EscSegment | EscContainer):
        :raise IndexError(by callable_args -> too few arguments):
        :raise TypeError(format requires or does not require a mapping):
        :raise TypeError(by printf (str.__mod__) -> conversion not supported):
        :raise KeyError(by printf (str.__mod__) -> dictionary assignment not found):
        """
        string = self.string
        hasesc = False

        def f_esc():
            nonlocal d, string
            string = string[:ms[0] + d] + ('%' * (_d := len(mg[-2]) // 2)) + string[ms[1] + d:]
            d -= _d

        def esc_format(esc: EscSegment) -> str:
            _f = mg[0]
            if mg[3] in ('-', '+'):
                _f = f'%{mg[3]}{0 if mg[4] == "" else int(mg[4]) + int(esc)}s'
            elif mg[3] != '':
                raise SyntaxError(f"unsupported flag for {esc.__repr__()} (supports `-' or `+' only)", f"got {repr(mg[3])}")
            elif mg[5] != 's':
                raise SyntaxError(f"unsupported conversion for {esc.__repr__()} (supports `s' only)", f"got {repr(mg[5])}")
            else:
                _f = '%s'
            return _f

        def inset(_f):
            nonlocal d, string
            string = string[:ms[0] + d] + _f + string[ms[1] + d:]
            d += len(_f) - len(mg[0])

        if _find_esc:
            if callable_args is not None:
                # iter_formatting_fe

                def formatting() -> str:
                    nonlocal hasesc
                    if mg[2]:
                        raise TypeError(f"format does not requires a mapping", f"got {repr(mg[0])}")
                    _f = mg[0]
                    if isinstance(arg := callable_args(), (EscSegment, EscContainer)):
                        hasesc = hasesc or arg.has_escape()
                        _f = esc_format(arg)
                    return _f % arg
            else:
                # dict_formatting_fe

                def formatting() -> str:
                    nonlocal hasesc
                    if not mg[2]:
                        raise TypeError(f"format requires a mapping", f"got {repr(mg[0])}")
                    _f = mg[0]
                    if isinstance(arg := kw_args[mg[2]], (EscSegment, EscContainer)):
                        hasesc = hasesc or arg.has_escape()
                        _f = esc_format(arg)
                    else:
                        arg = kw_args
                    return _f % arg

            if _return_str:
                def rval():
                    return self.intro + string + self.outro, hasesc
            else:
                def rval():
                    return self.new(self.intro, string, self.outro), hasesc
        else:
            if callable_args is not None:
                # iter_formatting

                def formatting() -> str:
                    if mg[2]:
                        raise TypeError(f"format does not requires a mapping", f"got {repr(mg[0])}")
                    _f = mg[0]
                    if isinstance(arg := callable_args(), (EscSegment, EscContainer)):
                        _f = esc_format(arg)
                    return _f % arg
            else:
                # dict_formatting

                def formatting() -> str:
                    if not mg[2]:
                        raise TypeError(f"format requires a mapping", f"got {repr(mg[0])}")
                    _f = mg[0]
                    if isinstance(arg := kw_args[mg[2]], (EscSegment, EscContainer)):
                        _f = esc_format(arg)
                    else:
                        arg = kw_args
                    return _f % arg

            if _return_str:
                def rval():
                    return self.intro + string + self.outro
            else:
                def rval():
                    return self.new(self.intro, string, self.outro)

        d = 0
        s = 0
        while m := search(_PRINTF_RE, self.string[s:]):
            mg = m.groups()
            _ms = m.span()
            ms = _ms[0] + s, _ms[1] + s
            s += _ms[1]
            if mg[-1]:
                f_esc()
                continue
            inset(formatting())

        return rval()

    @overload
    def formatting(self, next_arg: Callable[[], EscContainer | EscSegment | Any | str],
                   /, *, as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscSegment:
        ...

    @overload
    def formatting(self, kw_args: dict[str, EscContainer | EscSegment | Any | str],
                   /, *, as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscSegment:
        ...

    @overload
    def formatting(self, arg_tuple: tuple[EscContainer | EscSegment | Any | str],
                   /, *, as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscSegment:
        ...

    def formatting(self, args: dict[str, EscContainer | EscSegment | Any | str] |
                               Callable[[], EscContainer | EscSegment | Any | str] |
                               tuple[EscContainer | EscSegment | Any | str],
                   /, *,
                   as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscSegment:
        """
        Format fstring (``%``) patterns in EscSegment. The arguments can be formulated as dict, tuple, or callable.

        When formatting pattern like `"%-4s"` or `"%+2s"` with EscSegment/EscContainer arguments, their real length is
        considered and the format parameters are extended with the length of the escape sequences.
        The entered parameterization thus corresponds to the value after printing. Also supports any other fstring
        parameterization and argumentation. SyntaxError is raised if a fstring flag or conversion for an
        EscSegment/EscContainer is not supported (Supported flags: `-` and `+` only; Supported conversion: `s` only).

        Differing from the formatting by the modulo operator (``%``), the complete formatting of the arguments is not
        checked and if there are too few arguments the IndexError is not converted to a TypeError.

        Additionally, the return value can be optionally defined by one of the keyword arguments
            `as_str`
                Creates an ordinary string. (minimally less complex than ``%``)
            `as_str_if_esc`
                Creates an ordinal string from the occurrence of EscSegment/EscContainer parameterization.
                (More complex than `as_str` but can be minimally less complex than ``%``).

        **Note:** If EscSegment/EscContainer is formatted as an argument, its escape fields merge into the string field.
        Thus, in case of the presence of escape sequences, the EscSegment/EscContainer loses its typical properties.
        (The parameter extension property is created for a final operation).

        :raise SyntaxError(unsupported flag or conversion for EscSegment | EscContainer):
        :raise IndexError(by callable_args -> too few arguments):
        :raise TypeError(format requires or does not require a mapping):
        :raise TypeError(by printf (str.__mod__) -> conversion not supported):
        :raise KeyError(by printf (str.__mod__) -> dictionary assignment not found):
        """
        if as_str:
            if isinstance(args, dict):
                return self._formatting(kw_args=args, _return_str=True)
            elif callable(args):
                return self._formatting(callable_args=args, _return_str=True)
            else:
                args = list(args)
                return self._formatting(callable_args=lambda: args.pop(0), _return_str=True)
        elif as_str_if_esc:
            if isinstance(args, dict):
                s, hasesc = self._formatting(kw_args=args, _find_esc=True)
                if hasesc:
                    s = str(s)
                return s
            elif callable(args):
                s, hasesc = self._formatting(callable_args=args, _find_esc=True)
                if hasesc:
                    s = str(s)
                return s
            else:
                args = list(args)
                s, hasesc = self._formatting(callable_args=lambda: args.pop(0), _find_esc=True)
                if hasesc:
                    s = str(s)
                return s
        else:
            if isinstance(args, dict):
                return self._formatting(kw_args=args)
            elif callable(args):
                return self._formatting(callable_args=args)
            else:
                args = list(args)
                return self._formatting(callable_args=lambda: args.pop(0))

    def printable(self) -> str:
        """Return the string field."""
        return self.string

    def out(self) -> TextIO:
        """Write the sequence to stdout, then flush stdout.

        :return: stdout"""
        stdout.write(self)
        stdout.flush()
        return stdout

    def n_segments(self) -> int:
        """Return the number of segments in the container (Duck typing method; returns 1)."""
        return 1

    def has_escape(self) -> bool:
        """Return whether an escape sequence field is assigned."""
        return bool(self.intro or self.outro)

    def endswith_esc(self) -> bool:
        """Return whether an escape sequence field is assigned in the last segment in the container.
        (Duck typing method; alias to `has_escape()`)."""
        return self.has_escape()

    def startswith_esc(self) -> bool:
        """Return whether an escape sequence field is assigned in the first segment in the container.
        (Duck typing method; alias to `has_escape()`)."""
        return self.has_escape()

    def assimilate_string(self, __o: str | EscContainer | EscSegment) -> EscSegment | EscContainer:
        """Gradation of ``assimilate()``.

        Merge the segments at the intersection points if both parts do not contain any escape sequences.
        Otherwise, append the segment."""
        if (t := type(__o)) == str:
            if self.has_escape():
                return self.__add__(__o)
            else:
                return self.__and__(__o)
        elif isinstance(__o, EscSegment):
            if self.has_escape() or __o.has_escape():
                return self.__add__(__o)
            else:
                return self.__and__(__o.string)
        elif isinstance(__o, EscContainer):
            return EscContainer(self).assimilate_string(__o)
        else:
            raise TypeError(f'can only concatenate str | EscContainer | EscSegment (not type "{t}") to EscSegment')

    def assimilate(self, __o: str | EscContainer | EscSegment) -> EscSegment | EscContainer:
        """Merge the segments at the intersection points if both parts do not contain any escape sequences or if
        they are identical. Otherwise, append the segment."""
        if not __o:
            return self
        if (t := type(__o)) == str:
            if self.outro:
                return self.__add__(__o)
            else:
                return self.__and__(__o)
        elif isinstance(__o, EscSegment):
            if self.outro or __o.intro:
                if self.intro == __o.intro and self.outro == __o.outro:
                    return self.__and__(__o.string)
                else:
                    return self.__add__(__o)
            else:
                return self.__and__(__o.string).__rshift__(__o.outro)
        elif isinstance(__o, EscContainer):
            return EscContainer(self).assimilate(__o)
        else:
            raise TypeError(f'can only concatenate str | EscContainer | EscSegment (not type "{t}") to EscSegment')

    def __mod__(
            self,
            args: EscContainer | EscSegment | Any | str |
                  tuple[EscContainer | EscSegment | Any | str, ...] |
                  dict[str, EscContainer | EscSegment | Any | str]
    ) -> EscSegment:
        """
        Format fstring (``%``) patterns in EscSegment. The arguments can be formulated as dict, tuple, or as a
        single.

        When formatting pattern like `"%-4s"` or `"%+2s"` with EscSegment/EscContainer arguments, their real length is
        considered and the format parameters are extended with the length of the escape sequences.
        The entered parameterization thus corresponds to the value after printing.

        Also supports any other fstring parameterization and argumentation, and behaves similarly for
        exceptions. Differently, SyntaxError is raised if a fstring flag or conversion for an EscSegment/EscContainer
        is not supported (Supported flags: `-` and `+` only; Supported conversion: `s` only).

        **Note:** If EscSegment/EscContainer is formatted as an argument, its escape fields merge into the string field.
        Thus, in case of the presence of escape sequences, the EscSegment/EscContainer loses its typical properties.
        (The parameter extension property is created for a final operation).

        :raise SyntaxError(unsupported flag or conversion for EscSegment | EscContainer):
        :raise TypeError(too many or too few arguments):
        :raise TypeError(format requires or does not require a mapping):
        :raise TypeError(by printf (str.__mod__) -> conversion not supported):
        :raise KeyError(by printf (str.__mod__) -> dictionary assignment not found):
        """
        if isinstance(args, dict):
            return self._formatting(kw_args=args)
        elif isinstance(args, tuple):
            args = list(args)
        else:
            args = [args]
        try:
            new = self._formatting(callable_args=lambda: args.pop(0))
        except IndexError:
            raise TypeError('not enough arguments to format')
        if args:
            raise TypeError('not all arguments converted during formatting')
        return new

    def __getitem__(self, item: int | slice | tuple[int, int]) -> EscSegment:
        """relates to and is oriented to the string field"""
        try:
            start, stop = _slicei(item, self.len)
            return self.new(self.intro, self.string[start:stop], self.outro)
        except EOFError:
            return self.new(self.intro, '', self.outro)

    def __len__(self) -> int:
        """returns the length of the printable string (excl. escape sequences)"""
        return self.len

    def __int__(self) -> int:
        """returns the length of the escape sequences"""
        return self.esc_len

    def __abs__(self) -> int:
        """returns the real data length (including escape sequences)"""
        return self.len + self.esc_len

    def __repr__(self) -> str:
        return "<%s (%r:%r:%r) l/el=%d:%d>" % (self.__class__.__name__, self.intro, self.string, self.outro,
                                               self.len, self.esc_len)

    def __add__(self, __o: str | EscSegment | EscContainer) -> EscContainer:
        """returns an :class:`EscContainer`"""
        return EscContainer(self) + __o

    def __and__(self, string: str) -> EscSegment:
        """appends to the printable string and returns a new EscSegment"""
        return self.new(self.intro, self.string + string, self.outro)

    def __lshift__(self, other: str) -> EscSegment:
        """appends the intro escape sequence to `str` and returns a new EscSegment"""
        return self.wrap(other, '')

    def __rshift__(self, other: str) -> EscSegment:
        """appends to the outro escape sequence and returns a new EscSegment"""
        return self.wrap('', other)

    def __bool__(self) -> bool:
        return bool(self.intro or self.string or self.outro)

    def __reduce__(self) -> tuple[Callable[[str, str, str], EscSegment], tuple[str, str, str]]:
        """pickler support"""
        return self.new, (self.intro, self.string, self.outro)


class EscSlice(NamedTuple):
    """
    Slice object for :class:`EscContainer`.

    Is in the first instance the rough area of the :class:`EscSegment`'s, only by ``exact()`` the exact slice is
    created.

    By ``make()`` and ``makeexact()`` the sliced EscContainer can be created analogous from it.
    """
    sequence_segments: list[EscSegment]
    print_index: list[tuple[int, int]]
    start: int | None
    stop: int | None

    def exact(self) -> EscSlice:
        if self.start is None and self.stop is None:
            return EscSlice(self.sequence_segments, self.print_index, None, None)
        seq = self.sequence_segments.copy()
        if not seq:
            return self
        idx = self.print_index.copy()
        start, stop = self.start, self.stop
        if len(seq) == 1:
            seq[0] = seq[0][start:stop]
            idx[0] = (0, len(seq[0]))
        else:
            seq[0] = seq[0][start:]
            if stop is not None:
                if stop := stop - idx[-1][1]:  # negative index
                    seq[-1] = seq[-1][:stop]
            diff = idx[0][1] - (l0 := len(seq[0]))
            _idx = [(0, l0)]
            _idx.extend((_idx[-1][1], idx[i][1] - diff) for i in range(1, len(idx) - 1))
            _idx.append((_idx[-1][1], _idx[-1][1] + len(seq[-1])))
            idx = _idx
        return EscSlice(seq, idx, None, None)

    def make(self) -> EscContainer:
        return EscContainer.fromslice(self)

    def makeexact(self) -> EscContainer:
        return EscContainer.fromslice(self.exact())


NUL_SLC = EscSlice([EscSegment('')], [(0, 0)], None, None)


def __ec_len__(ec: EscContainer) -> int:
    x = sum(len(seg) for seg in ec.sequence_segments)
    ec._len = lambda *_: x
    return x


def __ec_int__(ec: EscContainer) -> int:
    x = sum(int(seg) for seg in ec.sequence_segments)
    ec._int = lambda *_: x
    return x


def __ec_abs__(ec: EscContainer) -> int:
    x = int(ec) + len(ec)
    ec._abs = lambda *_: x
    return x


class EscContainer(str):
    """
    A container for :class:`EscSegment`'s. Subclass of string.

    Structure:
        sequence_segments
            ``[EscSegment(...), ...]``
        print_index
            ``[(0, print length), (previous segment print length, extended  print length), ...]``

    The default ``EscContainer(EscSegment(...))`` initialization expects the EscSegment as a parameter.
    **[ ! ] IS NOT TYPE CHECKED**. The class method `new` first creates an `EscSegment` and then creates
    `EscContainer` from it.

    Unique features:
        - ``len(econt)``
            returns the length of the printable string (excl. escape sequences).
        - ``int(econt)``
            returns the length of the escape sequences.
        - ``abs(econt)``
            returns the real data length (including escape sequences).
        - ``econt + str | EscSegment | EscContainer``
            returns an EscContainer.
        - ``econt << str``
            appends the first intro escape sequence to `str` and returns a new EscContainer.
        - ``econt >> str``
            appends to the last outro escape sequence and returns a new EscContainer.
        - ``econt % eseg | econt2``
            considers the real length of ``eseg`` | ``econt2`` when formatting fstring arguments like `'%-4s'` or
            `'%+2s'` and extends the parameterization. So the entered parameterization corresponds to the final one
            after printing. Also supports any other fstring parameterization and argumentation, and behaves similarly for
            exceptions. Differently, SyntaxError is raised if a fstring flag or conversion for an EscSegment/EscContainer
            is not supported (Supported flags: `-` and `+` only; Supported conversion: `s` only).
        - ``eseg[0] | eseg[1:4] | eseg[(4, 7)]``
            relates to and is oriented to the string field.
        - ``__iter__``
            returns: Generator[ tuple[ EscSegment, tuple[int, int](print index) ] ]

    ****

    **Note:** The data type is fully implemented in Python, which combined with the complexity of its properties makes
    it a "heavy object". Especially frequently concatenation and slicing can slow down the program significantly.
    To reduce the computational cost of slicing or formatting, method ``assimilate()`` can be used for concatenation;
    this tries to merge the segments at the intersections and ignores irrelevant ones, minimizing the likelihood of a
    high number of segments (but also not recommended for concatenation of many diverse sequences, since it is more
    computationally intensive than ``__add__()``).
    Practically, its use should be avoided as far as possible.
    """
    sequence_segments: list[EscSegment]  # lists mostly faster then tuples
    print_index: list[tuple[int, int]]
    _len: Callable[[EscContainer], int]
    _int: Callable[[EscContainer], int]
    _abs: Callable[[EscContainer], int]

    __slots__ = ('sequence_segments', 'print_index', '_len', '_int', '_abs')

    def __new__(cls, seg: EscSegment) -> EscContainer:
        new = str.__new__(cls, str(seg))
        new.sequence_segments = [seg]
        new.print_index = [(0, len(seg))]
        new._len = __ec_len__
        new._int = __ec_int__
        new._abs = __ec_abs__
        return new

    @classmethod
    def new(cls, intro: str = '', string: str = '', outro: str = '') -> EscContainer:
        """Create a new `EscSegment` and from it a new `EscContainer`."""
        seg = EscSegment.new(intro, string, outro)
        new = str.__new__(cls, str(seg))
        new.sequence_segments = [seg]
        new.print_index = [(0, len(seg))]
        new._len = __ec_len__
        new._int = __ec_int__
        new._abs = __ec_abs__
        return new

    def clean(self) -> EscContainer:
        """Removes rudimentary segments (inplace)."""
        _l = len(self.sequence_segments)
        _i = 0
        while _i < _l:
            if not self.sequence_segments[_i]:
                self.sequence_segments.pop(_i)
                self.print_index.pop(_i)
                _l -= 1
            else:
                _i += 1
        if not self.sequence_segments:
            self.sequence_segments = [EscSegment('')]
            self.print_index = [(0, 0)]
        return self

    def wrap(self, sufseq: str, preseq: str, *, inner: bool = False, cellular: bool = False) -> EscContainer:
        """
        Executes the wrap method on each segment if `cellular` is True.
        Otherwise, extends the intro sequence of the first ``EscSegment``
        and the outro sequence of the last ``EscSegment`` depending on `inner`:

        wrap:
            first_segment = sufseq + EscContainer{0}.intro

            last_segment = EscContainer{0}.outro + preseq

            -> EscContainer{first_segment, ..., last_segment}

        inner-wrap:
            first_segment = EscContainer{0}.intro + sufseq

            last_segment = preseq + EscContainer{0}.outro

            -> EscContainer{first_segment, ..., last_segment}
        """
        if len(self.sequence_segments) == 1:
            return self.fromattr([self.sequence_segments[0].wrap(sufseq, preseq, inner=inner)], self.print_index)
        elif cellular:
            return self.fromattr([seg.wrap(sufseq, preseq, inner=inner) for seg in self.sequence_segments],
                                 self.print_index)
        else:
            return self.fromattr([self.sequence_segments[0].wrap(sufseq, '', inner=inner)]
                                 + self.sequence_segments[1:-1]
                                 + [self.sequence_segments[-1].wrap('', preseq, inner=inner)],
                                 self.print_index)

    @overload
    def formatting(self, next_arg: Callable[[], EscContainer | EscSegment | Any | str],
                   /, *, as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscContainer:
        ...

    @overload
    def formatting(self, kw_args: dict[str, EscContainer | EscSegment | Any | str],
                   /, *, as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscContainer:
        ...

    @overload
    def formatting(self, arg_tuple: tuple[EscContainer | EscSegment | Any | str],
                   /, *, as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscContainer:
        ...

    def formatting(self, args: dict[str, EscContainer | EscSegment | Any | str] |
                               Callable[[], EscContainer | EscSegment | Any | str] |
                               tuple[EscContainer | EscSegment | Any | str],
                   /, *,
                   as_str: bool = False, as_str_if_esc: bool = False
                   ) -> str | EscContainer:
        """
        Format fstring (``%``) patterns in EscContainer. The arguments can be formulated as dict, tuple, or callable.

        When formatting pattern like `"%-4s"` or `"%+2s"` with EscSegment/EscContainer arguments, their real length is
        considered and the format parameters are extended with the length of the escape sequences.
        The entered parameterization thus corresponds to the value after printing. Also supports any other fstring
        parameterization and argumentation. SyntaxError is raised if a fstring flag or conversion for an
        EscSegment/EscContainer is not supported (Supported flags: `-` and `+` only; Supported conversion: `s` only).

        Differing from the formatting by the modulo operator (``%``), the complete formatting of the arguments is not
        checked and if there are too few arguments the IndexError is not converted to a TypeError.

        Additionally, the return value can be optionally defined by one of the keyword arguments
            `as_str`
                Creates an ordinary string. (minimally less complex than ``%``)
            `as_str_if_esc`
                Creates an ordinal string from the occurrence of EscSegment/EscContainer parameterization.
                (More complex than `as_str` but can be minimally less complex than ``%``).

        **Note:** If EscSegment/EscContainer is formatted as an argument, its escape fields merge into the string field.
        Thus, in case of the presence of escape sequences, the EscSegment/EscContainer loses its typical properties.
        (The parameter extension property is created for a final operation).

        :raise SyntaxError(unsupported flag or conversion for EscSegment | EscContainer):
        :raise IndexError(by callable_args -> too few arguments):
        :raise TypeError(format requires or does not require a mapping):
        :raise TypeError(by printf (str.__mod__) -> conversion not supported):
        :raise KeyError(by printf (str.__mod__) -> dictionary assignment not found):
        """
        seq = self.sequence_segments.copy()
        idx = self.print_index.copy()
        if as_str:
            if isinstance(args, dict):
                return str().join(s._formatting(kw_args=args, _return_str=True) for s in seq)
            elif isinstance(args, tuple):
                args = list(args)
            else:
                args = [args]
            return str().join(s._formatting(callable_args=lambda: args.pop(0), _return_str=True) for s in seq)
        elif as_str_if_esc:
            if isinstance(args, dict):
                s, hasesc = seq[0]._formatting(kw_args=args, _find_esc=True)
                if hasesc:
                    return str(s) + str().join(s._formatting(kw_args=args, _return_str=True) for s in seq[1:])
                else:
                    seq[0] = s
                    idx[0] = (0, len(seq[0]))
                for p, i in _nfibidx(len(seq)):
                    s, hasesc = seq[i]._formatting(kw_args=args, _find_esc=True)
                    seq[i] = s
                    if hasesc:
                        return (str().join(s for s in seq[:i + 1]) +
                                str().join(s._formatting(kw_args=args, _return_str=True) for s in seq[i + 1:]))
                    else:
                        idx[i] = (s := idx[p][1], s + len(seq[i]))
                return self.fromattr(seq, idx)
            elif isinstance(args, tuple):
                args = list(args)
            else:
                args = [args]
            s, hasesc = seq[0]._formatting(callable_args=lambda: args.pop(0), _find_esc=True)
            if hasesc:
                return str(s) + str().join(s._formatting(callable_args=lambda: args.pop(0), _return_str=True) for s in seq[1:])
            else:
                seq[0] = s
                idx[0] = (0, len(seq[0]))
            for p, i in _nfibidx(len(seq)):
                s, hasesc = seq[i]._formatting(callable_args=lambda: args.pop(0), _find_esc=True)
                seq[i] = s
                if hasesc:
                    return (str().join(s for s in seq[:i + 1]) +
                            str().join(s._formatting(callable_args=lambda: args.pop(0), _return_str=True) for s in seq[i + 1:]))
                else:
                    idx[i] = (s := idx[p][1], s + len(seq[i]))
            return self.fromattr(seq, idx)
        else:
            if isinstance(args, dict):
                seq[0] = seq[0]._formatting(kw_args=args)
                idx[0] = (0, len(seq[0]))
                for p, i in _nfibidx(len(seq)):
                    seq[i] = seq[i]._formatting(kw_args=args)
                    idx[i] = (s := idx[p][1], s + len(seq[i]))
                return self.fromattr(seq, idx)
            elif isinstance(args, tuple):
                args = list(args)
            else:
                args = [args]
            seq[0] = seq[0]._formatting(callable_args=lambda: args.pop(0))
            idx[0] = (0, len(seq[0]))
            for p, i in _nfibidx(len(seq)):
                seq[i] = seq[i]._formatting(callable_args=lambda: args.pop(0))
                idx[i] = (s := idx[p][1], s + len(seq[i]))
            return self.fromattr(seq, idx)

    @classmethod
    def more(cls, *i_s_o: tuple[str, str, str] | str | EscSegment) -> EscContainer:
        """Create a container from a sequence of

        ( "<escape intro filed>", "<string field>", "<escape outro field>" ) | "<string field>" | :class:`EscSegment`."""
        seq = []
        idx = []
        s = 0
        for seg in i_s_o:
            if isinstance(seg, str):
                if isinstance(seg, EscSegment):
                    seq.append(seg)
                else:
                    seq.append(seg := EscSegment(seg))
            else:
                seq.append(seg := EscSegment.new(*seg))
            idx.append((s, (s := len(seg))))
        return cls.fromattr(seq, idx)

    @classmethod
    def fromattr(cls, seq: list[EscSegment], idx: list[tuple[int, int]]) -> EscContainer:
        """Create a new `EscContainer` from a list of `EscSegments` and an index of lengths
        of the total printable characters in relation to `EscSegment` positions."""
        new = str.__new__(cls, ''.join(seq))
        if not seq:
            new.sequence_segments = [EscSegment('')]
            new.print_index = [(0, 0)]
        else:
            new.sequence_segments = seq
            new.print_index = idx
        new._len = __ec_len__
        new._int = __ec_int__
        new._abs = __ec_abs__
        return new

    @classmethod
    def fromslice(cls, slc: EscSlice) -> EscContainer:
        """Create a new `EscContainer` from a slice object."""
        return cls.fromattr(slc.sequence_segments, slc.print_index)

    @overload
    def slicing(self, *, regard_string: int | slice | tuple[int, int]) -> EscSlice:
        ...

    @overload
    def slicing(self, *, regard_segments: int | slice | tuple[int, int]) -> EscSlice:
        ...

    def slicing(
            self, *,
            regard_string: int | slice | tuple[int, int] = 0,
            regard_segments: int | slice | tuple[int, int] = None
    ) -> EscSlice:
        """Create a slice object with regard to the string or the sequence of :class:`EscSegment`'s."""

        if regard_segments is not None:
            try:
                start, stop = _slicei(regard_segments, len(self.sequence_segments))
            except EOFError:
                return NUL_SLC

            seq, idx = self.sequence_segments[start:], self.print_index[start:]

            stop -= start
            seq, idx = seq[:stop], idx[:stop]
            _shiftidx(idx)
            return EscSlice(seq, idx, 0, None)

        else:
            try:
                start, stop = _slicei(regard_string, maxi := len(self))
            except EOFError:
                return NUL_SLC

            def _binsearch(__val, __idx):
                __lidx = len(self.print_index)
                __midx = __lidx // 2
                __i = 0

                def __search():
                    nonlocal __i, __midx
                    if __val(__idx[(_i := __i + __midx)][1]):
                        if _midx := __midx // 2:
                            __midx = _midx
                            __search()
                    else:
                        __i = _i
                        if _midx := __midx // 2:
                            __midx = _midx
                            __search()

                try:
                    __search()
                except IndexError:
                    pass

                for __i in range(__i, __lidx):
                    if __val(__idx[__i][1]):
                        break

                return __i

            if start:
                i = _binsearch(start.__lt__, self.print_index)
            else:
                i = 0

            seq, idx = self.sequence_segments[i:], self.print_index[i:]

            if stop >= maxi:
                div = _shiftidx(idx)
                return EscSlice(seq, idx, start - div, None)

            i = _binsearch(stop.__le__, idx)

            seq, idx = seq[:(ii := i + 1)], idx[:ii]
            div = _shiftidx(idx)
            return EscSlice(seq, idx, start - div, stop - div)

    def printable(self) -> str:
        """Return the string fields."""
        return str().join([s.string for s in self.sequence_segments])

    def out(self) -> TextIO:
        """Write the sequence to stdout, then flush stdout.

        :return: stdout"""
        stdout.write(self)
        stdout.flush()
        return stdout

    def n_segments(self) -> int:
        """Return the number of segments in the container."""
        return len(self.print_index)

    def has_escape(self) -> bool:
        """Return whether an escape sequence field is assigned."""
        for seg in self.sequence_segments:
            if seg.has_escape():
                return True
        else:
            return False

    def endswith_esc(self) -> bool:
        """Return whether an escape sequence field is assigned in the last segment in the container."""
        return self.sequence_segments[-1].has_escape()

    def startswith_esc(self) -> bool:
        """Return whether an escape sequence field is assigned in the first segment in the container. """
        return self.sequence_segments[0].has_escape()

    def assimilate_string(self, __o: str | EscContainer | EscSegment) -> EscContainer:
        """Gradation of ``assimilate()``.

        Merge the segments at the intersection points if both parts do not contain any escape sequences.
        Otherwise, append the segment."""
        seq = self.sequence_segments.copy()
        idx = self.print_index.copy()
        if (t := type(__o)) == str:
            if self.endswith_esc():
                seq.append(EscSegment(__o))
                idx.append(((s := self.print_index[-1][1]), s + len(__o)))
            else:
                seq[-1] &= __o
                idx[-1] = (idx[-1][0], idx[-1][1] + len(__o.string))
        elif isinstance(__o, EscSegment):
            if self.endswith_esc() or __o.has_escape():
                seq.append(__o)
                idx.append(((s := self.print_index[-1][1]), s + len(__o)))
            else:
                seq[-1] &= __o.string
                idx[-1] = (idx[-1][0], idx[-1][1] + len(__o.string))
        elif isinstance(__o, EscContainer):
            if self.endswith_esc() or __o.startswith_esc():
                seq.extend(__o.sequence_segments)
                last_i = idx[-1][1]
                idx.extend((s + last_i, e + last_i) for s, e in __o.print_index)
            else:
                seq[-1] &= (string := __o.sequence_segments.pop(0).string)
                __o.print_index.pop(0)
                last_i = idx[-1][1]
                idx[-1] = (idx[-1][0], idx[-1][1] + len(string))
                idx.extend((s + last_i, e + last_i) for s, e in __o.print_index)
                seq.extend(__o.sequence_segments)
        else:
            raise TypeError(f'can only concatenate str | EscContainer | EscSegment (not type "{t}") to EscContainer')
        return self.fromattr(seq, idx)

    def assimilate(self, __o: str | EscContainer | EscSegment) -> EscContainer:
        """Merge the segments at the intersection points if both parts do not contain any escape sequences or if
        they are identical. Otherwise, append the segment."""
        if not __o:
            return self
        seq = self.sequence_segments.copy()
        idx = self.print_index.copy()
        if (t := type(__o)) == str:
            if self.sequence_segments[-1].outro:
                seq.append(EscSegment(__o))
                idx.append(((s := self.print_index[-1][1]), s + len(__o)))
            else:
                seq[-1] &= __o
                idx[-1] = (idx[-1][0], idx[-1][1] + len(__o.string))
        elif isinstance(__o, EscSegment):
            if self.sequence_segments[-1].outro or __o.intro:
                if self.sequence_segments[-1].intro == __o.intro and self.sequence_segments[-1].outro == __o.outro:
                    seq[-1] &= __o
                    idx[-1] = (idx[-1][0], idx[-1][1] + len(__o.string))
                else:
                    seq.append(__o)
                    idx.append(((s := self.print_index[-1][1]), s + len(__o)))
            else:
                seq[-1] = (seq[-1] & __o.string) >> __o.outro
                idx[-1] = (idx[-1][0], idx[-1][1] + len(__o.string))
        elif isinstance(__o, EscContainer):
            if self.sequence_segments[-1].outro or __o.sequence_segments[0].intro:
                if (
                        self.sequence_segments[-1].intro == __o.sequence_segments[0].intro
                        and self.sequence_segments[-1].outro == __o.sequence_segments[0].outro
                ):
                    __seg = __o.sequence_segments.pop(0)
                    seq[-1] &= __seg.string
                    __o.print_index.pop(0)
                    last_i = idx[-1][1]
                    idx[-1] = (idx[-1][0], idx[-1][1] + len(__seg.string))
                    idx.extend((s + last_i, e + last_i) for s, e in __o.print_index)
                    seq.extend(__o.sequence_segments)
                else:
                    seq.extend(__o.sequence_segments)
                    last_i = idx[-1][1]
                    idx.extend((s + last_i, e + last_i) for s, e in __o.print_index)
            else:
                __seg = __o.sequence_segments.pop(0)
                seq[-1] = (seq[-1] & __seg.string) >> __seg.outro
                __o.print_index.pop(0)
                last_i = idx[-1][1]
                idx[-1] = (idx[-1][0], idx[-1][1] + len(__seg.string))
                idx.extend((s + last_i, e + last_i) for s, e in __o.print_index)
                seq.extend(__o.sequence_segments)
        else:
            raise TypeError(f'can only concatenate str | EscContainer | EscSegment (not type "{t}") to EscContainer')
        return self.fromattr(seq, idx)

    def __getitem__(self, item: int | slice | tuple[int, int]) -> EscContainer:
        """relates to and is oriented to the string fields"""
        return self.fromslice(self.slicing(regard_string=item).exact())

    def __mod__(
            self,
            args: EscContainer | EscSegment | Any | str |
                  tuple[EscContainer | EscSegment | Any | str, ...] |
                  dict[str, EscContainer | EscSegment | Any | str]
    ) -> EscContainer:
        """
        Format fstring (``%``) patterns in EscContainer. The arguments can be formulated as dict, tuple, or as a
        single.

        When formatting pattern like `"%-4s"` or `"%+2s"` with EscSegment/EscContainer arguments, their real length is
        considered and the format parameters are extended with the length of the escape sequences.
        The entered parameterization thus corresponds to the value after printing.

        Also supports any other fstring parameterization and argumentation, and behaves similarly for
        exceptions. Differently, SyntaxError is raised if a fstring flag or conversion for an EscSegment/EscContainer
        is not supported (Supported flags: `-` and `+` only; Supported conversion: `s` only).

        **Note:** If EscSegment/EscContainer is formatted as an argument, its escape fields merge into the string field.
        Thus, in case of the presence of escape sequences, the EscSegment/EscContainer loses its typical properties.
        (The parameter extension property is created for a final operation).

        :raise SyntaxError(unsupported flag or conversion for EscSegment | EscContainer):
        :raise TypeError(too many or too few arguments):
        :raise TypeError(format requires or does not require a mapping):
        :raise TypeError(by printf (str.__mod__) -> conversion not supported):
        :raise KeyError(by printf (str.__mod__) -> dictionary assignment not found):
        """
        seq = self.sequence_segments.copy()
        idx = self.print_index.copy()
        if isinstance(args, dict):
            seq[0] = seq[0]._formatting(kw_args=args)
            idx[0] = (0, len(seq[0]))
            for p, i in _nfibidx(len(seq)):
                seq[i] = seq[i]._formatting(kw_args=args)
                idx[i] = (s := idx[p][1], s + len(seq[i]))
            return self.fromattr(seq, idx)
        elif isinstance(args, tuple):
            args = list(args)
        else:
            args = [args]
        try:
            seq[0] = seq[0]._formatting(callable_args=lambda: args.pop(0))
            idx[0] = (0, len(seq[0]))
            for p, i in _nfibidx(len(seq)):
                seq[i] = seq[i]._formatting(callable_args=lambda: args.pop(0))
                idx[i] = (s := idx[p][1], s + len(seq[i]))
        except IndexError:
            raise TypeError('not enough arguments to format')
        if args:
            raise TypeError('not all arguments converted during formatting')
        return self.fromattr(seq, idx)

    def __add__(self, __o: str | EscContainer | EscSegment) -> EscContainer:
        """extends the segment sequence and returns a new EscContainer"""
        seq = self.sequence_segments.copy()
        idx = self.print_index.copy()
        if (t := type(__o)) == str:
            seq.append(EscSegment(__o))
            idx.append(((s := self.print_index[-1][1]), s + len(__o)))
        elif isinstance(__o, EscSegment):
            seq.append(__o)
            idx.append(((s := self.print_index[-1][1]), s + len(__o)))
        elif isinstance(__o, EscContainer):
            last_i = idx[-1][1]
            seq.extend(__o.sequence_segments)
            idx.extend((s + last_i, e + last_i) for s, e in __o.print_index)
        else:
            raise TypeError(f'can only concatenate str | EscContainer | EscSegment (not type "{t}") to EscContainer')
        return self.fromattr(seq, idx)

    def __len__(self) -> int:
        """returns the length of the printable string (excl. escape sequences)"""
        return self._len(self)

    def __int__(self) -> int:
        """returns the length of the escape sequences"""
        return self._int(self)

    def __abs__(self) -> int:
        """returns the real data length (including escape sequences)"""
        return self._abs(self)

    def __iter__(self) -> Generator[tuple[EscSegment, tuple[int, int]]]:
        """returns: Generator[ tuple[ EscSegment, tuple[int, int](print index) ] ]"""
        return ((seg, idx) for seg, idx in zip(self.sequence_segments, self.print_index))

    def __repr__(self) -> str:
        return "<%s: [%s]>" % (
            self.__class__.__qualname__, str().join("%r, " % seg for seg in self.sequence_segments)[:-2]
        )

    def __lshift__(self, other: str) -> EscContainer:
        """appends the first intro escape sequence to `str` and returns a new EscContainer"""
        return self.wrap(other, '')

    def __rshift__(self, other: str) -> EscContainer:
        """appends to the last outro escape sequence and returns a new EscContainer"""
        return self.wrap('', other)

    def __bool__(self) -> bool:
        for seg in self.sequence_segments:
            if seg:
                return True
        else:
            return False
