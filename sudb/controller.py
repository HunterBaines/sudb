# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

from __future__ import print_function
import os
import re
import stat
import textwrap
from collections import deque
from enum import IntEnum

import formatter as frmt
from cmdmap import CommandMapper
from board import Board
from solver import Solver


class SolverController(object):
    """An interactive 9x9 Sudoku solver modeled after a debugger.

    Parameters
    ----------
    puzzle : Board instance
        The puzzle board to use in the solver.
    init_commands : iterable of str
        An iterable object containing commands to run during
        initialization.
    command_queue : iterable of str
        An iterable object containing commands to run before taking
        commands from input.
    options : Options instance, optional
        The options to initialize the instance with (default the standard
        options in a new Options instance).

    Attributes
    ----------
    Status : class
        A class containing power-of-two int constants used as return values
        in `cmd_`-style methods and combinable using bitwise operations.
    Options : class
        A collection of variables that control settings in the instance.
    cmd : CommandMapper instance
        An object providing command completion and an automatically
        generated dict of command names to command methods in this class.
    puzzle : Board instance
        The puzzle board to solve.
    solver : Solver instance
        The object used to solve the puzzle.
    original_solver : Solver instance
        The `solver` in its original state (used for restarting).
    breakno : int
        A value used to assign a unique ID to a new breakpoint.
    breakpoints : tuple-keyed dict with int items
        A dict with one-indexed row, col key pointing to the unique
        `breakno` assigned to the breakpoint the key represents.
    checkpoints : str-keyed dict with Solver instance items
        A dict mapping user-defined checkpoints to a Solver instance, which
        provides enough data to restore state to what it was it was when
        the checkpoint was set.
    marks : tuple-keyed dict with set of int items
        A dict with *zero-indexed* row, col keys pointing to a user-defined
        set of candidates for that location.
    options : Options instance
        The set of options to use during this session.
    command_history : list of str
        A list of all commands entered during the session.
    command_queue : collections.deque of str
        A deque of commands to run before taking additional input in the
        `solve` method.

    Notes
    -----
    Any new '_cmd_'- and '_subcmd_'-style methods should be careful to
    follow the model of the existing ones. Other code in this class
    expects the following from these methods: the '_cmd_' or '_subcmd_'
    prefix (used in generating the command dictionary and command
    completer); the argv parameter, which is a list of str arguments (with
    the command's name as the zeroth element); the print_help parameter,
    which when equal to 1 should print a short help message and return and
    when equal to 2 should print a longer help message and return, and
    which should otherwise be ignored; and finally a Status constant as a
    return value.
    """

    class Status(IntEnum):
        """Constants representing the reason a command returned.

        Attributes
        ----------
        NONE : int
            Constant representing no status.
        OK : int
            Constant used for normal return.
        STUCK : int
            Constant used for return due to the solver being stuck.
        BREAK : int
            Constant used for return due to a breakpoint.
        QUIT : int
            Constant used to indicate the program should exit.
        REPEAT : int
            Constant used to indicate the command is repeatable (e.g., may
            be run again if the user hits RETURN).
        MANGLE : int
            Constant used to indicate the command should be mangled (e.g.,
            commented out) in any command history.
        OTHER : int
            Constant used for abnormal return for some other reason.
        """

        NONE = 0
        OK = 1
        STUCK = 2
        BREAK = 4
        QUIT = 8
        REPEAT = 16
        MANGLE = 32
        OTHER = 64


    class Options(object):
        """Options for use with SolverController instances.

        Attributes
        ----------
        aliases : dict of str to str
            A mapping of aliases to what they should be expanded to.
        ascii : bool
            True if ouput should only use ascii, and False if it may use
            UTF-8.
        markview : bool
            True if the larger version of the board with user-defined
            candidates displayed should be the default, and False if the
            most compact version (just clues and blanks) should be the
            default.
        guessbreak : bool
            True if the solver should always break on guessed moves, and
            False otherwise.
        prompt : str
            The string to display on each line of command entry.
        width : int
            The width to use for wrapping text and deciding which version
            of the user-defined-candidates-displayed board to output.
        comment_char : str
            The characters used to mark a line as a comment.
        """

        def __init__(self):
            # The leading space in the expansion of patterns that can begin
            # either at the start of the line ('^') or with whitespace
            # ('\s') is needed to avoid expanding something like 'help s'
            # into 'helpstep '. (The spaces will be stripped when dealing
            # with '^' matches, so distinguishing between it and the '\s'
            # matches with slightly different patterns is unnecessary.)
            self.aliases = {r'(^|\s)s(\s|$)': r' step ',
                            r'(^|\s)sm(\s|$)': r' stepm ',
                            r'(^\s*\d\s*\d\s*\d)': r'stepm \1'}
            self.ascii = False
            self.markview = False
            self.guessbreak = False
            self.prompt = '(sudb) '
            self.width = 0
            self.comment_char = '#'


    def __init__(self, puzzle, init_commands=None, command_queue=None, options=None):
        self.cmd = CommandMapper(self, pattern='^_(sub)?cmd_')

        self.puzzle = puzzle
        self.solver = Solver(puzzle)
        self.original_solver = Solver(puzzle.duplicate())

        self.breakno = 0
        self.breakpoints = {}
        self.checkpoints = {}
        self.marks = {}

        self.options = self.Options() if options is None else options
        self.command_history = []
        self.command_queue = deque() if command_queue is None else deque(command_queue)

        if init_commands is not None:
            for command in init_commands:
                self.run_command(command)


    def solve(self):
        """Interactively solve the puzzle.

        Interpret commands entered by the user and work toward moving the
        instance's `puzzle` to its solved state.

        Returns
        -------
        bool
            True if `puzzle` was successfully solved or False otherwise.
        """

        command = ''
        last_command = 'step'
        # To determine if stdin is coming from file or terminal
        stdin_piped = stat.S_ISFIFO(os.fstat(0).st_mode)

        name = '"{}"'.format(self.puzzle.name) if self.puzzle.name else hash(self.puzzle)
        print('Starting solver on puzzle with ID {}.'.format(name))
        self.print_puzzle()

        status = self.Status.NONE
        while not status & self.Status.QUIT:
            if self.command_queue:
                command = self.command_queue.popleft()
                print(self.options.prompt, command, sep='')
            else:
                try:
                    if stdin_piped:
                        command = raw_input()
                        # Mimic how this would look if input from terminal
                        print(self.options.prompt, command, sep='')
                    else:
                        command = raw_input(self.options.prompt).lower()
                except EOFError:
                    command = 'quit'
                    if stdin_piped:
                        print(self.options.prompt, end='')
                    print(command)

            if not command.split():
                # Command is just whitespace
                command = last_command

            status = self.run_command(command)

            if status & self.Status.MANGLE:
                self.command_history.append('{} {}'.format(self.options.comment_char, command))
            else:
                self.command_history.append(command)

            if status & self.Status.REPEAT:
                last_command = command

            if status & self.Status.STUCK:
                # The solver is stuck (no solution possible or solved already)
                # This can change if user, e.g., does an unstep, stepm, or restart
                if self.puzzle.is_complete() and self.puzzle.is_consistent():
                    print('The puzzle is solved.')
                else:
                    print('The solver is stuck. Try restarting.')

        # Even if solved at some point during session, it may not be solved at quit time
        return self.puzzle.is_complete() and self.puzzle.is_consistent()

    def run_command(self, command):
        """Parse and run the given command.

        Parameters
        ----------
        command : str
            The command to run (e.g., 'set width 70', 'se w 70', 'step',
            'pr m', etc.).

        Returns
        -------
        Status constant
            The return status of the command run.
        """

        command_name, arg_str = self.parse_command(command)
        command_args = arg_str.split()

        if command_name is None:
            return self.Status.OTHER
        elif command_name == 'set prompt':
            # Hack to get the prompt with literal everything (whitespace and
            # comments) to `set prompt`
            try:
                literal_argv = command.split(' ')
                arg_index = literal_argv.index(command.split()[2])
                command_args = [' '.join(literal_argv[arg_index:])]
            except IndexError:
                command_args = ['']

        argv = command_name.split() + command_args
        command_func = None
        try:
            # If subcommand, the parent command calls it
            command_func = self.cmd.commands[argv[0]]
        except KeyError:
            # This should only occur if there are bad commands in the
            # `commands` list passed to the initializer
            print('Undefined command: "{}". Try "help".'.format(command))
            return self.Status.OTHER

        # Running `command_func` outside try-except block means if
        # `command_func` happens to raise `KeyError`, the program won't
        # falsely claim that it's because the command is undefined
        return command_func(argv)

    def parse_command(self, command):
        """Return the expanded command name and any arguments as a tuple.

        Parameters
        ---------
        command : str
            The command to attempt to expand and seperate into a full
            command name and an argument string.

        Returns
        -------
        str tuple
            A tuple consisting of the (possibly) expanded command name and
            a string representing any passed arguments, so, for example, if
            `command` is 'se w 70', this method will return the tuple ('set
            width', '70'). If no command name can be determined, the first
            element of the tuple will be None.
        """

        if not command or command.startswith(self.options.comment_char):
            # command was None, an empty string, or just a comment
            return None, ''

        possible_commands = []

        # Kept around as-is (minus the comments) for error output
        command = self._remove_comments(command)
        temp_command = command
        for pat, rep in self.options.aliases.items():
            if re.findall(pat, temp_command):
                temp_command = re.sub(pat, rep, temp_command)
        command_tokens = temp_command.lower().split()
        command_tokens.reverse()

        full_command_name = ''
        while command_tokens:
            token = command_tokens.pop()
            # Match as many of the command tokens as possible
            full_command_name = '{} {}'.format(full_command_name, token).strip()
            completions = self.cmd.completions(full_command_name)
            if not completions:
                # So it can be added to the command_args string below
                command_tokens.append(token)
                break
            possible_commands = completions[:]

        command_tokens.reverse()
        command_args = ' '.join(command_tokens)

        if len(possible_commands) != 1:
            base_command_name = ''
            # Check if list similiar to ['set', 'set width', 'set ascii']
            # or to ['step', 'stepm'] and return common prefix if so
            prefixes = map(set, zip(*map(list, possible_commands)))
            for char_set in prefixes:
                if len(char_set) == 1:
                    base_command_name += char_set.pop()
                else:
                    break
            else:
                if base_command_name:
                    # Checking in case prefixes was empty
                    return base_command_name, command_args

            if len(possible_commands) > 1:
                # Check if list similiar to ['print candidates', 'print checkpoints'],
                # so common name can be used in error message
                base_names = set([cmd.split()[0] for cmd in possible_commands])
                base_command_name = '{} '.format(base_names.pop()) if len(base_names) == 1 else ''
                print('Ambiguous {}command "{}":'.format(base_command_name, command), end='')
                print(' {}.'.format(', '.join(possible_commands)))
                return None, command_args
            elif not possible_commands:
                # There could never be an 'Undefined X command: "Y"' here (for
                # command X with bad subcommand Y): Y has to be interpreted
                # as args for X since command X may take non-command-name
                # arguments (e.g., `break` can take a BREAKNO to delete).
                print('Undefined command: "', end='')
                try:
                    print('{}'.format(command.split()[0]), end='')
                except IndexError:
                    # Command is just whitespace
                    print('{}'.format(command), end='')
                print('". Try "help".')
                return None, command_args

        return possible_commands[0], command_args

    def _remove_comments(self, text):
        new_text = ''
        quote_stack = []
        for char in text:
            if char in ['\'', '"']:
                if quote_stack and quote_stack[-1] == char:
                    quote_stack.pop()
                else:
                    quote_stack.append(char)
            elif not quote_stack and char == self.options.comment_char:
                break
            new_text += char
        return new_text


    def printwrap(self, *args):
        """Print the passed strings wrapped to a defined width.

        Print the strings wrapped to the width defined in
        `self.options.width` or 70 if that width is 0.

        Parameters
        ----------
        args : list of str
            The text to be joined by a space and printed wrapped to the
            defined width.
        """

        text = ' '.join(args)
        width = self.options.width
        width = 70 if not width else width
        print('\n'.join(textwrap.wrap(text, width=width)))

    def print_puzzle(self, move_type=None, locations=None, solver=None, candidate_map=None,
                     treat_move_type_as_reason=False):
        """Display the puzzle with a move number.

        Print the current state of the instance's `puzzle` and the `moveno`
        associated with that state. Optionally color the location tuples
        given in `locations` some unique color based on the type specified
        in `move_type`, and display the candidates for a given location
        within its corresponding cell.

        Parameters
        ----------
        move_type : MoveType constant, optional
            A move type, which tells the method what color to use on the
            location tuples in `locations` (default type of last move).
        locations : iterable of int tuple, optional
            An iterable of row, column tuples that represent locations to
            color (default None).
        solver : Solver instance, optional
            The solver whose board and move count to use (default
            `self.solver`).
        candidate_map : dict of tuple to int set
            A mapping of *zero-indexed* row, column locations to the set of
            numbers representing possible values for that location (default
            None).
        treat_move_type_as_reason : bool, optional
            True if `move_type` should be interpreted as `MoveType.REASON`
            regardless of whether it actually is, which allows moves with a
            `last_move_type` that is non-deductive (e.g.,
            `MoveType.MANUAL`) to still display reasons by explicitly
            naming in the parameter `move_type` which deductive move type
            it should be treated as; False otherwise (default False).

        Examples
        --------
        >>> from controller import SolverController
        >>> from board import Board
        >>> puzzle_lines = ['003020600', '900305001', '001806400']
        >>> puzzle_lines.extend(['008102900', '700000008', '006708200'])
        >>> puzzle_lines.extend(['002609500', '800203009', '005010300'])
        >>> puzzle = Board(lines=puzzle_lines)
        >>> control = SolverController(puzzle, ascii_mode=True)
        >>> control.print_puzzle()

           MOVE 0
          .........................
        1 ! _ _ 3 ! _ 2 _ ! 6 _ _ !
        2 ! 9 _ _ ! 3 _ 5 ! _ _ 1 !
        3 ! _ _ 1 ! 8 _ 6 ! 4 _ _ !
          !.......!.......!.......!
        4 ! _ _ 8 ! 1 _ 2 ! 9 _ _ !
        5 ! 7 _ _ ! _ _ _ ! _ _ 8 !
        6 ! _ _ 6 ! 7 _ 8 ! 2 _ _ !
          !.......!.......!.......!
        7 ! _ _ 2 ! 6 _ 9 ! 5 _ _ !
        8 ! 8 _ _ ! 2 _ 3 ! _ _ 9 !
        9 ! _ _ 5 ! _ 1 _ ! 3 _ _ !
          !.......!.......!.......!
            1 2 3   4 5 6   7 8 9

        """

        if solver is None:
            solver = self.solver
        if move_type is None:
            move_type = solver.last_move_type()

        puzzle = solver.puzzle
        moveno = solver.move_count()

        separator = '\n'
        title = '   MOVE {}'.format(moveno)

        colormap = None
        if not locations:
            pass
        elif treat_move_type_as_reason or move_type == Solver.MoveType.REASON:
            title += ' (reasons)'
            # If `move_type` is `REASON`, the move type to use in interpreting 
            # the reasons will equal `self.solver.last_move_type()`
            colormap = self._get_reasons_colormap(locations, move_type, solver=solver)
        elif move_type == Solver.MoveType.GUESSED:
            title += ' (guessed)'
            colormap = frmt.get_colormap(locations, frmt.Color.GREEN)
        elif move_type == Solver.MoveType.MANUAL:
            title += ' (manual)'
            colormap = frmt.get_colormap(locations, frmt.Color.CYAN)
        elif move_type == Solver.MoveType.CORRECTED:
            title += ' (corrected)'
            colormap = frmt.get_colormap(locations, frmt.Color.RED)
        elif move_type == Solver.MoveType.DIFFERENCE:
            title += ' (differences)'
            colormap = frmt.get_colormap(locations, frmt.Color.YELLOW)
        else:
            colormap = frmt.get_colormap(locations, frmt.Color.BLUE)

        show_axes = True
        if candidate_map is not None:
            title = ''
            show_axes = False
        else:
            title += '\n'

        if self.options.markview and not candidate_map:
            candidate_map = self.marks

        puzzle_str = frmt.strfboard(puzzle, colormap=colormap, candidate_map=candidate_map,
                                    ascii_mode=self.options.ascii, show_axes=show_axes,
                                    terminal_width=self.options.width)

        output = separator + title + puzzle_str
        print(output)

    def _get_reasons_colormap(self, locations, reported_move_type, solver=None):
        NONVIABLE_BLANK_COLOR = frmt.Color.INVERT + frmt.Color.MAGENTA

        if solver is None:
            solver = self.solver

        actual_move_type = solver.last_move_type()
        if reported_move_type == Solver.MoveType.REASON:
            reported_move_type = actual_move_type

        colormap = frmt.get_colormap(locations, frmt.Color.MAGENTA)
        if actual_move_type == Solver.MoveType.NONE:
            return colormap

        _, original_row, original_col = solver.moves()[-1]

        # The color of the move to explain is always based on the actual move type
        if actual_move_type == Solver.MoveType.MANUAL:
            colormap[(original_row, original_col)] = frmt.Color.CYAN
        else:
            colormap[(original_row, original_col)] = frmt.Color.BLUE

        # But the colors of the rest are based on the reported move type so
        # a non-deductive `actual_move_type` (e.g., MANUAL) can still be
        # explained via a deductive method (given in `reported_move_type`)
        if reported_move_type == Solver.MoveType.ROWWISE:
            original_band = Board.band_containing_cell(original_row, original_col)
            for row, col in locations:
                band = Board.band_containing_cell(row, col)
                if band == original_band:
                    # Mark all cells in same row in box as nonviable
                    box, _ = Board.box_containing_cell(row, col)
                    box_cells = [(r, c) for (r, c) in Board.cells_in_box(box) if r == original_row]
                    for box_row, box_col in box_cells:
                        if self.puzzle.get_cell(box_row, box_col) == Board.BLANK:
                            colormap[(original_row, box_col)] = NONVIABLE_BLANK_COLOR
                elif self.puzzle.get_cell(original_row, col) == Board.BLANK:
                    colormap[(original_row, col)] = NONVIABLE_BLANK_COLOR
        elif reported_move_type == Solver.MoveType.COLWISE:
            original_stack = Board.stack_containing_cell(original_row, original_col)
            for row, col in locations:
                stack = Board.stack_containing_cell(row, col)
                if stack == original_stack:
                    # Mark all cells in same column in box as nonviable
                    box, _ = Board.box_containing_cell(row, col)
                    box_cells = [(r, c) for (r, c) in Board.cells_in_box(box) if c == original_col]
                    for box_row, box_col in box_cells:
                        if self.puzzle.get_cell(box_row, box_col) == Board.BLANK:
                            colormap[(box_row, original_col)] = NONVIABLE_BLANK_COLOR
                elif self.puzzle.get_cell(row, original_col) == Board.BLANK:
                    colormap[(row, original_col)] = NONVIABLE_BLANK_COLOR

        return colormap


    # START OF COMMAND METHODS
    ##########################################################################

    def _cmd_break(self, argv, print_help=0):
        if print_help == 1:
            print('Set breakpoint at specified location.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_break([], print_help=1)
            print('Usage: break ROW COL')
            print()
            self.printwrap('ROW COL indicates the location in the puzzle to break at',
                           'once the value of the cell at that location is known.')
            return self.Status.OK

        status = self.Status.REPEAT
        args = argv[1:]

        locations = self._get_locations(args)
        if not locations:
            return status | self.Status.OTHER

        row, col = locations[0]
        actual_row, actual_col = self._zero_correct(row, col)

        try:
            breakno = self.breakpoints[(row, col)]
            print('Note: redefined from breakpoint {}.'.format(breakno))
        except KeyError:
            pass

        self.breakno += 1
        # Note that the location is the user-specified, not the actual, one
        # If the breakpoint already exists, overwrite it
        self.breakpoints[(row, col)] = self.breakno

        print('Breakpoint {} at {}, {}'.format(self.breakno, row, col), end='')
        if self.puzzle.get_cell(actual_row, actual_col) != Board.BLANK:
            print(' (already passed)', end='')
        print('.')

        return status | self.Status.OK

    def _cmd_checkpoint(self, argv, print_help=0):
        if print_help == 1:
            print('Save the current board state at a given or default label.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_checkpoint([], print_help=1)
            print('Usage: checkpoint [CHECKPOINT]')
            print()
            self.printwrap('If CHECKPOINT is not given, the current move number will be used.',
                           'Use "restart CHECKPOINT" to restore this state of the board.')
            return self.Status.OK

        try:
            checkpoint = argv[1]
        except IndexError:
            # Default checkpoint label is the move number
            checkpoint = str(self.solver.move_count())

        saved_solver = self.solver.duplicate()
        self.checkpoints[checkpoint] = saved_solver

        print('Current state saved at "{}".'.format(checkpoint))

        return self.Status.OK


    # DELETE COMMANDS START

    def _cmd_delete(self, argv, print_help=0):
        if print_help == 1:
            print('Delete some user-set value.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_help_delete([], print_title=True)
            return self.Status.OK

        args = argv[1:]

        if not args:
            args = ['breakpoints'] + args
            return self._subcmd_delete_breakpoints(args)

        try:
            # Check if first char of first arg could be a breakno
            int(args[0][0])
            args = ['breakpoints'] + args
            return self._subcmd_delete_breakpoints(args)
        except ValueError:
            pass

        return self._call_subcommand(argv)

    def _subcmd_delete_breakpoints(self, argv, print_help=0):
        if print_help == 1:
            print('Delete all or matching breakpoints.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_delete_breakpoints([], print_help=1)
            print('Usage: delete breakpoints [BREAKNO [BREAKNO ...]]')
            print()
            self.printwrap('BREAKNO can be a number or a hyphen-specified range.',
                           'If not given, all breakpoints will be deleted.',
                           'The two commands "delete breakpoints BREAKNO" and "delete BREAKNO"',
                           'are equivalent (that is, the "breakpoints" is optional).')
            return self.Status.OK

        args = argv[1:]

        breaknos = self._get_numbers(args)
        if breaknos is None:
            return self.Status.OTHER
        elif not breaknos:
            if not self.breakpoints:
                print('No breakpoints to delete.')
            elif self._confirm('Delete all breakpoints?'):
                self.breakpoints = {}
            return self.Status.OK

        seen_breaknos = set()
        for bno in breaknos:
            for loc, loc_bno in self.breakpoints.items():
                if loc_bno == bno:
                    del self.breakpoints[loc]
                    seen_breaknos.add(bno)

        if not seen_breaknos:
            print('No matching breakpoints.')
        else:
            print('Deleted {} breakpoint'.format(len(seen_breaknos)), end='')
            print('s.' if len(seen_breaknos) != 1 else '.', )
            for bno in set(breaknos) - seen_breaknos:
                print('No breakpoint number {}.'.format(bno))

        return self.Status.OK

    def _subcmd_delete_checkpoints(self, argv, print_help=0):
        if print_help == 1:
            print('Delete all or matching checkpoints.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_delete_checkpoints([], print_help=1)
            print('Usage: delete checkpoints [CHECKPOINT [CHECKPOINT ...]]')
            print()
            self.printwrap('If no CHECKPOINT is given, all checkpoints will be deleted.')
            return self.Status.OK

        checkpoints = argv[1:]
        if not checkpoints:
            if not self.checkpoints:
                print('No checkpoints to delete.')
            elif self._confirm('Delete all checkpoints?'):
                self.checkpoints = {}
            return self.Status.OK

        seen_checkpoints = set()
        for checkpoint in checkpoints:
            try:
                del self.checkpoints[checkpoint]
                seen_checkpoints.add(checkpoint)
            except KeyError:
                pass

        if not seen_checkpoints:
            print('No matching checkpoints.')
        else:
            print('Deleted {} checkpoint'.format(len(seen_checkpoints)), end='')
            print('s.' if len(seen_checkpoints) != 1 else '.', )
            for checkpoint in set(checkpoints) - seen_checkpoints:
                print('No checkpoint matching "{}".'.format(checkpoint))

        return self.Status.OK

    def _subcmd_delete_marks(self, argv, print_help=0):
        if print_help == 1:
            print('Delete all or matching user-defined candidates.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_delete_marks([], print_help=1)
            print('Usage: delete marks [ROW COL [NUMBER [NUMBER ...]]]')
            print()
            self.printwrap('If ROW, COL, and one or more NUMBER are given,',
                           'delete each valid NUMBER from the user-defined candidate',
                           'list for that location. If only ROW and COL are given,',
                           'delete all numbers from that list. If no arguments are',
                           'given, delete all marks.')
            return self.Status.OK

        args = argv[1:]

        if not args:
            if not self.marks:
                print('No marks to delete.')
            elif self._confirm('Delete all marks?'):
                self.marks = {}
            return self.Status.OK

        try:
            row, col, numbers = self._get_locations_and_numbers(args)
            if numbers is None:
                raise TypeError
        except TypeError:
            # _get_locations_and_numbers returned None
            return self.Status.OTHER

        actual_row, actual_col = self._zero_correct(row, col)

        try:
            if not self.marks[(actual_row, actual_col)]:
                raise KeyError
        except KeyError:
            print('No marks at ({}, {}).'.format(row, col))
            return self.Status.OK

        if not numbers:
            del self.marks[(actual_row, actual_col)]
            print('Deleted all marks at ({}, {}).'.format(row, col))
            return self.Status.OK

        self.marks[(actual_row, actual_col)] -= set(numbers)
        if not self.marks[(actual_row, actual_col)]:
            del self.marks[(actual_row, actual_col)]
        print('Deleted from candidates for ({}, {}): {}.'.format(row, col, sorted(numbers)))
        return self.Status.OK

    # DELETE COMMANDS END


    def _cmd_explain(self, argv, print_help=0):
        if print_help == 1:
            print('Indicate the reason(s) for the last move.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_explain([], print_help=1)
            print('Usage: explain')
            return self.Status.OK

        status = self.Status.REPEAT

        move_type = self.solver.last_move_type()
        actual_move_type_is_manual = False

        if move_type == Solver.MoveType.NONE:
            print('The initial board is given.')
            return status | self.Status.OK
        elif move_type == Solver.MoveType.GUESSED:
            print('A guess pulled from a solved version of the board.')
            return status | self.Status.OK
        elif move_type == Solver.MoveType.MANUAL:
            # `move_type` can be changed when searching for reasons for manual move
            actual_move_type_is_manual = True

        _, row, col = self.solver.moves()[-1]
        box, _ = Board.box_containing_cell(row, col)

        output = ''
        if self.puzzle.rows()[row].count(Board.BLANK) == 0:
            output += 'It was the last blank in the row'
        if self.puzzle.columns()[col].count(Board.BLANK) == 0:
            output += ', column' if output else 'It was the last blank in the column'
        if self.puzzle.boxes()[box].count(Board.BLANK) == 0:
            output += ', box' if output else 'It was the last blank in the box'

        if output:
            rightmost_comma = output.rfind(',')
            if rightmost_comma > -1:
                # I guess I'm anti-Oxford-comma now
                output = output[:rightmost_comma] + ' and' + output[rightmost_comma+1:]
            output += '.'
            print(output)
            return status | self.Status.OK

        locations = set()
        if actual_move_type_is_manual:
            # See if manual move can be explained by known deductive methods
            max_locations = 0
            for deductive_type in Solver.DEDUCTIVE_MOVE_TYPES:
                # Find best explanation for manual move
                possible_reasons = self.solver.reasons(override_move_type=deductive_type)
                if len(possible_reasons) > max_locations:
                    # Try to find explanation with most locations (NB this
                    # means the manual and deduced explanation may differ)
                    max_locations = len(possible_reasons)
                    locations = possible_reasons
                    move_type = deductive_type
        else:
            locations = self.solver.reasons()

        if locations:
            if actual_move_type_is_manual:
                # Here `move_type` is the move type to be used in interpreting the reasons found
                self.print_puzzle(move_type=move_type, locations=locations,
                                  treat_move_type_as_reason=True)
                print('Possible reasons for manual move.')
            else:
                # Here the move type to use for interpreting the reasons will simply be
                # `self.solver.last_move_type()`
                self.print_puzzle(move_type=Solver.MoveType.REASON, locations=locations)

            return status | self.Status.OK

        print('No reason found for ', end='')
        print('{}move.'.format('manual ' if actual_move_type_is_manual else ''))
        return status | self.Status.OTHER

    def _cmd_finish(self, argv, print_help=0):
        if print_help == 1:
            print('Step until stuck or at solution or breakpoint.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_finish([], print_help=1)
            print('Usage: finish')
            return self.Status.OK

        status = self.Status.REPEAT
        step_argv = ['step', '1']
        while True:
            step_status = self._cmd_step(step_argv)
            if not self.Status.OK & step_status:
                return status | step_status


    # HELP COMMANDS START

    def _cmd_help(self, argv, print_help=0):
        if print_help == 1:
            print('Print all or matching commands.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_help_help([], print_title=True)
            return self.Status.OK

        status = self.Status.REPEAT
        args = argv[1:]

        if len(args) >= 1:
            command_name, _ = self.parse_command(' '.join(args))
            if command_name is None:
                return status | self.Status.OTHER
            self.cmd.commands[command_name]([], print_help=2)
            return status | self.Status.OK

        print('List of commands:\n')
        for command_name in sorted(self.cmd.commands.keys()):
            command = self.cmd.commands[command_name]
            print('{} -- '.format(command_name), end='')
            command([], print_help=1)
        return status | self.Status.OK

    def _subcmd_help_delete(self, argv, print_help=0, print_title=False):
        return self._abstract_subcmd_help('delete', print_help=print_help, print_title=print_title)

    def _subcmd_help_help(self, argv, print_help=0, print_title=False):
        return self._abstract_subcmd_help('help', print_help=print_help, print_title=print_title)

    def _subcmd_help_info(self, argv, print_help=0, print_title=False):
        return self._abstract_subcmd_help('info', print_help=print_help, print_title=print_title)

    def _subcmd_help_print(self, argv, print_help=0, print_title=False):
        return self._abstract_subcmd_help('print', print_help=print_help, print_title=print_title)

    def _subcmd_help_set(self, argv, print_help=0, print_title=False):
        return self._abstract_subcmd_help('set', print_help=print_help, print_title=print_title)

    def _abstract_subcmd_help(self, command_name, print_help=0, print_title=False):
        if print_help == 1:
            print('Print list of {} subcommands.'.format(command_name))
            return self.Status.OK
        elif print_help == 2:
            self._abstract_subcmd_help(command_name, print_help=1)
            print('Usage: help {}'.format(command_name))
            return self.Status.OK

        status = self.Status.REPEAT

        if print_title:
            print('List of {} subcommands:'.format(command_name))
            print()

        for subcommand_name in sorted(self.cmd.commands.keys()):
            if subcommand_name.startswith(command_name):
                command = self.cmd.commands[subcommand_name]
                print('{} -- '.format(subcommand_name), end='')
                command([], print_help=1)

        return status | self.Status.OK

    # HELP COMMANDS END
    # INFO COMMANDS START

    def _cmd_info(self, argv, print_help=0):
        if print_help == 1:
            print('Generic command for showing things about session.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_help_info([], print_title=True)
            return self.Status.OK

        status = self.Status.REPEAT

        if len(argv) < 2:
            self._subcmd_help_info([], print_title=True)
            return status | self.Status.OK

        return status | self._call_subcommand(argv)

    def _subcmd_info_breakpoints(self, argv, print_help=0):
        if print_help == 1:
            print('Show all or matching breakpoints.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_info_breakpoints([], print_help=1)
            print('Usage: info break [BREAKNO [BREAKNO ...]]')
            print()
            self.printwrap('BREAKNO can be a number or a hyphen-specified range.',
                           'If not given, all breakpoints will be shown.')
            return self.Status.OK

        args = argv[1:]

        breaknos = self._get_numbers(args)
        if breaknos is None:
            return self.Status.OTHER

        # Sort breakpoints by their breakno
        sorted_breaks = sorted(self.breakpoints.items(), key=lambda item: item[1])

        seen_breaknos = set()
        breakpoint_info_lines = ['Num\tCell']

        for (location, bno) in sorted_breaks:
            if not breaknos or bno in breaknos:
                # str(bno) instead of just bno because strings left align, numbers don't
                breakpoint_info_lines.append('{:2}\t{}, {}'.format(str(bno), *location))
                seen_breaknos.add(bno)

        if len(breakpoint_info_lines) == 1:
            print('No matching breakpoints.')
        else:
            print('\n'.join(breakpoint_info_lines))
            if breaknos:
                for bno in set(breaknos) - seen_breaknos:
                    print('No breakpoint number {}.'.format(bno))

        return self.Status.OK

    def _subcmd_info_checkpoints(self, argv, print_help=0):
        if print_help == 1:
            print('Show all or matching checkpoints.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_info_checkpoints([], print_help=1)
            print('Usage: info checkpoint [CHECKPOINT [CHECKPOINT ...]]')
            print()
            self.printwrap('If no CHECKPOINT is given, the move numbers of',
                           'all checkpoints will be shown.')
            return self.Status.OK

        checkpoints = argv[1:]
        if not checkpoints:
            # Since order in checkpoints not available, order by move number
            checkpoints = sorted(self.checkpoints.items(), key=lambda x: x[1].move_count())
            checkpoints = [key for key, _ in checkpoints]

        title = 'Check'
        longest_checkpoint = len(title)
        for checkpoint in checkpoints:
            # repr to account for quotes to be used in printout
            if len(repr(checkpoint)) > longest_checkpoint:
                longest_checkpoint = len(repr(checkpoint))
        title += ' ' * (longest_checkpoint - len(title))
        title += '\tMove'

        error_lines = []
        checkpoint_info_lines = [title]

        for checkpoint in checkpoints:
            try:
                saved_moveno = self.checkpoints[checkpoint].move_count()
                checkpoint_info = '"{}"'.format(checkpoint)
                checkpoint_info += ' ' * (longest_checkpoint - len(repr(checkpoint)))
                checkpoint_info += '\t{}'.format(saved_moveno)
                checkpoint_info_lines.append(checkpoint_info)
            except KeyError:
                error_lines.append('No checkpoint matching "{}".'.format(checkpoint))

        if len(checkpoint_info_lines) == 1:
            print('No matching checkpoints.')
        else:
            print('\n'.join(checkpoint_info_lines))
            if error_lines:
                print('\n'.join(error_lines))

        return self.Status.OK

    def _subcmd_info_marks(self, argv, print_help=0):
        if print_help == 1:
            print('Show all or matching user-defined candidates.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_info_marks([], print_help=1)
            print('Usage: info mark [ROW COL [ROW COL ...]]')
            print()
            self.printwrap('Show the candidates for each ROW COL location.',
                           'If none given, show all user-defined candidates.')
            return self.Status.OK

        args = argv[1:]

        locations = []
        if args:
            locations = self._get_locations(args)
            if locations is None:
                return self.Status.OTHER

        if not locations:
            locations = [loc for (loc, can) in self.marks.items() if can]
            locations.sort()
        else:
            locations = [self._zero_correct(row, col) for (row, col) in locations]

        error_lines = []
        locations_info_lines = ['Cell\tCandidates']

        # Remember that `marks` uses zero-indexed rows and columns
        for (actual_row, actual_col) in locations:
            row, col = self._zero_correct(actual_row, actual_col, inverted=True)

            if actual_row not in Board.SUDOKU_ROWS:
                error_lines.append('Invalid row {0} in ({0}, {1}).'.format(row, col))
                continue
            if actual_col not in Board.SUDOKU_COLS:
                error_lines.append('Invalid column {1} in ({0}, {1}).'.format(row, col))
                continue

            try:
                candidates = self.marks[(actual_row, actual_col)]
                if not candidates:
                    raise KeyError
                location_info = '{}, {}\t{}'.format(row, col, sorted(list(candidates)))
                locations_info_lines.append(location_info)
            except KeyError:
                error_lines.append('No candidates defined for ({}, {}).'.format(row, col))

        if len(locations_info_lines) == 1:
            print('No matching locations.')
        else:
            print('\n'.join(locations_info_lines))
            if error_lines:
                print('\n'.join(error_lines))

        return self.Status.OK

    # INFO COMMANDS END


    def _cmd_mark(self, argv, print_help=0):
        if print_help == 1:
            print('Mark one or more numbers as candidates for the given cell.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_mark([], print_help=1)
            print('Usage: mark ROW COL NUMBER [NUMBER ...]')
            print()
            self.printwrap('Add every valid NUMBER to a list of candidates for',
                           'the location defined by ROW COL. For viewing these',
                           'candidates, see "print marks" and "info marks".',
                           'For viewing candidates set by the computer, see',
                           '"print candidates" and "x".')
            return self.Status.OK

        args = argv[1:]

        try:
            row, col, numbers = self._get_locations_and_numbers(args)
            if not numbers:
                raise TypeError
        except TypeError:
            # _get_locations_and_numbers returned None
            return self.Status.OTHER

        actual_row, actual_col = self._zero_correct(row, col)

        try:
            candidates = self.marks[(actual_row, actual_col)]
            self.marks[(actual_row, actual_col)] = candidates.union(set(numbers))
        except KeyError:
            self.marks[(actual_row, actual_col)] = set(numbers)

        print('Added to candidates for ({}, {}): {}.'.format(row, col, sorted(numbers)))

        return self.Status.OK


    # PRINT COMMANDS START

    def _cmd_print(self, argv, print_help=0):
        if print_help == 1:
            print('Print the current state of the board.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_help_print([], print_title=True)
            return self.Status.OK

        status = self.Status.REPEAT

        if len(argv) < 2:
            self.print_puzzle()
            return status | self.Status.OK

        return status | self._call_subcommand(argv)

    def _subcmd_print_candidates(self, argv, print_help=0):
        if print_help == 1:
            print('Print board with generated candidates noted.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_print_candidates([], print_help=1)
            print('Usage: print candidates')
            return self.Status.OK

        candidate_map = {}
        for (actual_row, actual_col) in Board.SUDOKU_CELLS:
            candidate_map[(actual_row, actual_col)] = self.solver.candidates(actual_row,
                                                                             actual_col)
        self.print_puzzle(candidate_map=candidate_map)

        return self.Status.OK

    def _subcmd_print_checkpoints(self, argv, print_help=0):
        if print_help == 1:
            print('Print the state of the board at the given checkpoint.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_print_checkpoints([], print_help=1)
            print('Usage: print checkpoint CHECKPOINT')
            return self.Status.OK

        args = argv[1:]

        try:
            checkpoint = args[0]
            saved_solver = self.checkpoints[checkpoint]
            locations = self.puzzle.differences(saved_solver.puzzle)
            self.print_puzzle(move_type=Solver.MoveType.DIFFERENCE,
                              locations=locations, solver=saved_solver)
            return self.Status.OK
        except IndexError:
            print('Checkpoint not given.')
            return self.Status.OTHER
        except KeyError:
            print('No checkpoint matching "{}".'.format(checkpoint))
            return self.Status.OTHER

    def _subcmd_print_marks(self, argv, print_help=0):
        if print_help == 1:
            print('Print board with user-defined candidates noted.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_print_marks([], print_help=1)
            print('Usage: print marks')
            return self.Status.OK

        self.print_puzzle(candidate_map=self.marks)
        return self.Status.OK

    # PRINT COMMANDS END


    def _cmd_quit(self, argv, print_help=0):
        if print_help == 1:
            print('Quit the solver.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_quit([], print_help=1)
            print('Usage: quit')
            return self.Status.OK

        status = self.Status.REPEAT

        if self.puzzle.is_complete() and self.puzzle.is_consistent():
            return status | self.Status.QUIT

        print('The puzzle has not been solved.')
        if self._confirm('Quit anyway?'):
            return status | self.Status.QUIT
        else:
            return status | self.Status.OK

    def _cmd_restart(self, argv, print_help=0):
        if print_help == 1:
            print('Restart from beginning or from state at a given checkpoint.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_restart([], print_help=1)
            print('Usage: restart [CHECKPOINT]')
            print()

            self.printwrap('If CHECKPOINT is not given, restart from beginning.',
                           'Note that the current board state will be lost upon',
                           'restarting (unless it is also checkpointed).',
                           'Use "checkpoint" to define the checkpoint.')
            return self.Status.OK

        temp_solver = None
        try:
            checkpoint = argv[1]
        except IndexError:
            moveno = self.solver.move_count()
            if moveno != 0:
                print('The puzzle is beyond its original state.')
            if moveno == 0 or self._confirm('Restart anyway?'):
                temp_solver = self.original_solver
            else:
                return self.Status.OK

        try:
            temp_solver = self.checkpoints[checkpoint] if not temp_solver else temp_solver
            # The original solver can't be changed in case of another restart here
            saved_solver = temp_solver.duplicate()
            locations = self.puzzle.differences(saved_solver.puzzle)
            self.puzzle.copy(saved_solver.puzzle)
            self.solver = saved_solver
            self.solver.puzzle = self.puzzle
            self.print_puzzle(move_type=Solver.MoveType.CORRECTED, locations=locations)
        except KeyError:
            print('No state mapped to that checkpoint.')
            return self.Status.OTHER

        return self.Status.OK


    # SET COMMANDS START

    def _cmd_set(self, argv, print_help=0):
        if print_help == 1:
            print('Generic command for setting options.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_help_set([], print_title=True)
            return self.Status.OK

        if len(argv) < 2:
            self._subcmd_help_set([], print_title=True)
            return self.Status.OK

        return self._call_subcommand(argv)

    def _subcmd_set_ascii(self, argv, print_help=0):
        if print_help == 1:
            print('Toggle whether to use UTF-8 in output.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_set_ascii([], print_help=1)
            print('Usage: set ascii')
            return self.Status.OK

        ascii_mode = not self.options.ascii
        self.options.ascii = ascii_mode
        print('UTF-8 output {}.'.format('enabled' if not ascii_mode else 'disabled'))
        return self.Status.OK

    def _subcmd_set_guessbreak(self, argv, print_help=0):
        if print_help == 1:
            print('Toggle whether to break on guesses.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_set_guessbreak([], print_help=1)
            print('Usage: set guessbreak')
            return self.Status.OK

        guessbreak = not self.options.guessbreak
        self.options.guessbreak = guessbreak

        print('Break on guesses {}.'.format('enabled' if guessbreak else 'disabled'))
        return self.Status.OK

    def _subcmd_set_markview(self, argv, print_help=0):
        if print_help == 1:
            print('Toggle whether to always print the board with marks noted.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_set_markview([], print_help=1)
            print('Usage: set markview')
            return self.Status.OK

        markview = not self.options.markview
        self.options.markview = markview

        print('Always print marks {}.'.format('enabled' if markview else 'disabled'))
        return self.Status.OK

    def _subcmd_set_prompt(self, argv, print_help=0):
        if print_help == 1:
            print('Set the solver\'s prompt.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_set_prompt([], print_help=1)
            print('Usage: set prompt PROMPT')
            return self.Status.OK

        args = argv[1:]
        prompt = ''.join(args)
        self.options.prompt = prompt
        return self.Status.OK

    def _subcmd_set_width(self, argv, print_help=0):
        if print_help == 1:
            print('Set the width to use for output.')
            return self.Status.OK
        elif print_help == 2:
            self._subcmd_set_width([], print_help=1)
            print('Usage: set width WIDTH')
            print()
            print('Use 0 for the WIDTH to restore defaults.')
            return self.Status.OK

        args = argv[1:]

        try:
            width = int(args[0])
        except ValueError:
            print('Argument must be an integer.')
            return self.Status.OTHER
        except IndexError:
            print('Exactly one argument required.')
            return self.Status.OTHER

        if width < 0:
            print('Integer {} out of range.'.format(width))
            return self.Status.OTHER

        self.options.width = width
        if width:
            print('Width set to {} characters.'.format(width))
        else:
            print('Width defaults restored.')
        return self.Status.OK

    # SET COMMANDS END


    def _cmd_source(self, argv, print_help=0):
        if print_help == 1:
            print('Run commands from the given file.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_source([], print_help=1)
            print('Usage: source FILE')
            return self.Status.OK

        # All the commands from the sourced file will be added to
        # `command_history`, so running a script based on this history
        # would run the commands in the file twice
        status = self.Status.MANGLE

        args = argv[1:]

        if not args:
            print('No file given.')
            return status | self.Status.OTHER

        filename = ' '.join(args)

        try:
            with open(filename, 'r') as f:
                self.command_queue.extend([line for line in f.read().split('\n') if line])
        except IOError as err:
            print('Error reading "{}": {}.'.format(filename, err.strerror.lower()))
            return status | self.Status.OTHER

        return status | self.Status.OK


    # STEP COMMANDS START

    def _cmd_step(self, argv, print_help=0):
        if print_help == 1:
            print('Step for one or more moves.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_step([], print_help=1)
            print('Usage: step [INTEGER]')
            print()
            self.printwrap('Argument INTEGER means to step INTEGER times (or until',
                           'stuck or at a breakpoint). If not given, 1 is assumed.',
                           'Regardless of any ambiguity, "s" may be used for "step".')
            return self.Status.OK

        status = self.Status.REPEAT
        repeats = self._get_repeats(argv)

        for _ in range(repeats):
            location = self.solver.step()

            if not location:
                # No move could be deduced; time to guess
                move_type = Solver.MoveType.GUESSED
                location = self.solver.step_best_guess()
                if not location:
                    # Control value to indicate the stepper got stuck
                    return status | self.Status.STUCK

            move_type = self.solver.last_move_type()
            self.print_puzzle(move_type=move_type, locations=[location])

            # Check if at breakpoint
            user_location = self._zero_correct(*location, inverted=True)
            if self._is_breakpoint(*user_location):
                return status | self.Status.BREAK

            # Check if guessed move and if breaking should occur on guesses
            if self.options.guessbreak and move_type == Solver.MoveType.GUESSED:
                print('Breaking on guess; use "set guessbreak" to toggle off.')
                return status | self.Status.BREAK

        return status | self.Status.OK

    def _cmd_stepm(self, argv, print_help=0):
        if print_help == 1:
            print('Manually set cell at given location to given number.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_stepm([], print_help=1)
            print('Usage: stepm ROW COL NUMBER')
            print()
            self.printwrap('The two commands "stepm ROW COL NUMBER" and "ROW COL NUMBER"',
                           'are equivalent (that is, the "stepm" is optional).',
                           'Regardless of any ambiguity, "sm" may be used for "stepm".')
            return self.Status.OK

        args = argv[1:]

        try:
            move = ''.join(args)
            # Allow the arguments to be given by a single 3-digit number
            row, col, number = [int(digit) for digit in move]
        except ValueError:
            if len(args) == 3:
                print('Arguments must be integers.')
            elif not args or len(str(args[0])) != 3:
                print('Exactly three arguments required.')
            return self.Status.OTHER

        if self._validate_cell(row, col) != self.Status.OK:
            return self.Status.OTHER

        actual_row, actual_col = self._zero_correct(row, col)

        if not self.solver.step_manual(number, actual_row, actual_col):
            print('Move left board inconsistent. Ignored.')
            return self.Status.OTHER

        self.print_puzzle(move_type=Solver.MoveType.MANUAL, locations=[(actual_row, actual_col)])

        if self._is_breakpoint(row, col):
            return self.Status.BREAK

        return self.Status.OK

    def _cmd_unstep(self, argv, print_help=0):
        if print_help == 1:
            print('Undo one or more steps or stepm\'s.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_unstep([], print_help=1)
            print('Usage: unstep [INTEGER]')
            print()
            self.printwrap('Argument INTEGER means to unstep the last [INTEGER] steps or stepm\'s.',
                           'If not given, 1 is assumed. Note that unstepping does not trigger',
                           'breakpoints.')
            return self.Status.OK

        status = self.Status.REPEAT
        repeats = self._get_repeats(argv)

        for _ in range(repeats):
            location = self.solver.unstep()
            if location:
                self.print_puzzle(move_type=Solver.MoveType.CORRECTED, locations=[location])
            else:
                print('No steps left to undo.')
                return status | self.Status.OTHER

        return status | self.Status.OK

    # STEP COMMANDS END


    def _cmd_x(self, argv, print_help=0):
        if print_help == 1:
            print('Examine the generated candidates at one or more locations.')
            return self.Status.OK
        elif print_help == 2:
            self._cmd_x([], print_help=1)
            print('Usage: info ROW COL [ROW COL ...]')
            print()
            self.printwrap('See also "print candidates" for displaying all generated',
                           'candidates inline. Note that these candidates are distinct',
                           'from those set via the "mark" command.')
            return self.Status.OK

        status = self.Status.REPEAT
        args = argv[1:]

        locations = self._get_locations(args)
        if locations is None:
            return status | self.Status.OTHER

        error_lines = []
        locations_info_lines = ['Cell\tCandidates']

        for (row, col) in locations:
            actual_row, actual_col = self._zero_correct(row, col)
            if actual_row not in Board.SUDOKU_ROWS:
                error_lines.append('Invalid row {0} in ({0}, {1}).'.format(row, col))
            elif actual_col not in Board.SUDOKU_COLS:
                error_lines.append('Invalid column {1} in ({0}, {1}).'.format(row, col))
            else:
                candidates = self.solver.candidates(actual_row, actual_col)
                location_info = '{}, {}\t{}'.format(row, col, list(candidates))
                locations_info_lines.append(location_info)

        if len(locations_info_lines) == 1:
            print('No matching locations.')
        else:
            print('\n'.join(locations_info_lines))
            if error_lines:
                print('\n'.join(error_lines))

        return status | self.Status.OK

    # END OF COMMAND METHODS


    def _call_subcommand(self, argv):
        try:
            new_argv = ['{} {}'.format(argv[0], argv[1])] + argv[2:]
            return self.cmd.commands[new_argv[0]](new_argv)
        except KeyError:
            print('Undefined {0} command: "{1}". Try "help {0}".'.format(argv[0],
                                                                         ' '.join(argv[1:])))
            return self.Status.OTHER

    def _zero_correct(self, row, col, inverted=False):
        actual_row = row
        if Board.SUDOKU_ROWS[0] == 0:
            actual_row += -1 if not inverted else 1

        actual_col = col
        if Board.SUDOKU_COLS[0] == 0:
            actual_col += -1 if not inverted else 1

        return actual_row, actual_col

    def _validate_cell(self, row, col):
        actual_row, actual_col = self._zero_correct(row, col)

        if actual_row not in Board.SUDOKU_ROWS:
            print('Invalid row {0} in ({0}, {1}).'.format(row, col))
            return self.Status.OTHER
        if actual_col not in Board.SUDOKU_COLS:
            print('Invalid column {1} in ({0}, {1}).'.format(row, col))
            return self.Status.OTHER

        return self.Status.OK

    def _confirm(self, message):
        while True:
            try:
                confirm = raw_input('{} (y or n) '.format(message)).lower()
            except EOFError:
                print('EOF [assumed Y]')
                return True
            if confirm.startswith('y'):
                return True
            elif confirm.startswith('n'):
                print('Not confirmed.')
                return False
            else:
                print('Please answer y or n.')

    def _is_breakpoint(self, row, col):
        try:
            # Note this is the one-indexed, user-entered location
            breakno = self.breakpoints[(row, col)]
            print('Breakpoint {}: {}, {}.'.format(breakno, row, col))
            #del self.breakpoints[(row, col)]
            return True
        except KeyError:
            pass

        return False


    def _get_repeats(self, argv):
        try:
            repeats = int(argv[1])
            if repeats < 1:
                print('Integer {} out of range.'.format(repeats))
                repeats = 0
        except IndexError:
            repeats = 1
        except ValueError:
            repeats = 0
            print('Argument must be an integer.')

        return repeats

    def _get_locations(self, args):
        try:
            locations = ''.join(args)
            if len(locations) < 2:
                print('Too few arguments.')
                return None
            locations = zip(map(int, locations[::2]), map(int, locations[1::2]))
            for (row, col) in locations:
                if self._validate_cell(row, col) != self.Status.OK:
                    return None
            return locations
        except ValueError:
            print('Location arguments must be integer pairs.')
            return None

    def _get_numbers(self, args, sudoku_numbers=False):
        numbers = []

        for arg in args:
            try:
                if '-' in arg:
                    min_num, max_num = map(int, arg.split('-'))
                    if min_num >= max_num:
                        print('Invalid range {}-{}.'.format(min_num, max_num))
                    else:
                        numbers.extend(range(min_num, max_num+1))
                else:
                    numbers.append(int(arg))
            except ValueError:
                if not numbers:
                    # Exit with error if first arg is bad
                    print('Number argument must be integer or integer range.')
                    return None

        if sudoku_numbers:
            clean_numbers = set(Board.SUDOKU_NUMBERS).intersection(set(numbers))
            difference_count = len(set(numbers) - set(clean_numbers))
            if difference_count:
                print('Ignored {} invalid Sudoku number'.format(difference_count), end='')
                print('s.' if difference_count != 1 else '.')
                if not clean_numbers:
                    return None
            numbers = list(clean_numbers)

        return numbers

    def _get_locations_and_numbers(self, args):
        new_args = [''.join(list(tup)) for tup in re.findall(r'(.-.)|(.)', ''.join(args))]

        try:
            row, col = self._get_locations(new_args[:2])[0]
        except TypeError:
            # _get_locations returned None
            return None

        numbers = self._get_numbers(new_args[2:], sudoku_numbers=True)

        return row, col, numbers
