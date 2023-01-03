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

from typing import Callable, Literal, overload
from abc import abstractmethod

try:
    from ..buffer import TextBuffer
    from .._buffercomponents import _Row, ChunkLoad
    from .items import VisRowItem
    from .highlightertree import HighlighterGlobals
    __4doc1 = HighlighterGlobals
    from ...iodata.sgr import SGRWrap
    __4doc2 = SGRWrap
except ImportError:
    pass

from ...iodata.esccontainer import EscSegment, EscContainer
from .._buffercomponents._suit import _Suit
from .highlightertree import (HighlighterLeaf,
                              HighlighterBranch,
                              _HighlightTreeRegex,
                              _HighlightTreeAdvanced)


class HighlighterBase:
    """
    The most rudimentary highlighter component of a display, only the tab representations are implemented.
    """

    __buffer__: TextBuffer

    _vis_tab: Callable[[int], str]

    _active_suit: _Suit[HighlightRegex] | _Suit[HighlightAdvanced] | None

    _chunkid_cache: int | None
    _row_num_cache: int | None

    _prep_by_chunkload_interface_: Callable[[ChunkLoad], None]
    _prep_by_writeitem_interface_: Callable[[int, bool, _Row], None]

    _highlighted_rows_cache_max: int
    _highlighted_row_segments_max: int

    _enddef: tuple[Literal[0, 1, 2, None, "\n", ""], ...]

    __slots__ = ('__buffer__', '_vis_tab', '_active_suit',
                 '_prep_by_chunkload_interface_', '_prep_by_writeitem_interface_',
                 '_row_num_cache', '_chunkid_cache',
                 '_highlighted_rows_cache_max', '_highlighted_row_segments_max', '_enddef')

    def __bool__(self) -> bool:
        return type(self) != HighlighterBase

    def __init__(self, __buffer__: TextBuffer = None):
        self.__buffer__ = __buffer__
        self._prep_by_chunkload_interface_ = self._origin_prep_by_chunkload
        self._prep_by_writeitem_interface_ = self._origin_prep_by_writeitem
        self._active_suit = None

        self._enddef = (1, "\n")
        self._highlighted_rows_cache_max = 1000
        self._highlighted_row_segments_max = 100
        self._vis_tab = lambda n: ' ' * n

    @overload
    def settings(self, *,
                 vis_tab: Callable[[int], str] | None = ...
                 ) -> None:
        """
        Set the function to convert the relative tab range or convert to blanks when ``None`` is passed.
        """
        ...

    def settings(self, **kwargs) -> None:
        try:
            if (_vis_tab := kwargs.pop('vis_tab')) is None:
                def _vis_tab(n: int): return ' ' * n
            self._vis_tab = _vis_tab
        except KeyError:
            pass
        try:
            self._highlighted_rows_cache_max = kwargs.pop('highlighted_rows_cache_max') or 1000
        except KeyError:
            pass
        try:
            self._highlighted_row_segments_max = kwargs.pop('highlighted_row_segments_max') or 100
        except KeyError:
            pass
        try:
            if (enddef := kwargs.pop('line_end_definition')) is None:
                enddef = ("\n",)
        except KeyError:
            pass
        else:
            self._enddef = enddef + tuple({None: 0, "\n": 1, "": 2}[i] for i in enddef)
        if kwargs:
            raise ValueError(kwargs)

    def _tabvisual(self, row: _Row, vis_slice: tuple[int, int | None] | None, tab_spaces: tuple[int, ...]
                   ) -> EscSegment | EscContainer:
        if not vis_slice:
            vis_row = EscSegment('')
        elif vis_slice[1]:
            vis_row = str()
            for i in range(_l := len(tab_spaces)):
                vis_row += row.data_cache.raster[i]
                tab = tab_spaces[i]
                if len(vis_row) + tab >= vis_slice[0]:
                    vis_row = EscSegment(vis_row) + self._vis_tab(tab)
                    for _i in range(i + 1, _l):
                        vis_row += EscSegment(row.data_cache.raster[_i]) + self._vis_tab(tab_spaces[_i])
                        if len(vis_row) > vis_slice[1]:
                            break
                    break
                vis_row += chr(160) * tab  # NBSP " "
            else:
                vis_row = EscSegment(vis_row)
        elif vis_slice[0]:
            vis_row = str()
            for i in range(_l := len(tab_spaces)):
                vis_row += row.data_cache.raster[i]
                tab = tab_spaces[i]
                if len(vis_row) + tab >= vis_slice[0]:
                    vis_row = EscSegment(vis_row) + self._vis_tab(tab)
                    for _i in range(i + 1, _l):
                        vis_row += EscSegment(row.data_cache.raster[_i]) + self._vis_tab(tab_spaces[_i])
                    break
                vis_row += chr(160) * tab  # NBSP " "
            else:
                vis_row = EscSegment(vis_row)
        else:
            vis_row = EscSegment('')
            for seg, tab in zip(row.data_cache.raster, tab_spaces):
                vis_row += EscSegment(seg) + self._vis_tab(tab)
        return vis_row

    def __call__(self, rowitem: VisRowItem) -> EscSegment | EscContainer:
        return self._tabvisual(rowitem.row, rowitem.row_frame.vis_slice, rowitem.tab_spaces)

    @staticmethod
    def _apply_leafs(vis_row: EscContainer | EscSegment,
                     vis_slice: tuple[int, int | None] | None,
                     leafs: list[HighlighterLeaf],
                     setrowcache: Callable[[tuple[int, int | None] | None,
                                             EscContainer | EscSegment], EscContainer | EscSegment]
                     ) -> EscContainer:

        if not vis_slice:
            for leaf in leafs:
                vis_row = leaf(vis_row)
        elif not vis_slice[0]:
            if vis_slice[1] is None:
                for leaf in leafs:
                    vis_row = leaf(vis_row)
            else:
                for leaf in leafs:
                    if leaf.visual_span()[0] >= vis_slice[1]:
                        continue
                    vis_row = leaf(vis_row)
        elif vis_slice[1] is None:
            for leaf in leafs:
                if leaf.visual_span()[1] < vis_slice[0]:
                    continue
                vis_row = leaf(vis_row)
        else:
            for leaf in leafs:
                visspan = leaf.visual_span()
                if visspan[0] >= vis_slice[1] or visspan[1] < vis_slice[0]:
                    continue
                vis_row = leaf(vis_row)

        return setrowcache(vis_slice, vis_row)

    def suit(self, mode: Literal['sum', 'null'], leave_active: bool = False
             ) -> _Suit[HighlighterBase] | _Suit[HighlightRegex] | _Suit[HighlightAdvanced]:
        """
        Return a context manager, for a resource-saving preparation of the highlighter inside the suit.
        Leave an active suit when `leave_active` is ``True``.

        (Methods within the :class:`TextBuffer` and its components
        prepare the Highlighter and communicate relevant changes to the data)

        Modes:
            - ``"sum"``:
                Record changes in a rough way and apply the changes only when exiting.
            - ``"null"``:
                Do not record any changes and recalculate the highlighting based on the total data.
        """
        if self._active_suit:
            if leave_active:
                self._active_suit.__exit__(None, None, None)
            else:
                return _Suit(lambda: self, lambda *_: None)
        if mode[0] == 's':
            def enter(_):
                self._chunkid_cache = self._row_num_cache = None
                self._prep_by_chunkload_interface_ = self._sum_prep_by_chunkload
                self._prep_by_writeitem_interface_ = self._sum_prep_by_writeitem
                return self

            def exit_(*_):
                self._prep_by_chunkload_interface_ = self._origin_prep_by_chunkload
                self._prep_by_writeitem_interface_ = self._origin_prep_by_writeitem
                self._prepare_by_summary()

            return _Suit(enter, exit_)

        else:
            def enter(_):
                self._prep_by_chunkload_interface_ = lambda *_: None
                self._prep_by_writeitem_interface_ = lambda *_: None
                return self

            def exit_(*_):
                self._prep_by_chunkload_interface_ = self._origin_prep_by_chunkload
                self._prep_by_writeitem_interface_ = self._origin_prep_by_writeitem
                self._prepare_by_none()

            return _Suit(enter, exit_)

    @abstractmethod
    def _origin_prep_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        ...

    @abstractmethod
    def _origin_prep_by_writeitem(self, work_row: int, gt_too: bool, _row: _Row = None) -> None:
        ...

    @abstractmethod
    def _sum_prep_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        ...

    @abstractmethod
    def _sum_prep_by_writeitem(self, work_row: int, gt_too: bool, _row: _Row = None) -> None:
        ...

    @abstractmethod
    def _prepare_by_summary(self) -> None:
        ...

    @abstractmethod
    def _prepare_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        ...

    @abstractmethod
    def _prepare_by_writeitem(self, work_row: int, gt_too: bool, _row: _Row = None) -> None:
        ...

    @abstractmethod
    def _prepare_by_none(self) -> None:
        ...

    @abstractmethod
    def _announce(self, rowitems: list[VisRowItem]) -> None:
        ...

    @abstractmethod
    def purge_cache(self) -> None:
        ...


