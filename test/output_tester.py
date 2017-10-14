import os
import sys
import tempfile
import unittest


class OutputTester(unittest.TestCase):
    """A generic class for unit tests that require comparing output.

    """

    # Must be implemented by subclass
    EXPECTED_OUTPUT_FILE = None

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.EXPECTED_OUTPUT_FILE):
            cls.compare_file = open(cls.EXPECTED_OUTPUT_FILE, 'r')
            cls.output_file = tempfile.NamedTemporaryFile()
        else:
            cls.compare_file = None
            cls.output_file = open(cls.EXPECTED_OUTPUT_FILE, 'w')

    @classmethod
    def tearDownClass(cls):
        if cls.compare_file is None:
            print
            print 'Output written to {}.'.format(cls.EXPECTED_OUTPUT_FILE)
            print 'Future tests will compare actual output to this file.'
        else:
            cls.compare_file.close()
        cls.output_file.close()

    def redirect_output(self):
        sys.stdout = self.output_file
        sys.stderr = self.output_file

    def reset_output(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
