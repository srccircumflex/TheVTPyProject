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

from vtframework.io.io import InputSuper, StdinAdapter
from vtframework.iosys.vtermios import mod_ansiin, mod_ansiout

from vtframework.iodata.decpm import DECPModeIds, DECPrivateMode
from vtframework.iodata.requests import RequestOSColor
from vtframework.iodata.chars import Char
from vtframework.iodata.keys import EscEsc
from vtframework.iodata.esccontainer import EscSegment

from vtframework.io.io import out
from vtframework.io.modem import InputSuperModem, InputModem


def echo():

    mod_ansiin()
    mod_ansiout()
    #mod_nonprocess()

    # out(DECPrivateMode.high(DECPModeIds.SaveCursorAlternateScreenBuffer))
    out(DECPrivateMode.high(DECPModeIds.BracketedPasteMode))
    DECPrivateMode.high(1003).out()

    StdinAdapter().modblock.add_before_reset_atexit(lambda: DECPrivateMode.low(1003).out())
    #with ModemSuper(thread_block=True, manual_esc_tt=100, manual_esc_finals=()) as cr:
    cr = InputSuperModem(thread_block=True, manual_esc_tt=1, manual_esc_interpreter=True)

    cr.__interpreter__.SPACE_TARGETS.set(cr.__interpreter__.SPACE_TARGETS.ANY)

    cr.__interpreter__.bind_esc(lambda: print("\nESC   :: MAIN"))
    cr.__interpreter__.bind_intro(lambda c: print("%-4s  :: MAIN" % repr(c)[2:-1]))

    cr.__interpreter__.bind_to_interpreter("any", "p", lambda i, c: print("%-4s  :: ╚%s" % (repr(c)[2:-1], i.__class__.__name__)))
    cr.__interpreter__.bind_to_interpreter("any", "f", lambda i, c: print("%-4s  :: ╚%s\n" % (repr(c)[2:-1], i.__class__.__name__)))

    cr.__binder__.bind(EscSegment('\x1b'), lambda o, r: (DECPrivateMode.low(1003).out(), exit()), "a")
    cr.__binder__.bind(EscEsc(), lambda o, r: (DECPrivateMode.low(1003).out(), exit()), "a")
    cr.__binder__.bind(Char('a'), lambda o, r: RequestOSColor.environment().out(), "a")
    cr.__binder__.bind(object, lambda o, r: print("----> " + repr(o)), "a")

    cr.start(daemon=False)


if __name__ == "__main__":
    echo()
