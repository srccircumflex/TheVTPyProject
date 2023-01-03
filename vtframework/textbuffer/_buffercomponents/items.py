# MIT License
#
# Copyright (c) 2022 Adrian F. Hoefflin [srccircumflex]
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
from typing import Literal, NamedTuple, Generator, overload
from ast import literal_eval


try:
    from .row import _Row
    from .nullcomponent import _NullComponent
    __4doc1 = _NullComponent
    from .trimmer import _Trimmer
    __4doc2 = _Trimmer
    from .swap import _Swap
    __4doc3 = _Swap
    from .localhistory import _LocalHistory
    __4doc4 = _LocalHistory
except ImportError:
    pass


class DumpData(NamedTuple):
    """
    An item for cut data from the buffer. Is created by the :class:`_Trimmer` and can be processed by :class:`_Swap`.
    From which `side` the data was cut is defined as ``0`` (above the currently loaded data in the buffer) or ``1``
    (below).

    - `side`: ``Literal[0, 1],``
    - `start_point_data`: ``int,``
    - `start_point_content`: ``int,``
    - `start_point_row`: ``int,``
    - `start_point_linenum`: ``int,``
    - `rows`: ``list[`` :class:`_Row` ``]``
    """
    side: Literal[0, 1]
    start_point_data: int
    start_point_content: int
    start_point_row: int
    start_point_linenum: int
    rows: list[_Row]

    def db_rows(self) -> list[tuple[str, int]]:
        """
        Converts the rows stored in the item for SQL parameterization.

        Format: ``[ (`` `<content>`, `<end of row>` ``), ...]``; the end of an row is defined as ``0``
        if the row has no line break, a line break or non-breaking line break is specified as ``1`` or ``2``.
        """
        return self.rows_to_db_format(self.rows)

    @staticmethod
    def rows_to_db_format(rows: list[_Row]) -> list[tuple[str, int]]:
        """
        Converts `rows` for parameterization of SQL.

        Format: ``[ (`` `<content>`, `<end of row>` ``), ...]``; the end of an row is defined as ``0``
        if the row has no line break, a line break or non-breaking line break is specified as ``1`` or ``2``.
        """
        return [(row.content, {None: 0, '\n': 1, '': 2}[row.end]) for row in rows]


class ChunkData(NamedTuple):
    """
    A chunk data item created by the :class:`_Swap` when querying a slot and contains the content and metadata of a
    chunk. Is used internally by the swap as parameterization for ``_load_chunk``.

    The attributes starting with `start_point_` each store the starting points of the chunk data in relation to the
    total data. ``nrows`` indicates how many :class:`_Row`'s are stored in the chunk and ``nnl`` how many line breaks
    (non-breaking and real).

    The `rows` are stored in a list of ``(`` `<content>`, `<end of row>` ``)``, the end of a row is defined as ``0``
    if the row has no line break, a line break or non-breaking line break is specified as ``1`` or ``2``.

    - `slot_id`: ``int,``
    - `start_point_data`: ``int,``
    - `start_point_content`: ``int,``
    - `start_point_row`: ``int,``
    - `start_point_linenum`: ``int,``
    - `nrows`: ``int,``
    - `nnl`: ``int,``
    - `rows`: ``list[tuple[str, 0 | 1 | 2]]``
    """
    slot_id: int
    start_point_data: int
    start_point_content: int
    start_point_row: int
    start_point_linenum: int
    nrows: int
    nnl: int
    rows: list[tuple[str, int]]


class ChunkLoad(NamedTuple):
    """
    An object of information about the processing on the :class:`_Swap`.
    The general values `top_id` and `btm_id` are always set as integer when a swap is in use,
    otherwise they are :class:`_NullComponent`. The other values are called `work values`.

    ****

    ============ ================= ================ ============================================ ==============
    item-index   work-step-index   name             type                                         description
    ============ ================= ================ ============================================ ==============
    0            0                 `top_id`         : ``int | <_NullComponent>``                 \\-- The id of the upper chunk before working on swap.
    1            0                 `btm_id`         : ``int | <_NullComponent>``                 \\-- The id of the lower chunk before working on swap.
    2            4                 `top_cut`        : ``list[list[`` :class:`_Row` ``]] | None`` \\-- Cut rows from the top of the buffer.
    3            4                 `btm_cut`        : ``list[list[`` :class:`_Row` ``]] | None`` \\-- Cut rows from the bottom of the buffer.
    4            3                 `top_nload`      : ``int | None``                             \\-- Numer of loaded chunks to the top.
    5            3                 `btm_nload`      : ``int | None``                             \\-- Numer of loaded chunks to the bottom.
    6            2                 `spec_position`  : ``int | None``                             \\-- The position id of a specific loaded chunk.
    7            1                 `edited_ran`     : ``tuple[int | None, int | None] | None``   \\-- The first and last position id of chunks (``None`` means the current buffer) edited within the database slot (inplace).
    ============ ================= ================ ============================================ ==============

    ****

    ``bool(chunk_load)`` -> whether a `work value` is not ``None``
    """
    top_id: int
    btm_id: int

    top_cut: list[list[_Row]] = None
    btm_cut: list[list[_Row]] = None

    top_nload: int | None = None
    btm_nload: int | None = None

    spec_position: int | None = None
    edited_ran: tuple[int | None, int | None] | None = None

    def __bool__(self) -> bool:
        # spec_position cant be 0
        # btm_nload is None if top_nload is None
        # btm_cut is None if top_cut is None
        return bool(self.top_nload is not None or self.top_cut is not None or self.spec_position or self.edited_ran)


