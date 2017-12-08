# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

from __future__ import absolute_import, division, print_function

import os

from test.output_tester import OutputTester
from sudb.controller import SolverController
from sudb.board import Board
from sudb.solver import Solver


class TestControllerExplain(OutputTester):
    """Test output of controller commands involving explain.

    """
    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/controller_explain.out')
    PUZZLE_LINES = ["047050300", "038200097", "500380000", "920076850", "306892104",
                    "071540029", "000025008", "480009710", "002010430"]
    EXPLAIN_CMD = 'explain'


    @classmethod
    def setUpClass(cls):
        super(TestControllerExplain, cls).setUpClass()
        cls.maxDiff = None

        # Name it to avoid changes to default name affecting test
        cls.puzzle = Board(lines=cls.PUZZLE_LINES, name='test')
        cls.options = SolverController.Options()
        # So controller can quit without confirmation
        cls.options.assume_yes = True
        # To standardize output when `print` is called
        cls.options.width = 70


    def test_explain(self):
        # So the toggles below work as expected
        self.assertFalse(self.options.markview)

        # Set up main controller
        command_queue = []

        temp_solver = Solver(self.puzzle.duplicate())
        self.assertTrue(temp_solver.autosolve())

        command_queue.append('# Test `explain`ing the initial board')
        command_queue.append(self.EXPLAIN_CMD)
        command_queue.append('# Make explain run automatically after each step')
        command_queue.append('set explainsteps')

        seen_move_types = set()
        command_queue.append('# Test `explain`ing every `step` and `stepm` until solved')
        for num, row, col, _, move_type in temp_solver.move_history:
            new_move_type = move_type not in seen_move_types
            if new_move_type:
                command_queue.append('# Make sure this type of move displays properly in markview')
                command_queue.append('set markview # turn markview on')
            command_queue.append('step')
            # +1 to correct zero-indexed row, col from `temp_solver`
            command_queue.append('stepm {} {} {}'.format(row+1, col+1, num))
            if new_move_type:
                command_queue.append('set markview # turn markview off')
                seen_move_types.add(move_type)
        command_queue.append('quit')

        # Set up second controller for testing fringe cases
        fringe_puzzle = Board(name='blank board')
        fringe_command_queue = ['# Test some fringe cases']
        fringe_command_queue.append('# Try to explain unreasonable move')
        fringe_command_queue.append('stepm 5 5 9')
        fringe_command_queue.append('{}  # No reason for move'.format(self.EXPLAIN_CMD))
        fringe_command_queue.append('# Try to explain step that removes a clue')
        fringe_command_queue.append('stepm 5 5 0')
        fringe_command_queue.append('{}  # Just reprint board'.format(self.EXPLAIN_CMD))
        fringe_command_queue.append('quit')

        # Run commands
        controller = SolverController(self.puzzle, command_queue=command_queue,
                                      options=self.options)
        fringe_controller = SolverController(fringe_puzzle, command_queue=fringe_command_queue,
                                             options=self.options)
        self.redirect_output()
        controller.solve()
        # Turn off option set by previous controller
        fringe_controller.options.explainsteps = False
        fringe_controller.solve()
        self.reset_output()

        if self.compare_file is not None:
            self.output_file.seek(0)
            output_lines = self.output_file.read().splitlines()
            compare_lines = self.compare_file.read().splitlines()
            self.assertEqual(output_lines, compare_lines)
