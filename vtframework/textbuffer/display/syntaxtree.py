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

from typing import Callable, final, Any, overload
from re import Pattern, Match, search, finditer


########################################################################################################################
#                                                   The AST Object                                                     #
########################################################################################################################


class SyntaxTree:
    """
    Parser base object for designing an abstract syntax tree.

    ~~~~

    Designing
    ~~~~~~~~~

    The branches of the syntax tree are defined by :class:`SyntaxBranch` objects and are attached to the main ``root``
    branch; the start/node, termination, and leaves of a branch (and root branch) are created as a
    RegularExpression -- SyntaxLeaf-factory pair.

    Leaves defined in ``globals`` (:class:`SyntaxGlobals`) apply independently of currently active branches.

    >>> from re import compile
    >>>
    >>> #                     _ _ _ _ _ _ _ _
    >>> #                    |               |
    >>> #                    B - l - l - g - l ... E
    >>> #                   /
    >>> # R - l - g - l - l ... i
    >>>
    >>> ast = SyntaxTree()
    >>>
    >>> B = SyntaxBranch(node_pattern=compile("\\("), stop_pattern=compile("\\)"))
    >>> B.adopt_self()
    >>>
    >>> B.add_leaf(compile("regex"), lambda parent, pattern, match, relstart: SyntaxLeaf(parent, match, relstart))
    >>> ...
    >>> ast.root.add_branch(B)
    >>> ast.globals.add(compile("regex"), lambda parent, pattern, match, relstart: SyntaxLeaf(parent, match, relstart))

    ~~~~

    >>> from re import compile
    >>>
    >>> #                      _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    >>> #                    |                                  |
    >>> #                    B1 - l - l - l - E                 |
    >>> #                   /                                  /
    >>> # R - l - l - l - l - l - l ... i         B3 - l - l - l - l - l - E
    >>> #                          \\             /                 |
    >>> #                           B2 - l - l - l ... E           |
    >>> #                            \\ _ _ _ _ _ _ _ _ _ _ _ _ _ _ |
    >>>
    >>> ast = SyntaxTree()
    >>>
    >>> B1 = SyntaxBranch(node_pattern=compile('"'), stop_pattern=compile('"'))
    >>> B2 = SyntaxBranch(...
    >>> B3 = SyntaxBranch(...
    >>>
    >>> ast.root.add_branch(B1)
    >>> ast.root.add_branch(B2)
    >>>
    >>> B2.add_branch(B3)
    >>>
    >>> B3.add_branch(B1)
    >>>
    >>> B3.add_branch(B2)
    >>>
    >>> B*.add_leaf(...
    >>> ...

    ~~~~

    Parsing Process
    ~~~~~~~~~~~~~~~

    When using the special characters of regular expressions that refer to the beginning or end of a string,
    such as ``"^"`` or ``"\\Z"``, it must be noted that the row is sliced during parsing.
    The following illustration sketches the parsing process.

    >>> from re import compile
    >>>
    >>> square_bracket_branch = SyntaxBranch(node_pattern=compile("\\[node]"), stop_pattern=compile("\\[end]"))
    >>> curly_bracket_branch = SyntaxBranch(node_pattern=compile("\\{node}"), stop_pattern=compile("\\{end}"))
    >>> square_bracket_branch.add_branch(curly_bracket_branch)
    >>>
    >>> #   node_leaf      node_leaf          end_leaf              end_leaf
    >>> #    |    |  leafs  |    |    leafs    |   |     leafs       |   |
    >>> #    |    |[ - - - -|    |{ - - - - - }|   |- - - - - - - - ]|   |
    >>> #    |    |         |    |             |   |                 |   |
    >>> "... [node] foo bar {node} foo bar ... {end} ... foo bar ... [end] ..."
    >>>
    >>> ...
    >>> "[node]"                                                    # node found
    >>> " foo bar {node} foo bar ... {end} ... foo bar ... [end]"   # search for a sub-node
    >>> "{node}"                                                    # sub-node found
    >>> " foo bar "                                                 # applying Leave configurations to the remaining string
    >>> " foo bar ... {end} ... foo bar ... [end]"                  # search for the end of a branch
    >>> "{end}"                                                     # end of a branch found
    >>> " foo bar ... "                                             # apply leave configurations to the remaining string
    >>> ...

    Applicable leaves, branch-node leaves, and ending leaves of a branch are appended to a passed list
    (as :class:`SyntaxLeaf` objects) during parsing; active branches are passed within a list to the parsing
    process and expanded by it should another branch occur, or truncated should a branch end.

    A ``SyntaxLeaf`` contains the matched ``re.Match`` object, the origin ``SyntaxBranch`` and the relative starting
    point in the row, since it is sliced during the pars process. The methods with ``total_*`` prefix return the
    actual position in the row.

    Also, the ``node`` attribute is not ``None`` but the beginning ``SyntaxBranch`` object if the leaf represents the
    beginning of a branch.

    ~~~~

    The parse process is performed row by row using the methods with ``map_*`` prefix, or only a part solely to capture
    the branch bifurcations by ``branch_grow``. The methods ``map_leafs`` and ``branch_grow`` are interfaces to the
    actual methods which are realized as recursions, these underlying methods cannot be overwritten in inheritances.
    """

    _globals: SyntaxGlobals
    _root: SyntaxBranch

    @property
    def globals(self) -> SyntaxGlobals:
        """The :class:`SyntaxGlobals`."""
        return self._globals

    @property
    def root(self) -> SyntaxBranch:
        """The ``root`` - :class:`SyntaxBranch`"""
        return self._root

    def __init__(self):
        self._globals = SyntaxGlobals()
        self._root = SyntaxBranch('', '')

    def purge_globals(self) -> SyntaxGlobals:
        """Reinitialize the current :class:`SyntaxGlobals`."""
        self._globals = SyntaxGlobals()
        return self._globals

    def purge_root(self) -> SyntaxBranch:
        """Reinitialize the current ``root`` - :class:`SyntaxBranch`."""
        self._root = SyntaxBranch('', '')
        return self._root

    def set_globals(self, __new_globals: SyntaxGlobals) -> None:
        """Set the :class:`SyntaxGlobals`."""
        self._globals = __new_globals

    def set_root(self, __new_root: SyntaxBranch) -> None:
        """Set the ``root`` - :class:`SyntaxBranch`."""
        self._root = __new_root

    def map_globals(self, string: str, _out_: list[SyntaxLeaf]) -> list[SyntaxLeaf]:
        """
        Apply the leaves defined in the ``globals`` to a `string`,
        append the parsed leaves to the `_out_` list as :class:`SyntaxLeaf` objects.
        """
        return self.globals.mapping(string, 0, _out_)

    def branch_growing(self,
                       string: str,
                       has_end: bool,
                       _branches_: list[SyntaxBranch]
                       ) -> list[SyntaxBranch]:
        """
        Apply to a `string` only the :class:`SyntaxBranch` configurations (skip parsing the leaves)
        and expand or shorten the list of `_branches_`.

        Via `has_end` it is specified whether the string has a terminating end and is processed in
        connection with the `multiline` parameterization of the ``SyntaxBranch``.

        The list of `_branches_` represents the current sequence of active ``SyntaxBranch``'s;
        if it is empty, the ``root`` is the current ``SyntaxBranch``.
        """
        return self._branch_growing_recursion(string, has_end, _branches_)

    def map_leafs(self,
                  string: str,
                  has_end: bool,
                  _branches_: list[SyntaxBranch],
                  _leaf_out_: list[SyntaxLeaf]
                  ) -> tuple[list[SyntaxBranch], list[SyntaxLeaf]]:
        """
        Apply the entire configurations of the :class:`SyntaxBranch`'s and their :class:`SyntaxLeaf`'s to a `string`.
        Append the parsed leaves to the list `_leaf_out_` and expand or shorten the list of active `_branches_`.

        Via `has_end` it is specified whether the string has a terminating end and is processed in
        connection with the `multiline` parameterization of the ``SyntaxBranch``.

        The list of `_branches_` represents the current sequence of active ``SyntaxBranch``'s;
        if it is empty, the ``root`` is the current ``SyntaxBranch``.
        """
        return self._map_leafs_recursion(string, has_end, _branches_, _leaf_out_)

    def map_tree(self,
                 string: str,
                 has_end: bool,
                 _branches_: list[SyntaxBranch],
                 _leaf_out_: list[SyntaxLeaf]
                 ) -> tuple[list[SyntaxBranch], list[SyntaxLeaf]]:
        """
        Apply the entire configurations of the :class:`SyntaxBranch`'s and their :class:`SyntaxLeaf`'s to a `string`.
        Append the parsed leaves to the list `_leaf_out_` and expand or shorten the list of active `_branches_`.

        Then apply the leaves defined in ``globals`` to the `string` and append
        the parsed leaves as :class:`SyntaxLeaf` objects to the `_leaf_out_` list.

        Via `has_end` it is specified whether the string has a terminating end and is processed in
        connection with the `multiline` parameterization of the ``SyntaxBranch``.

        The list of `_branches_` represents the current sequence of active ``SyntaxBranch``'s;
        if it is empty, the ``root`` is the current ``SyntaxBranch``.
        """
        return self.map_leafs(string, has_end, _branches_, _leaf_out_)[0], self.map_globals(string, _leaf_out_)

    @final
    def _map_leafs_recursion(self,
                             string: str,
                             has_end: bool,
                             _branches_: list[SyntaxBranch],
                             _leaf_out_: list[SyntaxLeaf],
                             ___relstart: int = 0
                             ) -> tuple[list[SyntaxBranch], list[SyntaxLeaf]]:
        if _branches_:
            # active branches
            if stop_leaf := _branches_[-1].stops(string,
                                                 ___relstart):
                # end of branch found
                # check if a subbranch starts in the range of the parent branch
                _start_leafs_: list[SyntaxLeaf] = list()

                _branches_[-1].branch_mapping(string[:stop_leaf.start],
                                              ___relstart,
                                              _start_leafs_)

                if _start_leafs_:
                    # start of a subbranch found -> apply leaf configurations up to the end of the current branch
                    # -> append the subbranch -> recursion
                    _start_leaf = min(_start_leafs_)

                    _branches_[-1].leaf_mapping(string[:_start_leaf.start],
                                                ___relstart,
                                                _leaf_out_)

                    _branches_.append(_start_leaf.node.activate(_start_leaf, _branches_[-1]))

                    _leaf_out_.append(_start_leaf)

                    self._map_leafs_recursion(string[_start_leaf.end:],
                                              has_end,
                                              _branches_,
                                              _leaf_out_,
                                              ___relstart + _start_leaf.end)

                else:
                    # no subbranch found -> apply leaf configurations up to the end of the branch
                    # -> remove the branch -> recursion
                    _branches_[-1].leaf_mapping(string[:stop_leaf.start],
                                                ___relstart,
                                                _leaf_out_)

                    _leaf_out_.append(stop_leaf)

                    _branches_.pop(-1)

                    self._map_leafs_recursion(string[stop_leaf.end:],
                                              has_end,
                                              _branches_,
                                              _leaf_out_,
                                              ___relstart + stop_leaf.end)
            else:
                # stop of current branch not found
                # check if a subbranch starts in the row
                _start_leafs_: list[SyntaxLeaf] = list()

                _branches_[-1].branch_mapping(string,
                                              ___relstart,
                                              _start_leafs_)

                if _start_leafs_:
                    # start of a subbranch found -> apply leaf configurations up to the end of the current branch
                    # -> append the subbranch -> recursion
                    _start_leaf = min(_start_leafs_)

                    _branches_[-1].leaf_mapping(string[:_start_leaf.start],
                                                ___relstart,
                                                _leaf_out_)

                    _branches_.append(_start_leaf.node.activate(_start_leaf, _branches_[-1]))

                    _leaf_out_.append(_start_leaf)

                    self._map_leafs_recursion(string[_start_leaf.end:],
                                              has_end,
                                              _branches_,
                                              _leaf_out_,
                                              ___relstart + _start_leaf.end)
                else:
                    # no subbranch found -> apply leaf configurations up to the end of the row if
                    # multiline or multirow, otherwise pop current branch
                    if not _branches_[-1].multirow:
                        _branches_.pop(-1)
                    elif not _branches_[-1].multiline and has_end:
                        _branches_.pop(-1)
                    else:
                        _branches_[-1].leaf_mapping(string,
                                                    ___relstart,
                                                    _leaf_out_)
        else:
            # no active branch (except root)
            # check if a branch starts in the row
            _start_leafs_: list[SyntaxLeaf] = list()

            self.root.branch_mapping(string, ___relstart, _start_leafs_)

            if _start_leafs_:
                # start of a branch found -> apply leaf configurations up to the end of the current branch
                # -> append the subbranch -> recursion
                _start_leaf = min(_start_leafs_)

                self.root.leaf_mapping(string[:_start_leaf.start],
                                       ___relstart,
                                       _leaf_out_)

                _branches_.append(_start_leaf.node.activate(_start_leaf, self.root))

                _leaf_out_.append(_start_leaf)

                self._map_leafs_recursion(string[_start_leaf.end:],
                                          has_end,
                                          _branches_,
                                          _leaf_out_,
                                          ___relstart + _start_leaf.end)

            else:
                # no branch found -> apply leaf configurations up to the end of the row
                self.root.leaf_mapping(string,
                                       ___relstart,
                                       _leaf_out_)
                
        return _branches_, _leaf_out_

    @final
    def _branch_growing_recursion(self,
                                  string: str,
                                  has_end: bool,
                                  _branches_: list[SyntaxBranch],
                                  ___relstart: int = 0
                                  ) -> list[SyntaxBranch]:
        if _branches_:
            # active branches
            if stop_leaf := _branches_[-1].stops(string, ___relstart):
                # end of branch found
                # check if a subbranch starts in the range of the parent branch
                start_leafs: list[SyntaxLeaf] = list()

                _branches_[-1].branch_mapping(string[:stop_leaf.start],
                                              ___relstart,
                                              start_leafs)

                if start_leafs:
                    # start of a subbranch found -> append the subbranch -> recursion
                    _start_leaf = min(start_leafs)

                    _branches_.append(_start_leaf.node.activate(_start_leaf, _branches_[-1]))

                    self._branch_growing_recursion(string[_start_leaf.end:],
                                                   has_end,
                                                   _branches_,
                                                   ___relstart + _start_leaf.end)

                else:
                    # no subbranch found -> remove the branch -> recursion
                    _branches_.pop(-1)

                    self._branch_growing_recursion(string[stop_leaf.end:],
                                                   has_end,
                                                   _branches_,
                                                   ___relstart + stop_leaf.end)
            else:
                # stop of current branch not found
                # check if a subbranch starts in the row
                start_leafs: list[SyntaxLeaf] = list()

                _branches_[-1].branch_mapping(string, ___relstart, start_leafs)

                if start_leafs:
                    # start of a subbranch found -> append the subbranch -> recursion
                    _start_leaf = min(start_leafs)

                    _branches_.append(_start_leaf.node.activate(_start_leaf, _branches_[-1]))

                    self._branch_growing_recursion(string[_start_leaf.end:],
                                                   has_end,
                                                   _branches_,
                                                   ___relstart + _start_leaf.end)
                else:
                    # no subbranch found -> remove current branches if not multirow or -line
                    if has_end:
                        try:
                            while not _branches_[-1].multiline:
                                _branches_.pop(-1)
                        except IndexError:
                            pass
                    else:
                        try:
                            while not _branches_[-1].multirow:
                                _branches_.pop(-1)
                        except IndexError:
                            pass
        else:
            # no active branch (except root)
            # check if a branch starts in the row
            start_leafs: list[SyntaxLeaf] = list()

            self.root.branch_mapping(string, ___relstart, start_leafs)

            if start_leafs:
                # start of a branch found -> append the subbranch -> recursion
                _start_leaf = min(start_leafs)

                _branches_.append(_start_leaf.node.activate(_start_leaf, self.root))

                self._branch_growing_recursion(string[_start_leaf.end:],
                                               has_end,
                                               _branches_,
                                               ___relstart + _start_leaf.end)
                
        return _branches_


