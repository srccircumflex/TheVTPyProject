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

from typing import Pattern, Callable, Match, Any

try:
    from .._buffercomponents.row import _Row
except ImportError:
    pass

from vtframework.textbuffer.display.syntaxtree import (
    SyntaxBranch as _SyntaxBranch,
    SyntaxLeaf as _SyntaxLeaf,
    SyntaxGlobals as _SyntaxGlobals,
    SyntaxTree as _SyntaxTree)
from vtframework.iodata.esccontainer import EscSegment, EscContainer
from vtframework.iodata.sgr import SGRParams, SGRWrap


class __RowCatcher:
    __row__: _Row = None

    def catch(self, __row: _Row | None) -> None:
        self.__row__ = __row

    def get(self) -> _Row | None:
        return self.__row__


_RowCatcher = __RowCatcher()


class _LeafFactory:
    pattern: Pattern | str
    priority: Callable[[HighlighterLeaf, HighlighterLeaf], bool] | bool
    action: Callable[[HighlighterLeaf, EscSegment | EscContainer], EscSegment | EscContainer]

    def __init__(self,
                 pattern: Pattern | str,
                 sgr_params: SGRParams,
                 sgr_inner: bool,
                 sgr_cellular: bool,
                 priority: Callable[[HighlighterLeaf, HighlighterLeaf], bool] | bool
                 ):

        self.pattern = pattern
        self.priority = priority

        if sgr_params:
            def action(leaf: HighlighterLeaf, vis_row: EscSegment | EscContainer) -> EscContainer:
                span_start, span_end = leaf.visual_span()

                return vis_row[:span_start] + SGRWrap(
                    vis_row[span_start:span_end], sgr_params, inner=sgr_inner, cellular=sgr_cellular
                ) + vis_row[span_end:]
        else:
            def action(leaf: HighlighterLeaf, vis_row: EscSegment | EscContainer) -> EscContainer:
                return vis_row

        self.action = action

    def __call__(self, parent, pattern, match, relstart, _node=None) -> HighlighterLeaf:
        return HighlighterLeaf(parent,
                               match,
                               relstart,
                               _RowCatcher.get(),
                               self.action,
                               self.priority,
                               _node)


class HighlighterGlobals(_SyntaxGlobals):
    """
    The container for branch-independent highlight definitions.

    Definitions are created as RegularExpression -- :class:`SGRWrap`-parameter pairs using the ``add`` method,
    additionally each object can be used as a label to remove definitions afterwards.

    The graphical rendering of the characters matching `pattern`, is implemented by the ``Highlighter*`` component in
    the ``Display*`` via ``SGRWrap``. Therefore, the keyword arguments `sgr_inner` and `sgr_cellular` are passed to
    ``SGRWrap``.

    The `priority` of a syntax leaf over others found in a string is realized with ``__lt__``.

    The parameterization can be defined differently by an executable object, this executable object gets the origin
    :class:`HighlighterLeaf` and the other ``HighlighterLeaf`` and must return a boolean value whether the origin
    ``HighlighterLeaf`` has a higher priority than the other.
    If ``True`` is passed to `priority`, the earliest leaf has the highest priority, and if there is a tie
    the match with the largest span has priority. If the `priority` parameter is ``False``, the earliest leaf
    with the smallest span has priority.

    >>> from re import compile
    >>> from vtframework.iodata.sgr import Ground
    >>> __highlighter__: HighlightAdvanced
    >>>
    >>> # enable trailing spaces
    >>> __highlighter__.globals.add(compile("\\s*$"), Ground.name("cyan"), label="trailing spaces")
    >>>
    >>> # disable trailing spaces
    >>> __highlighter__.globals.remove_by_label("trailing spaces")
    """

    leafs: tuple[
        tuple[
            Pattern | str,
            Callable[[HighlighterGlobals, Pattern | str, Match, int], HighlighterLeaf],
            Any
        ], ...]

    def mapping(self, string: str, relstart: int, _out_: list[HighlighterLeaf]) -> list[HighlighterLeaf]:
        return super().mapping(string, relstart, _out_)

    def add(self,
            pattern: Pattern | str,
            sgr_params: SGRParams,
            *,
            sgr_inner: bool = True,
            sgr_cellular: bool = True,
            priority: Callable[[HighlighterLeaf, HighlighterLeaf], bool] | bool = True,
            label: Any = None
            ) -> None:
        """
        Add a globally applicable highlight rule to the :class:`HighlighterGlobals`.
        """
        super().add(pattern, _LeafFactory(pattern, sgr_params, sgr_inner, sgr_cellular, priority), label)


