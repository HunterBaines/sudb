# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

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


def error(message, prelude=None, status=0, maxline=70):
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
    """

    if prelude is None:
        prelude = 'error'

    prelude += ': '
    for line in message.split('\n'):
        wrapped_line = textwrap.wrap(line, maxline - len(prelude))
        if not wrapped_line:
            sys.stderr.write('\n')
        for subline in wrapped_line:
            sys.stderr.write('{}{}\n'.format(prelude, subline))
            if ':' in prelude:
                prelude = ' ' * len(prelude)

    if status:
        sys.exit(status)
