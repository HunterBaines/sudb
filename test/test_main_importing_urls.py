# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

from __future__ import absolute_import, division, print_function

import os

from test.main_tester import MainTester


class TestMainImportingURLS(MainTester):
    """Test output when importing puzzles from files given by URLs.

    """
    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/main_importing_urls.out')


    def test_main_importing_urls(self):
        commands = []

        normal_puzzle_text = os.path.join(self.PUZZLE_URL, 'normal_puzzle.txt')
        normal_puzzle_image = os.path.join(self.PUZZLE_URL, 'normal_puzzle.png')
        # Remove protocol
        _, malformed_url = self.PUZZLE_URL.split('://')
        nonexistent_puzzle = os.path.join(self.PUZZLE_URL, 'this_file_does_not_exist.txt')

        # Test importing a typical puzzle from linked text
        command = '{} --file {} --auto --difference'.format(self.program, normal_puzzle_text)
        commands.append(command)

        # Test importing a typical puzzle from a linked image
        command = '{} --file {} --auto --difference'.format(self.program, normal_puzzle_image)
        commands.append(command)

        # Test importing from a malformed link
        command = '{} --file {} --auto'.format(self.program, malformed_url)
        commands.append(command)

        # Test importing from a link to a non-existent file
        command = '{} --file {} --auto'.format(self.program, nonexistent_puzzle)
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
