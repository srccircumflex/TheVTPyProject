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

from typing import Callable, overload, Literal
from re import search, Pattern, compile
from functools import lru_cache

from vtframework.iodata.c1ctrl import CSI
from vtframework.iodata.esccontainer import EscSegment, EscContainer
from vtframework.iosys.gates import __STYLE_GATE__


class SGRParams(tuple):
    """
    Select Graphic Rendition - Parameters

    -> (param, ...)
    """

    def __new__(cls, *sgr: int) -> SGRParams:
        return tuple.__new__(cls, sgr)

    def __add__(self, x: tuple) -> SGRParams:
        return SGRParams(*self, *x)


class SGRSeqs(CSI):
    """
    Select Graphic Rendition - Sequence

    **[i] Windows / UNIX compatible**

    -> CSI param;... m

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/text-formatting`_
     ; `xterm/CSI/SGR`_

    .. _`microsoft/console-virtual-terminal-sequences/text-formatting`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-formatting
    .. _`xterm/CSI/SGR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Pm-m.1CA7
    """

    @__STYLE_GATE__(lambda cls, *args, **kwargs: cls.new_nul())
    def __new__(cls, *params: SGRParams) -> SGRSeqs:
        _params = ''
        if params:
            for __params in params:
                _params += str().join([f'{p};' for p in __params])
        return cls.new_csi(_params[:-1], 'm')


class SGRReset(CSI):
    """
    Reset the Graphic Rendition

    **[i] Windows / UNIX compatible**

    -> CSI m

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/text-formatting`_
     ; `xterm/CSI/SGR`_

    .. _`microsoft/console-virtual-terminal-sequences/text-formatting`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-formatting
    .. _`xterm/CSI/SGR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Pm-m.1CA7
    """

    @__STYLE_GATE__(lambda cls, *args, **kwargs: cls.new_nul())
    def __new__(cls) -> SGRReset:
        return cls.new('', '', cls.new_raw('[m'))


class SGRWrap(CSI):
    """
    Wraps the `string` in the SGR sequence of the `params` ( :class:`SGRParams` ) and the reset sequence
    ( :class:`SGRReset` ).

    "``CSI params m (SGR-Sequence) {`` `string` ``} CSI m(Graphic Rendition Reset)``"

    **[i] Windows / UNIX compatible**

    -> CSI param;... m { string } CSI m

    ****

    The keyword arguments `inner` and `cellular` are used when `string` is an :class:`EscSegment` or
    :class:`EscContainer` type.
    Depending on `inner`, the outermost escape sequences are then expanded:

        wrap:
            - EscSegment:
                EscSegment(sufseq + self.intro, self.string, self.outro + preseq)
            - EscContainer:
                first_segment = sufseq + EscContainer{0}.intro

                last_segment = EscContainer{0}.outro + preseq

                EscContainer{first_segment, ..., last_segment}

        inner-wrap:
            - EscSegment:
                EscSegment(self.intro + sufseq, self.string, preseq + self.outro)
            - EscContainer:
                first_segment = EscContainer{0}.intro + sufseq

                last_segment = preseq + EscContainer{0}.outro

                EscContainer{first_segment, ..., last_segment}

    If `cellular` is True and `string` is an ``EscContainer``, the wrap method is applied to each segment in `string`.

    ****

    ****

    # Resources:
     ; `microsoft/console-virtual-terminal-sequences/text-formatting`_
     ; `xterm/CSI/SGR`_

    .. _`microsoft/console-virtual-terminal-sequences/text-formatting`: https://docs.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences#text-formatting
    .. _`xterm/CSI/SGR`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-Pm-m.1CA7
    """

    def __new__(
            cls, string: str | EscSegment | EscContainer, *params: SGRParams,
            inner: bool = False, cellular: bool = False
    ) -> SGRWrap | EscSegment | EscContainer:
        if isinstance(string, (EscSegment, EscContainer)):
            return string.wrap(SGRSeqs(*params), SGRReset(), inner=inner, cellular=cellular)
        else:
            return cls.new(SGRSeqs(*params), string, SGRReset())

    def __mul__(self, n: int) -> SGRWrap:
        return self.new(self.intro, self.string * n, self.outro)


