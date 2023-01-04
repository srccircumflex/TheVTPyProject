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

from typing import Callable, Literal, Any
from collections import OrderedDict
from re import Pattern, search, finditer

try:
    from ..buffer import TextBuffer
except ImportError:
    pass

from .items import WriteItem


class _Row:
    """
    Row object for the processing and editing of text.

    **A Row can NOT be considered as an independent object**, but rather as a tool of the :class:`TextBuffer`.
    Basically, direct operations on this type without further ado, can disturb the stability of the whole
    ``TextBuffer`` and cause fatal errors.

    A positive return value of the manipulating methods is implemented as :class:`WriteItem` and the subclass
    :class:`WriteItem.Overflow`. This item contains the data for further processing by the :class:`TextBuffer`.
    For example, the overflow, which is always returned by ``writelines``, is inserted into the data by ``TextBuffer``
    depending on the write mode.

    Read processes on a _Row can be performed safely.

    - `Attribute` ``content``: The content data of the line without eventual line break.
    - `Attribute` ``end``: The end of the row, can be ``None`` for a non-existent, ``""`` for a non-breaking or
      ``"\\n"`` for an ordinary line break.

    Metadata:
    correct values cannot be assumed until after ``indexing()`` has been executed in the buffer.
    (The main buffer methods handle this).

    - `Attribute` ``__row_index__``: Indicates the location of the row in the list in the buffer.
    - `Attribute` ``__row_num__``: Contains the row number (respecting all data).
    - `Attribute` ``__line_num__``: Contains the line number (respecting all data). A line is defined in comparison to
      a row, as the area between two line breaks + line break at the end.
    - `Attribute` ``__content_start__``: Contains the content data start point at the beginning of the row
      (respecting all data). Content concerns the data without ends in the rows.
    - `Attribute` ``__data_start__``: Contains the data start point at the beginning of the row (respecting all data).
      Corresponds to the total number of characters before the row.
    - `Attribute` ``__next_row_num__``: ``__row_num__`` of the next line.
    - `Attribute` ``__next_line_num__``: ``__line_num__`` of the next line.
    - `Attribute` ``__next_content__``: ``__content_start__`` of the next line.
    - `Attribute` ``__next_data__``: ``__data_start__`` of the next line.

    - `Object` ``cursors``: :class:`_Cursors` is used for cursor processing of ``_Row`` and contains the positions of
      the cursor of a row in different contexts. Moving the cursor of the current row over this type has actual effect
      on the cursor in the ``TextBuffer``.

    - `Object` ``data_cache``: :class:`_DataCache` is a data cache for metadata about the row and the stored content.
    """

    content: str
    end: None | Literal['', '\n'] | str

    cursors: _Cursors
    data_cache: _DataCache

    tab_size: int
    tab_to_blanks: bool
    maxsize_param: int | None
    visual_max: int | None

    autowrap_points: Pattern | None

    _trim_: Callable[[], tuple[str, int | None] | None]

    __buffer__: TextBuffer

    __row_index__: int

    __row_num__: int
    __line_num__: int
    __content_start__: int
    __data_start__: int

    __next_row_num__: int
    __next_line_num__: int
    __next_content__: int
    __next_data__: int

    __slots__ = ('content', 'end', 'cursors', 'data_cache', 'tab_size', 'tab_to_blanks',
                 'maxsize_param', 'visual_max', 'autowrap_points', '_trim_', '__buffer__',
                 '__row_num__', '__line_num__', '__row_index__', '__content_start__', '__data_start__',
                 '__next_row_num__', '__next_line_num__', '__next_content__', '__next_data__')

    def _set_start_index_(self, _index: int, _row_n: int, _line_n: int, _cnt: int, _data: int
                          ) -> _Row:
        self.__row_index__ = _index
        self.__row_num__ = _row_n
        self.__line_num__ = _line_n
        self.__content_start__ = _cnt
        self.__data_start__ = _data
        return self

    def _set_next_index_(self, _row_n: int, _line_n: int, _cnt: int, _data: int) -> _Row:
        self.__next_row_num__ = _row_n
        self.__next_line_num__ = _line_n
        self.__next_content__ = _cnt
        self.__next_data__ = _data
        return self

    def __init__(
            self,
            __buffer__: TextBuffer,
            vis_maxsize: int | None,
            autowrap_points: Pattern | None,
            jump_points: Pattern,
            back_jump_points: Pattern,
            tab_size: int,
            tab_to_blanks: bool
    ):
        """
        Create a new row.

        Parameter:
            - `__buffer__`
                The :class:`TextBuffer` object for which ``_Row`` is created.
            - `vis_maxsize`
                The visual representation of the row content includes the shift of the tab character.
                This parameter can be used to define a maximum visual data size.
            - `autowrap_points`
                Can be specified for wrapping the row at a specific point as ``re.Pattern``.
                Then wrapping is done at the end of the ``re.Match`` when an `vis_maxsize` is specified.
            - `jump_points`
                Jump points for a special cursor movement defined as ``re.Pattern``. Applied when the cursor is moved
                forward in jump mode, the cursor is then moved to the end point of the ``re.Match`` or to the end of
                the row.
            - `back_jump_points`
                Jump points for a special cursor movement defined as ``re.Pattern``. Applied when the cursor is moved
                backward in jump mode, the cursor is then moved to the start point of the ``re.Match`` or to the
                beginning of the row.
            - `tab_size`
                Define the size of the visual representation of tab shifts.
            - `tab_to_blanks`
                Converts tabs to spaces directly as they are entered in a write operation, relative to the shift to
                the next tab stop.
        """
        self.content = str()
        self.end = None
        self.tab_size = tab_size
        self.tab_to_blanks = tab_to_blanks
        self.autowrap_points = autowrap_points

        self.__buffer__ = __buffer__

        self.cursors = _Cursors(self, jump_points, back_jump_points)

        self.visual_max = self.cursors.vis_pos_max = None
        self._resize(vis_maxsize)

        self._set_start_index_(0, 0, 0, 0, 0)
        self._set_next_index_(0, 0, 0, 0)

        self.data_cache = _DataCache(self)

    @classmethod
    def __newrow__(
            cls,
            baserow: _Row,
            **kwargs
    ) -> _Row:
        """
        Create a new row with the parameters from `baserow`.
        For the items of `kwargs` is a simple ``setattr`` loop used.
        """
        newrow = cls(
            baserow.__buffer__,
            baserow.maxsize_param,
            baserow.autowrap_points,
            baserow.cursors.jump_points,
            baserow.cursors.back_jump_points,
            baserow.tab_size,
            baserow.tab_to_blanks
        )
        for attr, val in kwargs.items():
            setattr(newrow, attr, val)
        return newrow

    def _trim(self) -> tuple[str, int | None] | None:
        """
        Cut the data to the predetermined length. Return the overflow [and the cut point (`autowrap_points`)]
        when the maximum length is exceeded.

        Returns: (`<overflow content>`, `<wrap-point>` | ``None``) | ``None``
        """
        with self:
            return self._trim_()

    def _resize(self, vis_maxsize: int | None) -> None:
        """Change the length parameterization. Will be observed only during the next operation."""
        self.maxsize_param = vis_maxsize
        if vis_maxsize:
            self.visual_max = vis_maxsize - 1
            self.cursors.vis_pos_max = vis_maxsize

            if self.autowrap_points:
                def trimming():
                    if self.data_cache.len_visual > self.visual_max:
                        self.end = None
                        _stop = self.cursors.tool_vis_to_cnt_excl(self.visual_max)
                        _content = self.content[:_stop]
                        if m := search(self.autowrap_points, _content):
                            self.content, of_content = self.content[:(e := m.end())], self.content[e:]
                        else:
                            e = None
                            of_content = self.content[_stop:]
                            self.content = _content
                        return of_content, e

            else:
                def trimming():
                    if self.data_cache.len_visual > self.visual_max:
                        self.end = None
                        _stop = self.cursors.tool_vis_to_cnt_excl(self.visual_max)
                        _content = self.content[:_stop]
                        of_content = self.content[_stop:]
                        self.content = _content
                        return of_content, None

            self._trim_ = trimming
        else:
            self.visual_max = self.cursors.vis_pos_max = None
            self._trim_ = lambda: None

    def _resize_bybaserow(self, baserow: _Row) -> None:
        """Change the length parameterization by `baserow`. Will be observed only during the next operation."""
        self._resize(baserow.maxsize_param)

    def _write_line(self,
                    line: str,
                    sub_chars: bool = False,
                    force_sub_chars: bool = False,
                    sub_line: bool = False
                    ) -> tuple[tuple[str, int | None] | None, int, str | None]:
        """
        Returns: ( (`<overflow content>`, `<wrap-point>` | ``None``) | ``None``,
        `<n deleted>`, `<removed content>` | ``None`` )
        """
        with self:
            if sub_line:
                deleted = len(removed := self.content[self.cursors.content:])
                removed = removed or None
                self.content = self.content[:self.cursors.content] + line
            elif not (nchars := len(line)):  # newline rudiment
                return self._trim(), 0, None
            elif force_sub_chars:
                if _removed := self.content[self.cursors.content:self.cursors.content + nchars]:
                    removed = _removed
                    deleted = len(removed)
                else:
                    removed = None
                    deleted = 0
                self.content = self.content[:self.cursors.content] + line + self.content[self.cursors.content + nchars:]
            elif sub_chars and (not line.count('\t')):
                try:
                    sub_end = min(self.content.index('\t', self.cursors.content), self.cursors.content + nchars)
                except ValueError:
                    sub_end = self.cursors.content + nchars
                if _removed := self.content[self.cursors.content:sub_end]:
                    removed = _removed
                    deleted = len(removed)
                else:
                    removed = None
                    deleted = 0
                self.content = self.content[:self.cursors.content] + line + self.content[sub_end:]
            else:
                self.content = self.content[:self.cursors.content] + line + self.content[self.cursors.content:]
                deleted = 0
                removed = None

            return self._trim(), deleted, removed

    def writelines(self, lines: list[str],
                   sub_chars: bool = False,
                   force_sub_chars: bool = False,
                   sub_line: bool = False,
                   nbnl: bool = False
                   ) -> WriteItem:
        """
        Write the first line from list `lines` and create an overflow object from the rest (:class:`WriteItem`)
        **[ ! ] CR ( "\\\\r" ) is not allowed**.

        Write in `substitute_chars` mode to replace characters associatively to the input in the row,
        at most up to the next tab (only used if neither a newline nor a tab is present in the `string`); OR

        don't care about tabs in the input and apply the substitution also to tabs when the mode
        `forcible_substitute_chars` is active; OR

        substitute the entire row from the cursor position in mode `substitute_line`;

        and replace line breaks with non-breaking line breaks when `nbnl`
        (`n`\\ on-`b`\\ reaking-`n`\\ ew-`l`\\ ine) is set to ``True``.

        Returns: :class:`WriteItem`
        """
        # get in shape
        if self.tab_to_blanks:
            first_raster = lines[0].split('\t')
            if after_t_row := first_raster[1:]:
                l_first_seg = len(first_raster[0])
                cur_seg = self.data_cache.raster[self.cursors.segment][:self.cursors.in_segment]
                first_t_space = self.tab_size - ((len(cur_seg) + l_first_seg) % self.tab_size)
                nwrite = l_first_seg + first_t_space
                first_row = first_raster[0] + ' ' * first_t_space
                for seg in after_t_row[:-1]:
                    l_seg = len(seg)
                    t_space = self.tab_size - (l_seg % self.tab_size)
                    nwrite += l_seg + t_space
                    first_row += seg + ' ' * t_space
                nwrite += len(after_t_row[-1])
                first_row += after_t_row[-1]
                lines[0] = first_row
            else:
                nwrite = len(lines[0])
            for i in range(1, len(lines)):
                row = ''
                for seg in (raster := lines[i].split('\t'))[:-1]:
                    l_seg = len(seg)
                    t_space = self.tab_size - (l_seg % self.tab_size)
                    nwrite += l_seg + t_space
                    row += seg + ' ' * t_space
                nwrite += len(raster[-1])
                row += raster[-1]
                lines[i] = row
        else:
            nwrite = sum(len(row) for row in lines)

        # write line
        with self:
            of_end = self.end
            diff_end = (self.end is not None)
            diff = self.data_cache.len_content
            overflow = None

            _line = lines.pop(0)
            if lines:
                self.end = ('' if nbnl else '\n')
                after = self.content[self.cursors.content:]
                self.content = self.content[:self.cursors.content]
                if sub_line:
                    _overflow, deleted, _ = self._write_line(_line, sub_chars, force_sub_chars, sub_line)
                    deleted += len(after)
                    removed = after or None
                    if _overflow:
                        overflow = [_overflow[0]] + lines
                    else:
                        overflow = lines
                else:
                    _overflow, deleted, removed = self._write_line(_line, sub_chars, force_sub_chars, sub_line)
                    if _overflow:
                        overflow = [_overflow[0]] + lines
                        overflow[-1] += after
                    else:
                        overflow = lines
                        overflow[-1] += after

            else:
                _overflow, deleted, removed = self._write_line(_line, sub_chars, force_sub_chars, sub_line)
                if _overflow:
                    overflow = [_overflow[0]]
            diff = (self.data_cache.len_content - diff) + ((self.end is not None) - diff_end)
            if overflow:
                overflow = WriteItem.Overflow(overflow, of_end, sub_line, nbnl, sum(len(row) for row in overflow))
            else:
                overflow = None

        return WriteItem(
            write=(nl := (lrr := len(lines))) + nwrite,
            newlines=nl > 0,
            write_rows=lrr - bool(lines and not lines[-1]) + 1,  # rudiment
            begin=self.__data_start__ + self.cursors.content,
            work_row=self.__row_num__,
            deleted=deleted,
            removed=removed,
            removed_end=None,
            diff=diff,
            overflow=overflow
        )

    def write(self, string: str,
              sub_chars: bool = False,
              force_sub_chars: bool = False,
              sub_line: bool = False,
              nbnl: bool = False
              ) -> WriteItem:
        """
        Write the first line from `string` and create an overflow object from the rest (:class:`WriteItem`)
        **[ ! ] CR ( "\\\\r" ) is not allowed**.

        Write in `substitute_chars` mode to replace characters associatively to the input in the row,
        at most up to the next tab (only used if neither a newline nor a tab is present in the `string`); OR

        don't care about tabs in the input and apply the substitution also to tabs when the mode
        `forcible_substitute_chars` is active; OR

        substitute the entire row from the cursor position in mode `substitute_line`;

        and replace line breaks with non-breaking line breaks when `nbnl`
        (`n`\\ on-`b`\\ reaking-`n`\\ ew-`l`\\ ine) is set to ``True``.

        Returns: :class:`WriteItem`
        """
        return self.writelines(string.split('\n'), sub_chars, force_sub_chars, sub_line, nbnl)

    def delete(self, end: bool = False) -> WriteItem | None:
        """
        Delete a character to the right of the cursor or the row ending.

        Returns :class:`WriteItem` if applicable in the row, otherwise ``None``.
        """
        with self:
            if end:
                if (end := self.end) is not None:
                    self.end = None
                    return WriteItem(write=0,
                                     newlines=False,
                                     write_rows=None,
                                     begin=self.__data_start__ + self.data_cache.len_content,
                                     work_row=self.__row_num__,
                                     deleted=1,
                                     removed='\n',
                                     removed_end=end,
                                     diff=-1)
            elif self.cursors.content != len(self.content):
                removed = self.content[self.cursors.content]
                self.content = self.content[:self.cursors.content] + self.content[self.cursors.content + 1:]
                return WriteItem(0, False, None, self.__data_start__ + self.cursors.content, self.__row_num__,
                                 1, removed, None, -1)

    def backspace(self) -> WriteItem | None:
        """
        Delete a character to the left of the cursor.

        Returns :class:`WriteItem` if applicable in the row, otherwise ``None``.
        """
        with self:
            if self.cursors.content != 0:
                removed = self.content[(s := self.cursors.content - 1)]
                self.content = self.content[:s] + self.content[self.cursors.content:]
                self.cursors.set_by_cnt(self.cursors.content - 1)
                return WriteItem(0, False, None, self.__data_start__ + self.cursors.content, self.__row_num__,
                                 1, removed, None, -1)

    def _remove_area(self, start: int, stop: int | None, st_gt_end: bool = True
                     ) -> tuple[str, str | Literal[False] | None]:
        """
        Delete the area from `start` to `stop` in the row (negative indexing is NOT allowed).

        Allow the coordinates to be greater than the existing data and read the end of line for it, instead of raising 
        an ``IndexError`` if `st_gt_end` is set to ``True``.

        Returns: ( `<removed content>`, `<removed row end>` | ``False`` )
        """
        removed = self.read_row_content(start, stop, st_gt_end)
        with self:
            if start > len(self.content):
                if st_gt_end:
                    self.end = None
                else:
                    raise IndexError(f'{start=}')
            elif stop is None:
                self.content = self.content[:start]
                self.end = None
            elif stop > len(self.content):
                if st_gt_end:
                    self.content = self.content[:start]
                    self.end = None
                else:
                    raise IndexError(f'{stop=}')
            else:
                self.content = self.content[:start] + self.content[stop:]
        return removed

    def shift(self, back: bool = False) -> WriteItem | None:
        """
        Write depending on the configuration of `tab_to_blanks` blanks or tabs when forward shifting,
        remove a tab or at most the equivalent number of blanks at the beginning of the line when `back` shifting.

        Returns :class:`WriteItem` if applicable in the row, otherwise ``None``.
        """
        write, deleted, removed = 0, 0, None
        if back:
            if self.content.startswith('\t'):
                with self:
                    self.content = self.content[1:]
                removed = '\t'
                deleted = 1
                diff = -1
            elif m := search("^\\s+", self.content):
                with self:
                    self.content = self.content[(rm := min(self.tab_size, m.end())):]
                removed = ' ' * rm
                deleted = rm
                diff = -rm
            else:
                return
        elif (free_space := self.data_cache.free_space) is None or free_space >= self.tab_size:
            if self.tab_to_blanks:
                with self:
                    self.content = ' ' * self.tab_size + self.content
                diff = write = self.tab_size
            else:
                with self:
                    self.content = '\t' + self.content
                diff = write = 1
        else:
            return

        return WriteItem(write=write,
                         newlines=False,
                         write_rows=None,
                         begin=self.__data_start__,
                         work_row=self.__row_num__,
                         deleted=deleted,
                         removed=removed,
                         removed_end=None,
                         diff=diff)

    def replace_tabs(self, start: int, stop: int | None, to_char: str = ' ') -> WriteItem | None:
        """
        Replace tab ranges `to_char` in the range from `start` to `stop` in the row (negative indexing is NOT allowed).

        Returns :class:`WriteItem` if applicable in the row, otherwise ``None``.
        """

        if not self.content:
            return

        if not (work_string := self.content[start:stop]):
            return

        work_raster = work_string.split('\t')
        if len(work_raster) < 2:
            return

        if to_char:

            try:
                start_seg, _ = self.cursors.tool_cnt_to_seg_in_seg(start)
            except IndexError:
                return

            if stop_seg := stop:
                if stop <= start:
                    return
                try:
                    stop_seg, _ = self.cursors.tool_cnt_to_seg_in_seg(stop)
                except IndexError:
                    stop_seg = None

            tab_sizes = tuple(
                self.tab_size - (len(s) % self.tab_size) for s in self.data_cache.raster[start_seg:stop_seg]
            )

            string = str().join(
                s + to_char * tab_sizes[n] for n, s in enumerate(work_raster[:-1])) + work_raster[-1]

        else:

            string = str().join(work_raster)

        before = self.content[:start]
        if stop is None:
            after = ''
        else:
            after = self.content[stop:]

        with self:
            self.content = before + string + after

        return WriteItem(write=(write := len(string)),
                         newlines=False,
                         write_rows=None,
                         begin=self.__data_start__ + start,
                         work_row=self.__row_num__,
                         deleted=(deleted := len(work_string)),
                         removed=work_string,
                         removed_end=None,
                         diff=write - deleted)

    def read_row_content(self, start: int, stop: int | None, st_gt_end: bool = True
                         ) -> tuple[str, str | Literal[False] | None]:
        """
        Read the area from `start` to `stop` in the row (negative indexing is NOT allowed).

        Allow the coordinates to be greater than the existing data and read the end of line for it, instead of raising 
        an ``IndexError`` if `st_gt_end` is set to ``True``.
        
        Returns: ( `<read content>`, `<read row end>` | ``False`` )
        """
        if start > len(self.content):
            if st_gt_end:
                return '', self.end
            else:
                raise IndexError(f'{start=}')
        elif stop is None:
            return self.content[start:], self.end
        elif stop > len(self.content):
            if st_gt_end:
                return self.content[start:], self.end
            else:
                raise IndexError(f'{stop=}')
        else:
            return self.content[start:stop], False

    def inrow(self) -> bool:
        """Whether when the main/buffer cursor is in the row."""
        return self.__row_index__ == self.__buffer__.current_row_idx

    def __enter__(self) -> _Row:
        """Start processing independently of the cache memory. (Called by its own methods)"""
        self.data_cache.__enter__()
        self.cursors.cur_translation_cache.__enter__()
        return self

    def __exit__(self, *args) -> None:
        """Stop the cache independent processing and clears the cache memory. (Called by its own methods)"""
        self.data_cache.__exit__()
        self.data_cache.change()
        self.cursors.cur_translation_cache.__exit__()
        self.cursors.cur_translation_cache.clear()

    def __lt__(self, other: _Row) -> bool:
        """``self.__row_num__ < other.__row_num__``"""
        return self.__row_num__ < other.__row_num__

    def __repr__(self) -> str:
        return "<%s n%d l%d c%d d%d i%d %r  %r>" % (
            self.__class__.__name__, self.__row_num__, self.__line_num__,
            self.__content_start__, self.__data_start__,
            self.__row_index__, self.content, self.end
        )

    def __bool__(self) -> bool:
        """Whether written data is available."""
        return self.end is not None or bool(self.data_cache.len_content)

    def __str__(self) -> str:
        """row ``content`` + row ``end``"""
        return self.content + (self.end or '')

    def __getitem__(self, item: int | slice) -> str:
        """eq. ``<str>[...]`` (``str.__getitem__``)"""
        end = ''
        if self.end == '\n':
            if isinstance(item, slice):
                if item.stop is None or item.stop > len(self.content):
                    end = '\n'
            elif item == len(self.content):
                return '\n'
        return self.content.__getitem__(item) + end

    def __hash__(self) -> int:
        """
        Calculated from:
            - class name
            - __row_num__
            - __line_num__
            - __content_start__
            - __data_start__
            - __row_index__
            - row content
            - row end
            - current content cursor position
        """
        return hash((self.__class__.__name__, self.__row_num__, self.__line_num__,
                     self.__content_start__, self.__data_start__, self.__row_index__,
                     self.content, self.end, self.cursors.content))


