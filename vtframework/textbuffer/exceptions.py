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

from sqlite3 import DatabaseError


class ConfigurationError(RuntimeError):
    """
    Raised when an action is not possible due to the current configuration of the buffer components.
    """


class ConfigurationWarning(RuntimeWarning):
    """
    Raised when the current configuration of the buffer components is not expected.
    """


class CursorError(EOFError):
    """
    Base Exception type for cursor movement errors.
    """

    def __str__(self) -> str:
        return str().join(str(a) for a in self.args)


class CursorChunkLoadError(CursorError):
    """
    Raised if the position cannot be reached via the swap because
    the chunk of a position or direction is not available.
    """


class CursorChunkMetaError(CursorChunkLoadError):
    """
    FATAL ERROR

    Raised when chunks of the required side are present, but the metadata indicates
    that a chunk for the expected position cannot be loaded. This error should never
    occur unless the swap's metadata or the database is corrupted.
    """


class CursorNegativeIndexingError(CursorError):
    """
    Raised when a negative value is passed as the expected position.
    """


class CursorPlacingError(CursorError):
    """
    Raised when a required chunk was loaded or not needed, but the final cursor positioning
    in the rows of the ``TextBuffer`` was not successful (may indicate a too high value).
    """


class DatabaseInitError(DatabaseError):
    """
    Basic Exception type for errors during the creation of a database.
    """

    def __str__(self) -> str:
        return str().join(str(a) for a in self.args)


class DatabaseTableError(DatabaseInitError):
    """
    Raised when errors occur during the creation of tables in a database.
    """


class DatabaseFilesError(DatabaseInitError):
    """
    Raised when there are conflicts with the files of a database.
    """


class DatabaseCorruptedError(DatabaseError):
    """
    FATAL ERROR

    Raised when the data in the database does not meet the expectations.
    """
