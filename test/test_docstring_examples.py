# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os
import sys
from cStringIO import StringIO
import unittest
import doctest


class TestDocstringExamples(unittest.TestCase):
    """Test code given under 'Examples' header in docstrings.

    """

    # Again, this all expects to be run from the project root
    PATH_TO_PYTHON_FILES = 'sudb/'


    def test_docstring_examples(self):
        for directory, _, filenames in os.walk(self.PATH_TO_PYTHON_FILES):
            python_files = [f for f in filenames if f.endswith('.py')]
            for pyfile in python_files:
                path = os.path.join(directory, pyfile)

                doctest_out = StringIO()
                self.redirect_output(doctest_out)
                result = doctest.testfile(path, module_relative=False)
                self.reset_output()

                # Test if doctest on file failed
                assertion_msg = 'doctest on "{}" failed:\n'.format(pyfile)
                assertion_msg += doctest_out.getvalue()
                self.assertEqual(result.failed, 0, assertion_msg)


    def redirect_output(self, custom_out):
        sys.stdout = custom_out
        sys.stderr = custom_out

    def reset_output(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
