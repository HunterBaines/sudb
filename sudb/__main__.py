# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""The main method for the package and an ErrorLogger subclass for Sudokus.

"""
from __future__ import absolute_import, division, print_function

import os
import sys
import tempfile
from argparse import ArgumentParser

from sudb import importer
from sudb import generator
from sudb import formatter as frmt
from sudb import error
from sudb.logger import ErrorLogger
from sudb.solver import Solver
from sudb.controller import SolverController


INIT_FILE = '~/.sudbinit'
CMDHIST_FILE = os.path.join(tempfile.gettempdir(), 'sudb_cmdhist')


class PuzzleErrorLogger(ErrorLogger):
    """An ErrorLogger subclass for errors related to Sudoku puzzles.

    Attributes
    ----------
    INCONSISTENT_BOARD : Error instance
        The error indicating the board's state is inconsistent with the
        rules of Sudoku (e.g., duplicates of the same number in the same
        row, column, or box).
    TOO_FEW_CLUES : Error instance
        The error indicating the board has fewer clues than the minimum
        required to guarantee the puzzle has a single solution.

    """
    INCONSISTENT_BOARD = error.Error('inconsistent board')
    TOO_FEW_CLUES = error.Error('too few clues')

    def __init__(self):
        errors = [self.INCONSISTENT_BOARD, self.TOO_FEW_CLUES]
        super(PuzzleErrorLogger, self).__init__(errors)

    def unsolvable_mask(self):
        """Return a mask of all errors that mark an unsolvable puzzle.

        Returns
        -------
        int
            A value representing the error numbers of all errors that
            indicate an unsolvable puzzle ORed together.

        """
        return self.INCONSISTENT_BOARD.errno

    def autolog(self, obj, report=False):
        puzzle = obj
        error_count = 0
        # For error reporting
        name = str(hash(puzzle)) if not puzzle.name else puzzle.name

        inconsistent_locations = puzzle.inconsistencies()
        if inconsistent_locations:
            self.log_error(puzzle, self.INCONSISTENT_BOARD)
            error_count += 1
            if report:
                colormap = frmt.get_colormap(inconsistent_locations, frmt.Color.RED)
                msg = 'puzzle has an inconsistent board:\n\n'
                msg += frmt.strfboard(puzzle, colormap=colormap, ascii_mode=True)
                msg += '\n'
                error.error(msg, prelude=name)

        # See the generator module for references on 17 being the minimum
        # for a proper Sudoku puzzle
        if puzzle.clue_count() < 17:
            self.log_error(puzzle, self.TOO_FEW_CLUES)
            error_count += 1
            if report:
                msg = 'puzzle contains fewer clues than the 17 required for a proper,'
                msg += ' single-solution Sudoku board'
                error.error(msg, prelude=name)

        return error_count


def main():
    """Get puzzle(s) from file, user, or seed and solve each in turn.

    Import puzzles from filenames given as commandline arguments, generate
    them from seed, or (if neither files nor seeds given) create them from
    lines manually entered by the user. If `-t` is given, reduce the number
    of clues in each puzzle as much as possible, or if `-s` is given,
    simplify the puzzle by filling in any cells that could not be deduced,
    and then solve each in turn without interaction (unless the `-i`
    argument is given). Output the end state of each board after attempting
    to solve it, and mark differences between it and the original board if
    the `-d` argument was used. Use only ASCII in the output if the `-a`
    argument was given.

    """
    args = _get_parser().parse_args()

    # Warn if the UTF-8 output will look like garbage on this terminal
    if not args.ascii and sys.stdout.encoding in ['ascii', 'ANSI_X3.4-1968']:
        msg = 'your terminal does not seem to support UTF-8 output;'
        msg += ' consider changing your terminal\'s character encoding'
        msg += ' settings or calling this program with the --ascii option.'
        msg += '\n'
        error.error(msg, prelude='warning')

    init_commands = []
    if not args.no_init:
        init_path = os.path.expanduser(INIT_FILE)
        try:
            with open(init_path, 'r') as init:
                init_commands = [line for line in init.read().split('\n') if line]
        except IOError:
            pass

    command_queue = [] if args.execute is None else args.execute

    # Flatten the list of puzzle lines
    lines = None if args.lines is None else [line for line_list in args.lines for line in line_list]

    if args.random is not None and not args.random:
        # `-r` was used without arguments
        args.random.append(generator.random_seed())

    log = PuzzleErrorLogger()
    puzzles = importer.get_puzzles(filenames=args.file, lines=lines, seeds=args.random, logger=log)
    solved_puzzles = 0

    if log.error_count() > 0:
        # There was an import error; print a newline to stderr for spacing
        error.error('', prelude='')
    print('{} puzzle{}to solve.'.format(len(puzzles), 's ' if len(puzzles) != 1 else ' '))

    for i, puzzle in enumerate(puzzles):
        _edit_puzzle(puzzle, args.satisfactory, args.minimized, args.symmetrical)

        skip_solving = False
        if log.autolog(puzzle, report=True) and log.in_mask(puzzle, log.unsolvable_mask()):
            # A unsolvable error occured
            skip_solving = True

        # A copy of the original is needed to find differences between it
        # and the final state of the board and for error output
        original_puzzle = puzzle.duplicate()

        if skip_solving:
            pass
        elif args.auto:
            auto_solver = Solver(puzzle)
            if auto_solver.autosolve_without_history():
                solved_puzzles += 1
        else:
            options = SolverController.Options()
            options.ascii = args.ascii
            solver = SolverController(puzzle, init_commands=init_commands,
                                      command_queue=command_queue, options=options)
            try:
                if solver.solve():
                    solved_puzzles += 1
            except BaseException:
                # To make it easier to return to board state at crash
                print('\nFinal State of Puzzle {} ({}):'.format(i+1, puzzle.name))
                print(puzzle)
                print()
                with open(CMDHIST_FILE, 'w+') as cmdhist:
                    cmdhist.write('\n'.join(solver.command_history))
                puzzle_line_args = ' '.join(str(original_puzzle).split())
                print('Command history saved in "{}". To restore:'.format(CMDHIST_FILE))
                print('{} -x "source {}" -l {}'.format(sys.argv[0], CMDHIST_FILE,
                                                       puzzle_line_args))
                print()
                raise

        colormap = None
        if args.difference:
            colormap = frmt.get_colormap(puzzle.differences(original_puzzle), frmt.Color.GREEN)
        puzzle_str = frmt.strfboard(puzzle, colormap=colormap, ascii_mode=args.ascii)

        print('\nEnd Board for Puzzle {}:'.format(i+1))
        print('{}\n({})\n'.format(puzzle_str, puzzle.name))

    print('Solved {} of {}.'.format(solved_puzzles, len(puzzles)))
    if log.error_count() > 0:
        print()
        log.print_summary()


def _get_parser():
    parser = ArgumentParser(description='Solve 9x9 Sudokus automatically or interactively.')

    file_help = 'import puzzles either from text files with one row of the puzzle'
    file_help += ' per line and "0" or any non-digit, non-whitespace character'
    file_help += ' representing blanks or from clean, sharp image files'

    parser.add_argument('-a', '--auto', action='store_true',
                        help='solve non-interactively')
    parser.add_argument('-A', '--ascii', action='store_true',
                        help='output only ASCII (no UTF-8)')
    parser.add_argument('-d', '--difference', action='store_true',
                        help='mark differences in the original and end board(s)')
    parser.add_argument('-f', '--file', nargs='+', help=file_help)
    parser.add_argument('-l', '--lines', metavar='LINE', nargs=9, action='append',
                        help='import a puzzle from the nine lines given')
    parser.add_argument('-m', '--minimized', action='store_true',
                        help='remove clues that are not needed to guarantee a unique solution')
    parser.add_argument('-n', '--no-init', action='store_true',
                        help='do not execute commands from {}'.format(INIT_FILE))
    parser.add_argument('-r', '--random', metavar='SEED', type=int, nargs='*',
                        help='generate a random board with a random seed or the seed(s) given')
    parser.add_argument('-s', '--satisfactory', action='store_true',
                        help='add clues that seem to require guessing instead of deduction')
    parser.add_argument('-S', '--symmetrical', action='store_true',
                        help='add or remove clues to give puzzle 180-degree rotational symmetry')
    parser.add_argument('-x', '--execute', metavar='COMMAND', action='append',
                        help='execute the command given (use -x "source FILE" '\
                             'to execute commands from file FILE)')

    return parser


def _edit_puzzle(puzzle, satisfactory, minimized, symmetrical):
    if not satisfactory and not minimized and not symmetrical:
        return

    original_clue_count = puzzle.clue_count()
    func_trace = ''
    clue_trace = ''
    func_count = 0

    if minimized and not symmetrical:
        # If `symmetrical`, a symmetry-preserving minimize will be used
        # instead later on when making the puzzle rotationally symmetric
        clue_change = generator.minimize(puzzle)
        func_trace += 'min'
        clue_trace += '{:+}'.format(clue_change)
        func_count += 1

    if satisfactory:
        clue_change = generator.make_satisfactory(puzzle)
        func_trace += '+' if func_trace else ''
        func_trace += 'sat'
        clue_trace += '{:+}'.format(clue_change)
        func_count += 1

    if symmetrical:
        clue_change = generator.make_rotationally_symmetric(puzzle, minimized=minimized,
                                                            keep_satisfactory=satisfactory)
        func_trace += '+' if func_trace else ''
        func_trace += 'minsym' if minimized else 'sym'
        clue_trace += '{:+}'.format(clue_change)
        func_count += 1

    if clue_trace.startswith('+'):
        clue_trace = clue_trace[1:]

    clue_change = puzzle.clue_count() - original_clue_count
    puzzle.name += ', {:+} clue{}'.format(clue_change, 's' if abs(clue_change) != 1 else '')
    puzzle.name += ' [' if func_count < 2 else ' [{}, '.format(clue_trace)
    puzzle.name += '{}]'.format(func_trace)


if __name__ == '__main__':
    main()
