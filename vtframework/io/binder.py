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
from typing import Callable, Literal, Type, Any
from functools import lru_cache

from vtframework.iodata.keys import Key
from vtframework.iodata.mouse import Mouse
from vtframework.iodata.replies import Reply
from vtframework.iodata.chars import Char
from vtframework.iodata.esccontainer import EscSegment


class BindItem:
    """
    An item for handling a bound function.
    This can be used to unbind or rebind the function.
    It also contains a reference to the :class:`Binding`.
    """

    __binding__: Binding
    func: Callable[[Key | Mouse | Reply | Char | EscSegment, Any], Any]
    id: int

    __slots__ = ('__binding__', 'func', 'id')
    
    def __init__(self,
                 __binding__: Binding,
                 __f: Callable[[Key | Mouse | Reply | Char | EscSegment, Any], Any],
                 _id: int):
        self.__binding__ = __binding__
        self.func = __f
        self.id = _id

    def unbind(self) -> None:
        """Unbind the function."""
        self.__binding__.bindings.pop(self.id)
        self.__binding__.call_order.remove(self.id)

    def rebind(self, mode: Literal["a", "i", "r", "x"] = "x", _index: int = 0) -> None:
        """
        Rebind the execution of `__f` to the :class:`Binding`; in `mode`:
            - ``"a"`` (append):
                Append func to the execution order.
            - ``"i"`` (insert):
                Insert func into the `_index` location in the execution order.
            - ``"r"`` (replace):
                Place func in the `_index` location in the execution order.
            - ``"x"`` (exclusive)
                Assign func exclusive, except of the protected bindings.
        """
        self.id = self.__binding__.bind(self.func, mode, _index).id

    def index(self) -> int:
        """:return: the position in the execution order."""
        return self.__binding__.call_order.index(self.id)

    def purge_binding(self) -> None:
        """Initialize the binding. (ALL bound functions are removed from the binding, except the protected)."""
        self.__binding__.init_binding()


class BindChainItem(tuple[BindItem]):
    """A container and manager for multiple :class:`BindItem`'s. Returned by :class:`Binder`.bindchain()."""
    
    def unbind(self) -> None:
        """Unbind all functions in the chain."""
        for itm in self:
            itm.unbind()

    def rebind(self, mode: Literal["a", "i", "r", "x"] = "x", _index: int = 0) -> None:
        """
        Rebind the execution of the functions in the chain to the :class:`Binding`; in `mode`:
            - ``"a"`` (append):
                Append the chain to the execution order.
            - ``"i"`` (insert):
                Insert the chain into the `_index` location in the execution order.
            - ``"r"`` (replace):
                Start at the `_index` location to insert the functions in the chain into the execution order.
            - ``"x"`` (exclusive)
                Assign the function chain exclusive, except of the protected bindings.
        """
        def _modes():
            future_mode = ("a" if mode == "x" else mode)
            yield mode
            while True:
                yield future_mode

        for itm, mode, i in zip(self, _modes(), range(_index, _index + len(self))):
            itm.rebind(mode, i)

    def range(self) -> tuple[int, int]:
        """:return: the position range of the chain in the execution order."""
        return self[0].index(), self[-1].index()

    def purge_binding(self) -> None:
        """Initialize the binding. (ALL bound functions are removed from the binding, except the protected)."""
        self[0].purge_binding()


