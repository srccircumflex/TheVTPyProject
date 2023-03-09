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

from threading import Thread
from typing import Iterable, Hashable
from time import sleep

from vtframework.io.io import Input, InputSuper, SpamHandle
from vtframework.io.binder import Binder


class InputModem(Input):
    """
    ``Input`` type as an overall concept for processing inputs via stdin.

    When the thread is started, inputs are continuously read from stdin, parsed/interpreted and passed to the
    ``__binder__``.

    ``stdin --> interpreter --> [ SpamHandler ] --> binder``

    The send method is also an indirect interface from input to the binder.

    See also documentation of :class:`Input` and :class:`Binder`.

    :param thread_smoothness: specifies the time value for how many seconds to wait in a thread iteration.
    :param thread_block: enables blocked reading of stdin in the thread (thread_smoothness is ignored in this case).
    :param thread_spam: optional handler for repeated inputs.
    :param mod: modifies the emulator accordingly if is True (nonblock and nonecho).
    :param find_all_bindings: Binder will search for all bindings, instead of breaking at first match.
    :param find_instance_bindings_only: Binder will not also search in the class cache when instance matches have been
      encountered.
    :param find_class_bindings_first: Binder will order type match[es] first when type and instance match[es] occur.
    :param use_alter_bindings: Binder will use the alternative memory-saving version of `Binding` (`BindingT`);
     at the expense of dynamics (no `BindItem` is returned when binding)
    """

    __binder__: Binder

    def __init__(self, thread_smoothness: float | bool = .03, thread_block: bool = False,
                 thread_spam: SpamHandle | None = SpamHandle(), mod: bool = True,
                 find_all_bindings: bool = False,
                 find_instance_bindings_only: bool = False, find_class_bindings_first: bool = False,
                 use_alter_bindings: bool = False
                 ):
        Input.__init__(self, thread_smoothness, thread_block, thread_spam, mod)
        self.__binder__ = Binder(find_all_bindings, find_instance_bindings_only, find_class_bindings_first,
                                 use_alter_bindings)

    def send(self, block: bool = False) -> bool:
        """
        Read with or without `block`\\ ing and send the object to the binder.

        :return: Whether something was executed
        """
        if block:
            if self.t_spam(self.getch(block=True), self._pipe):
                return self.__binder__.send(self.pipe_get(block=True))
        elif _cr := self.getch(block=False):
            if self.t_spam(_cr, self._pipe):
                return self.__binder__.send(self.pipe_get(block=True))
        return False

    def run(self) -> None:
        """
        Read with or without blocking (``self.t_block``) while ``self.t_keepalive`` is ``True`` and send the
        objects to the binder. Wait ``self.t_smoothness`` seconds in an iteration if ``self.t_block`` is ``False``.

        ``stdin --> interpreter --> [ SpamHandler ] --> binder``
        """
        if self.t_block:
            while self.t_keepalive:
                if self.t_spam(self.getch(block=True), self._pipe):
                    self.__binder__.send(self.pipe_get(block=True))
        elif self.t_smoothness:
            while self.t_keepalive:
                sleep(self.t_smoothness)
                if _cr := self.getch(block=False):
                    if self.t_spam(_cr, self._pipe):
                        self.__binder__.send(self.pipe_get(block=True))
        else:
            while self.t_keepalive:
                if _cr := self.getch(block=False):
                    if self.t_spam(_cr, self._pipe):
                        self.__binder__.send(self.pipe_get(block=True))