class HighlightRegex(HighlighterBase, _HighlightTreeRegex):
    """
    This Highlighter component enables the highlighting of individual patterns.

    Highlighter definitions are added via the `globals` property (:class:`HighlighterGlobals`).

    >>> # enable trailing spaces
    >>> from vtframework.iodata.sgr import Ground
    >>> __highlighter__: HighlightRegex
    >>> __highlighter__.globals.add(pattern=compile("\\s*$"), sgr_params=Ground.name("cyan"))

    Due to the high computational effort of highlighting, this object has a complex cache.
    Methods in the :class:`TextBuffer` and its components prepare the highlighter during processing
    and communicate changes. The limit of stored rows is 1000 by default, the maximum number of
    allowed segments in the row is set to 100 by default (read :class:`EscContainer`'s documentation
    for more information).
    """

    _rows_cache: dict[int, _HlRowCache]

    __slots__ = ('_rows_cache',)

    def __init__(self, __buffer__: TextBuffer):
        HighlighterBase.__init__(self, __buffer__)
        _HighlightTreeRegex.__init__(self)
        self._rows_cache = dict()

    def _origin_prep_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        pass

    def _origin_prep_by_writeitem(self, work_row: int, gt_too: bool, _row=None) -> None:
        self._rows_cache.pop(work_row, None)
        if gt_too:
            for k in tuple(self._rows_cache.keys()):
                if k > work_row:
                    self._rows_cache.pop(k)

    def _sum_prep_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        if not self._chunkid_cache:
            self._chunkid_cache = bool(chunk_load)

    def _sum_prep_by_writeitem(self, work_row: int, gt_too, _row=None) -> None:
        try:
            self._row_num_cache = min(work_row, self._row_num_cache)
        except TypeError:
            self._row_num_cache = work_row

    def _prepare_by_summary(self) -> None:
        if self._chunkid_cache:
            self._rows_cache.clear()
        elif self._row_num_cache is not None:
            self._origin_prep_by_writeitem(self._row_num_cache, True)

    def _prepare_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        self._prep_by_chunkload_interface_(chunk_load)

    def _prepare_by_writeitem(self, work_row: int, gt_too: bool, _row: _Row = None) -> None:
        self._prep_by_writeitem_interface_(work_row, gt_too, _row)

    def _prepare_by_none(self) -> None:
        self._rows_cache.clear()

    def _announce(self, rowitems: list[VisRowItem]) -> None:
        if len(self._rows_cache) > self._highlighted_rows_cache_max:
            self._rows_cache.clear()

    def __call__(self, rowitem: VisRowItem) -> EscSegment | EscContainer:
        if rowitem.row_frame.vis_slice:
            try:
                row_cache = self._rows_cache[rowitem.row.__row_num__]
                try:
                    return row_cache.__getitem__(rowitem.row_frame.vis_slice)
                except KeyError as e:
                    self.map_globals(_string := rowitem.row.content, rowitem.row, matches := list())
                    return self._apply_leafs(self._tabvisual(rowitem.row, e.args[1], rowitem.tab_spaces),
                                             e.args[1],
                                             matches,
                                             e.args[3])
            except KeyError:
                self._rows_cache[rowitem.row.__row_num__] = (
                    hlrc := _HlRowCache(self._highlighted_row_segments_max))
                self.map_globals(_string := rowitem.row.content, rowitem.row, matches := list())
                return self._apply_leafs(self._tabvisual(rowitem.row, rowitem.row_frame.vis_slice, rowitem.tab_spaces),
                                         rowitem.row_frame.vis_slice,
                                         matches,
                                         hlrc._setnew)
        else:
            return EscSegment('')
        
    def purge_cache(self) -> None:
        """
        Clean the cache. The next highlighting of the display is determined from scratch.
        """
        self._rows_cache.clear()

    @overload
    def settings(self, *,
                 highlighted_rows_cache_max: int | None = ...,
                 highlighted_row_segments_max: int | None = ...,
                 vis_tab: Callable[[int], str] | None = ...
                 ) -> None:
        """
        Set an upper limit of cached rows over `highlighted_rows_cache_max` (default: 1000) and/or
        the maximum number of segments per row over `highlighted_row_segments_max` (default: 100),
        read :class:`EscContainer`'s documentation for more information.
        Set the function which converts the relative tab range via `vis_tab` or convert to blanks when
        ``None`` is passed.
        """
        ...

    def settings(self, **kwargs) -> None:
        super().settings(**kwargs)