class HighlighterBranch(_SyntaxBranch):
    """
    The object represents a syntax branch of the highlighting.

    The definition of the node point and the stop point of a branch are each given by a RegularExpression;
    in addition, a graphical representation can optionally be assigned to the matched characters of the points,
    as :class:`SGRWrap`-parameters. The graphical rendering of the characters matching `node_pattern` and
    `stop_pattern`, is implemented by the ``Highlighter*`` component in the ``Display*`` via ``SGRWrap``. Therefore,
    the keyword arguments `*_sgr_params`, `*_sgr_inner` and `*_sgr_cellular` are passed to :class:`SGRWrap`.

    The `*_priority` of a syntax leaf over others found in a string is realized with ``__lt__``.

    The parameterization can be defined differently by an executable object, this executable object gets the origin
    :class:`HighlighterLeaf` and the other ``HighlighterLeaf`` and must return a boolean value whether the origin
    ``HighlighterLeaf`` has a higher priority than the other.
    If ``True`` is passed to `*_priority`, the earliest leaf has the highest priority, and if there is a tie
    the match with the largest span has priority. If the `*_priority` parameter is ``False``, the earliest leaf
    with the smallest span has priority.

    The `stop_pattern` of a branch can also be specified as an executable object, for example, to define the end of a
    branch depending on the node that occurred.
    The function is then executed when the branch is activated with the node-:class:`HighlighterLeaf` and must return
    the stopping pattern.

    >>> HighlighterBranch(node_pattern="['\\"]", stop_pattern=lambda leaf: leaf.match.group())

    A branch is activated when the `node_pattern` occurs and when the node leaf has the highest priority over other
    found leaves in the string. By default, the activation method returns the same object if the `stop_pattern` is
    parameterized as a pattern. If an executable object is passed as described above, an image of the current
    attributes of the branch is created by default during activation to preserve the stopping pattern (``snap``-method).
    A deviating activation function can also be passed via the keywordargument `activate`, this function then receives
    this branch object on activation and must return a branch object.

    The parameterizations of `multirow` and `multiline` are evaluated within the parsing process and indicate whether 
    the branch is valid across rows or lines. The string passed during the single execution of a parsing method in the
    ``_HighlightTree*`` (:class:`_SyntaxTree`) is interpreted as a row; a line break is defined via the argument
    `has_end` of the parsing methods.

    The leaves of the branch are also specified as RegularExpression -- :class:`SGRWrap`-parameter pairs using the
    ``add_leaf`` method, the `prority` is defined as for the node and stop leaves.
    Further ramifications are again added as a ``HighlighterBranch`` via the ``add_branch`` method.

    The freely definable `label`\\ s of a branch or leaf, are used for a later identification of syntax definitions,
    for example by the methods ``remove_leafs_by_label`` and ``remove_branches_by_label`` in the ``HighlighterBranch``.
    """

    def __init__(self,
                 node_pattern: Pattern | str,
                 stop_pattern: Pattern | str | Callable[[HighlighterLeaf], Pattern | str],
                 *,
                 node_sgr_params: SGRParams = None,
                 node_sgr_inner: bool = True,
                 node_sgr_cellular: bool = True,
                 node_priority: Callable[[HighlighterLeaf, HighlighterLeaf], bool] | bool = True,
                 stop_sgr_params: SGRParams = None,
                 stop_sgr_inner: bool = True,
                 stop_sgr_cellular: bool = True,
                 stop_priority: Callable[[HighlighterLeaf, HighlighterLeaf], bool] | bool = True,
                 activate: Callable[[HighlighterBranch], HighlighterBranch] = None,
                 multirow: bool = True,
                 multiline: bool = False,
                 label: Any = None):
        _SyntaxBranch.__init__(self,
                               node_pattern,
                               (stop_pattern if not callable(stop_pattern) else (lambda _, m: stop_pattern(m))),
                               _LeafFactory(node_pattern, node_sgr_params, node_sgr_inner, node_sgr_cellular,
                                            node_priority),
                               _LeafFactory(stop_pattern, stop_sgr_params, stop_sgr_inner, stop_sgr_cellular,
                                            stop_priority),
                               activate=activate,
                               multirow=multirow,
                               multiline=multiline,
                               label=label)

    def add_leaf(self,
                 pattern: Pattern | str,
                 sgr_params: SGRParams,
                 *,
                 sgr_inner: bool = True,
                 sgr_cellular: bool = True,
                 priority: Callable[[HighlighterLeaf, HighlighterLeaf], bool] | bool = True,
                 label: Any = None
                 ) -> None:
        """
        Add a highlight rule to the :class:`HighlighterBranch`.
        """
        super().add_leaf(pattern, _LeafFactory(pattern, sgr_params, sgr_inner, sgr_cellular, priority), label)

    def add_branch(self, branch: HighlighterBranch) -> None:
        """
        Add a ramification to the :class:`HighlighterBranch`.
        """
        super().add_branch(branch)