########################################################################################################################
#                                                   Its Components                                                     #
########################################################################################################################


class SyntaxGlobals:
    """
    A container for globally defined :class:`SyntaxLeaf`'s.

    The global leafs are created as RegularExpression -- SyntaxLeaf-factory pairs,
    additionally each object can be used as a label to remove definitions afterwards.


    >>> from re import compile
    >>>
    >>> ast = SyntaxTree()
    >>> ast.globals.add(compile("bar"), label=Any)
    >>> ast.globals.add(compile("foo"), label=object())
    >>> ...
    >>> ast.globals.remove_by_label(Any)
    """

    leafs: tuple[
        tuple[
            Pattern | str,
            Callable[[SyntaxGlobals, Pattern | str, Match, int], SyntaxLeaf],
            Any
        ], ...]

    def __init__(self):
        self.leafs = tuple()

    def add(self,
            pattern: Pattern | str,
            leaf: Callable[
                [SyntaxGlobals, Pattern | str, Match, int], SyntaxLeaf
            ] = lambda parent, pattern, match, relstart: SyntaxLeaf(parent, match, relstart),
            label: Any = None
            ) -> None:
        """
        Add a :class:`SyntaxLeaf`-rule.
        To the `leaf`-factory is passed on occurrence of a match on `pattern`; the ``SyntaxGlobals`` object, the
        `pattern`, the ``re.Match`` and the relative start, the execution should return an :class:`SyntaxLeaf`.
        Additionally, each object can be used as a `label` to remove definitions afterwards.
        """
        self.leafs += ((pattern, leaf, label),)

    def _remove(self, ref: Any, i_comp: int) -> None:
        leafs = list(self.leafs)
        i = 0
        for _ in range(len(leafs)):
            if leafs[i][i_comp] == ref:
                leafs.pop(i)
            else:
                i += 1
        self.leafs = tuple(leafs)

    def remove_by_label(self, label: Any) -> None:
        """Remove all definitions with `label`."""
        self._remove(label, 2)

    def remove_by_pattern(self, pattern: Pattern | str) -> None:
        """Remove all definitions with `pattern`."""
        self._remove(pattern, 0)

    def mapping(self, string: str, relstart: int, _out_: list[SyntaxLeaf]) -> list[SyntaxLeaf]:
        """
        Apply each definition of global leaves to the `string`. Append matches as :class:`SyntaxLeaf` objects to the
        list `_out_`.

        `relstart` specifies the start position of a substring.

        This method is executed inside the parsing methods in the :class:`SyntaxTree`.
        """
        for itm in self.leafs:
            _out_.extend(map(
                lambda m: itm[1](self, itm[0], m, relstart),
                finditer(itm[0], string)
            ))
        return _out_


