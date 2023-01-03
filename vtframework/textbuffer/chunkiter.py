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

from typing import Callable, Literal, Generator, Any, Iterable, Reversible
from collections import OrderedDict


try:
    from .buffer import TextBuffer, ChunkBuffer
    from ._buffercomponents.row import _Row
    from ._buffercomponents.swap import _MetaIndex, _Swap
except ImportError:
    pass


class ChunkIter(Reversible):
    """
    **[ ADVANCED USAGE ]**

    An object to iterate through defined areas of the buffer across the boundaries to the swap. Return pairs of a
    :class:`_Row` and the associated coordinate on iteration.
    If a chunk is needed for the current coordinate, it is temporarily loaded into memory as a :class:`ChunkBuffer`;
    also, if currently loaded lines need to be read from the :class:`TextBuffer`, an image is loaded into memory as a
    ``ChunkBuffer``; thus, the rows in the iteration are always a part of a :class:`ChunkBuffer`.

    The coordinates in the iteration are from the coordinates passed at initialization parsed components of a chunk
    catalog which is realized as OrderedDict (:class:`ChunkIter.ParsedCoords`). By this the adjusted coordinates to
    concerning chunks are stored.

    Coordinates can be expressed and typed in different ways. The coordinate data must be defined as a sorted list of
    data points ``[ <int>, ... ]`` or as a sorted list of data ranges ``[ [<int>, <int>], ... ]`` (optional, by default
    it is iterated over the whole data).

    To indicate what type of metadata it is, can be specified:
        - ``"data"``: orientate to the data points in rows. `sorted_coord` must be formulated with data points for this.
        - ``"content"``: orientate to the content data points in rows. `sorted_coord` must be formulated with content
          points for this.
        - ``"row"``: orientate to the row numbers. `sorted_coord` must be formulated with the row numbers for this.
        - ``"line"``: orientate to the line numbers in rows (compared to a row, a line is defined as the data between
          two line breaks + final line break). `sorted_coord` must be formulated with the line numbers for this.

    Depending on how or if data of rows are edited during iteration, a mode of metadata adjustment must be parameterized:
        - ``"memory"``: allows editing the rows in chunk buffers without affecting the actual chunks (sandbox mode).
        - ``"live metas"``: overwrites the chunk slot after leaving a ``ChunkBuffer`` and directly adjusts the
          metadata of all chunks around the edit.
        - ``"shadow metas"``: also overwrites the chunkslot after leaving a ``ChunkBuffer`` but writes the differences
          in the chunks separately, the actual metadata is then finally adjusted when leaving the iterator.

    ``ChunkIter`` is itself a reversible iterator, for this the mode is specified at creation.
    But the generator can also be obtained via the methods ``iter``, ``reversed`` or ``coordreversed``; in this case
    the mode can be rewritten again. If the ``ChunkIter`` is to be started directly as a ``coordreversed``-iterator
    (is not reversible), the mode must be selected correspondingly from ``"coords reversed + m"``,
    ``"coords reversed + l"`` or ``"coords reversed + s"``. The generator then orients itself to reversed coordinates
    and iterates forward through the rows.

        *About the metadata and editing in the iteration:*

        Note that the rows in the ``ChunkBuffer`` are selected during iteration based on the coordinates.
        So if data of the current ``ChunkBuffer`` is edited and the rows contained in it are indexed, this may affect the
        selection of the following rows based on the original coordinates when iterating forward. If the
        ``"live metas"`` mode is used for editing in a forward iteration, this effect will additionally affect the
        chunk level.

        At the end or break of the iteration, ``ChunkIter`` takes care of chunks that have become empty due to editing
        and removes them from the :class:`_Swap`.

    For the execution of functions within the ``ChunkIter`` during the iteration, these may be passed depending on the situation:
        - `chunk_enter`: executed whenever a new ``ChunkBuffer`` is created and entered; gets the ``ChunkBuffer`` and
          the parsed coordinates.
        - `chunk_exit`: is always executed when a ``ChunkBuffer`` is exited; gets the ``ChunkBuffer``.
        - `coord_enter`: executed when a coordinate starts; gets the row and coordinate (coordinate is only ``None``
          if no coordinates were passed).
        - `coord_continue`: executed when a coordinate is continued, and gets the row and coordinate.
        - `coord_break`: is executed at the interruption by a chunk boundary or at the termination of a coordinate and
          gets the current ``ChunkBuffer`` and the coordinate (never executed if no coordinates were passed).
    """

    class ParsedCoords(OrderedDict):
        """
        The adjusted ranges for a chunk are stored as a list or ``None`` under the chunk position number. If a
        coordinate spans multiple chunks, the original is stored in the adjusted values of the first affected chunk,
        if entire chunks are affected until the end of the coordinate, ``None`` are used as value instead of the list,
        under the last affected chunk, an adjusted version of the original is included in the list of values
        (the start is then equal to the chunk data start).

        ``ordered``, ``reversed`` and ``coordreversed`` are sorting methods and return a list of items.

        ``coordreversed`` is a method to sort the coordinates backwards but the respective chunks forwards.
        """
        @property
        def id_range(self) -> tuple[int | None, int | None] | None:
            if not self:
                return None
            d = self.copy()
            s = d.popitem(last=True)[0]
            if d:
                if (e := d.popitem(last=False)[0]) or s:
                    return s, e
            elif s:
                return s, s

        def __init__(self, iterable: Iterable[tuple[int | None, list[int] | list[list[int, int]]]] = None):
            if iterable is not None:
                OrderedDict.__init__(self, iterable)
            else:
                OrderedDict.__init__(self)

        def coordreversed(self) -> list[tuple[int | None, list[int] | list[list[int, int]] | None]]:
            items = [(itm[0], (itm[1].copy() if itm[1] is not None else None)) for itm in self.items()]
            if isinstance(items[0][1][0], list):
                def _get_dat(l_: list, i1, i2):
                    return l_[i1][i2]
            else:
                def _get_dat(l_: list, i1, i2):
                    return l_[i1]
            i = 0
            try:
                while True:
                    if items[(nxi := i + 1)][1] is None:
                        if len(items[i][1]) > 1:
                            _i = i + 1
                            items.insert(_i, (items[i][0], [items[i][1].pop(-1)]))
                            i += 2
                        else:
                            _i = i
                            i += 1
                        while items[i][1] is None:
                            items.insert(_i, items.pop(i))
                            i += 1
                        if len(items[i][1]) > 1:
                            items.insert(_i, (items[i][0], [items[i][1].pop(0)]))
                        else:
                            items.insert(_i, items.pop(i))
                    elif _get_dat(items[nxi][1], 0, 1) == _get_dat(items[i][1], -1, 1):
                        if len(items[i][1]) > 1:
                            _i = i + 1
                            items.insert(_i, (items[i][0], [items[i][1].pop(-1)]))
                            i += 2
                        else:
                            _i = i
                            i += 1
                        if len(items[i][1]) > 1:
                            items.insert(_i, (items[i][0], [items[i][1].pop(0)]))
                        else:
                            items.insert(_i, items.pop(i))
                        i += 1
                    else:
                        i += 1
            finally:
                return items

        def reversed(self) -> list[tuple[int | None, list[int] | list[list[int, int]] | None]]:
            return [(itm[0], (itm[1].copy() if itm[1] is not None else None)) for itm in self.items()]

        def ordered(self) -> list[tuple[int | None, list[int] | list[list[int, int]] | None]]:
            return [(itm[0], (sorted(itm[1].copy()) if itm[1] is not None else None)) for itm in reversed(self.items())]

    _iter_mode: str  # Literal['c', 'i']
    _suit_key: str  # Literal['r', 'l', 'm']
    parsed_coords: ParsedCoords[int | None, list[int] | list[list[int, int]] | None]
    _iter_suits_: dict[str,  # Literal['r', 'l', 's'],
                       tuple[Callable[[], Any], Callable[[ChunkBuffer], Any], Callable[[], Any], bool]]
    _iter_: Callable[[tuple[Callable[[], Any], Callable[[ChunkBuffer], Any], Callable[[], Any], bool]],
                     Generator[tuple[_Row, list[int, int] | int | None]]]
    _reversed_: Callable[[tuple[Callable[[], Any], Callable[[ChunkBuffer], Any], Callable[[], Any], bool]],
                         Generator[tuple[_Row, list[int, int] | int | None]]]
    _coordreversed_: Callable[[tuple[Callable[[], Any], Callable[[ChunkBuffer], Any], Callable[[], Any], bool]],
                              Generator[tuple[_Row, list[int, int] | int | None]]]

    def __init__(self,
                 __buffer__: TextBuffer,
                 mode: Literal[
                     'memory', 'm',
                     'live metas', 'l',
                     'shadow metas', 's',
                     'coords reversed + m', 'cm',
                     'coords reversed + l', 'cl',
                     'coords reversed + s', 'cs'
                 ],
                 sorted_coords: list[list[int, int]] | list[int] = None,
                 coord_type: Literal['data', 'd', 'content', 'c', 'row', 'r', 'line', 'l', ''] = 'd',
                 chunk_enter: Callable[[ChunkBuffer, list[list[int, int]] | list[int] | None], Any] = lambda *_: None,
                 chunk_exit: Callable[[ChunkBuffer], Any] = lambda *_: None,
                 coord_enter: Callable[[_Row, list[int, int] | int | None], Any] = lambda *_: None,
                 coord_continue: Callable[[_Row, list[int, int] | int | None], Any] = lambda *_: None,
                 coord_break: Callable[[ChunkBuffer, list[int, int] | int | None], Any] = lambda *_: None):

        if mode[0] == 'c':
            self._iter_mode = 'c'
            self._suit_key = mode[-1]
        else:
            self._iter_mode = 'i'
            self._suit_key = mode[0]

        self._iter_suits_ = {
            'm': (lambda: None, lambda _: None, lambda: None, True),
            'l': (lambda: None,
                  lambda b: __buffer__.__swap__.__meta_index__.adjust_by_position(b.__chunk_pos_id__,
                                                                                  *b._adjust_rows(0, endings=True)),
                  lambda: None,
                  False),
            's': (__buffer__.__swap__.__meta_index__.shadow_start,
                  lambda b: __buffer__.__swap__.__meta_index__.adjust_by_position(
                      b.__chunk_pos_id__,
                      *b._adjust_rows(0, endings=True)),
                  lambda: __buffer__.__swap__.__meta_index__.shadow_commit(),
                  False)
        }

        if sorted_coords is None:

            def _iter(suit, reversed_=lambda obj: obj):
                empty_chunks = list()
                def __coord_call(row):
                    nonlocal _coord_call
                    coord_enter(row, None)
                    _coord_call = lambda r: coord_continue(r, None)
                _coord_call = __coord_call
                try:
                    suit[0]()
                    for cid in reversed_(
                            __buffer__.__swap__.positions_top_ids + (None,) + __buffer__.__swap__.positions_bottom_ids):
                        try:
                            with __buffer__.ChunkBuffer(__buffer__, cid, sandbox=suit[3], delete_empty=False) as cb:
                                cb.strip()
                                chunk_enter(cb, None)
                                try:
                                    for row in reversed_(cb.rows):
                                        _coord_call(row)
                                        yield row, None
                                finally:
                                    chunk_exit(cb)
                                    suit[1](cb)
                        finally:
                            if cb.__empty__:
                                empty_chunks.append(cb.__chunk_pos_id__)
                finally:
                    suit[2]()
                    __buffer__.__swap__.remove_chunk_positions(*empty_chunks)

            self.parsed_coords = ChunkIter.ParsedCoords()
            self._iter_, self._reversed_, self._coordreversed_ = _iter, lambda s: _iter(s, reversed), _iter

        else:
            if isinstance(sorted_coords[0], list):
                def _get_dat(dat, i):
                    return dat[i]

            else:
                def _get_dat(dat, i):
                    return dat + i

            self.parsed_coords = self.pars_meta_coords(__buffer__, sorted_coords, coord_type)

            if (coord_type := coord_type[0]) == 'd':
                def startcon(row: _Row, datp: int):
                    return row.__data_start__ <= datp

                def ocontinuing(row: _Row, datp: int):
                    return row.__data_start__ < datp
            if coord_type == 'c':
                def startcon(row: _Row, datp: int):
                    return row.__content_start__ <= datp

                def ocontinuing(row: _Row, datp: int):
                    return row.__content_start__ < datp
            if coord_type == 'r':
                def startcon(row: _Row, datp: int):
                    return row.__row_num__ == datp

                def ocontinuing(row: _Row, datp: int):
                    return row.__row_num__ < datp

                def rcontinuing(row: _Row, datp: int):
                    return row.__row_num__ >= datp
            if coord_type == 'l':
                def startcon(row: _Row, datp: int):
                    return row.__line_num__ == datp

                def ocontinuing(row: _Row, datp: int):
                    return row.__line_num__ < datp

                def rcontinuing(row: _Row, datp: int):
                    return row.__line_num__ >= datp

            if coord_type in 'rl':

                def _iter(suit):
                    empty_chunks = list()
                    suit[0]()
                    try:
                        _coord_enter = coord_enter

                        def _coord_exit(__row, __coord):
                            nonlocal _coord_enter
                            _coord_enter = coord_enter
                            coord_continue(__row, __coord)

                        dat2 = coord = None
                        for cid, coords in self.parsed_coords.ordered():
                            try:
                                with __buffer__.ChunkBuffer(__buffer__, cid, sandbox=suit[3], delete_empty=False) as cb:
                                    cb.strip()
                                    chunk_enter(cb, coords)
                                    try:
                                        if coords is None:
                                            try:
                                                for row in cb.rows:
                                                    coord_continue(row, None)
                                                    yield row, None
                                            finally:
                                                coord_break(cb, coord)
                                        else:
                                            coord = coords.pop(0)
                                            dat1 = _get_dat(coord, 0)
                                            if dat2 == (dat2 := _get_dat(coord, 1)):
                                                _coord_enter = _coord_exit
                                            i = 0
                                            while True:
                                                if startcon((row := cb.rows[i]), dat1):
                                                    _coord_enter(row, coord)
                                                    yield row, coord
                                                    i += 1
                                                    try:
                                                        while ocontinuing((row := cb.rows[i]), dat2):
                                                            coord_continue(row, coord)
                                                            yield row, coord
                                                            i += 1
                                                    except IndexError:
                                                        pass
                                                    finally:
                                                        coord_break(cb, coord)
                                                        coord = coords.pop(0)
                                                        dat1 = _get_dat(coord, 0)
                                                        dat2 = _get_dat(coord, 1)
                                                else:
                                                    i += 1
                                    except IndexError:
                                        pass
                                    finally:
                                        chunk_exit(cb)
                                        suit[1](cb)
                            finally:
                                if cb.__empty__:
                                    empty_chunks.append(cb.__chunk_pos_id__)
                    finally:
                        suit[2]()
                        __buffer__.__swap__.remove_chunk_positions(*empty_chunks)

                def _riter(suit):
                    empty_chunks = list()
                    suit[0]()
                    try:
                        _coord_enter = coord_enter

                        def _coord_exit(__row, __coord):
                            nonlocal _coord_enter
                            _coord_enter = coord_enter
                            coord_continue(__row, __coord)

                        dat2 = coord = None
                        for cid, coords in self.parsed_coords.reversed():
                            try:
                                with __buffer__.ChunkBuffer(__buffer__, cid, sandbox=suit[3], delete_empty=False) as cb:
                                    cb.strip()
                                    chunk_enter(cb, coords)
                                    try:
                                        if coords is None:
                                            try:
                                                for row in reversed(cb.rows):
                                                    coord_continue(row, None)
                                                    yield row, None
                                            finally:
                                                coord_break(cb, coord)
                                        else:
                                            coord = coords.pop(0)
                                            dat1 = _get_dat(coord, 0)
                                            if dat2 == (dat2 := _get_dat(coord, 1) - 1):
                                                _coord_enter = _coord_exit
                                            i = len(cb.rows) - 1
                                            while True:
                                                if startcon((row := cb.rows[i]), dat2):
                                                    _coord_enter(row, coord)
                                                    yield row, coord
                                                    if (i := i - 1) < 0:
                                                        break
                                                    try:
                                                        while rcontinuing((row := cb.rows[i]), dat1):
                                                            coord_continue(row, coord)
                                                            yield row, coord
                                                            if (i := i - 1) < 0:
                                                                break
                                                    except IndexError:
                                                        pass
                                                    finally:
                                                        coord_break(cb, coord)
                                                        coord = coords.pop(0)
                                                        dat1 = _get_dat(coord, 0)
                                                        dat2 = _get_dat(coord, 1) - 1
                                                else:
                                                    if (i := i - 1) < 0:
                                                        break
                                    except IndexError:
                                        pass
                                    finally:
                                        chunk_exit(cb)
                                        suit[1](cb)
                            finally:
                                if cb.__empty__:
                                    empty_chunks.append(cb.__chunk_pos_id__)
                    finally:
                        suit[2]()
                        __buffer__.__swap__.remove_chunk_positions(*empty_chunks)

            else:

                def _iter(suit):
                    empty_chunks = list()
                    suit[0]()
                    try:
                        _coord_enter = coord_enter

                        def _coord_exit(__row, __coord):
                            nonlocal _coord_enter
                            _coord_enter = coord_enter
                            coord_continue(__row, __coord)

                        dat2 = coord = None
                        for cid, coords in self.parsed_coords.ordered():
                            try:
                                with __buffer__.ChunkBuffer(__buffer__, cid, sandbox=suit[3], delete_empty=False) as cb:
                                    cb.strip()
                                    chunk_enter(cb, coords)
                                    try:
                                        if coords is None:
                                            try:
                                                for row in cb.rows:
                                                    coord_continue(row, None)
                                                    yield row, None
                                            finally:
                                                coord_break(cb, coord)
                                        else:
                                            if dat2 == _get_dat(coords[0], 1):
                                                _coord_enter = _coord_exit
                                            while coords:
                                                coord = coords.pop(0)
                                                dat1 = _get_dat(coord, 0)
                                                dat2 = _get_dat(coord, 1)
                                                for ri in range(len(cb.rows) - 1, -1, -1):
                                                    if startcon((row := cb.rows[ri]), dat1):
                                                        _coord_enter(row, coord)
                                                        yield row, coord
                                                        try:
                                                            i = ri + 1
                                                            while ocontinuing((row := cb.rows[i]), dat2):
                                                                coord_continue(row, coord)
                                                                yield row, coord
                                                                i += 1
                                                        except IndexError:
                                                            pass
                                                        coord_break(cb, coord)
                                                        break
                                    except IndexError:
                                        pass
                                    finally:
                                        chunk_exit(cb)
                                        suit[1](cb)
                            finally:
                                if cb.__empty__:
                                    empty_chunks.append(cb.__chunk_pos_id__)
                    finally:
                        suit[2]()
                        __buffer__.__swap__.remove_chunk_positions(*empty_chunks)

                def _riter(suit):
                    empty_chunks = list()
                    suit[0]()
                    try:
                        _coord_enter = coord_enter

                        def _coord_exit(__row, __coord):
                            nonlocal _coord_enter
                            _coord_enter = coord_enter
                            coord_continue(__row, __coord)

                        dat2 = coord = None
                        for cid, coords in self.parsed_coords.reversed():
                            try:
                                with __buffer__.ChunkBuffer(__buffer__, cid, sandbox=suit[3], delete_empty=False) as cb:
                                    cb.strip()
                                    chunk_enter(cb, coords)
                                    try:
                                        if coords is None:
                                            try:
                                                for row in reversed(cb.rows):
                                                    coord_continue(row, None)
                                                    yield row, None
                                            finally:
                                                coord_break(cb, coord)
                                        else:
                                            coord = coords.pop(0)
                                            dat1 = _get_dat(coord, 0)
                                            if dat2 == (dat2 := _get_dat(coord, 1)):
                                                _coord_enter = _coord_exit
                                            ri = len(cb.rows) - 1
                                            while True:
                                                if ocontinuing((row := cb.rows[ri]), dat2):
                                                    _coord_enter(row, coord)
                                                    yield row, coord
                                                    try:
                                                        if (i := ri - 1) < 0:
                                                            continue
                                                        while startcon((row := cb.rows[i]), dat1):
                                                            coord_continue(row, coord)
                                                            yield row, coord
                                                            if (i := i - 1) < 0:
                                                                break
                                                    except IndexError:
                                                        pass
                                                    finally:
                                                        coord_break(cb, coord)
                                                        coord = coords.pop(0)
                                                        dat1 = _get_dat(coord, 0)
                                                        dat2 = _get_dat(coord, 1)
                                                elif (ri := ri - 1) < 0:
                                                    break
                                    except IndexError:
                                        pass
                                    finally:
                                        chunk_exit(cb)
                                        suit[1](cb)
                            finally:
                                if cb.__empty__:
                                    empty_chunks.append(cb.__chunk_pos_id__)
                    finally:
                        suit[2]()
                        __buffer__.__swap__.remove_chunk_positions(*empty_chunks)

            if coord_type == 'l':

                def _criter(suit):
                    empty_chunks = list()
                    suit[0]()
                    try:
                        _coord_enter = coord_enter

                        def _coord_exit(__row, __coord):
                            nonlocal _coord_enter
                            _coord_enter = coord_enter
                            coord_continue(__row, __coord)

                        dat2 = coord = None
                        for cid, coords in self.parsed_coords.coordreversed():
                            try:
                                with __buffer__.ChunkBuffer(__buffer__, cid, sandbox=suit[3], delete_empty=False) as cb:
                                    cb.strip()
                                    chunk_enter(cb, coords)
                                    try:
                                        if coords is None:
                                            try:
                                                for row in cb.rows:
                                                    coord_continue(row, None)
                                                    yield row, None
                                            finally:
                                                coord_break(cb, coord)
                                        else:
                                            coord = coords.pop(0)
                                            dat1 = _get_dat(coord, 0) - 1
                                            if dat2 == (dat2 := _get_dat(coord, 1)):
                                                _coord_enter = _coord_exit
                                            for ri in range(len(cb.rows) - 1, -1, -1):
                                                while startcon(cb.rows[ri], dat1):
                                                    try:
                                                        def coord_call(__row, __coord):
                                                            nonlocal coord_call
                                                            _coord_enter(__row, __coord)
                                                            coord_call = coord_continue
    
                                                        i = ri + 1
                                                        while ocontinuing((row := cb.rows[i]), dat2):
                                                            coord_call(row, coord)
                                                            yield row, coord
                                                            i += 1
                                                    except IndexError:
                                                        pass
                                                    finally:
                                                        coord_break(cb, coord)
                                                        coord = coords.pop(0)
                                                        dat1 = _get_dat(coord, 0) - 1
                                                        dat2 = _get_dat(coord, 1)
    
                                            # coords.pop has not raised IndexError -> dat1 not found -> dat1 < rows[-1]
                                            def coord_call(__row, __coord):
                                                nonlocal coord_call
                                                _coord_enter(__row, __coord)
                                                coord_call = coord_continue
    
                                            try:
                                                i = 0
                                                while ocontinuing((row := cb.rows[i]), dat2):
                                                    coord_call(row, coord)
                                                    yield row, coord
                                                    i += 1
                                            finally:
                                                coord_break(cb, coord)
                                    except IndexError:
                                        pass
                                    finally:
                                        chunk_exit(cb)
                                        suit[1](cb)
                            finally:
                                if cb.__empty__:
                                    empty_chunks.append(cb.__chunk_pos_id__)
                    finally:
                        suit[2]()
                        __buffer__.__swap__.remove_chunk_positions(*empty_chunks)

            else:

                def _criter(suit):
                    empty_chunks = list()
                    suit[0]()
                    try:
                        _coord_enter = coord_enter

                        def _coord_exit(__row, __coord):
                            nonlocal _coord_enter
                            _coord_enter = coord_enter
                            coord_continue(__row, __coord)

                        dat2 = coord = None
                        for cid, coords in self.parsed_coords.coordreversed():
                            try:
                                with __buffer__.ChunkBuffer(__buffer__, cid, sandbox=suit[3], delete_empty=False) as cb:
                                    cb.strip()
                                    chunk_enter(cb, coords)
                                    try:
                                        if coords is None:
                                            try:
                                                for row in cb.rows:
                                                    coord_continue(row, None)
                                                    yield row, None
                                            finally:
                                                coord_break(cb, coord)
                                        else:
                                            coord = coords.pop(0)
                                            dat1 = _get_dat(coord, 0)
                                            if dat2 == (dat2 := _get_dat(coord, 1)):
                                                _coord_enter = _coord_exit
                                            for ri in range(len(cb.rows) - 1, -1, -1):
                                                while startcon((row := cb.rows[ri]), dat1):
                                                    _coord_enter(row, coord)
                                                    yield row, coord
                                                    try:
                                                        i = ri + 1
                                                        while ocontinuing((row := cb.rows[i]), dat2):
                                                            coord_continue(row, coord)
                                                            yield row, coord
                                                            i += 1
                                                    except IndexError:
                                                        pass
                                                    finally:
                                                        coord_break(cb, coord)
                                                        coord = coords.pop(0)
                                                        dat1 = _get_dat(coord, 0)
                                                        dat2 = _get_dat(coord, 1)
                                    except IndexError:
                                        pass
                                    finally:
                                        chunk_exit(cb)
                                        suit[1](cb)
                            finally:
                                if cb.__empty__:
                                    empty_chunks.append(cb.__chunk_pos_id__)
                    finally:
                        suit[2]()
                        __buffer__.__swap__.remove_chunk_positions(*empty_chunks)

            self._iter_, self._reversed_, self._coordreversed_ = _iter, _riter, _criter

    @staticmethod
    def pars_meta_coords(__buffer__: TextBuffer,
                         sorted_meta_coords: list[list[int, int]] | list[int],
                         coord_type: Literal['data', 'd', 'content', 'c', 'row', 'r', 'line', 'l']
                         ) -> ChunkIter.ParsedCoords:
        """
        Parse sorted meta coordinates to a chunk catalog;
        Or sort out not applicable coordinates if swap is not initialized.

        Coordinates can be defined as ranges ``[ [start, stop], ... ]`` or as data points ``[ point, ... ]``

        [+] __swap__.adjust
        """

        __buffer__.__swap__.__meta_index__.adjust_bottom_auto()
        mkey, bmeta, blast = {'d': (0, __buffer__.__start_point_data__, __buffer__.rows[-1].data_cache.len_absdata),
                              'c': (
                                  1, __buffer__.__start_point_content__, __buffer__.rows[-1].data_cache.len_abscontent),
                              'r': (2, __buffer__.__start_point_row_num__, __buffer__.rows[-1].__row_num__),
                              'l': (3, __buffer__.__start_point_line_num__, __buffer__.rows[-1].__line_num__)
                              }[coord_type[0]]
        if isinstance(sorted_meta_coords[0], list):

            def _get_dat(i1, i2):
                return sorted_meta_coords[i1][i2]

            def _set_dat(i1, i2, val):
                sorted_meta_coords[i1][i2] = val

            def _chunk_cross_form(idxi, coordi):
                # set the last (final) entry to: [start of chunk, end of coord]
                return [[dat_index[chunk_ids[idxi - 1]][mkey], _get_dat(coordi, 1)]]

        else:
            def _get_dat(i1, i2):
                return sorted_meta_coords[i1] + i2

            def _set_dat(i1, i2, val):
                sorted_meta_coords[i1] = val

            def _chunk_cross_form(idxi, coordi):
                return [_get_dat(coordi, 0)]

        if coord_type == 'l':
            if not __buffer__.__swap__:
                while _get_dat(0, 1) < bmeta:
                    sorted_meta_coords.pop(0)
                _set_dat(-1, 0, max(bmeta, _get_dat(-1, 0)))
                while _get_dat(-1, 0) > blast:
                    sorted_meta_coords.pop(-1)
                sorted_meta_coords.reverse()
                return ChunkIter.ParsedCoords([(None, sorted_meta_coords)])
            else:
                chunk_ids, dat_index = __buffer__.__swap__.__meta_index__.get_meta_indices()
                _start0 = ()
                if _get_dat(0, 0) == 0:
                    _start0 = [(chunk_ids[0], [sorted_meta_coords[0]])]
                    i = 1
                    chunk_cross = False
                    try:
                        while dat_index[chunk_ids[i]][mkey] < _get_dat(0, 1):
                            _start0.append((chunk_ids[i], None))
                            i += 1
                            chunk_cross = True
                    except IndexError:
                        pass
                    if chunk_cross:
                        _start0[-1] = (_start0[-1][0], _chunk_cross_form(i, 0))
                    sorted_meta_coords.pop(0)

                chunk_ranges = ChunkIter.ParsedCoords()
                try:
                    for ri in range(len(chunk_ids) - 1, -1, -1):
                        chunk_id = chunk_ids[ri]
                        while dat_index[chunk_id][mkey] <= _get_dat(-1, 0) - 1:
                            _chunk_ranges = [(chunk_id, [sorted_meta_coords[-1]])]
                            ri += 1
                            chunk_cross = False
                            try:
                                while dat_index[chunk_ids[ri]][mkey] < _get_dat(-1, 1):
                                    _chunk_ranges.append((chunk_ids[ri], None))
                                    ri += 1
                                    chunk_cross = True
                            except IndexError:
                                pass
                            if dat_index[chunk_id][mkey] + dat_index[chunk_id][5] < _get_dat(-1, 0):
                                _chunk_ranges.pop(0)
                                _chunk_ranges[0] = (_chunk_ranges[0][0], [sorted_meta_coords[-1]])
                                chunk_cross = len(_chunk_ranges) > 1
                            if chunk_cross:
                                _chunk_ranges[-1] = (_chunk_ranges[-1][0], _chunk_cross_form(ri, -1))

                            sorted_meta_coords.pop(-1)

                            for id_, ran in reversed(_chunk_ranges):
                                if ran is None:
                                    chunk_ranges[id_] = None
                                else:
                                    try:
                                        if chunk_ranges[id_] is None:
                                            chunk_ranges[id_] = list()
                                        chunk_ranges[id_] += ran
                                    except KeyError:
                                        chunk_ranges[id_] = ran
                finally:
                    for id_, ran in reversed(_start0):
                        if ran is None:
                            chunk_ranges[id_] = None
                        else:
                            try:
                                if chunk_ranges[id_] is None:
                                    chunk_ranges[id_] = list()
                                chunk_ranges[id_] += ran
                            except KeyError:
                                chunk_ranges[id_] = ran
                    return chunk_ranges

        elif not __buffer__.__swap__:
            while _get_dat(0, 1) < bmeta:
                sorted_meta_coords.pop(0)
            _set_dat(-1, 0, max(bmeta, _get_dat(-1, 0)))
            while _get_dat(-1, 0) > blast:
                sorted_meta_coords.pop(-1)
            sorted_meta_coords.reverse()
            return ChunkIter.ParsedCoords([(None, sorted_meta_coords)])
        else:
            chunk_ids, dat_index = __buffer__.__swap__.__meta_index__.get_meta_indices()
            chunk_ranges = ChunkIter.ParsedCoords()
            try:
                for ri in range(len(chunk_ids) - 1, -1, -1):
                    chunk_id = chunk_ids[ri]
                    while dat_index[chunk_id][mkey] <= _get_dat(-1, 0):
                        _chunk_ranges = [(chunk_id, [sorted_meta_coords[-1]])]
                        ri += 1
                        chunk_cross = False
                        try:
                            while dat_index[chunk_ids[ri]][mkey] < _get_dat(-1, 1):
                                _chunk_ranges.append((chunk_ids[ri], None))
                                ri += 1
                                chunk_cross = True
                        except IndexError:
                            pass
                        if chunk_cross:
                            _chunk_ranges[-1] = (_chunk_ranges[-1][0], _chunk_cross_form(ri, -1))

                        sorted_meta_coords.pop(-1)

                        for id_, ran in reversed(_chunk_ranges):
                            if ran is None:
                                chunk_ranges[id_] = None
                            else:
                                try:
                                    if chunk_ranges[id_] is None:
                                        chunk_ranges[id_] = list()
                                    chunk_ranges[id_] += ran
                                except KeyError:
                                    chunk_ranges[id_] = ran
            finally:
                return chunk_ranges

    def iter(self, mode: Literal['readonly', 'r', 'live metas', 'l', 'shadow metas', 's'] = None
             ) -> Generator[tuple[_Row, list[int, int] | int | None]]:
        """Return a generator for a forward iteration."""
        mode = (mode or self._suit_key)[0]
        return self._iter_(self._iter_suits_[mode])

    def reversed(self, mode: Literal['readonly', 'r', 'live metas', 'l', 'shadow metas', 's'] = None
                 ) -> Generator[tuple[_Row, list[int, int] | int | None]]:
        """Return a generator for a backward iteration."""
        mode = (mode or self._suit_key)[0]
        return self._reversed_(self._iter_suits_[mode])

    def coordreversed(self, mode: Literal['readonly', 'r', 'live metas', 'l', 'shadow metas', 's'] = None
                      ) -> Generator[tuple[_Row, list[int, int] | int | None]]:
        """Return a generator for the forward iteration in the coordinates but from backward coordinates."""
        mode = (mode or self._suit_key)[0]
        return self._coordreversed_(self._iter_suits_[mode])

    def __iter__(self) -> Generator[tuple[_Row, list[int, int] | int | None]]:
        if self._iter_mode == "c":
            return self.coordreversed()
        else:
            return self.iter()

    def __reversed__(self) -> Generator[tuple[_Row, list[int, int] | int | None]]:
        if self._iter_mode == "c":
            return self.coordreversed()
        else:
            return self.reversed()

    def run(self) -> int:
        """Run the iteration, return the number of iterations."""
        i = 0
        for _ in self:
            i += 1
        return i