class ChunkMetaItem:
    """
    A memory unit for metadata of a chunk stored in :class:`_Swap`.

    The attributes starting with `start_point_` each store the starting points of the chunk data in relation to the
    total data. ``nrows`` indicates how many :class:`_Row`'s are stored in the chunk and ``nnl`` how many line breaks
    (non-breaking and real).

    - `start_point_data`: ``int``,
    - `start_point_content`: ``int``,
    - `start_point_row`: ``int``,
    - `start_point_linenum`: ``int``,
    - `nrows`: ``int``,
    - `nnl`: ``int``
    """
    start_point_data: int
    start_point_content: int
    start_point_row: int
    start_point_linenum: int
    nrows: int
    nnl: int

    __slots__ = ('start_point_data', 'start_point_content', 'start_point_row', 'start_point_linenum',
                 'nrows', 'nnl')

    def __init__(self,
                 start_point_data: int,
                 start_point_content: int,
                 start_point_row: int,
                 start_point_linenum: int,
                 nrows: int,
                 nnl: int):
        self.start_point_data = start_point_data
        self.start_point_content = start_point_content
        self.start_point_row = start_point_row
        self.start_point_linenum = start_point_linenum
        self.nrows = nrows
        self.nnl = nnl

    @overload
    def set(self, *,
            start_point_data: int = ...,
            start_point_content: int = ...,
            start_point_row: int = ...,
            start_point_linenum: int = ...,
            nrows: int = ...,
            nnl: int = ...) -> None:
        ...

    def set(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def copy(self) -> ChunkMetaItem:
        return self.__class__(self.start_point_data,
                              self.start_point_content,
                              self.start_point_row,
                              self.start_point_linenum,
                              self.nrows,
                              self.nnl)

    def __iter__(self) -> Generator[int]:
        for attr in self.__slots__:
            yield getattr(self, attr)

    def __repr__(self) -> str:
        rep = f"<{self.__class__.__name__} ""{"
        for attr in self.__slots__:
            rep += f"{attr}={getattr(self, attr)}, "
        return rep[:-2] + "}>"


class HistoryItem(NamedTuple):
    r"""
    An item to store a chronological progress, created by ``_add_*`` methods in :class:`_LocalHistory`.
    Is used internally by ``_LocalHistory`` as parameterization for ``_dump`` and ``_do``.

    ****

    ============ =================== ========================================================================= ==============
    item-index   name                type                                                                      description
    ============ =================== ========================================================================= ==============
    0            `id_`               : ``int``                                                                 \-- Chronological position, is negative for redo items.
    8            `order_`            : ``int = None``                                                          \-- Chronological order for united actions.
    1            `type_`             : ``int``                                                                 \-- Action type.
    2            `typeval`           : ``int``                                                                 \-- Action value, subset of `type_`.
    3            `work_row`          : ``int = None``                                                          \-- (( Action data and information ))
    4            `coord`             : ``list[list[int, int]] | list[int] | list[int, int] = None``            \-- (( Action data and information ))
    5            `removed`           : ``list[list[str, "" | "\n" | Literal[False] | None]] = None``           \-- (( Action data and information ))
    6            `restrict_removed`  : ``list[list[str, "" | "\n" | Literal[False] | None]] | str = None``     \-- (( Action data and information ))
    7            `cursor`            : ``int = None``                                                          \-- (( Action data and information ))
    ============ =================== ========================================================================= ==============

    ****

    Assemblies:

    - `type_` = ``-8`` : `[ restrict removement ]`

        Created only by the restrictive morph of :class:`_Trimmer`. Saves the data removed by the mode.

        - `order_`: Is always at least -1 or lower, because even if unification is not active, a second entry is made in the database for the action.
        - `restrict_removed`: The removed data. Only set in undo items. Is always a literal when the item is read from the database; is only parsed within the processing by an interface in the ``_Trimmer``.
        - `cursor`: Is set only in redo-items and specifies the order-id of the associated chronological item.
    
    - `type_` = ``-2`` : `removed range`

        Storage of a remote area. Can also be created within the undo/redo process as a result of the counter action.

        - `removed`: The removed data.
        - `cursor`: The data start position.
    
    - `type_` = ``-1`` : `removed`

        Created in consequence of characters removed one by one and can be held inside :class:`_LocalHistory` for extension.

        - `typeval` = ``-2``: `deleted`
        - `typeval` = ``-1``: `backspaced`
        - `typeval` = ``-12``: `deleted newline`
        - `typeval` = ``-11``: `backspaced newline`
        - `coord`: The start position stored in mutable type.
        - `removed`: The removed data.
        - `work_row`: The line number in which was removed.
    
    - `type_` = ``0`` : `cursor`

        Used for special cursor operations.

        - `typeval`: Is always ``0``.
        - `cursor`: The position.

    - `type_` = ``1`` : `written`

        Memory for write actions. Except of type values -16 and -8, items are held for extensions by :class:`_LocalHistory`.

        - `typeval` = ``-16`` : `removed`

            Created when the write process has removed data only (for example tab-backshift).

            - `coord`: The start position stored in mutable type (standardization).
            - `removed`: The removed data.
            - `work_row`: The row number in which was removed.

        - `typeval` = ``-8`` : `line substituted`

            Will be created for line substitutions.

            - `coord`: The start and end position of written characters.
            - `removed`: The removed data.
            - `work_row`: The row number in which the substitution has started.

        - `typeval` = ``-4`` : `substituted`

            Created for character substitutions.

            - `coord`: The start and end position of written characters.
            - `removed`: The removed data.
            - `work_row`: The row number in which the substitution has started.
            - [ `restrict_removed` ]: Is only present in held items for extensions and only when the :class:`_Trimmer` is active in restrictive morph; is entered separately when the transit to the database is made.

        - `typeval` = ``1`` : `written`

            Storage of simple write actions.

            - `coord`: The start and end position of written characters.
            - `work_row`: The row number in which was written.
            - [ `restrict_removed` ]: Is only present in held items for extensions and only when the :class:`_Trimmer` is active in restrictive morph; is entered separately when the transit to the database is made.

        - `typeval` = ``2`` : `has newline`

            Storage of simple write actions with line breaks.

            - `coord`: The start and end position of written characters.
            - `work_row`: The row number in which was written.
            - [ `restrict_removed` ]: Is only present in held items for extensions and only when the :class:`_Trimmer` is active in restrictive morph; is entered separately when the transit to the database is made.

    - `type_` = ``2`` : `rewritten`

        Created within undo and redo actions.

        - `typeval` = ``-32``: `re-substitution`

            Undone substitution.

            - `coord`: The start and end position of written characters.
            - `work_row`: The row number in which the substitution has started.

        - `typeval` = ``4``: `rewrite`

            Simple rewrite.

            - `coord`: The start and end position of written characters.
            - `work_row`: The line number in which the writing was started.

    - `type_` = ``4`` : `marks`

        Saving of current marker coordinates before editing. Always all markers are entered.
        The type values for this type are only comments and are not relevant for redo and undo.

        - `typeval` = ``-105``: `removed by adjust`
        - `typeval` = ``-103``: `pop`
        - `typeval` = ``-102``: `conflicts with input`
        - `typeval` = ``-101``: `lapping`
        - `typeval` = ``-100``: `marker purged`
        - `typeval` = ``100``: `new mark added`
        - `typeval` = ``101``: `external adding`
        - `typeval` = ``126``: `undo/redo`
        - `coord`: The markings as a list of areas.
        - `cursor`: Is optionally set to automatically set the cursor after undo/redo.
    
    - `type_` = ``32`` : `metadata (intern)`

        Created internally by :class:`_LocalHistory` to store object data for a branch in branch forking mode.
        Cannot be reached by Undo and Redo.

        - `id_`: Is always ``0``.
    """

    class TYPES:
        RESTRICT_REMOVEMENT = -8
        REMOVE_RANGE = -2
        REMOVE = -1
        CURSOR = 0
        WRITE = 1
        RE_WRITE = 2
        MARKS = 4
        BRANCH_METADATA = 32

        __slots__ = ()

    class TYPEVALS:
        RE_SUBSTITUTION = -32
        W_REMOVE = -16
        DELETED_NEWLINE = -12
        BACKSPACED_NEWLINE = -11
        LINE_SUBSTITUTED = -8
        SUBSTITUTED = -4
        DELETE = -2
        BACKSPACE = -1
        POSITION = 0
        WRITE = 1
        W_HAS_NEWLINE = 2
        RE_WRITE = 4

        class MARKERCOMMENTS:
            REMOVED_BY_ADJUST = -105
            POP = -103
            INPUT_CONFLICT = -102
            LAPPING = -101
            PURGED = -100
            NEW_MARKING = 100
            EXTERNAL_ADDING = 101
            UNDO_REDO = 126

            __slots__ = ()

        __slots__ = ()

    id_: int = None
    type_: int = None
    typeval: int = None
    work_row: int = None
    coord: list = None  # list[list[int, int]] | list[int] | list[int, int]
    removed: list[list[str, str | bool | None]] = None
    restrict_removed: list[list[str, str | None]] | str = None
    cursor: int = None
    order_: int = None

    @classmethod
    def from_db(cls, dbrow: tuple) -> HistoryItem:
        """Create the item from a db row."""
        return cls(id_=dbrow[0],
                   type_=dbrow[1],
                   typeval=dbrow[2],
                   work_row=dbrow[3],
                   coord=(literal_eval(dbrow[4]) if dbrow[4] else None),
                   removed=(literal_eval(dbrow[5]) if dbrow[5] else None),
                   restrict_removed=dbrow[6],
                   cursor=dbrow[7],
                   order_=dbrow[8])


class WriteItem(NamedTuple):
    r"""
    An object with information and follow-up parameterization for processing :class:`_Row` data.

    ****

    ============ ================ =========================================== ==============
    item-index   name             type                                        description
    ============ ================ =========================================== ==============
    0            `write`          : ``int``                                   \-- The string length of the entered data.
    1            `newlines`       : ``bool``                                  \-- Whether a line break is written.
    2            `write_rows`     : ``int | None``                            \-- The number of lines processed (not mandatory coinciding with the number of line breaks).
    3            `begin`          : ``int``                                   \-- The total position in the data at which writing was started.
    4            `work_row`       : ``int``                                   \-- The row number at which writing was started.
    5            `deleted`        : ``int``                                   \-- The number of characters removed from the row during an edit.
    6            `removed`        : ``str | None``                            \-- The data of the row removed during an edit.
    7            `removed_end`    : ``str | None``                            \-- The end removed from the row. If it is ``None``, none has been removed, otherwise it can be ``""`` for a non-breaking or ``"\n"`` for an ordinary line break.
    8            `diff`           : ``int``                                   \-- The difference in the row after writing.
    9            `overflow`       : :class:`WriteItem.Overflow` ``| None``    \-- Overflow object for the parameterization of the subsequent processing by :class:`TextBuffer`.
    ============ ================ =========================================== ==============
    """

    class Overflow(NamedTuple):
        r"""
        Overflow object for the parameterization of the subsequent processing (element of :class:`WriteItem`).

        ****

        ============ ================ =========================================== ==============
        item-index   name             type                                        description
        ============ ================ =========================================== ==============
        0            `lines`          : ``list[str]``                             \-- Overflowing data (is processed in place, the list is thus finally empty).
        1            `end`            : ``None | str``                            \-- Overflowing line break (``""`` for a non-breaking or ``"\n"`` for an ordinary line break) or ``None``.
        2            `substitution`   : ``bool``                                  \-- Whether to process the overflow in substitution mode.
        3            `nbnl`           : ``bool``                                  \-- Whether to write non-breaking line breaks.
        4            `len`            : ``int``                                   \-- The length of the overflow without overflowing line break.
        ============ ================ =========================================== ==============

        ****

        ``len(overflow)`` -> The total length (incl. line break).
        """
        lines: list[str]
        end: None | str
        substitution: bool
        nbnl: bool
        len: int

        def __len__(self):
            return self.len + (self.end is not None)

        def __bool__(self):
            return True

        def __repr__(self) -> str:
            return f"<{self.__class__.__name__} {repr(self.lines)[-100:]=} " \
                   f"{self.end=} {self.substitution=} {self.nbnl=} {self.len=}>"

    write: int
    newlines: bool
    write_rows: int | None
    begin: int
    work_row: int
    deleted: int
    removed: str | None
    removed_end: str | None
    diff: int
    overflow: Overflow | None = None
