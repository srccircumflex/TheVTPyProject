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
from typing import Type
from re import search


class Char(str):
    """
    The base class for characters.

    Derivatives:
        - :class:`ASCII`
        - :class:`UTF8`
        - :class:`Pasted`
    """

    @property
    def __vtdtid__(self):
        return 0

    @__vtdtid__.setter
    def __vtdtid__(self, v):
        raise AttributeError("__vtdtid__ is not settable")

    @__vtdtid__.deleter
    def __vtdtid__(self):
        raise AttributeError("__vtdtid__ is not deletable")

    def __new__(cls, _chr: str):
        return str.__new__(cls, _chr)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({super().__repr__()})>"

    @staticmethod
    def eval(x: str) -> Char:
        """Create a :class:`Char` instance from a representative sting of a :class:`Char` instance.

        :raise ValueError(exception): on errors with the original exception as argument."""
        try:
            return eval(x[1:-1])
        except Exception as e:
            raise ValueError(e)


class ASCII(Char):
    """
    ASCII Character (Range 0x21 - 0x7e)

    Derivatives:
        - :class:`Space`
    """

    def __new__(cls, _chr: str) -> ASCII:
        return str.__new__(cls, _chr)


class UTF8(Char):
    """
    UTF8 Sequence (Sequence start in range 0xc2 - 0xf4)
    """

    def __new__(cls, _chr: str) -> UTF8:
        return str.__new__(cls, _chr)


class Space(ASCII):
    r"""
    - ``0x09`` : Tab -> "\\t"
    - ``0x0a`` : Linefeed -> "\\n"
    - ``0x0d`` : Return -> "\\n"
    - ``0x20`` : Space -> " "

    Note: replaces "\\r" to "\\n"
    """
    def __new__(cls, _chr: str) -> Space:
        return str.__new__(cls, _chr.replace('\r', '\n'))


class Pasted(Char):
    """
    Pasted content when bracketed paste mode is active.

    Activated by:
        - [CSI ? 2004 h]    : :class:`DECPrivateMode`.high(2004)

    ****

    # Resources:
     ; `xterm/Bracketed-Paste-Mode`_
     : `xterm/CSI/DECPM/Bracketed-Paste-Mode`_

    .. _`xterm/Bracketed-Paste-Mode`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Bracketed-Paste-Mode
    .. _`xterm/CSI/DECPM/Bracketed-Paste-Mode`: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-%5F-ordered-by-the-final-character-lparen-s-rparen%3ACSI-%3F-Pm-h%3APs-%3D-2-0-0-4.1F7D
    """

    def __new__(cls, _seqs: str) -> Pasted:
        return str.__new__(cls, _seqs)


def Eval(x: str) -> Char | Type[Char]:
    """Return a :class:`Char` instance or type from a representative sting.

    :raise ValueError(exception): on errors with the original exception as argument."""
    try:
        if x.startswith('<class '):  # Type repr
            return eval(search("(?<=\\.)\\w+(?='>$)", x).group())
        else:
            return Char.eval(x)
    except Exception as e:
        raise ValueError(e)