class InputSuperModem(InputSuper):
    """
    ``InputSuper`` type as an overall concept for processing inputs via stdin.

    When the thread is started, inputs are continuously read from stdin, parsed/interpreted and passed to the
    ``__binder__``.

    ``adapter --> interpreter --> [ SpamHandler ] --> binder``

    The send method is also an indirect interface from input to the binder.

    See also documentation of :class:`InputSuper` and :class:`Binder`.

    :param find_all_bindings: Binder will search for all bindings, instead of breaking at first match.
    :param find_instance_bindings_only: Binder will not also search in the class cache when instance matches have been
      encountered.
    :param find_class_bindings_first: Binder will order type match[es] first when type and instance match[es] occur.
    :param use_alter_bindings: Binder will use the alternative memory-saving version of `Binding` (`BindingT`);
     at the expense of dynamics (no `BindItem` is returned when binding)
    """

    __binder__: Binder

    def __init__(self, thread_smoothness: float | bool = .03, thread_block: bool = False,
                 thread_spam: SpamHandle | None = SpamHandle(), manual_esc_tt: float = .8,
                 manual_esc_interpreter: bool = False,
                 manual_esc_finals: tuple[int | tuple[int, int], ...] | None = (0xa, 0xd, 0x1b),
                 find_all_bindings: bool = False,
                 find_instance_bindings_only: bool = False, find_class_bindings_first: bool = False,
                 use_alter_bindings: bool = False
                 ):
        InputSuper.__init__(self, thread_smoothness, thread_block, thread_spam, manual_esc_tt, manual_esc_interpreter,
                            manual_esc_finals)
        self.__binder__ = Binder(find_all_bindings, find_instance_bindings_only, find_class_bindings_first,
                                 use_alter_bindings)

    def send(self, block: bool = False) -> bool:
        """
        Read with or without `block`\\ ing and send the object to the binder.

        :return: Whether something was executed
        """
        if block:
            if self.t_spam(self.getch(block=True), self._pipe):
                return self.__binder__.send(self.pipe_get(block=True))
        elif _cr := self.getch(block=False):
            if self.t_spam(_cr, self._pipe):
                return self.__binder__.send(self.pipe_get(block=True))
        return False

    def run(self) -> None:
        """
        Read with or without blocking (``self.t_block``) while ``self.t_keepalive`` is ``True`` and send the
        objects to the binder. Wait ``self.t_smoothness`` seconds in an iteration if ``self.t_block`` is ``False``.

        ``stdin --> adapter --> interpreter --> [ SpamHandler ] --> binder``

        Recognize and supervise manual input of esc.
        """
        try:
            if self.t_block:
                while self.t_keepalive:
                    if self.t_spam(self.getch(block=True), self._pipe):
                        self.__binder__.send(self.pipe_get(block=True))
            elif self.t_smoothness:
                while self.t_keepalive:
                    sleep(self.t_smoothness)
                    if _cr := self.getch(block=False):
                        if self.t_spam(_cr, self._pipe):
                            self.__binder__.send(self.pipe_get(block=True))
            else:
                while self.t_keepalive:
                    if _cr := self.getch(block=False):
                        if self.t_spam(_cr, self._pipe):
                            self.__binder__.send(self.pipe_get(block=True))
        except EOFError:
            self.t_keepalive = False


