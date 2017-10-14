# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os

from test.output_tester import OutputTester
from sudb.controller import SolverController
from sudb.board import Board


class TestControllerHelp(OutputTester):
    """Test output of controller command `help COMMAND`.

    """

    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(), 'test/expected_output/controller_help.out')
    # How hard would it be to derive matching text from the alias regexes themselves?
    ALIASES = ['s', 'sm', 'sb', 'sc', 'sr', '555']


    @classmethod
    def setUpClass(cls):
        super(TestControllerHelp, cls).setUpClass()
        cls.maxDiff = None

        # Name it to avoid changes to default name affecting test
        cls.puzzle = Board(name='test')
        cls.options = SolverController.Options()
        # So controller can quit without confirmation
        cls.options.assume_yes = True


    def test_help(self):
        self.assertEqual(len(self.ALIASES), len(SolverController.Options().aliases))

        # Add help commands for non-aliased commands
        command_queue = []
        for command in SolverController(self.puzzle).cmd.commands:
            command_queue.append('help ' + command)
            if command.startswith('help'):
                # This can introduce duplicates, but they'll be removed before running
                command_queue.append(command)

        # Add help commands for aliased commands
        for alias in self.ALIASES:
            command_queue.append('help ' + alias)

        # Remove duplicates and standardize order
        command_queue = list(set(command_queue))
        command_queue.sort()

        # So the controller will exit
        command_queue.append('quit')

        # Run commands
        controller = SolverController(self.puzzle, command_queue=command_queue,
                                      options=self.options)
        self.redirect_output()
        controller.solve()
        self.reset_output()

        if self.compare_file is None:
            # Output already written to `EXPECTED_OUTPUT_FILE`; nothing else to do
            return

        # Compare output
        self.output_file.seek(0)
        output_lines = self.output_file.read().splitlines()
        compare_lines = self.compare_file.read().splitlines()
        self.assertEqual(output_lines, compare_lines)
