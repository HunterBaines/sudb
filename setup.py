# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

from distutils.core import setup

import sudb


setup(name='sudb',
      author=sudb.__author__,
      author_email=sudb.__email__,
      license=sudb.__license__,
      packages=['sudb'],
      scripts=['scripts/sudb']
     )