class HighlighterLeaf(_SyntaxLeaf):
    """
    The syntax leaf object is generated as the result of a parse by ``_HighlightTree*`` (:class:`_SyntaxTree`)
    and is used for further automatic processing of the highlighting.

    The object contains the ``parent`` :class:`HighlighterBranch` or :class:`HighlighterGlobals`, the ``re.Match``,
    the relative start ( ``relstart`` ) of a substring and, if the leaf represents the beginning of a
    ``HighlighterBranch``, the beginning branch under ``node``.

    In addition, to the deviation is assigned the relevant :class:`_Row` object and an action, for the graphical
    conversion of the matched text.

    Since the string is sliced during the parsing process, the ``start``/``end``/``span`` methods of the ``re.Match``
    object (also realized as properties in the ``HighlighterLeaf``) may not return the actual values with reference to
    the passed string; therefore, the values can be obtained considering the relative starting point via the properties
    with ``total_*`` prefix.
    """

    row: _Row
    action: Callable[[HighlighterLeaf, EscSegment | EscContainer], EscSegment | EscContainer]

    def __init__(self,
                 parent: HighlighterGlobals | HighlighterBranch,
                 match: Match,
                 relstart: int,
                 row: _Row,
                 action: Callable[[HighlighterLeaf, EscSegment | EscContainer], EscSegment | EscContainer],
                 priority: Callable[[HighlighterLeaf, HighlighterLeaf], bool] | bool = True,
                 _node: HighlighterBranch = None):
        _SyntaxLeaf.__init__(self, parent, match, relstart, priority, _node)
        self.row = row
        self.action = action

    def visual_span(self) -> tuple[int, int]:
        span = self.match.span()
        return (self.row.cursors.tool_cnt_to_vis(span[0] + self.relstart),
                self.row.cursors.tool_cnt_to_vis(span[1] + self.relstart))

    def __call__(self, vis_row: EscSegment | EscContainer) -> EscContainer:
        return self.action(self, vis_row)


class _HighlightTreeRegex(_SyntaxTree):
    _globals: HighlighterGlobals

    def __init__(self):
        _SyntaxTree.__init__(self)
        self._globals = HighlighterGlobals()

    @property
    def root(self) -> _SyntaxBranch:
        """:raises AttributeError:"""
        raise AttributeError

    def set_root(self, __new_root: _SyntaxBranch) -> None:
        """:raises AttributeError:"""
        raise AttributeError

    def purge_root(self) -> _SyntaxBranch:
        """:raises AttributeError:"""
        raise AttributeError

    def branch_growing(self, *args, **kwargs) -> None:
        """:raises AttributeError:"""
        raise AttributeError

    def map_leafs(self, *args, **kwargs) -> None:
        """:raises AttributeError:"""
        raise AttributeError

    def map_tree(self, *args, **kwargs) -> None:
        """:raises AttributeError:"""
        raise AttributeError

    @property
    def globals(self) -> HighlighterGlobals:
        """
        The :class:`HighlighterGlobals`.
        """
        return self._globals

    def purge_globals(self) -> HighlighterGlobals:
        """
        Reinitialize the current :class:`HighlighterGlobals`.
        """
        self._globals = HighlighterGlobals()
        return self._globals

    def set_globals(self, __new_globals: HighlighterGlobals) -> None:
        """
        Set the :class:`HighlighterGlobals`.
        """
        super().set_globals(__new_globals)

    def map_globals(self, string: str, row: _Row, _out_: list[_SyntaxLeaf]) -> None:
        """
        This method is executed during the parsing process.

        Apply the leaves defined in the globals to a `string`, append the parsed leaves to the `_out_` list as
        :class:`HighlighterLeaf` objects.
        """
        _RowCatcher.catch(row)
        super().map_globals(string, _out_)


