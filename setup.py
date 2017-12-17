# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import sys
from distutils.core import setup

import sudb


FAILURE = '\033[1;31m' + 'Install cannot proceed.' + '\033[00m'


if len(sys.argv) > 1 and sys.argv[1] == 'install':
    # Check python version
    if sys.version_info < (3, 4):
        sys.exit(FAILURE + ' Sorry, Python 3.4 or above is required.')


setup(name='sudb',
      description='Sudoku debugger',
      long_description=sudb.__doc__,
      author=sudb.__author__,
      author_email=sudb.__email__,
      license=sudb.__license__,
      packages=['sudb'],
      scripts=['scripts/sudb'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Operating System :: MacOS',
          'Operating System :: POSIX',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Games/Entertainment :: Puzzle Games'
          ]
     )