class RGBTablesPrism:
    """
    Static methods:
        - create_rgb_row
        - rgb_from_row
        - Prism.[...]
    """
    class Prism:

        @staticmethod
        def gray(r: int, g: int, b: int) -> bool: return r == g == b

        @staticmethod
        def light(r: int, g: int, b: int) -> bool: return r > 200 and g > 200 and b > 200

        @staticmethod
        def dark(r: int, g: int, b: int) -> bool: return r < 200 and g < 200 and b < 200

        @staticmethod
        def red(r: int, g: int, b: int) -> bool: return r > g and r > b

        @staticmethod
        def green(r: int, g: int, b: int) -> bool: return g > r and g > b

        @staticmethod
        def blue(r: int, g: int, b: int) -> bool: return b > g and b > r

        @staticmethod
        def cyan(r: int, g: int, b: int) -> bool: return (g == b and r < g) or (b > 100 and g > 100 and r < 32)

        @staticmethod
        def yellow(r: int, g: int, b: int) -> bool: return (r == g and b < r) or (r > 100 and g > 100 and b < 32)

        @staticmethod
        def magenta(r: int, g: int, b: int) -> bool: return (r == b and g < r) or (r > 100 and b > 100 and g < 32)

    pallet_folder: str
    src_file: str | None

    def __init__(self, pallet_folder: str, src_file: str = None):
        """Processing of rgb tables."""
        self.pallet_folder = pallet_folder
        self.src_file = src_file

    def _get_spectra_file_func(self) -> dict[str, tuple[str], Callable[[int, int, int], bool]]:
        """Composes an index from the attributes in Prism.

        :return: { spectrum-name : ( dst-path, comparison function ) }"""
        _spectra = {}
        for _spectrum in self.Prism.__dict__:
            if _spectrum.startswith('_'):
                continue
            _spectra.setdefault(_spectrum, (f"{self.pallet_folder}/{_spectrum}.txt", getattr(self.Prism, _spectrum)))
        return _spectra

    def flush(self) -> None:
        """Deletes the content of each spectrum file."""
        for _spectrum, item in self._get_spectra_file_func().items():
            with open(item[0], "w") as f:
                f.write("")

    @staticmethod
    def rgb_from_row_by_pattern_obj(row: bytes, _name_regex: Pattern[bytes] = compile(b"[\\w ]*\\w")) -> tuple[int, int, int, bytes] | None:
        """Returns the rgb values and the name from a table row.

        :return: ( r, g, b, name )"""
        if m := search(b'^\\s*(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(' + _name_regex.pattern + b')(#|$)', row, _name_regex.flags):
            return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)

    @staticmethod
    def rgb_from_row(row: bytes, _name_regex: bytes = b"[\\w ]*\\w") -> tuple[int, int, int, bytes] | None:
        """Returns the rgb values and the name from a table row.

        :return: ( r, g, b, name )"""
        if m := search(b'^\\s*(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(' + _name_regex + b')(#|$)', row):
            return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)

    @staticmethod
    def create_rgb_row(r: int, g: int, b: int, _id: bytes) -> bytes:
        """Creates and returns (r, g, b, _id) in table row format."""
        return b'%-3d %-3d %-3d    %s\n' % (r, g, b, _id)

    def refraction(self) -> None:
        """Distributes the values from the source table into files from partial spectra."""
        if not self.src_file:
            raise FileNotFoundError('no source file specified')
        _spectra_items = self._get_spectra_file_func().items()
        _spectra_files = {item[0]: open(item[0], "ab") for _, item in _spectra_items}
        with open(self.src_file, "rb") as f:
            while ln := f.readline():
                if rgb_id := self.rgb_from_row(ln):
                    r, g, b, _id = rgb_id
                    for _spectrum, item in _spectra_items:
                        if item[1](r, g, b):
                            _spectra_files[item[0]].write(self.create_rgb_row(r, g, b, _id))
                            print(1)
        for file in _spectra_files.values():
            file.close()

    def spectra_headers(self) -> list[str]:
        """Returns a list of the partial spectra."""
        return list(self._get_spectra_file_func())

    def spectrum(self, header: str) -> list[tuple[int, int, int, bytes]]:
        """Returns all values of a partial spectrum.

        :return: [ ( r, g, b, name ), ... ]"""
        _spectrum = []
        with open(self._get_spectra_file_func()[header][0], "rb") as f:
            while ln := f.readline():
                if rgb_id := self.rgb_from_row(ln):
                    _spectrum.append(rgb_id)
        return _spectrum


@lru_cache()
def _getname(color: str, src_table: str = search('.*[\\\\/]', __file__).group() + '_rgb/_X11color_table.txt') -> tuple[int, int, int, int]:
    """
    :return: (2, r, g, b)

    :raise LookupError(color):
    """
    color = color.encode()
    with open(src_table, "rb") as f:
        while ln := f.readline():
            if rgb_id := RGBTablesPrism.rgb_from_row(ln, color):
                r, g, b, _ = rgb_id
                return 2, r, g, b
        _getname.cache_clear()
        raise LookupError(color)