class _CursorCache:
    """LRU-Cache for cursor translations."""

    cache: list[OrderedDict[tuple, Any]]
    __buffer__: TextBuffer
    _processing: bool

    def __init__(self, __buffer__: TextBuffer, _n_slots: int):
        self.cache = [OrderedDict() for _ in range(_n_slots)]
        self.__buffer__ = __buffer__
        self._processing = False

    # slot 0:  tool_vis_to_cnt_excl          (default size: 4)
    # slot 1:  tool_seg_in_seg_to_vis        (default size: 8)
    # slot 2:  tool_cnt_to_seg_in_seg        (default size: 16)
    # slot 3:  tool_cnt_to_vis               (default size: 32)
    # slot 4:  tool_vis_to_cnt               (default size: 32)
    # slot 5:  content_limit                 (default size: 1)

    def __call__(self, func: Callable, slot: int, *args) -> Any:
        if self._processing:
            return func(*args)
        try:
            return self.cache[slot][args]
        except KeyError:
            if len(self.cache[slot]) > self.__buffer__.__cursor_translation_cache_sizes__[slot]:
                self.cache[slot].popitem(last=False)
            val = func(*args)
            self.cache[slot][args] = val
            return val

    def clear(self) -> None:
        """Clear each method cache."""
        self.cache = [OrderedDict() for _ in range(len(self.cache))]

    def __enter__(self) -> None:
        """Independent processing."""
        self._processing = True

    def __exit__(self, *args) -> None:
        """Stops independent processing."""
        self._processing = False


