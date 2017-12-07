# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

from __future__ import absolute_import, division, print_function

import os

from test.output_tester import OutputTester
from sudb.controller import SolverController
from sudb.board import Board


class TestControllerSet(OutputTester):
    """Test output of controller commands involving set.

    """

    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/controller_set.out')
    # A puzzle--with guesses--is needed to test certain settings
    PUZZLE_LINES = ['000003017', '015009008', '060000000', '100007000', '009000200',
                    '000500004', '000000020', '500600340', '340200000']
    # The move number on which the first guess occurs
    MOVE_OF_FIRST_GUESS = 6
    SET_CMD = 'set'


    @classmethod
    def setUpClass(cls):
        super(TestControllerSet, cls).setUpClass()
        cls.maxDiff = None

        # Name it to avoid changes to default name affecting test
        cls.puzzle = Board(lines=cls.PUZZLE_LINES, name='test')
        cls.options = SolverController.Options()
        # So controller can quit without confirmation
        cls.options.assume_yes = True
        # To standardize output when `print` is called
        cls.options.width = 70


    def test_set(self):
        command_queue = []

        command_queue.append('# first try `set` with no subcommand')
        command_queue.append(self.SET_CMD)

        command_queue.append('# test `set ascii`')
        command_queue.append('{} ascii # turn on'.format(self.SET_CMD))
        command_queue.append('print')
        command_queue.append('{} ascii # turn off'.format(self.SET_CMD))
        command_queue.append('print')

        command_queue.append('# test `set guessbreak`')
        command_queue.append('step {}'.format(self.MOVE_OF_FIRST_GUESS-1))
        command_queue.append('check move_before_guess')
        command_queue.append('step 2')
        command_queue.append('restart move_before_guess')
        command_queue.append('{} guessbreak # turn on'.format(self.SET_CMD))
        command_queue.append('step 2')
        command_queue.append('restart')
        command_queue.append('{} guessbreak # turn off'.format(self.SET_CMD))

        command_queue.append('# test `set markview`')
        command_queue.append('mark 1 1 9')
        command_queue.append('mark 9 9 9')
        for effect in ('on', 'off'):
            command_queue.append('{} markview # turn {}'.format(self.SET_CMD, effect))
            command_queue.append('step')
            command_queue.append('explain')
            command_queue.append('unstep')

        command_queue.append('# test `set prompt`')
        command_queue.append('set prompt sudb# ')
        command_queue.append('set prompt all spaces  taken    literally> ')
        command_queue.append('# even no argument is taken literally')
        command_queue.append('set prompt')
        command_queue.append('# reset prompt')
        command_queue.append('set prompt {}'.format(self.options.prompt))

        command_queue.append('# test `set width`')
        command_queue.append('{} width 80 # set wide'.format(self.SET_CMD))
        command_queue.append('print marks')
        command_queue.append('help step')
        command_queue.append('{} width 60 # set narrow'.format(self.SET_CMD))
        command_queue.append('print marks')
        command_queue.append('{} ascii # show ascii version'.format(self.SET_CMD))
        command_queue.append('print marks')
        command_queue.append('help step')
        command_queue.append('{} width 0  # restore default'.format(self.SET_CMD))

        command_queue.append('# test passing bad arguments')
        command_queue.append('# Undefined set command')
        command_queue.append('{} madeup_set_command'.format(self.SET_CMD))
        command_queue.append('# Argument must be integer')
        command_queue.append('{} width x'.format(self.SET_CMD))
        command_queue.append('# Integer out of range')
        command_queue.append('{} width -1'.format(self.SET_CMD))
        command_queue.append('# One argument required')
        command_queue.append('{} width'.format(self.SET_CMD))

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