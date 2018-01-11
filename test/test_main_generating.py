# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os

from test.main_tester import MainTester


class TestMainGenerating(MainTester):
    """Test output when generating puzzles.

    """
    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/main_generating.out')


    def test_main_generating(self):
        commands = []

        improper_puzzle = os.path.join(self.PUZZLE_PATH, 'too_few_clues_puzzle.txt')
        # Preferably one that is non-satisfactory when minimized
        seed = 1

        file_prog = self.program + ' --auto --difference --file {}'.format(improper_puzzle)
        seed_prog = self.program + ' --auto --difference --random {}'.format(seed)

        # Test making file-imported puzzle satisfactory
        command = '{} --satisfactory'.format(file_prog)
        commands.append(command)

        # Test making file-imported puzzle satisfactory and symmetrical
        command = '{} --satisfactory --symmetrical'.format(file_prog)
        commands.append(command)

        # Test making file-imported puzzle minimized, satisfactory, and
        # symmetrical
        command = '{} --minimized --satisfactory --symmetrical'.format(file_prog)
        commands.append(command)

        # Test just generating
        commands.append(seed_prog)

        # Test minimizing
        command = '{} --minimized'.format(seed_prog)
        commands.append(command)

        # Test making minimized version satisfactory
        command = '{} --minimized --satisfactory'.format(seed_prog)
        commands.append(command)

        # Test generating a symmetrical Sudoku
        command = '{} --symmetrical'.format(seed_prog)
        commands.append(command)

        # Test generating a minimized, symmetrical Sudoku
        command = '{} --minimized --symmetrical'.format(seed_prog)
        commands.append(command)

        # Test generating a minimized, satisfactory, symmetrical Sudoku
        command = '{} --minimized --satisfactory --symmetrical'.format(seed_prog)
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
