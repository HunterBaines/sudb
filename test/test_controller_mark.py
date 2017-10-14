# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os

from test.output_tester import OutputTester
from sudb.controller import SolverController
from sudb.board import Board


class TestControllerMark(OutputTester):
    """Test output of controller commands involving marks.

    """

    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(), 'test/expected_output/controller_mark.out')
    # List of tuples of form (location, candidates list)
    MARK_ARGS = [(['1', '1'], ['1']), (['5', '5'], Board.SUDOKU_STRINGS),
                 (['9', '9'], ['4-5', '7', '9']), (['5', '9'], ['1-3', '5', '7-9']),
                 (['0', '1'], ['1']), (['1', '0'], ['1']), (['1', '1'], ['a']),
                 (['1', '1'], [''])]
    DELETE_ARGS = [['1', '1', '1'], ['5', '5'], ['9', '9', '4-9'],
                   ['5', '9', '1-3', '5', '7-8'], ['0', '1'], ['1', '0'],
                   ['1', '1'], ['5', '9', 'a'], ['5', '9', '1'], [''], ['']]

    # Which variation on `mark` to use (e.g., 'mark', 'm', etc.)
    MARK_CMD = 'mark'
    # E.g., 'info', 'i', etc.
    INFO_CMD = 'info'
    # E.g., 'print', 'p', etc.
    PRINT_CMD = 'print'
    # E.g., 'delete', 'del', 'd', etc.
    DELETE_CMD = 'delete'
    # Which string to insert between arguments (e.g., ' ', '')
    ARG_SEP = ' '


    @classmethod
    def setUpClass(cls):
        super(TestControllerMark, cls).setUpClass()
        cls.maxDiff = None

        # Name it to avoid changes to default name affecting test
        cls.puzzle = Board(name='test')
        cls.options = SolverController.Options()
        # So controller can quit without confirmation
        cls.options.assume_yes = True
        # To standardize output when `print` is called
        cls.options.width = 70


    def test_mark(self):
        command_queue = []
        all_locations = set()

        generic_info_command = '{} {}'.format(self.INFO_CMD, self.MARK_CMD)
        generic_print_command = '{} {}'.format(self.PRINT_CMD, self.MARK_CMD)
        generic_delete_command = '{} {}'.format(self.DELETE_CMD, self.MARK_CMD)

        # Add `mark` and `info` commands to queue
        for location, numbers in self.MARK_ARGS:
            location_args = self.ARG_SEP.join(location)
            number_args = self.ARG_SEP.join(numbers)
            full_args = location_args + self.ARG_SEP + number_args

            mark_command = '{} {}'.format(self.MARK_CMD, full_args)
            info_command = '{} {}'.format(generic_info_command, location_args)

            all_locations.add(location_args)
            command_queue.append(mark_command)
            command_queue.append(info_command)

        all_location_args = self.ARG_SEP.join(sorted(list(all_locations)))
        command_queue.append('# Display all marks via `info` in two ways')
        command_queue.append('{} {}'.format(generic_info_command, all_location_args))
        command_queue.append(generic_info_command)

        command_queue.append('# Display all marks via `print`')
        command_queue.append(generic_print_command)

        command_queue.append('# Delete marks')
        for arg_list in self.DELETE_ARGS:
            delete_args = self.ARG_SEP.join(arg_list)
            command_queue.append('{} {}'.format(generic_delete_command, delete_args))

        command_queue.append('# Check that the marks have been deleted via `info`')
        command_queue.append('{} {}'.format(generic_info_command, all_location_args))
        command_queue.append(generic_info_command)

        command_queue.append('# Check that the marks have been deleted via `print`')
        command_queue.append(generic_print_command)

        # Tell controller to exit
        command_queue.append('quit')

        # Run commands
        controller = SolverController(self.puzzle, command_queue=command_queue,
                                      options=self.options)
        self.redirect_output()
        controller.solve()
        self.reset_output()

        if self.compare_file is None:
            return

        self.output_file.seek(0)
        output_lines = self.output_file.read().splitlines()
        compare_lines = self.compare_file.read().splitlines()
        self.assertEqual(output_lines, compare_lines)