class _HighlightTreeAdvanced(_SyntaxTree):
    current_branches: list[HighlighterBranch]

    _globals: HighlighterGlobals
    _root: HighlighterBranch

    @property
    def globals(self) -> HighlighterGlobals:
        """
        The :class:`HighlighterGlobals`.
        """
        return self._globals

    def set_globals(self, __new_globals: HighlighterGlobals) -> None:
        """
        Set the :class:`HighlighterGlobals`.
        """
        super().set_globals(__new_globals)

    def purge_globals(self) -> HighlighterGlobals:
        """
        Reinitialize the current :class:`HighlighterGlobals`.
        """
        self._globals = HighlighterGlobals()
        return self._globals

    @property
    def root(self) -> HighlighterBranch:
        """
        The root-:class:`HighlighterBranch`.
        """
        return self._root

    def set_root(self, __new_root: HighlighterBranch) -> None:
        """
        Set the :class:`HighlighterBranch`.
        """
        self._root = __new_root

    def purge_root(self) -> HighlighterBranch:
        """
        Reinitialize the current :class:`HighlighterBranch`.
        """
        self._root = HighlighterBranch('', '')
        return self._root

    def __init__(self):
        _SyntaxTree.__init__(self)
        self.current_branches = list()
        self._globals = HighlighterGlobals()
        self._root = HighlighterBranch('', '')

    def branch_growing(self, string: str, has_end: bool, _branches_: list[_SyntaxBranch]) -> None:
        """
        This method is executed during the parsing process.
        
        Apply to a `string` only the :class:`HighlighterBranch` configurations (skip parsing the leaves) and expand or 
        shorten the list of `_branches_`.
        Via `has_end` it is specified whether the string has a terminating end and is processed in connection with the 
        ``multiline`` parameterization of the ``HighlighterBranch``.
        The list of `_branches_` represents the current sequence of active ``HighlighterBranch``'s; if it is empty, 
        the ``root`` is the current ``HighlighterBranch``.
        """
        _RowCatcher.catch(None)
        super().branch_growing(string, has_end, _branches_)

    def map_globals(self, string: str, row: _Row, _out_: list[_SyntaxLeaf]) -> None:
        """
        This method is executed during the parsing process.
        
        Apply the leaves defined in the :class:`HighlighterGlobals` to a `string`, append the parsed leaves to the 
        `_out_` list as :class:`HighlighterLeaf` objects.
        """
        _RowCatcher.catch(row)
        super().map_globals(string, _out_)

    def map_leafs(self, string: str, row: _Row, has_end: bool, _branches_: list[_SyntaxBranch],
                  _leaf_out_: list[_SyntaxLeaf]) -> None:
        """
        This method is executed during the parsing process.
        
        Apply the entire configurations of the :class:`HighlighterBranch`'s and their :class:`HighlighterLeaf`'s to a 
        `string`. Append the parsed leaves to the list `_leaf_out_` and expand or shorten the list of active 
        `_branches_`.
        Via `has_end` it is specified whether the string has a terminating end and is processed in connection with the 
        ``multiline`` parameterization of the ``HighlighterBranch``.
        The list of `_branches_` represents the current sequence of active ``HighlighterBranch``'s; if it is empty,
        the ``root`` is the current ``HighlighterBranch``.
        """
        _RowCatcher.catch(row)
        super().map_leafs(string, has_end, _branches_, _leaf_out_)
