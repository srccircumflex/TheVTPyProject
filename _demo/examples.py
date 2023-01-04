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


class OSColorTests:

    from vtframework.iodata.replies import ReplyOSColor

    @staticmethod
    def request_color_slots(print_: bool = True) -> dict[str, str | ReplyOSColor]:

        from vtframework.iodata.requests import RequestOSColor
        from vtframework.iodata.replies import ReplyOSColor
        from vtframework.io import Input
        from vtframework.iosys.vtermios import mod_ansiout, mod_ansiin

        mod_ansiout()
        mod_ansiin()

        color_slot_replies: dict[str, str | ReplyOSColor] = {
            "*env*fore": "",
            "*env*ground": "",
            "|env|cursor": "",
            "black": "",
            "red": "",
            "green": "",
            "yellow": "",
            "blue": "",
            "magenta": "",
            "cyan": "",
            "white": "",
            "#black": "",
            "#red": "",
            "#green": "",
            "#yellow": "",
            "#blue": "",
            "#magenta": "",
            "#cyan": "",
            "#white": "",
        }
        with Input() as input_:

            for slot in color_slot_replies:
                if slot[0] == "*":
                    RequestOSColor.environment(fore=slot.endswith("fore")).out()
                elif slot[0] == "|":
                    RequestOSColor.cursor().out()
                elif slot[0] == "#":
                    RequestOSColor.rel(slot[1:], bright_version=True).out()
                else:
                    RequestOSColor.rel(slot).out()
                color_slot_replies[slot] = input_.read(block=False, smoothness=.04, flush_io=True)

        if print_:
            for i in color_slot_replies.items():
                print("%-16s%r" % i)

        return color_slot_replies

    @staticmethod
    def set_color_slots_by_replies(origins: dict[str, str | ReplyOSColor]) -> None:

        from vtframework.iodata.os import OSColorControl
        from vtframework.iosys.vtermios import mod_ansiout, mod_ansiin

        mod_ansiout()
        mod_ansiin()

        for slot in origins:
            if color := origins[slot]:
                if slot[0] == "*":
                    if slot.endswith("fore"):
                        OSColorControl.set_environment_color(fore=(color['r'], color['g'], color['b'])).out()
                    else:
                        OSColorControl.set_environment_color(back=(color['r'], color['g'], color['b'])).out()
                elif slot[0] == "|":
                    OSColorControl.set_cursor_color((color['r'], color['g'], color['b'])).out()
                else:
                    OSColorControl.set_rel_color(slot, (color['r'], color['g'], color['b'])).out()

    @staticmethod
    def sgr_hypnotising(iterations: int = 3, frame_timeout: float = .01,
                        colors: tuple | list = (
                            "MediumSpringGreen",
                            "#CCFF00",
                            (12, 234, 22),
                            "DeepPink1",
                            "LightGoldenrodYellow",
                            (12, 234, 22),
                            "MediumOrchid",
                            "#0035FF",
                            "#FF2900",
                            (12, 234, 22),
                        )
                        ):

        from time import sleep
        import atexit
        from random import shuffle, randint

        from vtframework.iodata.decpm import ScreenAlternateBuffer
        from vtframework.iodata.cursor import CursorNavigate, CursorStyle
        from vtframework.iodata.os import OSColorControl, WindowManipulation
        from vtframework.iosys.vtermios import mod_ansiout, mod_ansiin
        from _demo.sgr_lookup_tui import SGRLookUp

        mod_ansiout()
        mod_ansiin()

        colors = list(colors)
        shuffle(colors)
        colors_max_index = len(colors) - 1


        def change_colors():
            _ = OSColorControl.set_environment_color(
                fore=colors[randint(0, colors_max_index)],
                back=colors[randint(0, colors_max_index)]
            ).out()
            for slot in (
                    "black",
                    "red",
                    "green",
                    "yellow",
                    "blue",
                    "magenta",
                    "cyan",
                    "white"
            ):
                _ = OSColorControl.set_rel_color(slot, colors[randint(0, colors_max_index)]).out()
            sleep(frame_timeout)

        def main_loop(iterations):
            for cur_col in colors[:iterations]:
                _ = OSColorControl.set_cursor_color(cur_col).out()
                CursorNavigate.position(13, 4).out()
                for i in range(1, 9):
                    change_colors()
                    if i % 2:
                        for _ in range(i * 2):
                            _ = CursorNavigate.forward().out()
                            change_colors()
                        for _ in range(i):
                            _ = CursorNavigate.down().out()
                            change_colors()
                    else:
                        for _ in range(i * 2):
                            _ = CursorNavigate.back().out()
                            change_colors()
                        for _ in range(i):
                            _ = CursorNavigate.up().out()
                            change_colors()

        try:
            alt_buffer = ScreenAlternateBuffer()
            alt_buffer.highout()
            _ = CursorStyle.steady_block().out()
            _ = atexit.register(lambda *_: CursorStyle.blinking_block().out())
            _ = CursorNavigate.position().out()
            for rcs in SGRLookUp.lookup_rel():
                print(rcs)
            sleep(2)
            _ = WindowManipulation.resize(30, 10).out()
            main_loop(iterations)
        finally:
            _ = OSColorControl.reset_cursor_color().out()
            _ = OSColorControl.reset_environment_color().out()
            _ = OSColorControl.reset_rel_color().out()
            _ = CursorNavigate.position(0, 9).out()
            sleep(.2)
            _ = WindowManipulation.resize(80, 24).out()
            sleep(2)
            alt_buffer.lowout()


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
    from sys import argv
    if code := str().join(a + ' ' for a in argv[1:]):
        exec(code[:-1])
    #echo_routing()
    #test_oscolor()
    #visual_interpreters()

