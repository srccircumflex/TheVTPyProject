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

import sys
from re import sub

try:
    sys.path.append(sub("[/\\\\]_demo[/\\\\][^/\\\\]+$", "", __file__))
finally:
    pass


def echo_routing():

    from vtframework.io import StdinAdapter, InputSuperModem, InputRouter
    from vtframework.iodata import ManualESC
    from vtframework.iosys.vtermios import mod_ansiin
    from vtframework.iodata.keys import NavKey

    mod_ansiin()

    StdinAdapter()

    router = InputRouter(thread_block=True, **{
        k: InputSuperModem(
            manual_esc_tt=0,
            find_class_bindings_first=True,
            use_alter_bindings=True
        ) for k in "udrl"
    })

    entry_label = "( l )"

    def switch(entry):
        nonlocal entry_label
        entry_label = "( %s )" % entry
        router.switch_gate(entry)

    for modem in router.modems():

        modem.__binder__.bind(object, lambda o, r: print(repr(o), entry_label))
        modem.__binder__.bind(NavKey(NavKey.K.A_UP), lambda o, r: switch("u"))
        modem.__binder__.bind(NavKey(NavKey.K.A_DOWN), lambda o, r: switch("d"))
        modem.__binder__.bind(NavKey(NavKey.K.A_LEFT), lambda o, r: switch("l"))
        modem.__binder__.bind(NavKey(NavKey.K.A_RIGHT), lambda o, r: switch("r"))

        modem.__binder__.bind(ManualESC(''), lambda o, r: exit(0))

    router.switch_gate("l")

    router.start(daemon=False)


def test_oscolor_request():

    from vtframework.iodata import RequestOSColor
    from vtframework.io import Input
    from vtframework.iosys.vtermios import mod_ansiout

    mod_ansiout()

    with Input() as input_:

        RequestOSColor.rel("red").out()

        reply = input_.read(block=False, smoothness=.02, flush_io=True)

    print(repr(reply))

    return bool(reply)


def visual_interpreters():

    from vtframework.io import InputSuper, StdinAdapter
    from vtframework.iosys.vtermios import mod_ansiin
    from vtframework.iodata import EscEsc

    import sys

    mod_ansiin()

    StdinAdapter()
    sys.stdin: StdinAdapter

    print(f"{repr(sys.stdin)=}")

    input_ = InputSuper(thread_block=True, manual_esc_tt=3, manual_esc_interpreter=True, manual_esc_finals=(0x1b,))

    input_.__interpreter__.SPACE_TARGETS.set(input_.__interpreter__.SPACE_TARGETS.ANY)
    input_.__interpreter__.bind_esc(lambda: print("\nESC   :: MAIN"))
    input_.__interpreter__.bind_intro(lambda c: print("%-4s  :: MAIN" % repr(c)[2:-1]))
    input_.__interpreter__.bind_to_interpreter("any", "p", lambda i, c: print("%-4s  :: ╚%s" % (repr(c)[2:-1], i.__class__.__name__)))
    input_.__interpreter__.bind_to_interpreter("any", "f", lambda i, c: print("%-4s  :: ╚%s\n" % (repr(c)[2:-1], i.__class__.__name__)))

    with input_:

        try:
            while True:

                in_ = input_.getch(block=True)

                print("----> " + repr(in_))

                if in_ in (EscEsc(), "\x1b"):
                    sys.stdin.stop()
                    print("\n\nPress any key > ", end="")

        except EOFError:
            pass

    print(f"{repr(sys.stdin)=}")


if __name__ == "__main__":
    pass
    #echo_routing()
    #test_oscolor_request()
    #visual_interpreters()

