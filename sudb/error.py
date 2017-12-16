# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""A class for defining errors and a function for printing error messages.

"""
from __future__ import absolute_import, division, print_function

import sys
import textwrap


class Error(object):
    """An error IDed by an int flag and a string description.

    Parameters
    ----------
    strerror : str
        A string description of the error.

    Attributes
    ----------
    next_errno : int
        A static power-of-two int to be assigned to the next Error
        instance.
    errno : int
        A power-of-two int that identifies this Error instance and can be
        ORed with other error numbers to create an error mask.
    strerror : str
        A string description of this Error instance.

    """
    next_errno = 1

    def __init__(self, strerror):
        self.errno = Error.next_errno
        Error.next_errno <<= 1
        self.strerror = strerror

    def __eq__(self, other):
        return self.errno == other.errno

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return self.errno


def error(message, prelude=None, status=0, maxline=70, minwidth=20):
    """Print wrapped message to stderr and exit with status if nonzero.

    Print to stderr a message wrapped to `maxline`. The first line will be
    preceded by `prelude`, a colon, and a space, and each subsequent line
    will be aligned to the character after that space. If `status` is
    nonzero, the program will afterwards exit with that value.

    Parameters
    ----------
    message : str
        The error message to print.
    prelude : str, optional
        The text to print before a colon and the error message (default
        'error').
    status : int, optional
        The value to call `exit` with if nonzero (default 0).
    maxline : int, optional
        The max number of characters to include in each line of output
        counting the prelude and padding (default 70).
    minwidth : int, optional
        The minimum number of characters that should be reserved for
        `message`; if `prelude` and its padding don't allow for this,
        `message` will begin printing a line below `prelude` (default 20).

    """
    if prelude is None:
        prelude = 'error'
    prelude += ': '

    width = maxline - len(prelude)
    if width < minwidth:
        # `prelude` is too long to use as prefix for each `message` line
        for subline in textwrap.wrap(prelude, maxline):
            print(subline, file=sys.stderr)
        width = maxline
        prelude = ''

    for line in message.split('\n'):
        wrapped_line = textwrap.wrap(line, width)
        if not wrapped_line:
            print(file=sys.stderr)
        for subline in wrapped_line:
            print(prelude, subline, sep='', file=sys.stderr)
            if ':' in prelude:
                # Redefine `prelude` as padding
                prelude = ' ' * len(prelude)

    if status:
        sys.exit(status)