class _Cursors:
    """
    Row Cursor processing.

    - `Attribute` ``content``: Cursor position within the row-content-string.
    - `Attribute` ``visual``: Row-Cursor position with consideration of the visual representation of tab spaces.
    - `Attribute` ``segment``: Segment number of the tap-separated-row-content-string in which the cursor is located.
    - `Attribute` ``in_segment``: Cursor position within the tap-separated-row-content-string-segment.
    - `Property` ``data_cursor``: The current content-cursor position in the totality of the data.
    - `Property` ``content_limit``: Current maximum position of the content cursor.
    """

    segment: int
    in_segment: int
    content: int
    visual: int

    __row__: _Row
    jump_points: Pattern
    back_jump_points: Pattern
    vis_pos_max: int | None

    cur_translation_cache: _CursorCache

    __slots__ = ('segment', 'in_segment', 'content', 'visual', '__row__',
                 'jump_points', 'back_jump_points', 'vis_pos_max', 'cur_translation_cache')

    @property
    def data_cursor(self) -> int:
        """The current cursor position in the totality of the data."""
        return self.__row__.__data_start__ + self.content

    @property
    def content_limit(self) -> int:
        """
        Current maximum position of the content cursor.

        cache slot: 5
        """

        def f():
            try:
                if self.vis_pos_max:
                    return self.tool_vis_to_cnt(self.vis_pos_max)
            except IndexError:
                pass
            return len(self.__row__.content)

        return self.cur_translation_cache(f, 5)

    def __init__(self, __row__: _Row, jump_points: Pattern, back_jump_points: Pattern,
                 vis_max: int = None):
        self.__row__ = __row__
        self.jump_points = jump_points
        self.back_jump_points = back_jump_points
        self.vis_pos_max = vis_max
        self.cur_translation_cache = _CursorCache(__row__.__buffer__, 6)
        self.reset()

    def reset(self) -> None:
        """Reset each value to 0."""
        self.segment = self.in_segment = self.content = self.visual = 0

    def new_cnt_cursor(
            self, __z: int, jump: bool = False, border: bool = False, as_far: bool = False
    ) -> int | None:
        """
        Calculate and verify a new content-cursor position.

        :param __z: is added to content-cursor (integer)
        :param jump: jump to a predefined point (direction defined via __z: [ -1 | 1 ])
        :param border: jump to pos1 or end (direction defined via __z: [ -1 | 1 ])
        :param as_far: return the most obvious value (only significant if jump and border are False)

        :return: new content-cursor or None
        """
        if jump:
            if __z > 0:
                if not (
                        m := search(self.jump_points,
                                    (_str := self.__row__.content)[self.content:])):
                    return min(self.content_limit, len(_str))
                else:
                    return min(self.content_limit, self.content + m.end())
            else:
                if not (
                        m := list(
                            finditer(self.back_jump_points, self.__row__.content[:self.content]))):
                    return 0
                else:
                    return m[-1].start()
        elif border:
            if __z > 0:
                if self.__row__.maxsize_param:
                    return self.content_limit
                else:
                    return self.__row__.data_cache.len_content
            else:
                return 0
        elif (_max := self.content_limit) >= (cursor := self.content + __z) >= 0:
            return cursor
        elif as_far:
            return max(0, min(cursor, _max))
        else:
            return

    def move(self, __z: int, jump: bool = False, border: bool = False) -> bool:
        """
        Move the cursors by a content-cursor summand.

        :param __z: is added to content-cursor (integer)
        :param jump: jump to a predefined point (direction defined via __z: [ -1 | 1 ])
        :param border: jump to pos1 or end (direction defined via __z: [ -1 | 1 ])

        :return: True on success, otherwise False
        """
        if (cursor := self.new_cnt_cursor(__z, jump, border)) is not None:
            self.set_by_cnt(cursor)
            return True
        return False

    def set_by_cnt(self, __n: int) -> None:
        """
        Set the cursors by a content-cursor position (natural number).

        :raise IndexError: if n is too large in relation to the row data
        """
        self.segment, self.in_segment = self.tool_cnt_to_seg_in_seg(__n)
        self.content = __n
        self.visual = self.tool_seg_in_seg_to_vis(self.segment, self.in_segment)

    def set_by_vis(self, __n: int) -> None:
        """
        Set the cursors by a visual-cursor position (natural number).

        :raise IndexError: if n is too large in relation to the row data
        """
        self.set_by_cnt(self.tool_vis_to_cnt(__n))

    def tool_seg_in_seg_to_vis(self, seg: int, in_seg: int) -> int:
        """
        Visual-cursor in relation to segment-cursors.

        cache slot: 1
        """

        def f(_seg: int, _in_seg: int):
            return sum(self.__row__.data_cache.visual_len_index[:_seg]) + _in_seg

        return self.cur_translation_cache.__call__(f, 1, seg, in_seg)

    def tool_cnt_to_seg_in_seg(self, __n: int) -> tuple[int, int]:
        """
        Segment-cursors in relation to content-cursor.

        cache slot: 2

        :raises IndexError: if n is too large in relation to the row data
        """

        def f(n):
            i = 0
            while n > (_l := len(self.__row__.data_cache.raster[i])):
                n -= _l + 1
                i += 1
            return i, n

        return self.cur_translation_cache.__call__(f, 2, __n)

    def tool_cnt_to_vis(self, __n: int) -> int:
        """
        Visual-cursor in relation to content-cursor.

        cache slot: 3

        :raises IndexError: if n is too large in relation to the row data
        """

        def f(n):
            seg, in_seg = self.tool_cnt_to_seg_in_seg(n)
            if seg:
                return sum(self.__row__.data_cache.visual_len_index[:seg]) + in_seg
            return n

        return self.cur_translation_cache.__call__(f, 3, __n)

    def tool_vis_to_cnt(self, __n: int) -> int:
        """
        Content-cursor in relation to visual-cursor, incl. incompletely enclosed tab.

        cache slot: 4

        :raises IndexError: if n is too large in relation to the row data
        """

        def f(n):
            i = 0
            visual_index = self.__row__.data_cache.visual_len_index
            seg_len = visual_index[i]
            raster = self.__row__.data_cache.raster
            while n > seg_len:
                n -= seg_len
                i += 1
                seg_len = visual_index[i]
            if i != len(visual_index) - 1 and n == seg_len:
                n = len(raster[i]) + 1
            return sum(len(s) + 1 for s in raster[:i]) + n

        return self.cur_translation_cache.__call__(f, 4, __n)

    def tool_vis_to_cnt_excl(self, __n: int) -> int:
        """
        Content-cursor in relation to visual-cursor, excl. incompletely enclosed tab.

        cache slot: 0

        :raises IndexError: if n is too large in relation to the row data
        """

        def f(n):
            i = 0
            visual_index = self.__row__.data_cache.visual_len_index
            seg_len = visual_index[i]
            raster = self.__row__.data_cache.raster
            while n > seg_len:
                n -= seg_len
                i += 1
                seg_len = visual_index[i]
            if (_l := len(raster[i])) < n:
                n = (_l if not i else 0)
            return sum(len(s) + 1 for s in raster[:i]) + n

        return self.cur_translation_cache.__call__(f, 0, __n)

    def __repr__(self) -> str:
        return "<%s seg=%d in_seg=%d dat=%d vis=%d>" % (
            self.__class__.__qualname__, self.segment, self.in_segment, self.content, self.visual)


