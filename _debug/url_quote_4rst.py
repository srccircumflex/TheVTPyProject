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


from re import search, sub, Pattern


def quote(s: str):
    return s.replace(
        '%', '%25'
    ).replace(
        ' ', '%20'
    ).replace(
        '!', '%21'
    ).replace(
        '#', '%23'
    ).replace(
        '$', '%24'
    ).replace(
        '&', '%26'
    ).replace(
        "'", '%27'
    ).replace(
        '(', '%28'
    ).replace(
        ')', '%29'
    ).replace(
        '*', '%2A'
    ).replace(
        '+', '%2B'
    ).replace(
        ',', '%2C'
    ).replace(
        '/', '%2F'
    ).replace(
        ':', '%3A'
    ).replace(
        ';', '%3B'
    ).replace(
        '=', '%3D'
    ).replace(
        '?', '%3F'
    ).replace(
        '@', '%40'
    ).replace(
        '[', '%5B'
    ).replace(
        ']', '%5D'
    ).replace(
        '<', '%3C'
    ).replace(
        '>', '%3E'
    ).replace(
        '\\', '%5C'
    ).replace(
        '^', '%5E'
    ).replace(
        '_', '%5F'
    ).replace(
        '`', '%60'
    ).replace(
        '{', '%7B'
    ).replace(
        '|', '%7C'
    ).replace(
        '}', '%7D'
    ).replace(
        '~', '%7E'
    )


def quote_cli_loop():
    try:
        while True:
            print(quote(input('>').strip()))
    except KeyboardInterrupt:
        exit()


def quote_file(file: str, regex: Pattern):
    with open(file) as _if, open(file + '.out', "w") as _of:
        while line := _if.readline():
            if m := search(regex, line):
                _of.write(sub(regex, quote(m.group()), line))
            else:
                _of.write(line)