class HighlightAdvanced(HighlighterBase, _HighlightTreeAdvanced):
    """
    This highlighter component allows a complex design of the highlighting through a syntax tree.

    Designing
    ~~~~~~~~~

    The branches of the highlight syntax tree are defined by :class:`HighlighterBranch` objects and are attached to 
    the main ``root`` branch; the start/node, termination, and leaves of a branch (incl. root branch) are created as
    RegularExpression -- :class:`SGRWrap`-parameter pairs.

    Leaves defined in ``globals`` (:class:`HighlighterGlobals`) apply independently of currently active branches.

    >>> from re import compile
    >>> from vtframework.iodata.sgr import Fore
    >>> __highlighter__: HighlightAdvanced
    >>>
    >>> #                     _ _ _ _ _ _ _ _
    >>> #                    |               |
    >>> #                    B - l - l - g - l ... E
    >>> #                   /
    >>> # R - l - g - l - l ... i
    >>>
    >>> B = HighlighterBranch(node_pattern=compile("\\("), stop_pattern=compile("\\)"))
    >>> B.adopt_self()
    >>>
    >>> B.add_leaf(compile("regex"), Fore.red)
    >>> ...
    >>> __highlighter__.root.add_branch(B)
    >>>
    >>> __highlighter__.globals.add(compile("regex"), Fore.green)

    ~~~~

    >>> from re import compile
    >>> __highlighter__: HighlightAdvanced
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
    >>>
    >>> B1 = HighlighterBranch(node_pattern=compile('"'), stop_pattern=compile('"'))
    >>> B2 = HighlighterBranch(...
    >>> B3 = HighlighterBranch(...
    >>>
    >>> __highlighter__.root.add_branch(B1)
    >>> __highlighter__.root.add_branch(B2)
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
    
    Via the :class:`HighlighterBranch` methods with ``adopt_*`` prefix definitions of branches and/or leaves can be 
    adopted from other branches.

    >>> from re import compile
    >>> __highlighter__: HighlightAdvanced
    >>>
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
    >>>
    >>> B1 = HighlighterBranch(...
    >>> B2 = HighlighterBranch(...
    >>> B3 = HighlighterBranch(...
    >>> B4 = HighlighterBranch(...
    >>> B5 = HighlighterBranch(...
    >>>
    >>> __highlighter__.root.add_branch(B1)
    >>>
    >>> B1.add_branch(B2)
    >>> B2.add_branch(B3)
    >>>
    >>> __highlighter__.root.add_branch(B4)
    >>>
    >>> B4.add_branch(B5)
    >>>
    >>> B4.adopt_branches(__highlighter__.root)
    >>>
    >>> B4.adopt_branches(B1)
    >>>
    >>> B*.add_leaf(...
    >>>
    >>> B4.adopt_leafs(B1)
    >>> ...

    Parsing Process
    ~~~~~~~~~~~~~~~

    When using the special characters of regular expressions that refer to the beginning or end of a string,
    such as ``"^"`` or ``"\\Z"``, it must be noted that the row is sliced during parsing.
    The following illustration sketches the parsing process.

    >>> from re import compile
    >>>
    >>> square_bracket_branch = HighlighterBranch(node_pattern=compile("\\[node]"), stop_pattern=compile("\\[end]"))
    >>> curly_bracket_branch = HighlighterBranch(node_pattern=compile("\\{node}"), stop_pattern=compile("\\{end}"))
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

    ~~~~

    Due to the high computational effort of highlighting, this object has a complex cache.
    Methods in the :class:`TextBuffer` and its components prepare the highlighter during processing
    and communicate changes. The limit of stored rows is 1000 by default, the maximum number of
    allowed segments in the row is set to 100 by default (read :class:`EscContainer`'s documentation
    for more information).
    """
    
    _rows_cache: dict[
        int, tuple[int,
                   _HlRowCache,
                   list[HighlighterLeaf] | None,
                   list[HighlighterBranch]]]
    _chunk_cache: list[tuple[int, int, list[HighlighterBranch]]]

    __slots__ = ('_rows_cache', '_chunk_cache')

    def __init__(self, __buffer__: TextBuffer):
        HighlighterBase.__init__(self, __buffer__)
        _HighlightTreeAdvanced.__init__(self)
        self._chunk_cache = list()
        self._rows_cache = dict()

    def _origin_prep_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        self.current_branches.clear()  # cleanup
        if not (cur_t_id := self.__buffer__.__swap__.current_chunk_ids[0]):
            # no upper chunks
            self._chunk_cache.clear()
        elif chunk_load:
            if chunk_load.edited_ran and chunk_load.edited_ran[0] and chunk_load.edited_ran[0] < 0:
                # upper chunk processed
                # delete obsolete cache positions based on the position processed in the upper part
                if chunk_load.top_nload is not None:
                    self._chunk_cache = self._chunk_cache[:abs(max(chunk_load.edited_ran[0] + 1,
                                                                   chunk_load.top_id + chunk_load.top_nload + 1))]
                else:
                    self._chunk_cache = self._chunk_cache[:abs(chunk_load.edited_ran[0] + 1)]
                if chunk_load.top_cut:
                    # expand the cache, get the final data from the item instead of retrieving it from the db
                    self._extend_chunk_cache(-(len(self._chunk_cache) + 1), (cur_t_id + len(chunk_load.top_cut)) - 1,
                                             chunk_load.top_cut)
                else:
                    # expand the cache with the remaining top positions in the db
                    self._extend_chunk_cache(-(len(self._chunk_cache) + 1), cur_t_id - 1)
            elif chunk_load.top_cut is not None:
                # rows dumped to top or bottom
                # delete obsolete cache items based on the data dumped to top
                self._chunk_cache = self._chunk_cache[:abs(cur_t_id) - len(chunk_load.top_cut)]
                # expand the cache, get the final data from the item instead of retrieving it from the db
                self._extend_chunk_cache(-(len(self._chunk_cache) + 1), (cur_t_id + len(chunk_load.top_cut)) - 1,
                                         chunk_load.top_cut)
            else:
                # a specific chunk loaded or chunks eventually loaded
                # delete obsolete cache positions based on the current position
                # expand the cache with the remaining top positions in the db
                self._chunk_cache = self._chunk_cache[:abs(cur_t_id)]
                self._extend_chunk_cache(-(len(self._chunk_cache) + 1), cur_t_id - 1)

    def _origin_prep_by_writeitem(self, work_row: int, gt_too: bool, _row: _Row = None) -> None:
        self.current_branches.clear()  # cleanup
        if not self.__buffer__.__swap__.current_chunk_ids[0]:
            self._chunk_cache.clear()
        if gt_too:
            self._rows_cache.pop(work_row, None)
            for k in tuple(self._rows_cache.keys()):
                if k > work_row:
                    self._rows_cache.pop(k)
        else:
            try:
                row_cache = self._rows_cache.pop(work_row)
                if _row is not None:
                    if work_row > 0:
                        regions = self._rows_cache[work_row - 1][3].copy()
                    else:
                        regions = list()
                    self._branch_growing_recursion(_row.content, _row.end in self._enddef, regions)
                    if row_cache[3] != regions:
                        for k in tuple(self._rows_cache.keys()):
                            if k > work_row:
                                self._rows_cache.pop(k)
                else:
                    for k in tuple(self._rows_cache.keys()):
                        if k > work_row:
                            self._rows_cache.pop(k)
            except KeyError:
                for k in tuple(self._rows_cache.keys()):
                    if k > work_row:
                        self._rows_cache.pop(k)

    def _sum_prep_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        if chunk_load:
            if chunk_load.edited_ran and chunk_load.edited_ran[0] and (_eid := chunk_load.edited_ran[0] + 1) <= 0:
                if chunk_load.spec_position and chunk_load.spec_position < 0:
                    _id = chunk_load.spec_position
                    if chunk_load.top_nload is not None:
                        _id += chunk_load.top_nload
                else:
                    _id = _eid
            elif chunk_load.spec_position and chunk_load.spec_position < 0:
                _id = _eid = chunk_load.spec_position + 1
                if chunk_load.top_nload is not None:
                    _id += chunk_load.top_nload
            elif chunk_load.top_nload:
                _id = _eid = chunk_load.top_id + chunk_load.top_nload
            elif chunk_load.top_cut:
                _id = _eid = chunk_load.top_id
            else:
                return
            try:
                self._chunkid_cache = max(_id, _eid, self._chunkid_cache)
            except TypeError:
                self._chunkid_cache = max(_id, _eid)

    def _sum_prep_by_writeitem(self, work_row: int, gt_too, _row=None) -> None:
        try:
            self._row_num_cache = min(work_row, self._row_num_cache)
        except TypeError:
            self._row_num_cache = work_row

    def _prepare_by_summary(self) -> None:
        self.current_branches.clear()  # cleanup
        if not (cur_t_id := self.__buffer__.__swap__.current_chunk_ids[0]):
            # no upper chunks
            self._rows_cache.clear()
            self._chunk_cache.clear()
        elif self._chunkid_cache is not None:
            self._rows_cache.clear()
            self._chunk_cache = self._chunk_cache[:abs(self._chunkid_cache)]
            self._extend_chunk_cache(-(len(self._chunk_cache) + 1), cur_t_id - 1)
        elif self._row_num_cache is not None:
            self._origin_prep_by_writeitem(self._row_num_cache, True)

    def _prepare_by_chunkload(self, chunk_load: ChunkLoad) -> None:
        self._prep_by_chunkload_interface_(chunk_load)

    def _prepare_by_writeitem(self, work_row: int, gt_too: bool, _row: _Row = None) -> None:
        self._prep_by_writeitem_interface_(work_row, gt_too, _row)

    def _prepare_by_none(self) -> None:
        # mallet method
        self._chunk_cache.clear()
        self._rows_cache.clear()
        self.current_branches.clear()
        if cur_t_id := self.__buffer__.__swap__.current_chunk_ids[0]:
            self._extend_chunk_cache(-1, cur_t_id - 1)

    def _extend_chunk_cache(self, _from: int, _to_exl: int, _and_with: list[list[_Row]] = None) -> None:
        if self._chunk_cache:
            self.current_branches = self._chunk_cache[-1][-1].copy()
        if _from:
            for _id in range(_from, _to_exl, -1):
                chunk = self.__buffer__.__swap__.get_chunk(_id)
                for _row in chunk.rows:
                    self.branch_growing(_row[0], _row[1] in self._enddef, self.current_branches)
                self._chunk_cache.append(
                    (chunk.start_point_row, chunk.start_point_data, self.current_branches.copy()))
        if _and_with:
            for rows in _and_with:
                for _row in rows:
                    self.branch_growing(_row.content, _row.end in self._enddef, self.current_branches)
                self._chunk_cache.append(
                    (rows[0].__row_num__,
                     rows[0].__data_start__,
                     self.current_branches.copy()))

    def _announce(self, rowitems: list[VisRowItem]) -> None:

        if len(self._rows_cache) > self._highlighted_rows_cache_max:
            self._rows_cache.clear()

        if self._chunk_cache:
            self.current_branches = self._chunk_cache[-1][-1].copy()

        if rownum := rowitems[0].row.__row_num__:
            s_row = self.__buffer__.rows[0].__row_num__
            last_cr = None
            e = rownum - 1
            for cache_row in self._rows_cache:
                if s_row <= cache_row <= e:
                    if last_cr is None or cache_row > last_cr:
                        last_cr = cache_row
            if last_cr is not None:
                s = ((e := rowitems[0].row.__row_index__) - (rowitems[0].row.__row_num__ - last_cr)) + 1
                self.current_branches = self._rows_cache[last_cr][3].copy()
                for row in self.__buffer__.rows[s:e]:
                    self.branch_growing(row.content, row.end in self._enddef, self.current_branches)
                    self._rows_cache[row.__row_num__] = (
                        row.__data_start__, _HlRowCache(self._highlighted_row_segments_max), None,
                        self.current_branches.copy())
            else:
                for row in self.__buffer__.rows[:rowitems[0].row.__row_index__]:
                    self.branch_growing(row.content, row.end in self._enddef, self.current_branches)
                    self._rows_cache[row.__row_num__] = (
                        row.__data_start__, _HlRowCache(self._highlighted_row_segments_max), None,
                        self.current_branches.copy())

    def __call__(self, rowitem: VisRowItem) -> EscSegment | EscContainer:
        try:
            row_cache = self._rows_cache[rowitem.row.__row_num__]
            matches = row_cache[2]
            if rowitem.row_frame.vis_slice:
                try:
                    vis_row = row_cache[1].__getitem__(rowitem.row_frame.vis_slice)
                    self.current_branches = row_cache[3].copy()
                    return vis_row
                except KeyError as e:
                    if matches is None:
                        self.current_branches = row_cache[3].copy()
                        self.map_leafs(rowitem.row.content, rowitem.row, rowitem.row.end in self._enddef, self.current_branches, matches := list())
                        self.map_globals(rowitem.row.content, rowitem.row, matches)
                        self._rows_cache[rowitem.row.__row_num__] = (row_cache[0],
                                                                     row_cache[1],
                                                                     matches,
                                                                     row_cache[3])
                    else:
                        self.current_branches = row_cache[3].copy()
                    try:
                        return self._apply_leafs(self._tabvisual(rowitem.row, e.args[1], rowitem.tab_spaces),
                                                 e.args[1], matches, e.args[3])
                    except Exception as _e:
                        raise Exception(_e.__traceback__.tb_next, e, matches, rowitem)
            else:
                self.current_branches = row_cache[3].copy()
                return EscSegment('')
        except KeyError:
            self.map_leafs(rowitem.row.content, rowitem.row, rowitem.row.end in self._enddef, self.current_branches, matches := list())
            self.map_globals(rowitem.row.content, rowitem.row, matches)
            self._rows_cache[rowitem.row.__row_num__] = (rowitem.row.__data_start__,
                                                         (hlrc := _HlRowCache(self._highlighted_row_segments_max)),
                                                         matches,
                                                         self.current_branches.copy())
            if rowitem.row_frame.vis_slice:
                return self._apply_leafs(self._tabvisual(rowitem.row, rowitem.row_frame.vis_slice, rowitem.tab_spaces),
                                         rowitem.row_frame.vis_slice, matches, hlrc._setnew)
            else:
                return EscSegment('')

    def purge_cache(self) -> None:
        """
        Clean the cache. The next highlighting of the display is determined from scratch.
        """
        self._chunk_cache.clear()
        self._rows_cache.clear()

    @overload
    def settings(self, *,
                 highlighted_rows_cache_max: int | None = ...,
                 highlighted_row_segments_max: int | None = ...,
                 vis_tab: Callable[[int], str] | None = ...,
                 line_end_definition: tuple[Literal[None, "\n", ""], ...] | None = ...
                 ) -> None:
        """
        Set an upper limit of cached rows over `highlighted_rows_cache_max` (default: 1000) and/or
        the maximum number of segments per row over `highlighted_row_segments_max` (default: 100),
        read :class:`EscContainer`'s documentation for more information.
        Set the function which converts the relative tab range via `vis_tab` or convert to blanks when
        ``None`` is passed.
        Define the line-breaking ends of a :class:`_Row` via `line_end_definition`; the definition is 
        evaluated in connection with the ``multiline`` parameterization of a :class:`HighlighterBranch`.
        """
        ...

    def settings(self, **kwargs) -> None:
        super().settings(**kwargs)