class SyntaxBranch:
    """
    Syntax branch object used by the :class:`SyntaxTree`.

    The beginning of a branch is defined by the `node_pattern` and the leaf is created by the `node_leaf`
    factory, which must return a :class:`SyntaxLeaf` object with the ``node`` attribute set to the beginning
    branch.

    If the beginning of a branch is recognized by the parser methods in the AST, a definable `activate` function
    is executed, which must return a branch object.

    By default, the same object is returned and appended to the sequence of active branches if the `stop_pattern`
    is a pattern;

    if the `stop_pattern` is defined as an executable object, it receives the ``SyntaxBranch`` object
    and the node-``SyntaxLeaf`` on activation and must return a ``pattern`` that defines the end of the branch.
    Upon activation, a "deep copy" (``snap``) of the branch object is then created and appended to the sequence
    of active branches, if `activate` was ``None`` at creation.

    The terminating leaf object is then created by the factory `stop_leaf` when the pattern occurs.

    The leaf factories receive the parent ``SyntaxBranch``, the applicable ``pattern``, the ``re.Match`` and the
    ``relative start`` of the sub-string when the `node_pattern` or `stop_pattern` occurs; in additionally, the
    beginning ``SyntaxBranch`` object is passed to the `node_leaf` factory.

    The parameters `multirow` and `multiline` are evaluated in the parser methods of the AST.
    If the parameter `multirow` is set to ``True``, after processing a single string the branch is NOT removed from
    the sequence of active branches if the string is not line ending.
    If the parameter `multiline` is set to ``True``, the branch will be kept in the sequence even over line endings.

    Via the parameterization `label` each object can be passed to identify the branch.

    The attributes ``__start_leaf__`` and ``__parent_branch__`` are only set by the AST when the ``activate``-METHOD
    is executed, then the ``stop_pattern`` is determined within the method and finally the PARAMETERIZED
    `activate`-FUNCTION is executed.

    ~~~~

    The leaves of the branch are created as ``pattern`` -- ``SyntaxLeaf``-factory pairs and further forks to branches
    within the branch are also defined as ``SyntaxBranch`` objects.

    >>> from re import compile
    >>>
    >>> ast = SyntaxTree()
    >>>
    >>> B1 = SyntaxBranch(node_pattern=compile("\\("), stop_pattern=compile("\\)"), multiline=True, label="numbers in tuple")
    >>> B1.add_leaf(compile("\\d+"),)
    >>> B1.add_leaf(compile(","), label="comma")
    >>>
    >>> B2 = SyntaxBranch(node_pattern=compile("#"), stop_pattern="$", multirow=False, label="comment")
    >>> B2.add_leaf(compile(".+"), lambda parent, pattern, match, relstart: SyntaxLeaf(parent, match, relstart))
    >>>
    >>> B1.add_branch(B2)
    >>> ast.root.add_branch(B1)

    ~~~~

    Via methods with ``adopt_*`` prefix definitions of branches and/or leaves can be adopted from other branches.

    >>> from re import compile
    >>>
    >>> #                     _ _ _ _ _ _ _ _
    >>> #                    |               |
    >>> #                    B - l - l - l - l ... E
    >>> #                   /
    >>> # R - l - l - l - l ... i
    >>>
    >>> ast = SyntaxTree()
    >>>
    >>> B = SyntaxBranch(...
    >>> B.adopt_self()
    >>> ...
    >>> ast.root.add_branch(B)

    >>> from re import compile
    >>> #                    _ _ _ _ _ _ _[adopt_branches(root) **] _ _ _ _ _ _ _ _ _ _ _
    >>> #                   |     _ _ [adopt_branches(B1) + adopt_leafs(B1)] _ _ _ _ _   |
    >>> #                   |    |                                                    |  |
    >>> #                   |   B1 - l - l - l - E       B3 - l - l - l - l - l - E   |  |
    >>> #                   \\ /      \\                /                               |  |
    >>> #                    /        B2 - l - l - l ... E                            |  |
    >>> #                   /                                                         |  |
    >>> # R - l - l - l - l - l - l ... i         B5 - l - l - l - l - l - E          |  |
    >>> #                         /\\             /                                    |  |
    >>> #                        /  B4 - l - l - l ... E                              |  |
    >>> #                       |_[**] _ _ /   |  \\ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ |  |
    >>> #                                      | _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ |
    >>> ast = SyntaxTree()
    >>>
    >>> B1 = SyntaxBranch(...
    >>> B2 = SyntaxBranch(...
    >>> B3 = SyntaxBranch(...
    >>> B4 = SyntaxBranch(...
    >>> B5 = SyntaxBranch(...
    >>>
    >>> ast.root.add_branch(B1)
    >>>
    >>> B1.add_branch(B2)
    >>> B2.add_branch(B3)
    >>>
    >>> ast.root.add_branch(B4)
    >>>
    >>> B4.add_branch(B5)
    >>>
    >>> B4.adopt_branches(ast.root)
    >>>
    >>> B4.adopt_branches(B1)
    >>>
    >>> B*.add_leaf(...
    >>>
    >>> B4.adopt_leafs(B1)
    >>> ...
    """
    label: Any

    node_pattern: Pattern | str
    _stop_pattern_f_: Callable[[SyntaxBranch, SyntaxLeaf], Pattern | str]
    stop_pattern: Pattern | str | None

    node_leaf: Callable[[SyntaxBranch, Pattern | str, Match, int, SyntaxBranch], SyntaxLeaf]
    stop_leaf: Callable[[SyntaxBranch, Pattern | str, Match, int], SyntaxLeaf]

    _activate_: Callable[[SyntaxBranch], SyntaxBranch]

    branches: tuple[SyntaxBranch]
    leafs: tuple[
        tuple[
            Pattern | str,
            Callable[[SyntaxBranch, Pattern | str, Match, int], SyntaxLeaf],
            Any
        ], ...]

    multirow: bool
    multiline: bool

    __node_leaf__: SyntaxLeaf
    __parent_branch__: SyntaxBranch

    def __init__(self,
                 node_pattern: Pattern | str,
                 stop_pattern: Pattern | str | Callable[[SyntaxBranch, SyntaxLeaf], Pattern | str],
                 node_leaf: Callable[
                                  [SyntaxBranch, Pattern | str, Match, int, SyntaxBranch],
                                  SyntaxLeaf
                 ] = lambda parent, pattern, match, relstart, self: SyntaxLeaf(parent, match, relstart, _node=self),
                 stop_leaf: Callable[
                                  [SyntaxBranch, Pattern | str, Match, int],
                                  SyntaxLeaf
                 ] = lambda parent, pattern, match, relstart: SyntaxLeaf(parent, match, relstart),
                 *,
                 activate: Callable[[SyntaxBranch], SyntaxBranch] = None,
                 multirow: bool = True,
                 multiline: bool = False,
                 label: Any = None):

        self.label = label

        self.node_pattern = node_pattern

        if callable(stop_pattern):
            self._stop_pattern_f_ = stop_pattern
            if activate is None:
                self._activate_ = lambda r: r.snap()
            else:
                self._activate_ = activate
            self.stop_pattern = None
        else:
            self._stop_pattern_f_ = lambda *_: stop_pattern
            if activate is None:
                self._activate_ = lambda r: r
            else:
                self._activate_ = activate
            self.stop_pattern = stop_pattern

        self.node_leaf = node_leaf
        self.stop_leaf = stop_leaf

        self.leafs = tuple()
        self.branches = tuple()
        self.multiline = multiline
        self.multirow = multirow or multiline

    def add_leaf(self, pattern: Pattern | str,
                 leaf: Callable[
                     [SyntaxBranch, Pattern | str, Match, int], SyntaxLeaf
                 ] = lambda parent, pattern, match, relstart: SyntaxLeaf(parent, match, relstart),
                 label: Any = None) -> None:
        """
        Add a leaf of the branch as a ``pattern`` -- :class:`SyntaxLeaf`-factory.

        >>> from re import compile
        >>> branch.add_leaf("regex",)
        >>> branch.add_leaf(compile(","), label="comma")
        >>> branch.add_leaf(compile(".+"), lambda parent, pattern, match, relstart: SyntaxLeaf(parent, match, relstart))

        For later identification, each object can be used as a `label`.
        """
        self.leafs += ((pattern, leaf, label),)

    def add_branch(self, branch: SyntaxBranch) -> None:
        """
        Add a fork to the branch.
        """
        self.branches += (branch,)

    def adopt_leafs(self, branch_or_globals: SyntaxBranch | SyntaxGlobals) -> None:
        """
        Add leaves from another branch to the branch.
        """
        self.leafs += branch_or_globals.leafs

    def adopt_branches(self, branch: SyntaxBranch) -> None:
        """
        Add forks to the branch from another branch.
        """
        self.branches += branch.branches

    def adopt_self(self) -> None:
        """
        Add to the branch itself for a recursion.
        """
        self.branches += (self,)

    def _remove_leafs(self, ref: Any, i_comp: int) -> bool:
        """
        Return if something has been removed.
        """
        leafs = list(self.leafs)
        i = 0
        v = False
        for _ in range(len(leafs)):
            if leafs[i][i_comp] == ref:
                leafs.pop(i)
                v = True
            else:
                i += 1
        self.leafs = tuple(leafs)
        return v

    def _deep_remove(self, mth: str, args: tuple, kwargs: dict, __branch_mem_ids: set) -> bool:
        """
        Return if something has been removed.
        """
        v = False
        for branch in self.branches:
            if (id_ := id(branch)) not in __branch_mem_ids:
                __branch_mem_ids.add(id_)
                v |= getattr(branch, mth)(*args, **kwargs)
                branch._deep_remove(mth, args, kwargs, __branch_mem_ids)
        return v

    def remove_leafs_by_label(self, label: Any, deep: bool = False) -> bool:
        """
        Remove ``SyntaxLeaf`` definitions with `label` [, in the `deep` of all branches and ramifications].
        Return if something has been removed.
        """
        v = self._remove_leafs(label, 2)
        if deep:
            return v | self._deep_remove('_remove_leafs', (label, 2), {}, {id(self)})
        return v

    def remove_leafs_by_pattern(self, pattern: Pattern | str, deep: bool = False) -> bool:
        """
        Remove ``SyntaxLeaf`` definitions with `pattern` [, in the `deep` of all branches and ramifications].
        Return if something has been removed.
        """
        v = self._remove_leafs(pattern, 0)
        if deep:
            return v | self._deep_remove('_remove_leafs', (pattern, 0), {}, {id(self)})
        return v

    def _remove_branches_by_attributes(self, _or_: bool = False, **attributes) -> bool:

        branches = list(self.branches)

        default, pval, compm = {
            True: (False, True, '__eq__'),
            False: (True, False, '__ne__')
        }[_or_]

        i = 0
        v = False
        for _ in range(len(branches)):
            remove = default
            for attr, val in attributes.items():
                if getattr(getattr(branches[i], attr), compm)(val):
                    remove = pval
                    break
            if not remove:
                i += 1
            else:
                v = True
                branches.pop(i)

        self.branches = tuple(branches)
        return v

    @overload
    def remove_branches_by_attributes(self, deep: bool = False, _or_: bool = False,
                                      *,
                                      label: Any = ...,
                                      node_pattern: Pattern | str = ...,
                                      _stop_pattern_f_: Callable[[SyntaxBranch, SyntaxLeaf], Pattern | str] = ...,
                                      stop_pattern: Pattern | str | None = ...,
                                      node_leaf: Callable[[SyntaxBranch, Pattern | str, Match, int, SyntaxBranch], SyntaxLeaf] = ...,
                                      stop_leaf: Callable[[SyntaxBranch, Pattern | str, Match, int], SyntaxLeaf] = ...,
                                      _activate_: Callable[[SyntaxBranch], SyntaxBranch] = ...,
                                      branches: tuple[SyntaxBranch] = ...,
                                      leafs: tuple[tuple[Pattern | str, Callable[[SyntaxBranch, Pattern | str, Match, int], SyntaxLeaf], Any], ...] = ...,
                                      multirow: bool = ...,
                                      multiline: bool = ...,
                                      __start_leaf__: SyntaxLeaf = ...,
                                      __parent_branch__: SyntaxBranch = ...,
                                      **attributes: Any
                                      ) -> None:
        ...

    def remove_branches_by_attributes(self, deep: bool = False, _or_: bool = False, **attributes) -> bool:
        """
        Remove branch ramifications with the applicable attributes [, to the `deep` of all branches and ramifications].
        Remove when all attribute conditions are satisfied `_or_` when only one attribute applies.
        Return if something has been removed.
        """
        v = self._remove_branches_by_attributes(_or_, **attributes)
        if deep:
            return v | self._deep_remove('_remove_branches_by_attributes', (_or_,), attributes, {id(self)})
        return v

    def remove_branches_by_label(self, label: Any, deep: bool = False) -> bool:
        """
        Remove branch ramifications with `label` [, to the `deep` of all branches and ramifications].
        Return if something has been removed.
        """
        return self.remove_branches_by_attributes(deep, label=label)

    def starts(self, string: str, relstart: int, parent: SyntaxBranch) -> SyntaxLeaf | None:
        """
        Return a :class:`SyntaxLeaf` when the branch starts in the `string`.

        Executed inside the pars methods in the :class:`SyntaxTree` and gets the
        `relative starting` point of a substring and the `parent`-``SyntaxBranch``.
        """
        if start_m := search(self.node_pattern, string):
            return self.node_leaf(parent, self.node_pattern, start_m, relstart, self)

    def stops(self, string: str, relstart: int) -> SyntaxLeaf | None:
        """
        Return a :class:`SyntaxLeaf` when the branch stops in the `string`.

        Executed inside the pars methods in the :class:`SyntaxTree` and gets the
        `relative starting` point of a substring.
        """
        if stop_m := search(self.stop_pattern, string):
            return self.stop_leaf(self, self.stop_pattern, stop_m, relstart)

    def snap(self) -> SyntaxBranch:
        """
        Create a "deep copy" (snap) from the current attributes of the ``SyntaxBranch``.
        (Preservation should e.g. exist dependencies to the ``stop_pattern``).
        """
        branch = self.__class__(node_pattern=self.node_pattern, stop_pattern=self.stop_pattern)
        branch._stop_pattern_f_ = self._stop_pattern_f_
        branch.stop_pattern = self.stop_pattern
        branch.node_leaf = self.node_leaf
        branch.stop_leaf = self.stop_leaf
        branch._activate_ = self._activate_
        branch.multirow = self.multirow
        branch.multiline = self.multiline
        branch.branches = self.branches
        branch.leafs = self.leafs
        branch.__node_leaf__ = self.__node_leaf__
        branch.__parent_branch__ = self.__parent_branch__
        return branch

    def poll_stop_pattern(self, node_leaf: SyntaxLeaf = None) -> None:
        """
        Poll the ``stop_pattern``.

        Executed within the ``activate`` method and is only efficient if the
        `stop_pattern` is defined as an executable object.

        :raises AttributeError: node_leaf is not passed and __node_leaf__ is not yet set in the object.
        """
        self.stop_pattern = self._stop_pattern_f_(self, (node_leaf if node_leaf is not None else self.__node_leaf__))

    def activate(self, node_leaf: SyntaxLeaf, parent: SyntaxBranch) -> SyntaxBranch:
        """
        Set the ``__node_leaf__`` and ``__parent_branch__`` attributes, poll the ``stop_pattern``
        and return the activated version of the ``SyntaxBranch`` object.

        Executed inside the pars methods in the :class:`SyntaxTree` and gets the node-:class:`SyntaxLeaf`
        and the parent ``SyntaxBranch``.
        """
        self.__node_leaf__ = node_leaf
        self.__parent_branch__ = parent
        self.poll_stop_pattern(node_leaf)
        return self._activate_(self)

    def leaf_mapping(self, string: str, relstart: int, _out_: list[SyntaxLeaf]) -> list[SyntaxLeaf]:
        """
        Apply each branch leaf definition to the `string`.
        Append matches as :class:`SyntaxLeaf` objects to the list `_out_`.

        `relstart` specifies the start position of a substring.

        This method is executed inside the parsing methods in the :class:`SyntaxTree`.
        """
        for itm in self.leafs:
            _out_.extend(map(
                lambda m: itm[1](self, itm[0], m, relstart),
                finditer(itm[0], string)
            ))
        return _out_

    def branch_mapping(self, string: str, relstart: int, _out_: list[SyntaxLeaf]) -> list[SyntaxLeaf]:
        """
        Apply each definition of nodes to branches to the "string".
        Append matches as :class:`SyntaxLeaf` objects to the list `_out_`.

        `relstart` specifies the start position of a substring.

        This method is executed inside the parsing methods in the :class:`SyntaxTree`.
        """
        for branch in self.branches:
            if _start_leaf := branch.starts(string, relstart, self):
                _out_.append(_start_leaf)
        return _out_

    def __repr__(self) -> str:
        return f"<({self.__class__.__name__} {repr(self.node_pattern)} {repr(self.label)})>"


