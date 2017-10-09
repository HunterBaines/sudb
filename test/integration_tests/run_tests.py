#!/usr/bin/env python

# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os
import sys
import shutil
import subprocess
import tempfile


# Path to test script relative to this script
TEST_SCRIPT = 'tests.py'
# The file containing the expected output
EXPECTED_OUTFILE = 'expected_output.txt'
# The filename to use for automatically saving output on failure
SAVED_OUTFILE = 'actual_output.txt'


def main():
    dir_of_script = os.path.dirname(os.path.realpath(__file__))
    # So this script can be run from outside of its containing directory
    os.chdir(dir_of_script)

    actual_outfile = tempfile.NamedTemporaryFile()

    retval = subprocess.call(['python', TEST_SCRIPT], stdout=actual_outfile, stderr=actual_outfile)
    if retval != 0:
        test_path = os.path.join(dir_of_script, TEST_SCRIPT)
        sys.stderr.write('ERROR: Attempt to run test script "{}" failed.\n'.format(test_path))
        sys.exit(retval)

    diff_command = 'diff {} {}'.format(EXPECTED_OUTFILE, actual_outfile.name)
    retval = subprocess.call(diff_command.split())
    if retval == 0:
        try:
            # This also relies on the working directory being the same as the script
            subprocess.call(['coverage', 'report'])
            print
        except OSError:
            # `coverage` isn't installed
            pass
        # `diff` returns 0 when the files are the same
        print 'OK'
    elif retval == 1:
        # `diff` returns 1 when the files are different
        saved_outfile_name = os.path.join(tempfile.tempdir, SAVED_OUTFILE)
        shutil.copyfile(actual_outfile.name, saved_outfile_name)
        print 'FAILED: Test output saved to "{}".'.format(saved_outfile_name)
    elif retval == 2:
        # `diff` returns 2 when an error has occurred
        sys.stderr.write('ERROR: Command "{}" failed.\n'.format(diff_command))

    actual_outfile.close()
    sys.exit(retval)


if __name__ == '__main__':
    main()
