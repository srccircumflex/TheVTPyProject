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

from vtframework.textbuffer.display.highlighters import HighlightAdvanced
from vtframework.textbuffer.display.highlightertree import HighlighterBranch
from vtframework.iodata.sgr import Fore, BOLD
from re import compile, search

from vtframework.textbuffer.display.syntaxtree import SyntaxLeaf


def python_darkula(hl: HighlightAdvanced):
    if not isinstance(hl, HighlightAdvanced):
        return

    # trailing spaces
    # from vtframework.iodata.sgr import Ground
    # hl.globals.add(compile('\\s*$'), Ground.name('blue'))

    # comments
    cmt = HighlighterBranch(compile("#"), compile("$"),
                            node_sgr_params=Fore.hex('BEA4A4'))
    cmt.add_leaf(compile(".+"), Fore.hex('BEA4A4'))

    # keywords
    hl.root.add_leaf(compile(
        '(?<!\\w)('
        'and|as|assert|break|continue|del|elif|else|except|False|finally|'
        'for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|'
        'raise|return|True|try|while|with|yield|,'
        ')(?!\\w)'
    ), Fore.hex('cc7832') + BOLD)

    # numbers
    hl.root.add_leaf(compile(
        '(?<!\\w)'
        '\\d[ox]?\\d*'
        '(?!\\w)'
    ), Fore.hex('99D2FA'))

    # magic methods and -values
    hl.root.add_leaf(compile(
        '(?<!\\w)('
        '__delattr__|__dir__|__eq__|__format__|__getattribute__|'
        '__ge__|__gt__|__hash__|__init_subclass__|__init__|__le__|'
        '__lt__|__new__|__ne__|__reduce_ex__|__reduce__|'
        '__setattr__|__sizeof__|__str__|__subclasshook__|'
        '__slots__|__dict__|__doc__|__module__|__class__|'
        '__call__|__instancecheck__|__prepare__|__repr__|'
        '__subclasscheck__|__subclasses__|__abstractmethods__|'
        '__base__|__bases__|__basicsize__|__dictoffset__|__flags__|'
        '__itemsize__|__mro__|__name__|__qualname__|__text_signature__|__weakrefoffset__'
        ')(?!\\w)'
    ), Fore.hex('b200b2'))

    # def
    func = HighlighterBranch(compile('(?<!\\w)def '), compile('(?=\\()'), node_sgr_params=Fore.hex('cc7832') + BOLD)
    func.add_leaf(compile('.+'), Fore.hex('ffc66d'))

    # class
    class ClassReg(HighlighterBranch):

        def __init__(self, *args, **kwargs):
            HighlighterBranch.__init__(self,
                                       compile('(?<!\\w)class '),
                                       lambda m: '^(?=\\s{0,' + str(max(0, m.total_start)) + '}\\S)',
                                       node_sgr_params=Fore.hex('cc7832') + BOLD,
                                       multiline=True,
                                       activate=lambda r: r.snap())

        def stops(self, string: str, relstart: int) -> SyntaxLeaf | None:
            if not relstart:
                return super().stops(string, relstart)

    cls = ClassReg()
    cls.add_leaf(compile('(?<!\\w)self(?!\\w)'), Fore.hex('94558d'))
    mmeth = HighlighterBranch(compile('(?<!\\w)def (?=('
                                      '__delattr__|__dir__|__eq__|__format__|__getattribute__|'
                                      '__ge__|__gt__|__hash__|__init_subclass__|__init__|__le__|'
                                      '__lt__|__new__|__ne__|__reduce_ex__|__reduce__|__repr__|'
                                      '__setattr__|__sizeof__|__str__|__subclasshook__|__call__|__instancecheck__|'
                                      '__prepare__|__subclasscheck__|__subclasses__'
                                      ')\\()'), compile('(?=\\()'), node_sgr_params=Fore.hex('cc7832') + BOLD)
    mmeth.add_leaf(compile('.+'), Fore.hex('b200b2'))

    # builtins
    hl.root.add_leaf(compile(
        '(?<!\\w)('
        'abs|all|any|ascii|bin|breakpoint|callable|chr|compile|copyright|credits|delattr|dir|divmod|eval|exec|'
        'exit|format|getattr|globals|hasattr|hash|help|hex|id|input|isinstance|issubclass|iter|len|license|locals|max|'
        'min|next|oct|open|ord|pow|print|quit|repr|round|setattr|sorted|sum|vars|__build_class__|__import__|object|'
        'BaseException|Exception|ArithmeticError|AssertionError|AttributeError|OSError|IOError|EnvironmentError|'
        'BlockingIOError|int|bool|ConnectionError|BrokenPipeError|BufferError|bytearray|bytes|Warning|BytesWarning|'
        'ChildProcessError|classmethod|complex|ConnectionAbortedError|ConnectionRefusedError|ConnectionResetError|'
        'DeprecationWarning|dict|enumerate|EOFError|FileExistsError|FileNotFoundError|filter|float|FloatingPointError|'
        'frozenset|FutureWarning|GeneratorExit|ImportError|ImportWarning|SyntaxError|IndentationError|LookupError|'
        'IndexError|InterruptedError|IsADirectoryError|KeyboardInterrupt|KeyError|list|map|MemoryError|memoryview|'
        'ModuleNotFoundError|NameError|NotADirectoryError|RuntimeError|NotImplementedError|OverflowError|'
        'PendingDeprecationWarning|PermissionError|ProcessLookupError|property|range|RecursionError|ReferenceError|'
        'ResourceWarning|reversed|RuntimeWarning|set|slice|staticmethod|StopAsyncIteration|StopIteration|str|'
        'super|SyntaxWarning|SystemError|SystemExit|TabError|TimeoutError|tuple|type|TypeError|UnboundLocalError|'
        'ValueError|UnicodeError|UnicodeDecodeError|UnicodeEncodeError|UnicodeTranslateError|UnicodeWarning|'
        'UserWarning|ZeroDivisionError|zip|__loader__|Ellipsis|NotImplemented|__spec__'
        ')(?!\\w)'
    ), Fore.hex('8888c6') + BOLD)

    # decorators
    hl.root.add_leaf(compile('@\\w*'), Fore.hex('bbb529'))

    # simple strings
    string = HighlighterBranch(compile('[\'"]'), lambda m: m.match.group(),
                               node_sgr_params=Fore.name('white'),
                               stop_sgr_params=Fore.name('white'))
    string.add_leaf('.+', Fore.name('white'), sgr_inner=False)

    bstring = HighlighterBranch(compile('b[\'"]'), lambda m: m.match.group()[1],
                                node_sgr_params=Fore.hex('a5c261'),
                                stop_sgr_params=Fore.hex('a5c261'))
    bstring.add_leaf('.+', Fore.hex('a5c261'), sgr_inner=False)

    fstring = HighlighterBranch(compile('f[\'"]'), lambda m: m.match.group()[1],
                                node_sgr_params=Fore.name('white'),
                                stop_sgr_params=Fore.name('white'))
    fstring.add_leaf('.+', Fore.name('white'), sgr_inner=False)
    _fstring_func = HighlighterBranch(compile('\\{'), compile("}"),
                                      node_sgr_params=Fore.name('yellow'),
                                      stop_sgr_params=Fore.name('yellow'))
    fstring.add_branch(_fstring_func)

    # multiline strings
    mline_string = HighlighterBranch(compile('(\'\'\'|""")'), lambda m: m.match.group(),
                                     node_sgr_params=Fore.name('white'),
                                     stop_sgr_params=Fore.name('white'),
                                     multiline=True)
    mline_string.add_leaf('.+', Fore.name('white'), sgr_inner=False)

    mline_bstring = HighlighterBranch(compile('b(\'\'\'|""")'), lambda m: m.match.group()[1:],
                                      node_sgr_params=Fore.hex('a5c261'),
                                      stop_sgr_params=Fore.hex('a5c261'),
                                      multiline=True)
    mline_bstring.add_leaf('.+', Fore.hex('a5c261'), sgr_inner=False)

    mline_fstring = HighlighterBranch(compile('f(\'\'\'|""")'), lambda m: m.match.group()[1:],
                                      node_sgr_params=Fore.name('white'),
                                      stop_sgr_params=Fore.name('white'),
                                      multiline=True)
    mline_fstring.add_leaf('.+', Fore.name('white'), sgr_inner=False)
    _mline_fstring_func = HighlighterBranch(compile('\\{'), compile("}"),
                                            node_sgr_params=Fore.name('yellow'),
                                            stop_sgr_params=Fore.name('yellow'),
                                            multiline=True)
    mline_fstring.add_branch(_mline_fstring_func)

    # string-masks
    stringmask = HighlighterBranch(compile('\\\\'), '.',
                                   node_sgr_params=Fore.name('orange3') + BOLD,
                                   stop_sgr_params=Fore.name('orange3') + BOLD)
    string.add_branch(stringmask)
    bstring.add_branch(stringmask)
    fstring.add_branch(stringmask)

    mline_string.add_branch(stringmask)
    mline_bstring.add_branch(stringmask)
    mline_fstring.add_branch(stringmask)

    rstring = HighlighterBranch(compile('r[\'"]'), lambda m: m.match.group()[1],
                                node_sgr_params=Fore.name('white'),
                                stop_sgr_params=Fore.name('white'))
    rstring.add_leaf('.+', Fore.name('white'))

    mline_rstring = HighlighterBranch(compile('r(\'\'\'|""")'), lambda m: m.match.group()[1:],
                                      node_sgr_params=Fore.name('white'),
                                      stop_sgr_params=Fore.name('white'),
                                      multiline=True)
    mline_rstring.add_leaf('.+', Fore.name('white'))

    class RStringMask(HighlighterBranch):

        def stops(self, _string: str, relstart: int) -> SyntaxLeaf | None:
            if stop_m := search('.', _string):
                if stop_m.group()[0] == self.stop_pattern:
                    return self.stop_leaf(self, self.stop_pattern, stop_m, relstart)
                else:
                    return self.node_leaf(self, self.node_pattern, stop_m, relstart, None)

    rstringmask = RStringMask(compile('\\\\'), lambda m: m.node.__parent_branch__.__node_leaf__.match.group()[1],
                              node_sgr_params=Fore.name('white'),
                              stop_sgr_params=Fore.name('orange3') + BOLD)
    rstring.add_branch(rstringmask)

    mline_rstringmask = RStringMask(compile('\\\\'),
                                    lambda m: m.node.__parent_branch__.__node_leaf__.match.group()[1],
                                    node_sgr_params=Fore.name('white'),
                                    stop_sgr_params=Fore.name('orange3') + BOLD,
                                    multiline=True)
    mline_rstring.add_branch(mline_rstringmask)

    # add root-leafs to subbranches
    _fstring_func.adopt_leafs(hl.root)
    _mline_fstring_func.adopt_leafs(hl.root)
    cls.adopt_leafs(hl.root)

    # add first branches
    hl.root.add_branch(string)
    hl.root.add_branch(bstring)
    hl.root.add_branch(rstring)
    hl.root.add_branch(fstring)

    # add string branches to fstring func branch
    _fstring_func.adopt_branches(hl.root)

    #
    hl.root.add_branch(mline_string)
    hl.root.add_branch(mline_bstring)
    hl.root.add_branch(mline_rstring)
    hl.root.add_branch(mline_fstring)
    hl.root.add_branch(cmt)

    # add string branches to fstring func branch
    _mline_fstring_func.adopt_branches(hl.root)

    hl.root.add_branch(cls)

    # copy root-branches to class-branch
    cls.adopt_branches(hl.root)

    # add method branches to class-branch
    cls.add_branch(mmeth)
    cls.add_branch(func)

    # add class- and func-branch to root
    hl.root.add_branch(func)
