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

from typing import Callable, Literal, Generator, IO, Iterator, AnyStr
from io import UnsupportedOperation

try:
    from .buffer import TextBuffer
    from ._buffercomponents.row import _Row
except ImportError:
    pass

from .chunkiter import ChunkIter


class Reader(IO):
    """
    Independent io object to read from a :class:`TextBuffer`.

    ``Reader`` has, apart from the known reading methods, methods to read lines by a number, a number of rows or
    specific data ranges.
    A line is defined as the content between two line breaks + final line break, a row corresponds to one
    :class:`_Row` in the ``TextBuffer``.

    To assign different endings to the rows during reading, a dictionary can be passed via the `endings` parameter,
    which contains the different replacements. The keys can be selected from ``None`` (no ending),
    ``"\\n"`` (newline) and ``""`` (unbroken newline) and the value can be assigned as bytes.

    To create ``Reader`` as a binary read object, an encoding or ``True`` (UTF8) can be specified by the parameter
    `bin_mode`.

    Set `tabs_to_blanks` to a tab size or to ``True`` (same size as in ``TextBuffer``) to convert tab shifts to blanks
    when reading or replace the tab characters via `replace_tabs`, the replacement is specified as bytes.

    Define `progress` to set an approximate starting point (starts at the beginning of the applicable row) or 
    define the data ranges to be read with `dat_ranges` as a sorted list ``[ [<start>, <stop>], ... ]``.
    The `progress` attribute is NOT updated during reading.
    """

    __buffer__: TextBuffer
    progress: int
    _current_chunk: list[AnyStr]
    buffer: AnyStr
    _next_rowdata_: Callable[[], None]
    _next_iteration_: Callable[[], None]
    _eof: bool
    _nl: AnyStr
    _mode: str
    _encoding: str

    __slots__ = ('__buffer__', 'progress', '_current_chunk', 'buffer', '_next_rowdata_', '_next_iteration_',
                 '_eof', '_nl', '_mode', '_encoding')

    def __init__(
            self,
            __buffer__: TextBuffer,
            *,
            bin_mode: bool | str = False,
            endings: dict[Literal['', '\n'] | None, bytes] = None,
            tabs_to_blanks: int | bool = False,
            replace_tabs: bytes = None,
            progress: int = 0,
            dat_ranges: list[list[int, int]] = None
    ):
        self.__buffer__ = __buffer__
        self.progress = progress
        self._eof = False
        self._mode = "r"

        _endings: dict[str | None | bool, bytes | str] = (dict() if endings is None else endings)
        _endings[False] = b''
        tabs_to_blanks = (__buffer__._top_baserow.tab_size if tabs_to_blanks is True else tabs_to_blanks)

        if bin_mode:
            _endings.setdefault(None, b'')
            _endings.setdefault('', b'')
            _endings.setdefault('\n', b'\n')
            self._encoding = ("utf-8" if bin_mode is True else bin_mode)
            self._mode = "rb"
            if tabs_to_blanks:
                def convert(content: str, end: str | bool | None) -> bytes:
                    raster = content.split('\t')
                    return (str().join(
                        [s + ' ' * (tabs_to_blanks - (len(s) % tabs_to_blanks)) for s in raster[:-1]]
                    ) + raster[-1]).encode(self._encoding) + _endings[end]
            elif replace_tabs is not None:
                def convert(content: str, end: str | bool | None) -> bytes:
                    return content.replace('\t', replace_tabs).encode(self._encoding) + _endings[end]
            else:
                def convert(content: str, end: str | bool | None) -> bytes:
                    return content.replace('\t', replace_tabs).encode(self._encoding) + _endings[end]
            self.buffer = bytes()
            self._nl = b'\n'
        else:
            _endings = {k: v.decode() for k, v in _endings.items()}
            _endings.setdefault(None, '')
            _endings.setdefault('', '')
            _endings.setdefault('\n', '\n')
            if tabs_to_blanks:
                def convert(content: str, end: str | bool | None) -> str:
                    raster = content.split('\t')
                    return str().join(s + ' ' * (tabs_to_blanks - (len(s) % tabs_to_blanks)) for s in raster[:-1]
                                      ) + raster[-1] + _endings[end]
            elif replace_tabs is not None:
                replace_tabs = replace_tabs.decode()

                def convert(content: str, end: str | bool | None) -> str:
                    return content.replace('\t', replace_tabs) + _endings[end]
            else:
                def convert(content: str, end: str | bool | None) -> str:
                    return content + _endings[end]
            self.buffer = str()
            self._nl = '\n'

        if __buffer__.__swap__:
            if dat_ranges is not None:
                def gen_chunk() -> Generator[None]:
                    def rows_to_data(rows: list[_Row]):
                        if (_range := chunk_ranges[id_]) is None:
                            self._current_chunk += [convert(row.content, row.end) for row in rows]
                        else:
                            _range: list[list[int, int]]
                            chunk_range_dat = []
                            for row in reversed(rows):
                                while _range and _range[0][1] > row.__data_start__:
                                    start = max(0, _range[0][0] - row.__data_start__)
                                    stop = _range[0][1] - row.__data_start__
                                    chunk_range_dat.insert(0, convert(*row.read_row_content(start, stop)))
                                    if _range[0][0] >= row.__data_start__:
                                        _range.pop(0)
                                    else:
                                        break
                            self._current_chunk += chunk_range_dat

                    for range_ in dat_ranges.copy():
                        chunk_ranges = ChunkIter.pars_meta_coords(__buffer__, [range_], 'd')
                        self._current_chunk = []
                        for id_ in reversed(chunk_ranges.keys()):
                            if id_ is None:
                                rows_to_data(__buffer__.rows)
                            else:
                                rows_to_data(__buffer__.__swap__.chunk_buffer(id_, sandbox=True).rows)
                        yield

                gen_chunk = gen_chunk()

                try:
                    next(gen_chunk)
                except StopIteration:
                    self._current_chunk = list()

                def next_rowdata():
                    try:
                        self.buffer += self._current_chunk.pop(0)
                    except IndexError:
                        try:
                            next(gen_chunk)
                            self.buffer += self._current_chunk.pop(0)
                        except StopIteration:
                            self._eof = True
                            raise EOFError

                def next_iter():
                    if self._current_chunk:
                        self.buffer += self.buffer.__class__().join(self._current_chunk)
                        self._current_chunk.clear()
                    else:
                        try:
                            next(gen_chunk)
                            self.buffer += self.buffer.__class__().join(self._current_chunk)
                            self._current_chunk.clear()
                        except StopIteration:
                            self._eof = True
                            raise EOFError
            else:
                ids, index = __buffer__.__swap__.__meta_index__.get_meta_indices()
                ids = list(ids)
                try:
                    while progress > index[ids[1]][0]:
                        ids.pop(0)
                except IndexError:
                    pass

                if (first := ids.pop(0)) is None:
                    first_rows = __buffer__.rows
                else:
                    first_rows = __buffer__.__swap__.chunk_buffer(first, sandbox=True).rows
                i = 0
                try:
                    while progress > first_rows[i].__data_start__:
                        i += 1
                except IndexError:
                    pass

                self._current_chunk = [convert(row.content, row.end) for row in first_rows[i:]]

                def gen_chunk() -> Generator[None]:
                    for id_ in ids:
                        if id_ is None:
                            self._current_chunk = [convert(row.content, row.end) for row in __buffer__.rows]
                        else:
                            self._current_chunk = [convert(row.content, row.end) for row in
                                                   __buffer__.__swap__.chunk_buffer(id_, sandbox=True).rows]
                        yield

                gen_chunk = gen_chunk()

                def next_rowdata():
                    try:
                        self.buffer += self._current_chunk.pop(0)
                    except IndexError:
                        try:
                            next(gen_chunk)
                            self.buffer += self._current_chunk.pop(0)
                        except StopIteration:
                            self._eof = True
                            raise EOFError

                next_iter = next_rowdata
        elif dat_ranges is not None:
            def gen_chunk() -> Generator[None]:
                for range_ in dat_ranges.copy():
                    _range: list[list[int, int]] = ChunkIter.pars_meta_coords(__buffer__, [range_], 'd').ordered()[0][1]
                    self._current_chunk = []
                    for row in reversed(__buffer__.rows):
                        while _range and _range[0][1] > row.__data_start__:
                            start = max(0, _range[0][0] - row.__data_start__)
                            stop = _range[0][1] - row.__data_start__
                            self._current_chunk.insert(0, convert(*row.read_row_content(start, stop)))
                            if _range[0][0] >= row.__data_start__:
                                _range.pop(0)
                            else:
                                break
                    yield

            gen_chunk = gen_chunk()

            try:
                next(gen_chunk)
            except StopIteration:
                self._current_chunk = list()

            def next_rowdata():
                try:
                    self.buffer += self._current_chunk.pop(0)
                except IndexError:
                    try:
                        next(gen_chunk)
                        self.buffer += self._current_chunk.pop(0)
                    except StopIteration:
                        self._eof = True
                        raise EOFError

            def next_iter():
                if self._current_chunk:
                    self.buffer += self.buffer.__class__().join(self._current_chunk)
                    self._current_chunk.clear()
                else:
                    try:
                        next(gen_chunk)
                        self.buffer += self.buffer.__class__().join(self._current_chunk)
                        self._current_chunk.clear()
                    except StopIteration:
                        self._eof = True
                        raise EOFError
        else:
            i = 0
            try:
                while progress > __buffer__.rows[i].__data_start__:
                    i += 1
            except IndexError:
                pass

            self._current_chunk = [convert(row.content, row.end) for row in __buffer__.rows[i:]]

            def next_rowdata() -> None:
                try:
                    self.buffer += self._current_chunk.pop(0)
                except IndexError:
                    self._eof = True
                    raise EOFError

            next_iter = next_rowdata

        self._next_rowdata_ = next_rowdata
        self._next_iteration_ = next_iter

    def read(self, __lim: int = None) -> AnyStr:
        """
        Read all data in ``TextBuffer`` or until a character limit is reached.

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        if __lim is None:
            try:
                while True:
                    self._next_rowdata_()
            except EOFError:
                return self.buffer
            finally:
                self.buffer = self.buffer.__class__()
        else:
            try:
                while len(self.buffer) < __lim:
                    self._next_rowdata_()
            except EOFError:
                pass
            try:
                return self.buffer[:__lim]
            finally:
                self.buffer = self.buffer[__lim:]

    def readline(self, __lim: int = None) -> AnyStr:
        """
        Read until the next real line break or at most until the character limit is reached.

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        if __lim is None:
            try:
                while not self.buffer.endswith(self._nl):
                    self._next_rowdata_()
            except EOFError:
                pass
            try:
                return self.buffer
            finally:
                self.buffer = self.buffer.__class__()
        else:
            try:
                while len(self.buffer) < __lim and not self.buffer.endswith(self._nl):
                    self._next_rowdata_()
            except EOFError:
                pass
            try:
                return self.buffer[:__lim]
            finally:
                self.buffer = self.buffer[__lim:]

    def readlines(self, __hint: int = None) -> list[AnyStr]:
        """
        Read all lines in the ``TextBuffer`` or until the lines read include the character hint and keep "\\n".

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        lines = list()
        if __hint is None:
            try:
                while True:
                    lines.append(self.readline())
            except EOFError:
                pass
            return lines
        else:
            try:
                while True:
                    lines.append(line := self.readline(__hint))
                    if (__hint := __hint - len(line)) <= 0:
                        break
            except EOFError:
                pass
            return lines

    def readnlines(self, __n: int, __hint: int = None) -> list[AnyStr]:
        """
        Read a number of lines or until the lines read include the character hint and keep "\\n".

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        lines = list()
        if __hint is None:
            try:
                for _ in range(__n):
                    lines.append(self.readline())
            except EOFError:
                pass
            return lines
        else:
            try:
                for _ in range(__n):
                    lines.append(line := self.readline(__hint))
                    if (__hint := __hint - len(line)) <= 0:
                        break
            except EOFError:
                pass
            return lines

    def readrow(self, __lim: int = None) -> AnyStr:
        """
        Read the next row into the reader buffer if it is empty and return the entire buffer or up to the character
        limit (corresponds to the remaining characters or an entire row).

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        if not self.buffer:
            self._next_rowdata_()
        if __lim is None:
            try:
                return self.buffer
            finally:
                self.buffer = self.buffer.__class__()
        else:
            try:
                return self.buffer[:__lim]
            finally:
                self.buffer = self.buffer[__lim:]

    def readrows(self, __n: int, __hint: int = None) -> list[AnyStr]:
        """
        Read a number of rows or until the rows read include the character hint.

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        rows = list()
        if __hint is None:
            try:
                for _ in range(__n):
                    rows.append(self.readrow())
            except EOFError:
                pass
            return rows
        else:
            try:
                for _ in range(__n):
                    rows.append(row := self.readrow(__hint))
                    if (__hint := __hint - len(row)) <= 0:
                        break
            except EOFError:
                pass
            return rows

    def readiteration(self, __lim: int = None) -> AnyStr:
        """
        Read the next iteration (the next data range if configured, otherwise the next row)
        completely or until a character limit is reached.

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        if not self.buffer:
            self._next_iteration_()
        if __lim is None:
            try:
                return self.buffer
            finally:
                self.buffer = self.buffer.__class__()
        else:
            try:
                return self.buffer[:__lim]
            finally:
                self.buffer = self.buffer[__lim:]

    def readiterations(self, __n: int, __hint: int = None) -> list[AnyStr]:
        """
        Read a number of iterations (data ranges if configured, otherwise the rows)
        or until the iterations read include the character hint.

        :raises EOFError: End of data reached.
        """
        if self._eof and not self.buffer:
            raise EOFError
        rows = list()
        if __hint is None:
            try:
                for _ in range(__n):
                    rows.append(self.readiteration())
            except EOFError:
                pass
            return rows
        else:
            try:
                for _ in range(__n):
                    rows.append(row := self.readiteration(__hint))
                    if (__hint := __hint - len(row)) <= 0:
                        break
            except EOFError:
                pass
            return rows

    def close(self) -> None:
        """
        Delete the internal buffer attributes of ``Reader`` and thus free memory
        (subsequent read processes will raise ``AttributeError``).
        """
        del (self._current_chunk,
             self.buffer,
             self._next_rowdata_,
             self._next_iteration_)

    @property
    def eof(self) -> bool:
        """whether the end of the data has been reached"""
        return self._eof

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def mode(self) -> str:
        """``"r"`` | ``"rb"``"""
        return self._mode

    @property
    def name(self) -> str:
        """``""``"""
        return ""

    @property
    def closed(self) -> bool:
        """whether the reader buffer is deleted"""
        try:
            _ = self._eof
            return True
        except AttributeError:
            return False

    def fileno(self) -> int:
        """``pass``"""
        pass

    def flush(self) -> None:
        """``pass``"""
        pass

    def isatty(self) -> bool:
        """``False``"""
        return False

    def readable(self) -> bool:
        """``True``"""
        return True

    def seek(self, __offset: int, __whence: int = ...) -> int:
        """:raises NotImplementedError:"""
        raise NotImplementedError

    def seekable(self) -> bool:
        """``False``"""
        return False

    def tell(self) -> int:
        """``progress``"""
        return self.progress

    def truncate(self, __size: int | None = ...) -> int:
        """:raises NotImplementedError:"""
        raise NotImplementedError

    def writable(self) -> bool:
        """``False``"""
        return False

    def write(self, __s) -> int:
        """:raises UnsupportedOperation:"""
        raise UnsupportedOperation

    def writelines(self, __lines) -> None:
        """:raises UnsupportedOperation:"""
        raise UnsupportedOperation

    def __next__(self) -> str:
        """next row"""
        return self.readrow()

    def __iter__(self) -> Iterator[str]:
        """row iterator"""
        return self

    def __enter__(self) -> Reader:
        """``Reader``"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Execute the ``close`` method of ``Reader``"""
        self.close()