class Binding:
    """
    A manager for functions bound to `class_or_instance`.
    Consists of two memories for functions, one for dynamic operations (functions can be unbound and rebound via
    the :class:`BindItem` (returned on binding), or assigned exclusively) and a protected one which is independent
    of the dynamic one and can only be extended or initiated. The functions of the protected memory are executed
    before the functions in the dynamic cache when called.
    """
    
    reference: type | object
    bindings: dict[int, Callable[[Key | Mouse | Reply | Char | EscSegment, Any], Any]]
    call_order: list[int]
    pb: tuple[Callable[[Key | Mouse | Reply | Char | EscSegment, Any], Any]] | tuple
    
    _bind_id: int
    _hash: int

    __slots__ = ('bindings', 'pb', 'call_order', '_bind_id', 'reference', 'comp', '_hash')

    def __init__(
            self,
            class_or_instance: Type[Key | Mouse | Reply | Char | EscSegment] | Key | Mouse | Reply | Char | EscSegment
    ):
        self.init_binding()
        self.init_protected()
        self.reference = class_or_instance
        if type(class_or_instance) == type:
            def comp(other): return isinstance(other, self.reference)
        else:
            def comp(other): return self.reference == other
        self.comp = comp
        self._hash = hash(class_or_instance)

    def init_binding(self) -> None:
        """Initializes the Binding."""
        self.bindings = {}
        self.call_order = []
        self._bind_id = 0

    def init_protected(self) -> None:
        """Initialize the memory for protected bindings."""
        self.pb = ()

    def __call__(self, other: Key | Mouse | Reply | Char | EscSegment, prev_rval: Any, *, _comp: bool = True
                 ) -> tuple[bool, Any]:
        """
        Compare `other` with the reference item of the binding if `_comp` is True,
        then execute the bound functions if the comparison is positive.

        :return: Comparison result, function return value.
        """
        if _comp and not self.comp(other):
            return False, prev_rval
        for pb in self.pb:
            prev_rval = pb(other, prev_rval)
        for _bind_id in self.call_order:
            prev_rval = self.bindings[_bind_id](other, prev_rval)
        return True, prev_rval

    def bind(
            self,
            __f: Callable[[Key | Mouse | Reply | Char | EscSegment, Any], Any],
            mode: Literal["a", "i", "r", "x", "~a", "~i", "~r"] = "x",
            _index: int = 0
    ) -> BindItem | None:
        """
        Bind the execution of `__f` to the :class:`Binding`/:class:`BindingT`, in `mode`:
            - ``"a"`` (append):
                Append func to the execution order.
            - ``"i"`` (insert):
                Insert func into the `_index` location in the execution order.
            - ``"r"`` (replace):
                Place func in the `_index` location in the execution order.
            - ``"x"`` (exclusive)
                Assign func exclusive, except of the protected bindings.
            - ``"~a"`` (append to the protected bindings)
            - ``"~i"`` (insert into the protected bindings)
            - ``"~r"`` (replace a protected binding)

        returns:
            - :class:`BindItem` or
            - ``None`` in ``"~"`` mode or if the alternate Bindings are in use.
        """
        if mode == "a":
            self.bindings[self._bind_id] = __f
            self.call_order.append(self._bind_id)
            item = BindItem(self, __f, self._bind_id)
            self._bind_id += 1
        elif mode == "i":
            self.bindings[self._bind_id] = __f
            self.call_order.insert(_index, self._bind_id)
            item = BindItem(self, __f, self._bind_id)
            self._bind_id += 1
        elif mode == "r":
            self.bindings[self.call_order[_index]] = __f
            item = BindItem(self, __f, self._bind_id)
        elif mode == "x":
            self.bindings = {self._bind_id: __f}
            self.call_order = [self._bind_id]
            item = BindItem(self, __f, self._bind_id)
            self._bind_id += 1
        elif mode == "~a":
            self.pb += (__f,)
            item = None
        elif mode == "~i":
            self.pb = self.pb[:_index] + (__f,) + self.pb[_index:]
            item = None
        elif mode == "~r":
            self.pb = self.pb[:_index] + (__f,) + self.pb[_index + 1:]
            item = None
        else:
            raise ValueError(mode)
        return item

    def __eq__(self, other: Binding):
        return self._hash == other._hash

    def __len__(self):
        """Number of bound functions, excl. protected."""
        return len(self.bindings)


