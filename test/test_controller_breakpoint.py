# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

from __future__ import absolute_import, division, print_function

import os

from test.output_tester import OutputTester
from sudb.controller import SolverController
from sudb.board import Board


class TestControllerBreakpoint(OutputTester):
    """Test output of controller commands involving breakpoints.

    """

    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/controller_breakpoint.out')
    # An actual puzzle is needed so the solver can make deductions and break at them
    PUZZLE_LINES = ['200009050', '050001400', '030026081', '000480000', '100200007',
                    '008013900', '900030100', '700000009', '000000006']
    # List of (row, col) breakpoints
    # NB `delete` tests expect at least 4 breakpoints---preferably, all in
    # the same row so row prioritization can cut back on output
    BREAKPOINTS = [(3, 1), (3, 3), (3, 4), (3, 7)]

    # Which variation on `breakpoint` to use (e.g., 'break', 'b', etc.)
    BREAK_CMD = 'break'
    # Which variation on `finish` to use (e.g., `finish`, `fin`)
    FINISH_CMD = 'finish'
    # E.g., 'info', 'i', etc.
    INFO_CMD = 'info'
    # E.g., 'delete', 'del', 'd', etc.
    DELETE_CMD = 'delete'


    @classmethod
    def setUpClass(cls):
        assert len(cls.BREAKPOINTS) >= 3, 'Must have 4 or more breakpoints to test `delete`'
        super(TestControllerBreakpoint, cls).setUpClass()
        cls.maxDiff = None

        # Name it to avoid changes to default name affecting test
        cls.puzzle = Board(lines=cls.PUZZLE_LINES, name='test')
        cls.options = SolverController.Options()
        # So controller can quit without confirmation
        cls.options.assume_yes = True
        # To standardize output when `print` is called
        cls.options.width = 70


    def test_breakpoint(self):
        command_queue = []
        breakpoint_count = len(self.BREAKPOINTS)

        generic_info_command = '{} {}'.format(self.INFO_CMD, self.BREAK_CMD)
        generic_delete_command = '{} {}'.format(self.DELETE_CMD, self.BREAK_CMD)

        command_queue.append('# test setting breakpoints and `info break`')
        for i, (row, col) in enumerate(self.BREAKPOINTS):
            command_queue.append('{} {} {}'.format(self.BREAK_CMD, row, col))
            # Where i+1 is the breakpoint id
            command_queue.append('{} {}'.format(generic_info_command, i+1))
        command_queue.append('# show all breakpoints via `info` in various ways')
        command_queue.append(generic_info_command)
        command_queue.append('{} 1-{}'.format(generic_info_command, breakpoint_count))

        command_queue.append('# test breaking on breakpoints')
        for i in range(breakpoint_count):
            command_queue.append(self.FINISH_CMD)
            command_queue.append('# should be breakpoint {}'.format(i+1))

        # This is why at least 4 elements are required in self.BREAKPOINTS
        command_queue.append('# test deleting')
        command_queue.append('{} 1'.format(self.DELETE_CMD))
        command_queue.append('# test deleting a range')
        command_queue.append('{} 2-3'.format(self.DELETE_CMD))
        command_queue.append('# test deleting all')
        command_queue.append(self.DELETE_CMD)

        command_queue.append('# test passing bad arguments to various commands')
        command_queue.append('# Too few arguments')
        command_queue.append('{} 1'.format(self.BREAK_CMD))
        command_queue.append('# Invalid row')
        command_queue.append('{} 0 1'.format(self.BREAK_CMD))
        command_queue.append('# Invalid column')
        command_queue.append('{} 1 0'.format(self.BREAK_CMD))
        command_queue.append('# Must be integer')
        command_queue.append('{} x y'.format(self.BREAK_CMD))
        command_queue.append('{} x'.format(generic_info_command))
        command_queue.append('{} x'.format(generic_delete_command))
        command_queue.append('# No matching breakpoints')
        command_queue.append('{} 0'.format(generic_info_command))
        command_queue.append('{} 0'.format(generic_delete_command))
        command_queue.append(generic_info_command)
        command_queue.append(generic_delete_command)

        command_queue.append('# test setting breakpoint on already-passed cell')
        command_queue.append('{} {} {}'.format(self.BREAK_CMD, *self.BREAKPOINTS[0]))
        # Breakpoint ids are not reused, so the next is one more than last
        new_breakpoint_id = breakpoint_count + 1

        command_queue.append('# test giving `info` a partially bad range')
        command_queue.append('{} {}-{}'.format(generic_info_command, new_breakpoint_id,
                                               new_breakpoint_id+2))
        command_queue.append('# test redefining a breakpoint')
        command_queue.append('{} {} {}'.format(self.BREAK_CMD, *self.BREAKPOINTS[0]))
        new_breakpoint_id += 1

        command_queue.append('# test deleting with longer version of `delete`')
        command_queue.append('{} {}'.format(generic_delete_command, new_breakpoint_id))

        command_queue.append('# add back to do another `delete` test')
        command_queue.append('{} {} {}'.format(self.BREAK_CMD, *self.BREAKPOINTS[0]))
        new_breakpoint_id += 1
        command_queue.append('# test giving `delete` a partially bad range')
        command_queue.append('{} {}-{}'.format(generic_delete_command, new_breakpoint_id,
                                               new_breakpoint_id+2))

        # Tell controller to exit
        command_queue.append('quit')

        # Run commands
        controller = SolverController(self.puzzle, command_queue=command_queue,
                                      options=self.options)
        # Prioritize row used so there is less output to wade through
        priority_row = self.BREAKPOINTS[0][0]
        # Unlike SolverController, Solver uses zero-, not one-, indexed rows
        controller.solver.prioritize_row(priority_row-1)
        self.redirect_output()
        controller.solve()
        self.reset_output()

        if self.compare_file is None:
            return

        self.output_file.seek(0)
        output_lines = self.output_file.read().splitlines()
        compare_lines = self.compare_file.read().splitlines()
        self.assertEqual(output_lines, compare_lines)