class _HlRowCache:
    slice_key: tuple[int, int | None]
    slice_val: EscSegment | EscContainer
    default_val: EscSegment | EscContainer
    _smax_: Callable[[tuple[int, int | None]], None]

    __slots__ = ('slice_key', 'slice_val', 'default_val', '_smax_')

    def __init__(self, segments_max: int):
        if not segments_max:
            def smax(__item):
                raise KeyError('segments max: !make', __item, '!set', self._setnew)
        else:
            def smax(__item):
                if self.slice_val.n_segments() > segments_max:
                    raise KeyError('segments max: !make', __item, '!set', self._setnew)
        self._smax_ = smax

    def __getitem__(self, item: tuple[int, int | None] | None) -> EscSegment | EscContainer:
        try:
            return self.default_val
        except AttributeError:
            if not item:
                raise KeyError
            try:
                cache_slice = self.slice_key
            except AttributeError:
                raise KeyError('key not set: !make', item, '!set', self._setnew)
            self._smax_(item)
            if cache_slice[1] is None:
                if item[0] >= cache_slice[0]:
                    return self.slice_val
                else:
                    try:
                        if item[1] >= cache_slice[0]:  # TypeError possible
                            raise KeyError(
                                'cache stop == None: item start < cache start: item stop >= cache start: !make',
                                (item[0], cache_slice[0]),
                                '!set', self._alnonestop)
                        else:
                            raise KeyError(
                                'cache stop == None: item start < cache start: item stop < cache start: !make',
                                item,
                                '!set', self._setnew)
                    except TypeError:
                        raise KeyError(
                            'cache stop == item stop == None: item start < cache start: !make',
                            (item[0], cache_slice[0]),
                            '!set', self._alnonestop)
            else:
                try:
                    if cache_slice[1] >= item[1]:  # TypeError possible
                        if cache_slice[0] <= item[0]:
                            return self.slice_val
                        elif item[1] >= cache_slice[0]:
                            raise KeyError(
                                'cache stop >= item stop: cache start > item start: item stop >= cache start: !make',
                                (item[0], cache_slice[0]),
                                '!set', self._appendl)
                        else:
                            raise KeyError(
                                'cache stop >= item stop: cache start > item start: item stop < cache start: !make',
                                item,
                                '!set', self._setnew)
                    elif cache_slice[0] <= item[0] < cache_slice[1]:
                        raise KeyError(
                            'cache stop < item stop: cache start <= item start < cache stop: !make',
                            (cache_slice[1], item[1]),
                            '!set', self._appendr)
                    else:
                        raise KeyError('cache stop < item stop: cache start > item start: !make', item,
                                       '!set', self._setnew)
                except TypeError:
                    if cache_slice[0] <= item[0] < cache_slice[1]:
                        raise KeyError('item stop == None: cache start <= item start < cache stop: !make',
                                       (cache_slice[1], None),
                                       '!set', self._arnonestop)
                    else:
                        raise KeyError('item stop == None: cache start > item start: !make', item,
                                       '!set', self._setnew)

    def _arnonestop(self, key: tuple[int, int | None] | None,
                    value: EscSegment | EscContainer) -> EscSegment | EscContainer:
        # self.slice_val = self.slice_val[:key[0]] + value[key[0]:]
        self.slice_val = self.slice_val[:key[0]].assimilate(value[key[0]:])
        self.slice_key = (self.slice_key[0], key[1])
        if not self.slice_key[0]:
            self.default_val = self.slice_val
        return self.slice_val

    def _appendr(self, key: tuple[int, int | None] | None,
                 value: EscSegment | EscContainer) -> EscSegment | EscContainer:
        # self.slice_val = self.slice_val[:key[0]] + value[key[0]:]
        self.slice_val = self.slice_val[:key[0]].assimilate(value[key[0]:])
        self.slice_key = (self.slice_key[0], key[1])
        return self.slice_val

    def _alnonestop(self, key: tuple[int, int | None] | None,
                    value: EscSegment | EscContainer) -> EscSegment | EscContainer:
        # self.slice_val = value[:key[1]] + self.slice_val[key[1]:]
        self.slice_val = value[:key[1]].assimilate(self.slice_val[key[1]:])
        self.slice_key = (key[0], self.slice_key[1])
        if not key[0]:
            self.default_val = self.slice_val
        return self.slice_val

    def _appendl(self, key: tuple[int, int | None] | None,
                 value: EscSegment | EscContainer) -> EscSegment | EscContainer:
        # self.slice_val = value[:key[1]] + self.slice_val[key[1]:]
        self.slice_val = value[:key[1]].assimilate(self.slice_val[key[1]:])
        self.slice_key = (key[0], self.slice_key[1])
        return self.slice_val

    def _setnew(self, key: tuple[int, int | None] | None,
                value: EscSegment | EscContainer) -> EscSegment | EscContainer:
        self.slice_key = key
        self.slice_val = value
        if not key[0] and not key[1]:
            self.default_val = value
        return value

    def _setdefault(self, key: None, value: EscSegment | EscContainer) -> EscSegment | EscContainer:
        self.default_val = value
        return value

    def __repr__(self) -> str:
        rep = "<" + self.__class__.__name__
        for attr in self.__slots__[:-1]:
            try:
                getattr(self, attr)
                rep += " " + attr + ":S"
            except AttributeError:
                rep += " " + attr + ":U"
        return rep + ">"