@lru_cache()
def _getrgb(r: int, g: int, b: int) -> tuple[int, int, int, int]:
    """
    :return: (2, r, g, b)

    :raise ValueError(r, g, b):
    """
    for c in (r, g, b):
        if c not in range(256):
            _getrgb.cache_clear()
            raise ValueError(r, g, b)
    return 2, r, g, b


@lru_cache()
def _get256(_256: int) -> tuple[int, int]:
    r"""
    :return: (5, _256)

    :raise ValueError(_256):
    """
    if _256 not in range(256):
        _get256.cache_clear()
        raise ValueError(str(_256))
    return 5, _256


class Fore:
    """Factory methods and default values for SGR foreground color parameters."""
    reset = default = SGRParams(39)

    black_rel = SGRParams(30)
    red_rel = SGRParams(31)
    green_rel = SGRParams(32)
    yellow_rel = SGRParams(33)
    blue_rel = SGRParams(34)
    magenta_rel = SGRParams(35)
    cyan_rel = SGRParams(36)
    white_rel = SGRParams(37)

    black = SGRParams(38, *_getrgb(0, 0, 0))
    red = SGRParams(38, *_getrgb(255, 0, 0))
    green = SGRParams(38, *_getrgb(0, 255, 0))
    yellow = SGRParams(38, *_getrgb(255, 255, 0))
    blue = SGRParams(38, *_getrgb(0, 0, 255))
    magenta = SGRParams(38, *_getrgb(255, 0, 255))
    cyan = SGRParams(38, *_getrgb(0, 255, 255))
    white = SGRParams(38, *_getrgb(255, 255, 255))

    __slots__ = ()

    @staticmethod
    def name(color: str) -> SGRParams:
        """
        Get the color from the name. (`Color table: ./_rgb/_X11color_table.txt`)

        :return: SGRParams(38, 2, r, g, b)

        :raise LookupError(color):
        """
        return SGRParams(38, *_getname(color))

    @staticmethod
    def b256(_256: int) -> SGRParams:
        """
        Get the color parameters from the base 256 table.

        :return: SGRParams(38, 5, _256)

        :raise ValueError(_256):
        """
        return SGRParams(38, *_get256(_256))

    @staticmethod
    def rgb(r: int, g: int, b: int) -> SGRParams:
        """
        Get the color from numeric rgb values.

        :return: SGRParams(38, 2, r, g, b)

        :raise ValueError(r, g, b):
        """
        return SGRParams(38, *_getrgb(r, g, b))

    @staticmethod
    def hex(x: str) -> SGRParams:
        """
        Get the color from a hex string. [ ! ] '#' not allowed.

        :return: SGRParams(38, 2, r, g, b)

        :raise ValueError(r, g, b):
        :raise ValueError(invalid literal):
        """
        r = int(x[:2], 16)
        g = int(x[2:4], 16)
        b = int(x[4:], 16)
        return SGRParams(38, *_getrgb(r, g, b))

    @staticmethod
    @overload
    def get(color_name: str, /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(hex_string: Literal["#rrggbb"], /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(b256: int, /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(r: int, g: int, b: int, /) -> SGRParams:
        ...

    @staticmethod
    def get(*args) -> SGRParams:
        """
        Get the color from a hex string, from numeric rgb values, from the name or from base 256.

        :param args: str(color name) | str(#rrggbb) | int(r), int(g), int(b) | int(base 256)

        :return: SGRParams(38, 2, r, g, b)  |  SGRParams(38, 5, _256)
        :raise LookupError(color name):
        :raise ValueError(r, g, b):
        :raise ValueError(base 256):
        :raise ValueError(invalid hex-literal):
        """
        if args:
            if isinstance(args[0], str):
                if args[0][0] == '#':
                    return Fore.hex(args[0][1:])
                else:
                    return Fore.name(args[0])
            elif len(args) == 3:
                return Fore.rgb(*args)
            else:
                return Fore.b256(args[0])


class Ground:
    """Factory methods and default values for SGR background color parameters."""
    reset = default = SGRParams(49)

    black_rel = SGRParams(40)
    red_rel = SGRParams(41)
    green_rel = SGRParams(42)
    yellow_rel = SGRParams(43)
    blue_rel = SGRParams(44)
    magenta_rel = SGRParams(45)
    cyan_rel = SGRParams(46)
    white_rel = SGRParams(47)

    black = SGRParams(48, *_getrgb(0, 0, 0))
    red = SGRParams(48, *_getrgb(255, 0, 0))
    green = SGRParams(48, *_getrgb(0, 255, 0))
    yellow = SGRParams(48, *_getrgb(255, 255, 0))
    blue = SGRParams(48, *_getrgb(0, 0, 255))
    magenta = SGRParams(48, *_getrgb(255, 0, 255))
    cyan = SGRParams(48, *_getrgb(0, 255, 255))
    white = SGRParams(48, *_getrgb(255, 255, 255))

    __slots__ = ()

    @staticmethod
    def name(color: str) -> SGRParams:
        """
        Get the color from the name. (`Color table: ./_rgb/_X11color_table.txt`)

        :return: SGRParams(48, 2, r, g, b)

        :raise LookupError(color):
        """
        return SGRParams(48, *_getname(color))

    @staticmethod
    def b256(_256: int) -> SGRParams:
        """
        Get the color parameters from the base 256 table.

        :return: SGRParams(48, 5, _256)

        :raise ValueError(_256):
        """
        return SGRParams(48, *_get256(_256))

    @staticmethod
    def rgb(r: int, g: int, b: int) -> SGRParams:
        """
        Get the color from numeric rgb values.

        :return: SGRParams(48, 2, r, g, b)

        :raise ValueError(r, g, b):
        """
        return SGRParams(48, *_getrgb(r, g, b))

    @staticmethod
    def hex(x: str) -> SGRParams:
        """
        Get the color from a hex string. [ ! ] '#' not allowed.

        :return: SGRParams(48, 2, r, g, b)

        :raise ValueError(r, g, b):
        :raise ValueError(invalid literal):
        """
        r = int(x[:2], 16)
        g = int(x[2:4], 16)
        b = int(x[4:], 16)
        return SGRParams(48, *_getrgb(r, g, b))

    @staticmethod
    @overload
    def get(color_name: str, /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(hex_string: Literal["#rrggbb"], /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(b256: int, /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(r: int, g: int, b: int, /) -> SGRParams:
        ...

    @staticmethod
    def get(*args) -> SGRParams:
        """
        Get the color from a hex string, from numeric rgb values, from the name or from base 256.

        :param args: str(color name) | str(#rrggbb) | int(r), int(g), int(b) | int(base 256)

        :return: SGRParams(48, 2, r, g, b)  |  SGRParams(48, 5, _256)
        :raise LookupError(color name):
        :raise ValueError(r, g, b):
        :raise ValueError(base 256):
        :raise ValueError(invalid hex-literal):
        """
        if args:
            if isinstance(args[0], str):
                if args[0][0] == '#':
                    return Fore.hex(args[0][1:])
                else:
                    return Fore.name(args[0])
            elif len(args) == 3:
                return Fore.rgb(*args)
            else:
                return Fore.b256(args[0])


def hasname(color: str) -> tuple[int, int, int, int] | None:
    """Returns ``(2, r, g, b)`` if `color` is contained in the X11 table, otherwise ``None``.

    (`Color table: ./_rgb/_X11color_table.txt`)"""
    try:
        return _getname(color)
    except LookupError:
        return


class _ColoredUnderline:
    """
    Emulator dependent support of colored underlines.
    
    Known emulators:
        - Kitty
        - VTE
        - Mintty
        - iTerm2
    """

    reset = default = SGRParams(59)

    black = SGRParams(58, *_getrgb(0, 0, 0))
    red = SGRParams(58, *_getrgb(255, 0, 0))
    green = SGRParams(58, *_getrgb(0, 255, 0))
    yellow = SGRParams(58, *_getrgb(255, 255, 0))
    blue = SGRParams(58, *_getrgb(0, 0, 255))
    magenta = SGRParams(58, *_getrgb(255, 0, 255))
    cyan = SGRParams(58, *_getrgb(0, 255, 255))
    white = SGRParams(58, *_getrgb(255, 255, 255))

    @staticmethod
    def name(color: str) -> SGRParams:
        """
        Get the color from the name. (`Color table: ./_rgb/_X11color_table.txt`)

        :return: SGRParams(58, 2, r, g, b)

        :raise LookupError(color):
        """
        return SGRParams(58, *_getname(color))

    @staticmethod
    def b256(_256: int) -> SGRParams:
        """
        Get the color parameters from the base 256 table.

        :return: SGRParams(58, 5, _256)

        :raise ValueError(_256):
        """
        return SGRParams(58, *_get256(_256))

    @staticmethod
    def rgb(r: int, g: int, b: int) -> SGRParams:
        """
        Get the color from numeric rgb values.

        :return: SGRParams(58, 2, r, g, b)

        :raise ValueError(r, g, b):
        """
        return SGRParams(58, *_getrgb(r, g, b))

    @staticmethod
    def hex(x: str) -> SGRParams:
        """
        Get the color from a hex string. [ ! ] '#' not allowed.

        :return: SGRParams(58, 2, r, g, b)

        :raise ValueError(r, g, b):
        :raise ValueError(invalid literal):
        """
        r = int(x[:2], 16)
        g = int(x[2:4], 16)
        b = int(x[4:], 16)
        return SGRParams(58, *_getrgb(r, g, b))

    @staticmethod
    @overload
    def get(color_name: str, /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(hex_string: Literal["#rrggbb"], /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(b256: int, /) -> SGRParams:
        ...

    @staticmethod
    @overload
    def get(r: int, g: int, b: int, /) -> SGRParams:
        ...

    @staticmethod
    def get(*args) -> SGRParams:
        """
        Get the color from a hex string, from numeric rgb values, from the name or from base 256.

        :param args: str(color name) | str(#rrggbb) | int(r), int(g), int(b) | int(base 256)

        :return: SGRParams(58, 2, r, g, b)  |  SGRParams(58, 5, _256)
        :raise LookupError(color name):
        :raise ValueError(r, g, b):
        :raise ValueError(base 256):
        :raise ValueError(invalid hex-literal):
        """
        if args:
            if isinstance(args[0], str):
                if args[0][0] == '#':
                    return Fore.hex(args[0][1:])
                else:
                    return Fore.name(args[0])
            elif len(args) == 3:
                return Fore.rgb(*args)
            else:
                return Fore.b256(args[0])


class StyleBasics:
    """Collection of basic SGR style parameters."""
    class SupportRare:
        """rarely supported."""
        italic = SGRParams(3)
        blink_rapid = SGRParams(6)
        hide = SGRParams(8)
        underline_doubly = SGRParams(21)

    purge_sgr = SGRParams(0)
    bold = SGRParams(1)
    dim = SGRParams(2)
    underline = SGRParams(4)
    blink = SGRParams(5)
    invert = SGRParams(7)
    strike = SGRParams(9)


RESET = StyleBasics.purge_sgr
BOLD = StyleBasics.bold
DIM = StyleBasics.dim
UNDERLINE = StyleBasics.underline
BLINK = StyleBasics.blink
INVERT = StyleBasics.invert
STRIKE = StyleBasics.strike


class StyleResets:
    """Collection of resets of the corresponding parameters."""
    not_bold = SGRParams(22)
    not_italic = SGRParams(23)
    not_blackletter = SGRParams(23)
    not_underlined = SGRParams(24)
    not_blink = SGRParams(25)
    not_invert = SGRParams(27)
    not_hide = SGRParams(28)
    not_strike = SGRParams(29)
    any = (
        not_bold +
        not_italic +
        not_blackletter +
        not_underlined +
        not_blink +
        not_invert +
        not_hide +
        not_strike
    )
    purge_sgr = StyleBasics.purge_sgr


class StyleFonts:
    """Collection of font parameters. Rarely supported in general."""
    class SupportRare:
        """supported even more rarely"""
        blackletter = SGRParams(20)

    reset = default = SGRParams(10)
    XI = SGRParams(11)
    XII = SGRParams(12)
    XIII = SGRParams(13)
    XIV = SGRParams(14)
    XV = SGRParams(15)
    XVI = SGRParams(16)
    XVII = SGRParams(17)
    XVIII = SGRParams(18)
    XIX = SGRParams(19)


class StyleSpecials:
    """Collection of special style parameters. Rarely supported in general."""
    class Ideogram:
        underline = SGRParams(60)
        underline_doubly = SGRParams(61)
        overline = SGRParams(62)
        overline_doubly = SGRParams(63)
        stress = SGRParams(64)
        reset = SGRParams(65)

    class SupportMintty:
        """Supported only by Mintty."""
        framed = SGRParams(51)
        encircled = SGRParams(52)
        not_framed = SGRParams(54)
        not_encircled = SGRParams(54)
        superscript = SGRParams(73)
        subscript = SGRParams(74)
        not_superscript = SGRParams(75)
        not_subscript = SGRParams(75)

    proportional_spacing = SGRParams(26)
    not_proportional_spacing = SGRParams(50)
    overlined = SGRParams(53)
    not_overlined = SGRParams(55)