class SyntaxLeaf:
    """
    The syntax leaf object is generated as the result of a parse by :class:`SyntaxTree` and is used for further
    processing.

    The object contains the ``parent`` :class:`SyntaxBranch` or :class:`SyntaxGlobals`, the ``re.Match``,
    the relative start ( ``relstart`` ) of a substring and, if the leaf represents the beginning of a
    ``SyntaxBranch``, the beginning branch under ``node``.

    The `priority` of a leaf over others found in a string is realized with ``__lt__``.

    The parameterization can be defined differently by an executable object, this executable object gets
    this ``SyntaxLeaf`` and the other ``SyntaxLeaf`` and must return a boolean value if this ``SyntaxLeaf`` has a
    higher priority than the other.
    If ``True`` is passed to `priority`, the earliest leaf has the highest priority, and if there is a tie
    the match with the largest span has priority. If the `priority` parameter is ``False``, the earliest leaf
    with the smallest span has priority.

    Since the string is sliced during the parsing process, the ``start``/``end``/``span`` methods of the ``re.Match``
    object (also realized as properties in the ``SyntaxLeaf``) may not return the actual values with reference to the
    passed string; therefore, the values can be obtained considering the relative starting point via the properties
    with ``total_*`` prefix.
    """
    parent: SyntaxGlobals | SyntaxBranch
    match: Match
    relstart: int

    node: SyntaxBranch | None

    _priority: Callable[[SyntaxLeaf, SyntaxLeaf], bool]

    _start: Callable[[], int]
    _end: Callable[[], int]
    _span: Callable[[], int]
    _total_start: Callable[[], int]
    _total_end: Callable[[], int]
    _total_span: Callable[[], int]

    @property
    def start(self) -> int:
        return self._start()

    @property
    def end(self) -> int:
        return self._end()

    @property
    def span(self) -> tuple[int, int]:
        return self._start(), self._end()

    @property
    def total_start(self) -> int:
        return self._total_start()

    @property
    def total_end(self) -> int:
        return self._total_end()

    @property
    def total_span(self) -> tuple[int, int]:
        return self._total_start(), self._total_end()

    def __init__(self,
                 parent: SyntaxGlobals | SyntaxBranch,
                 match: Match,
                 relstart: int,
                 priority: Callable[[SyntaxLeaf, SyntaxLeaf], bool] | bool = True,
                 _node: SyntaxBranch = None):
        self.parent = parent
        self.match = match
        self.relstart = relstart

        if callable(priority):
            pass
        elif priority:
            def priority(_self: SyntaxLeaf, other: SyntaxLeaf) -> bool:
                selfspan = _self.match.span()
                otherspan = other.match.span()
                if selfspan[0] > otherspan[0]:
                    return False
                elif selfspan[0] == otherspan[0]:
                    return selfspan[1] > otherspan[1]
                else:
                    return True
        else:
            def priority(_self: SyntaxLeaf, other: SyntaxLeaf) -> bool:
                return _self.match.span() < other.match.span()

        self._priority = priority

        self.node = _node

        def __start(*_):
            x = match.start()
            self._start = lambda *_: x
            return x

        self._start = __start

        def __end(*_):
            x = match.end()
            self._end = lambda *_: x
            return x

        self._end = __end

        def __tstart(*_):
            x = self.relstart + self._start()
            self._total_start = lambda *_: x
            return x

        self._total_start = __tstart

        def __tend(*_):
            x = self.relstart + self._end()
            self._total_end = lambda *_: x
            return x

        self._total_end = __tend

    def __lt__(self, other: SyntaxLeaf) -> bool:
        return self._priority(self, other)

    def __repr__(self) -> str:
        return f"<({self.__class__.__name__} {repr(self.match)} node: {repr(self.node)})>"
