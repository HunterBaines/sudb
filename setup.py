# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import sys
from distutils.core import setup

import sudb


FAILURE = '\033[1;31m' + 'Install cannot proceed.' + '\033[00m'


if len(sys.argv) > 1 and sys.argv[1] == 'install':
    # Check python version
    if sys.version_info.major != 2:
        sys.exit(FAILURE + ' Sorry, only Python 2 is supported.')

    # Check if enum module is installed
    try:
        from enum import IntEnum, unique
    except ImportError:
        sys.exit(FAILURE + ' The package "enum34", the backport\n'\
                 + 'of Enum from Python 3.4, is required. Please install it:\n'\
                 + '\n'\
                 + "# via your system's package manager, e.g.:\n"\
                 + '$ sudo apt install python-enum34\n'\
                 + '\n'\
                 + "# or via Python's package manager:\n"\
                 + '$ sudo pip install enum34\n')


setup(name='sudb',
      author=sudb.__author__,
      author_email=sudb.__email__,
      license=sudb.__license__,
      packages=['sudb'],
      scripts=['scripts/sudb'],
      requires=['enum']
     )
