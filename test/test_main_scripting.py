# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os

from test.main_tester import MainTester


class TestMainScripting(MainTester):
    """Test output for `sudb.__main__` uses related to scripting.

    """
    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/main_scripting.out')


    def test_main_scripting(self):
        commands = []

        normal_puzzle = os.path.join(self.PUZZLE_PATH, 'normal_puzzle.txt')
        simple_script = os.path.join(self.PUZZLE_PATH, 'simple_script.txt')
        puzzle_with_script = os.path.join(self.PUZZLE_PATH, 'integrated_puzzle_and_script.txt')

        # Test running commands (redirect from /dev/null to give it EOF and
        # thereby cause it to quit without confirmation)
        command = '{} --file {} --execute "source {}" < /dev/null'.format(self.program,
                                                                          normal_puzzle,
                                                                          simple_script)
        commands.append(command)

        # Test importing puzzle and running commands from same file
        command = 'cat {} | {}'.format(puzzle_with_script, self.program)
        commands.append(command)

        self.redirect_output()
        for command in commands:
            self.run_command(command)
        self.reset_output()

        if self.compare_file is None:
            return

        self.output_file.seek(0)
        output_lines = self.output_file.read().splitlines()
        compare_lines = self.compare_file.read().splitlines()
        self.assertEqual(output_lines, compare_lines)