class InputRouter(Thread):
    """
    This object offers a central handling for several :class:`InputModem` | :class:`InputSuperModem` objects.

    If the thread is started, inputs are processed from the modem defined as ``current_modem`` continuously.
    The method ``send`` is also oriented to the ``current_modem`` and processes one input [ in `block`\\ ing mode ].

    Before any of the actions can be performed, entries must be entered and ``switch_gate`` must be executed a
    first time. Entries can be created during the initialization or afterwards via methods.

        >>> router = InputRouter(main_modem=<InputModem>)
        >>>
        >>> router.setdefault_table_entry(42, <InputSuperModem>)
        >>> router[object] = <InputModem>
        >>>
        >>> router.switch_gate("main_modem")
        >>>
        >>> router.start(daemon=True)

    :param thread_smoothness: specifies the time value for how many seconds to wait in a thread iteration.
    :param thread_block: enables blocked reading of stdin in the thread (thread_smoothness is ignored in this case).
    :param modems: Modem entries in the table.
    """

    _modems: dict[Hashable, InputModem | InputSuperModem]
    current_modem: InputModem | InputSuperModem
    
    t_smoothness: float
    t_block: bool
    t_keepalive: bool

    def __init__(self, thread_smoothness: float | bool = .003, thread_block: bool = False,
                 **modems: InputModem | InputSuperModem):
        self._modems = dict(**modems)
        Thread.__init__(self, daemon=True)
        self.t_smoothness = float(thread_smoothness)
        self.t_block = thread_block
        self.t_keepalive = True
        
    def switch_gate(self, entry: Hashable) -> None:
        """set ``current_modem``"""
        self.current_modem = self._modems[entry]

    def send(self, block: bool = False) -> bool:
        """Process an input from stdin by the ``current_modem`` [ in `block`\\ ing mode ]."""
        if block:
            if self.current_modem.t_spam(self.current_modem.getch(block=True), self.current_modem._pipe):
                return self.current_modem.__binder__.send(self.current_modem.pipe_get(block=True))
        elif _cr := self.current_modem.getch(block=False):
            if self.current_modem.t_spam(_cr, self.current_modem._pipe):
                return self.current_modem.__binder__.send(self.current_modem.pipe_get(block=True))
        return False

    def run(self) -> None:
        """
        Process inputs from stdin [ in blocking mode (``self.t_block``) ] by the modem defined as ``current_modem``
        while ``self.t_keepalive`` is ``True`` . Wait ``self.t_smoothness`` seconds in an iteration if ``self.t_block``
        is ``False``.
        """
        try:
            if self.t_block:
                while self.t_keepalive:
                    if self.current_modem.t_spam(self.current_modem.getch(block=True), self.current_modem._pipe):
                        self.current_modem.__binder__.send(self.current_modem.pipe_get(block=True))
            elif self.t_smoothness:
                while self.t_keepalive:
                    sleep(self.t_smoothness)
                    if _cr := self.current_modem.getch(block=False):
                        if self.current_modem.t_spam(_cr, self.current_modem._pipe):
                            self.current_modem.__binder__.send(self.current_modem.pipe_get(block=True))
            else:
                while self.t_keepalive:
                    if _cr := self.current_modem.getch(block=False):
                        if self.current_modem.t_spam(_cr, self.current_modem._pipe):
                            self.current_modem.__binder__.send(self.current_modem.pipe_get(block=True))
        except EOFError:
            self.t_keepalive = False

    def stop(self) -> None:
        """Stop the thread loop in ``self.run``."""
        self.t_keepalive = False

    def start(self, *, daemon: bool = True) -> None:
        """[Re-]Start the thread."""
        self.t_keepalive = True
        self.daemon = daemon
        super().start()
        
    def pop_table_entry(self, entry: Hashable) -> InputModem | InputSuperModem | None:
        """
        Pop an entry from the table.

        :return: An modem entry or None.
        """
        return self._modems.pop(entry, None)
    
    def setdefault_table_entry(self, entry: Hashable, modem: InputModem | InputSuperModem) -> bool:
        """
        Set default table entry.

        :return: Whether the entry was free and modem was thus set.
        """
        if entry in self._modems:
            return False
        else:
            self._modems[entry] = modem
            return True

    def add_table_entry(self, entry: Hashable, modem: InputModem | InputSuperModem) -> None:
        """
        Add a table entry.

        :raises KeyError(entry): entry is already set
        """
        if entry in self._modems:
            raise KeyError(entry)
        else:
            self._modems[entry] = modem

    def set_table_entry(self, entry: Hashable, modem: InputModem | InputSuperModem) -> None:
        """Set a table entry."""
        self._modems[entry] = modem

    def entries(self) -> Iterable[Hashable]:
        """``Iterable[entry keys]``"""
        return self._modems.keys()
    
    def modems(self) -> Iterable[InputModem | InputSuperModem]:
        """``Iterable[modems]``"""
        return self._modems.values()
    
    def table_items(self) -> Iterable[tuple[Hashable, InputModem | InputSuperModem]]:
        """``Iterable[(entry key, modem)]``"""
        return self._modems.items()

    def __getitem__(self, entry: Hashable) -> InputModem | InputSuperModem:
        """
        ``modem = router[modem entry]``

        :raises KeyError(entry):
        """
        return self._modems.__getitem__(entry)

    def __setitem__(self, entry: Hashable, modem: InputModem | InputSuperModem) -> None:
        """``router[modem entry] = modem``"""
        return self._modems.__setitem__(entry, modem)

    def __delitem__(self, entry: Hashable) -> None:
        """
        ``del router[modem entry]``

        :raises KeyError(entry):
        """
        return self._modems.__delitem__(entry)

    def __contains__(self, entry: Hashable) -> bool:
        """``entry in table``"""
        return entry in self._modems