class _DataCache:
    """
    Row Metadata Cache.

    - `Property` ``len_visual``: The visual length (incl. visual tab representation).
    - `Property` ``len_visual_incl``: The visual length incl. linebreak.
    - `Property` ``len_content``: The string length.
    - `Property` ``len_abscontent``: The total content length at the end of the row (excl. line breaks).
    - `Property` ``len_absdata``: The total data length at the end of the row (incl. all line breaks).
    - `Property` ``len_absdata_excl``: The total data length at the end of the row (incl. all line breaks, except the own).
    - `Property` ``raster``: The row data as tab separated raster.
    - `Property` ``visual_len_index``: The visual lengths of each segment in the separated raster.
    - `Property` ``free_space``: Remaining content space in the row. Is an integer value only if a maximum is defined.
    """

    _changed: bool
    _changed_raster: bool
    _len_visual: int
    _len_content: int
    _free_space: int | None
    _raster: list[str]
    _visual_len_index: list[int]
    __row__: _Row
    _processing: bool

    __slots__ = ('_changed', '_changed_raster', '_len_visual', '_len_content', '_raster',
                 '_visual_len_index', '__row__', '_processing', '_free_space')

    @property
    def len_visual(self) -> int:
        """The visual length (incl. visual tab representation)."""
        self()
        return self._len_visual

    @property
    def len_visual_incl(self) -> int:
        """The visual length (incl. visual tab representation) incl. linebreak."""
        self()
        return self._len_visual + bool(self.__row__.end)

    @property
    def len_content(self) -> int:
        """The string length."""
        self()
        return self._len_content

    @property
    def len_abscontent(self) -> int:
        """The total content length at the end of the row (excl. line breaks)."""
        return self.__row__.__content_start__ + self._len_content

    @property
    def len_absdata(self) -> int:
        """The total data length at the end of the row (incl. all line breaks)."""
        return self.__row__.__data_start__ + self.len_content + (self.__row__.end is not None)

    @property
    def len_absdata_excl(self) -> int:
        """The total data length at the end of the row (incl. all line breaks, except the own)."""
        return self.__row__.__data_start__ + self.len_content

    @property
    def raster(self) -> list[str]:
        """The row data as tab separated raster."""
        if self._processing:
            self._raster = self.__row__.content.split('\t')
        elif self._changed_raster:
            self._raster = self.__row__.content.split('\t')
            self._changed_raster = False
        return self._raster

    @property
    def visual_len_index(self) -> list[int]:
        """The visual lengths of each segment."""
        self()
        return self._visual_len_index

    @property
    def free_space(self) -> int | None:
        """Remaining content space in the row. Is an integer value only if a maximum is defined."""
        self()
        return self._free_space

    def __init__(self, __row__: _Row):
        self.__row__ = __row__
        self._processing = False
        self._changed = True
        self._changed_raster = True
        self()

    def __call__(self) -> None:
        if self._changed or self._processing:
            self._raster = self.raster
            self.reset()
            for seg in self._raster[:-1]:
                vis_len = (_l := len(seg)) + (self.__row__.tab_size - (_l % self.__row__.tab_size))
                self._len_visual += vis_len
                self._visual_len_index.append(vis_len)
            self._len_content = len(self.__row__.content)
            self._len_visual += (_l := len(self._raster[-1]))
            self._visual_len_index.append(_l)
            if self.__row__.visual_max:
                self._free_space = self.__row__.visual_max - self._len_visual
            else:
                self._free_space = None

    def reset(self) -> None:
        """Clear each field."""
        if not self._processing:
            self._changed = False
            self._changed_raster = False
        self._len_content = self._len_visual = 0
        self._visual_len_index = list()

    def change(self) -> None:
        """Mark a change."""
        self._changed = True
        self._changed_raster = True

    def __enter__(self) -> None:
        """Independent processing."""
        self._processing = True

    def __exit__(self, *args) -> None:
        """Stops independent processing."""
        self._processing = False
