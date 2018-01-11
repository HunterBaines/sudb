# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os
import sys
import subprocess

from test.output_tester import OutputTester


class MainTester(OutputTester):
    """Test output of various invocations of sudb.__main__.

    """
    EXPECTED_OUTPUT_FILE = None
    PUZZLE_PATH = 'test/data'
    PUZZLE_URL = 'https://raw.githubusercontent.com/HunterBaines/sudb/master/test/data'

    @classmethod
    def setUpClass(cls):
        super(MainTester, cls).setUpClass()
        cls.maxDiff = None

        cls.interpreter = 'python{} -m '.format(sys.version_info.major)
        try:
            # Try to detect if being run via `coverage` (assumes a shell
            # that sets `_` to the path of the currently running
            # executable); note `sys.version`, `sys.argv[0]`, and
            # `sys.executable` don't seem to work for this purpose
            if 'SUDB_COVERAGE' in os.environ or os.environ['_'].endswith('coverage'):
                cls.interpreter = 'coverage run -a -m '
        except KeyError:
            pass

        # `--no-init` so testing not influenced by contents of tester's
        # "~/sudbinit"
        cls.program = cls.interpreter + 'sudb --no-init'

    def run_command(self, command):
        # Trim interpreter from command so changing the interpreter doesn't
        # influence the test output and, therefore, its result
        relevant_command = command.replace(self.interpreter, '')
        sys.stdout.write('$ {}\n'.format(relevant_command))
        # Otherwise this can end up being printed *after* output from
        # the command given to `subprocess`
        sys.stdout.flush()
        retval = subprocess.call(command, shell=True, stdout=sys.stdout, stderr=sys.stderr)
        return retval
