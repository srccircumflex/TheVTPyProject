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
from typing import Callable
from threading import Thread
from os import get_terminal_size
from time import sleep


class GeoWatcher(Thread):
    size: tuple[int, int]
    width: int
    height: int
    bound: Callable[[tuple[int, int]], ...]
    per: float
    ctrl_val: bool

    def __init__(self, per: float = .005):
        Thread.__init__(self, daemon=True)
        self.bound = lambda *_: None
        self.size = get_terminal_size()
        self.width, self.height = self.size
        self.per = per
        self.start()
        self.ctrl_val = False

    def run(self) -> None:
        while True:
            sleep(self.per)
            if (size := get_terminal_size()) != self.size:
                self.bound(size)
                self.size = size
                self.width, self.height = self.size
                self.ctrl_val = True
            elif self.ctrl_val:
                self.bound(size)
                self.size = size
                self.width, self.height = self.size
                self.ctrl_val = False

    def bind(self, binding: Callable[[tuple[int, int]], ...]):
        self.bound = binding
