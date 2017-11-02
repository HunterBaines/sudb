# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import os

from test.output_tester import OutputTester
from sudb.controller import SolverController
from sudb.board import Board


class TestControllerCheckpoint(OutputTester):
    """Test output of controller commands involving checkpoints.

    """

    # This expects to be run from the project root
    EXPECTED_OUTPUT_FILE = os.path.join(os.getcwd(),
                                        'test/expected_output/controller_checkpoint.out')
    # An actual puzzle is needed so the solver can make deductions and checkpoint them
    PUZZLE_LINES = ['200009050', '050001400', '030026081', '000480000', '100200007',
                    '008013900', '900030100', '700000009', '000000006']
    # List of (checkpoint label, move number) tuples
    CHECKPOINTS = [('moveno_0', 0), ('moveno_1a', 1), ('moveno_1b', 1),
                   ('moveno_3', 3), ('moveno_7', 7)]

    # Which variation on `checkpoint` to use (e.g., 'checkpoint', 'check', etc.)
    CHECK_CMD = 'checkpoint'
    # Which variation on `restart` to use (e.g., 'restart', 'r', etc.)
    RESTART_CMD = 'restart'
    # Which variation `step` to use (e.g., 'step', 's')
    STEP_CMD = 'step'
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
        super(TestControllerCheckpoint, cls).setUpClass()
        cls.maxDiff = None

        # Name it to avoid changes to default name affecting test
        cls.puzzle = Board(lines=cls.PUZZLE_LINES, name='test')
        cls.options = SolverController.Options()
        # So controller can quit without confirmation
        cls.options.assume_yes = True
        # To standardize output when `print` is called
        cls.options.width = 70


    def test_checkpoint(self):
        command_queue = []
        current_moveno = 0

        generic_info_command = '{} {}'.format(self.INFO_CMD, self.CHECK_CMD)
        generic_print_command = '{} {}'.format(self.PRINT_CMD, self.CHECK_CMD)
        generic_delete_command = '{} {}'.format(self.DELETE_CMD, self.CHECK_CMD)

        command_queue.append('# test `checkpoint` and `info checkpoint`')
        for check, moveno in self.CHECKPOINTS:
            if moveno != current_moveno:
                steps_needed = moveno - current_moveno
                step_command = '{} {}'.format(self.STEP_CMD, steps_needed)
                command_queue.append(step_command)
                current_moveno += steps_needed
            command_queue.append('{} {}'.format(self.CHECK_CMD, check))
            command_queue.append('{} {}'.format(generic_info_command, check))

        command_queue.append('# test `print checkpoint` and `restart`')
        for check, _ in self.CHECKPOINTS:
            command_queue.append('{} {}'.format(generic_print_command, check))
            command_queue.append('{} {}'.format(self.RESTART_CMD, check))

        command_queue.append('# test redefining a checkpoint')
        # Step beyond last checkpoint so new checkpoint has different move number
        command_queue.append(self.STEP_CMD)
        command_queue.append('{} {}'.format(self.CHECK_CMD, self.CHECKPOINTS[-1][0]))

        command_queue.append('# test `delete checkpoint`')
        # Display all checkpoints before deleting any
        command_queue.append(generic_info_command)
        for check, _ in self.CHECKPOINTS:
            command_queue.append('{} {}'.format(generic_delete_command, check))
            # Display checkpoints left to test that checkpoint was deleted
            command_queue.append(generic_info_command)
        command_queue.append('# try deleting when no checkpoints left')
        command_queue.append(generic_delete_command)

        command_queue.append('# try deleting multiple checkpoints at once')
        test_checkpoint_labels = ['multidel_1', 'multidel_2', 'multidel_3']
        for check in test_checkpoint_labels:
            command_queue.append('{} {}'.format(self.CHECK_CMD, check))
        command_queue.append(generic_info_command)
        command_queue.append('{} {}'.format(generic_delete_command,
                                            self.ARG_SEP.join(test_checkpoint_labels)))
        command_queue.append(generic_info_command)

        command_queue.append('# test special arguments')
        for arg in ['', 'fake_label', 'multi-word label']:
            command_queue.append('# try using argument "{}"'.format(arg))
            if not arg.startswith('fake'):
                command_queue.append('{} {}'.format(self.CHECK_CMD, arg))
            command_queue.append('{} {}'.format(generic_info_command, arg))
            command_queue.append('{} {}'.format(generic_print_command, arg))
            command_queue.append('{} {}'.format(self.RESTART_CMD, arg))
            command_queue.append('{} {}'.format(generic_delete_command, arg))

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
