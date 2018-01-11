# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os

from test.main_tester import MainTester


class TestMainImportingFiles(MainTester):
    """Test output when importing puzzles from local files.

    """
    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/main_importing_files.out')


    def test_main_importing_files(self):
        commands = []

        normal_puzzle_text = os.path.join(self.PUZZLE_PATH, 'normal_puzzle.txt')
        normal_puzzle_image = os.path.join(self.PUZZLE_PATH, 'normal_puzzle.png')
        multiple_puzzles = os.path.join(self.PUZZLE_PATH, 'multiple_puzzles.txt')
        inconsistent_puzzle = os.path.join(self.PUZZLE_PATH, 'inconsistent_puzzle.txt')
        improper_puzzle = os.path.join(self.PUZZLE_PATH, 'too_few_clues_puzzle.txt')
        nonexistent_puzzle = 'this_file_does_not_exist.txt'

        # Test importing a typical puzzle from text
        command = '{} --file {} --auto --difference'.format(self.program, normal_puzzle_text)
        commands.append(command)

        # Test importing a typical puzzle from an image
        command = '{} --file {} --auto --difference'.format(self.program, normal_puzzle_image)
        commands.append(command)

        # Test importing a typical puzzle from `--lines`
        with open(normal_puzzle_text, 'r') as puzzle_file:
            lines = ' '.join(puzzle_file.read().splitlines())
        command = '{} --lines {} --auto --difference'.format(self.program, lines)
        commands.append(command)

        # Test importing a typical puzzle from stdin
        command = '{} --auto --difference < {}'.format(self.program, normal_puzzle_text)
        commands.append(command)

       # Test importing multiple puzzles with alternate formats and titles
        command = '{} --file {} --auto --ascii'.format(self.program, multiple_puzzles)
        commands.append(command)

        # Test importing an inconsistent puzzle
        command = '{} --file {} --auto --ascii'.format(self.program, inconsistent_puzzle)
        commands.append(command)

        # Test importing improper puzzle
        command = '{} --file {} --auto --ascii'.format(self.program, improper_puzzle)
        commands.append(command)

        # Test importing from a non-existent file
        command = '{} --file {} --auto --ascii'.format(self.program, nonexistent_puzzle)
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