class BindingT(Binding):
    """
    A more resource efficient version of :class:`Binding`.
    Replaces the handling of bound functions with a dictionary and order-list with a tuple.
    At the cost of dynamic; bindings generally do not return :class:`BindItem`.
    """
    
    bindings: tuple[Callable[[Key | Mouse | Reply | Char | EscSegment, Any], Any]] | tuple
    call_order = None
    _bind_id = None

    def __init__(
            self,
            class_or_instance: Type[Key | Mouse | Reply | Char | EscSegment] | Key | Mouse | Reply | Char | EscSegment
    ):
        Binding.__init__(self, class_or_instance)

    def init_binding(self) -> None:
        self.bindings = ()

    def __call__(self, other: Key | Mouse | Reply | Char | EscSegment, prev_rval: Any, *, _comp: bool = True
                 ) -> tuple[bool, Any]:
        if _comp and not self.comp(other):
            return False, prev_rval
        for pb in self.pb:
            prev_rval = pb(other, prev_rval)
        for b in self.bindings:
            prev_rval = b(other, prev_rval)
        return True, prev_rval

    def bind(
            self,
            __f: Callable[[Key | Mouse | Reply | Char | EscSegment, Any], Any],
            mode: Literal["a", "i", "r", "x", "~a", "~i", "~r"] = "x",
            _index: int = 0
    ) -> None:
        if mode == "a":
            self.bindings += (__f,)
        elif mode == "i":
            self.bindings = self.bindings[:_index] + (__f,) + self.bindings[_index:]
        elif mode == "r":
            self.bindings = self.bindings[:_index] + (__f,) + self.bindings[_index + 1:]
        elif mode == "x":
            self.bindings = (__f,)
        elif mode == "~a":
            self.pb += (__f,)
        elif mode == "~i":
            self.pb = self.pb[:_index] + (__f,) + self.pb[_index:]
        elif mode == "~r":
            self.pb = self.pb[:_index] + (__f,) + self.pb[_index + 1:]
        else:
            raise ValueError(mode)


