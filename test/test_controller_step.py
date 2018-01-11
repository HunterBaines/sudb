# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os

from test.output_tester import OutputTester
from sudb.controller import SolverController
from sudb.board import Board
from sudb.solver import Solver


class TestControllerStep(OutputTester):
    """Test output of controller commands involving step.

    """

    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/controller_step.out')
    # An actual puzzle is needed so the solver can perform `step`s
    PUZZLE_LINES = ['200009050', '050001400', '030026081', '000480000', '100200007',
                    '008013900', '900030100', '700000009', '000000006']

    # A command and the location it affects if made as first step on puzzle
    FIRST_MOVES = [('step', 1, 5), ('stepr 3', 3, 1), ('stepc 7', 3, 7),
                   ('stepb 5', 5, 5), ('949', 9, 4)]
    INCONSISTENT_MOVE = 'stepm 119'

    STEP_CMDS = ('step', 's')
    STEPR_CMDS = ('stepr', 'sr')
    STEPC_CMDS = ('stepc', 'sc')
    STEPB_CMDS = ('stepb', 'sb')
    STEPM_CMDS = ('stepm', 'sm')
    UNSTEP_CMD = 'unstep'

    BREAK_CMD = 'break'
    DELETE_CMD = 'delete'


    @classmethod
    def setUpClass(cls):
        super(TestControllerStep, cls).setUpClass()
        cls.maxDiff = None

        # Name it to avoid changes to default name affecting test
        cls.puzzle = Board(lines=cls.PUZZLE_LINES, name='test')
        cls.options = SolverController.Options()
        # So controller can quit without confirmation
        cls.options.assume_yes = True
        # To standardize output when `print` is called
        cls.options.width = 70


    def test_step(self):
        command_queue = []

        available_first_moves = []
        solver = Solver(self.puzzle)
        for (row, col) in Board.SUDOKU_CELLS:
            candidates = solver.candidates(row, col)
            if len(candidates) == 1 and self.puzzle.get_cell(row, col) == Board.BLANK:
                # Solver uses zero-indexed locations, so correct
                available_first_moves.append((row+1, col+1, candidates.pop()))

        command_queue.append('# test `step` variants')
        for i, (row, col, num) in enumerate(available_first_moves[:2]):
            command_queue.append('# try to deduce {} at ({}, {})'.format(num, row, col))
            box, _ = Board.box_containing_cell(row-1, col-1)
            box += 1
            # Alternate the command variation used each iteration
            command_queue.append('{} {}'.format(self.STEPR_CMDS[i % 2], row))
            command_queue.append(self.UNSTEP_CMD)
            command_queue.append('{} {}'.format(self.STEPC_CMDS[i % 2], col))
            command_queue.append(self.UNSTEP_CMD)
            command_queue.append('{} {}'.format(self.STEPB_CMDS[i % 2], box))
            command_queue.append(self.UNSTEP_CMD)
            command_queue.append('# set {} at ({}, {}) manually'.format(num, row, col))
            command_queue.append('{} {} {} {}'.format(self.STEPM_CMDS[i % 2], row, col, num))
            command_queue.append(self.UNSTEP_CMD)
            command_queue.append('# using `stepm` ROW COL NUM alias')
            command_queue.append('{1}{0}{2}{0}{3}'.format(' ' * (i % 2), row, col, num))
            command_queue.append(self.UNSTEP_CMD)


        command_queue.append('# test breaking on `step`s')
        for step_cmd, row, col in self.FIRST_MOVES:
            command_queue.append('{} {} {}'.format(self.BREAK_CMD, row, col))
            command_queue.append(step_cmd)
            command_queue.append('# breakpoint at ({}, {})'.format(row, col))
            command_queue.append(self.UNSTEP_CMD)
        command_queue.append(self.DELETE_CMD)

        command_queue.append('# test repeating `step`s')
        command_queue.append('{} 2'.format(self.STEP_CMDS[0]))
        command_queue.append('{} 12'.format(self.STEPR_CMDS[0]))
        command_queue.append('{} 12'.format(self.STEPC_CMDS[0]))
        command_queue.append('{} 12'.format(self.STEPB_CMDS[0]))
        command_queue.append('{} 8'.format(self.UNSTEP_CMD))

        command_queue.append('# test passing bad arguments to various commands')
        command_queue.append('# No steps left to undo')
        command_queue.append('{} 82'.format(self.UNSTEP_CMD))
        command_queue.append('# Must be integer')
        command_queue.append('{} x'.format(self.STEP_CMDS[0]))
        command_queue.append('{} x'.format(self.UNSTEP_CMD))
        command_queue.append('{} 1 x'.format(self.STEPR_CMDS[0]))
        command_queue.append('{} 1 x'.format(self.STEPC_CMDS[0]))
        command_queue.append('{} 1 x'.format(self.STEPB_CMDS[0]))
        command_queue.append('{} x x x'.format(self.STEPM_CMDS[0]))
        command_queue.append('# Invalid row')
        command_queue.append('{} 0 1 1'.format(self.STEPM_CMDS[0]))
        command_queue.append('{} 0'.format(self.STEPR_CMDS[0]))
        command_queue.append('# Invalid column')
        command_queue.append('{} 1 0 1'.format(self.STEPM_CMDS[0]))
        command_queue.append('{} 0'.format(self.STEPC_CMDS[0]))
        command_queue.append('# Invalid box')
        command_queue.append('{} 0'.format(self.STEPB_CMDS[0]))
        command_queue.append('# Argument required')
        command_queue.append(self.STEPR_CMDS[0])
        command_queue.append(self.STEPC_CMDS[0])
        command_queue.append(self.STEPB_CMDS[0])
        command_queue.append('# Exactly three arguments required')
        command_queue.append('{}'.format(self.STEPM_CMDS[0]))
        command_queue.append('{} 1'.format(self.STEPM_CMDS[0]))
        command_queue.append('{} 1 1'.format(self.STEPM_CMDS[0]))
        command_queue.append('# Inconsistent move')
        command_queue.append(self.INCONSISTENT_MOVE)

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