class Binder:
    """
    A manager to bind functions to reference objects and types.
    Consists of two caches, one for bindings to instances and one for bindings to types.

    If `alter_bindings` is ``True``, Binder uses the alternative memory-saving version :class:`BindingT` instead of
    :class:`Binding`; in this mode no :class:`BindItem`'s are returned when binding, these are for the unbinding
    and rebinding of a function.

    If a :class:`Binding` to a reference already exists, it is extended.
    When executing the functions found then, the following one always receives the applicable input and the
    return value of the previously executed function; for the function that is executed first, this is always
    the input and ``None``.

    The bindings are kept in tuples, so they are ordered and are queried one after the other when searching.
    By default, the search process in a cache type is stopped at the first match.

    :param find_all_matches: Search for all bindings, instead of breaking at first match.
    :param find_instance_match_only: Do not also search in the class cache when instance matches have been encountered.
    :param find_class_match_first: Order type match[es] first when type and instance match[es] occur.
    :param alter_bindings: Use the alternative resource-saving version of `Binding` (`BindingT`);
     at the expense of dynamics (no `BindItem` is returned when binding)
    """

    instancecache: dict[int, tuple[Binding]]
    classcache: tuple[Binding] | tuple
    _get_match_: Callable[[Key | Mouse | Reply | Char | EscSegment], tuple[list[Binding], list[Binding]] | tuple[list[Binding]] | None]
    _Binding: Type[Binding]

    __slots__ = ('instancecache', 'classcache', '_get_match_', '_Binding')
    
    def __init__(self,
                 find_all_matches: bool = False,
                 find_instance_match_only: bool = False, find_class_match_first: bool = False,
                 alter_bindings: bool = False):
        self.init_binder()

        if find_all_matches:
            if find_instance_match_only:
                def get_m(_in) -> tuple:
                    if bindings := self.instancecache.get(_in.__vtdtid__):
                        if inst_m := [b for b in bindings if b.comp(_in)]:
                            return inst_m,
                    if cls_m := [b for b in self.classcache if b.comp(_in)]:
                        return cls_m,
            elif find_class_match_first:
                def get_m(_in) -> tuple:
                    if bindings := self.instancecache.get(_in.__vtdtid__):
                        if cls_m := [b for b in self.classcache if b.comp(_in)]:
                            if inst_m := [b for b in bindings if b.comp(_in)]:
                                return cls_m, inst_m
                            return cls_m,
                        elif inst_m := [b for b in bindings if b.comp(_in)]:
                            return inst_m,
                    elif cls_m := [b for b in self.classcache if b.comp(_in)]:
                        return cls_m,
            else:
                def get_m(_in) -> tuple:
                    if bindings := self.instancecache.get(_in.__vtdtid__):
                        if cls_m := [b for b in self.classcache if b.comp(_in)]:
                            if inst_m := [b for b in bindings if b.comp(_in)]:
                                return inst_m, cls_m
                            return cls_m,
                        elif inst_m := [b for b in bindings if b.comp(_in)]:
                            return inst_m,
                    elif cls_m := [b for b in self.classcache if b.comp(_in)]:
                        return cls_m,
        else:
            if find_instance_match_only:
                def get_m(_in) -> tuple:
                    if bindings := self.instancecache.get(_in.__vtdtid__):
                        for b in bindings:
                            if b.comp(_in):
                                return [b],
                    for b in self.classcache:
                        if b.comp(_in):
                            return [b],
            elif find_class_match_first:
                def get_m(_in) -> tuple:
                    if bindings := self.instancecache.get(_in.__vtdtid__):
                        for b in bindings:
                            if b.comp(_in):
                                for cb in self.classcache:
                                    if cb.comp(_in):
                                        return [cb], [b]
                                return [b],
                    for b in self.classcache:
                        if b.comp(_in):
                            return [b],
            else:
                def get_m(_in) -> tuple:
                    if bindings := self.instancecache.get(_in.__vtdtid__):
                        for b in bindings:
                            if b.comp(_in):
                                for cb in self.classcache:
                                    if cb.comp(_in):
                                        return [b], [cb]
                                return [b],
                    for b in self.classcache:
                        if b.comp(_in):
                            return [b],

        self._get_match_ = get_m

        if alter_bindings:
            self._Binding = BindingT
        else:
            self._Binding = Binding

    def init_binder(self) -> None:
        """Initializes the Binder."""
        self.instancecache = {}
        self.classcache = ()
        self.get_match.cache_clear()

    @lru_cache(20)
    def get_match(self, item: Key | Mouse | Reply | Char | EscSegment
                  ) -> tuple[list[Binding], list[Binding]] | tuple[list[Binding]] | None:
        """Return the bindings for `item` or None.
        Positive result can be a one-tuple or double-tuple;
        the order of the double-tuple depends on the parameter `find_class_match_first`."""
        return self._get_match_(item)
        
    def __call__(self, __input: Key | Mouse | Reply | Char | EscSegment) -> bool:
        """The gate for the execution of the functions bound to `__input`.
        For optimization, it uses `get_match` with the lru_cache(20) to get the bound functions.
        Returns whether something was executed."""
        if match := self.get_match(__input):
            rval = None
            for m in match:
                for b in m:
                    rval = b.__call__(__input, rval, _comp=False)[1]
            return True
        return False

    def send(self, __input: Key | Mouse | Reply | Char | EscSegment) -> bool:
        """The gate for the execution of the functions bound to `__input`.
        For optimization, it uses `get_match` with the lru_cache(20) to get the bound functions.
        Returns whether something was executed."""
        return self.__call__(__input)

    def bind(
            self,
            class_or_instance: Type[Key | Mouse | Reply | Char | EscSegment] | Key | Mouse | Reply | Char | EscSegment,
            func: Callable[[Any, Any], Any],
            mode: Literal["a", "i", "r", "x", "~a", "~i", "~r"] = "x",
            _index: int = 0
    ) -> BindItem | None:
        """
        Bind the execution of `func` to the :class:`Binding`/:class:`BindingT`, in `mode`:
            - ``"a"`` (append):
                Append func to the execution order.
            - ``"i"`` (insert):
                Insert func into the `_index` location in the execution order.
            - ``"r"`` (replace):
                Place func in the `_index` location in the execution order.
            - ``"x"`` (exclusive)
                Assign func exclusive, except of the protected bindings.
            - ``"~a"`` (append to the protected bindings)
            - ``"~i"`` (insert into the protected bindings)
            - ``"~r"`` (replace a protected binding)

        `func` gets the applicable object and the return value of a previously executed function in the binding.

        returns:
            - :class:`BindItem` or
            - ``None`` in ``"~"`` mode or if the alternate Bindings are in use.
        """
        if type(class_or_instance) == type:
            if not (binding := self.get_binding(class_or_instance)):
                self.classcache += (binding := self._Binding(class_or_instance),)
                self.get_match.cache_clear()
        else:
            self.instancecache.setdefault(class_or_instance.__vtdtid__, tuple())
            if not (binding := self.get_binding(class_or_instance)):
                self.instancecache[class_or_instance.__vtdtid__] += (binding := self._Binding(class_or_instance),)
                self.get_match.cache_clear()
        return binding.bind(func, mode, _index)

    def bindchain(
            self,
            class_or_instance: Type[Key | Mouse | Reply | Char | EscSegment] | Key | Mouse | Reply | Char | EscSegment,
            *funcs: Callable[[Any, Any], Any],
            mode: Literal["a", "i", "r", "x", "~a", "~i", "~r"] = "x",
            _index: int = 0
    ) -> BindChainItem | None:
        """
        Bind the execution of the chain `funcs` to the :class:`Binding`/:class:`BindingT`, in `mode`:
            - ``"a"`` (append):
                Append the chain to the execution order.
            - ``"i"`` (insert):
                Insert the chain into the `_index` location in the execution order.
            - ``"r"`` (replace):
                Start at the `_index` location to insert the functions in the chain into the execution order.
            - ``"x"`` (exclusive)
                Assign the function chain exclusive, except of the protected bindings.
            - ``"~a"`` (append to the protected bindings)
            - ``"~i"`` (insert into the protected bindings)
            - ``"~r"`` (replace protected bindings)

        Each `func` in `funcs` gets the applicable object and the return value of a previously executed function in the
        binding.

        returns:
            - :class:`BindChainItem` or
            - ``None`` in ``"~"`` mode or if the alternate Bindings are in use. 
        """
        if type(class_or_instance) == type:
            if not (binding := self.get_binding(class_or_instance)):
                self.classcache += (binding := self._Binding(class_or_instance),)
                self.get_match.cache_clear()
        else:
            self.instancecache.setdefault(class_or_instance.__vtdtid__, tuple())
            if not (binding := self.get_binding(class_or_instance)):
                self.instancecache[class_or_instance.__vtdtid__] += (binding := self._Binding(class_or_instance),)
                self.get_match.cache_clear()

        def _modes():
            future_mode = ("a" if mode == "x" else mode)
            yield mode
            while True:
                yield future_mode

        if (chain := BindChainItem(
                binding.bind(func, mode, i) for func, mode, i in zip(funcs, _modes(), range(_index, _index + len(funcs)))
                ))[0]:
            return chain

    def get_binding(
            self,
            class_or_instance: Type[Key | Mouse | Reply | Char | EscSegment] | Key | Mouse | Reply | Char | EscSegment
    ) -> Binding | None:
        """:return: Binding to `class_or_instance` or None."""
        h = hash(class_or_instance)
        if type(class_or_instance) == type:
            for b in self.classcache:
                if b._hash == h:
                    return b
        else:
            for b in self.instancecache[class_or_instance.__vtdtid__]:
                if b._hash == h:
                    return b

    def __getitem__(
            self,
            class_or_instance: Type[Key | Mouse | Reply | Char | EscSegment] | Key | Mouse | Reply | Char | EscSegment
    ) -> Binding:
        """
        :return: Binding to `class_or_instance`
        :raise KeyError: If `class_or_instance` does not match.
        """
        if not (b := self.get_binding(class_or_instance)):
            raise KeyError(class_or_instance)
        return b
