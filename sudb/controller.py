# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""The module containing the SolverController class.

"""
from __future__ import absolute_import, division, print_function

import os
import re
import stat
import textwrap
import readline
from collections import deque
from functools import wraps
from enum import IntEnum

from sudb import formatter as frmt
from sudb.cmdmap import CommandMapper
from sudb.board import Board
from sudb.solver import Solver


# Redefine builtin `input` to equal `raw_input` like in Python 3
try:
    # Python 2
    # pylint: disable=redefined-builtin,invalid-name
    input = raw_input
except NameError:
    # Python 3
    pass


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
    breakpoints : dict of int tuple to int
        A dict with one-indexed row, col key pointing to the unique
        `breakno` assigned to the breakpoint the key represents.
    checkpoints : dict of str to Solver instance
        A dict mapping user-defined checkpoints to a Solver instance, which
        provides enough data to restore state to what it was it was when
        the checkpoint was set.
    marks : dict of int tuple to int set
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

        Notes
        -----
        Ideally, this would subclass `enum.IntFlag`, but that class is not
        included in the backport of `enum`. If this program ever only
        supports Python 3.6 and above, the class it inherits from should be
        changed.

        """
        NONE = 0
        # pylint: disable=invalid-name; `OK` is an okay name
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
        prompt : str
            The string to display on each line of command entry.
        comment_char : str
            The characters used to mark a line as a comment.
        move_type_colormap : dict of MoveType constant to Color constant
            A dict mapping a move type to the color to use when printing
            the board with that move highlighted.
        default_color : Color constant
            The color to use if one is needed but no viable one exists in
            `move_type_colormap`.
        ascii : bool
            True if ouput should only use ascii, and False if it may use
            UTF-8.
        assume_yes : bool
            True is all yes/no confirmations should be assumed to be "yes"
            and False if confirmation should be obtained each time.
        markview : bool
            True if the larger version of the board with user-defined
            candidates displayed should be the default, and False if the
            most compact version (just clues and blanks) should be the
            default.
        guessbreak : bool
            True if the solver should always break on guessed moves, and
            False if it may continue through them.
        width : int
            The width to use for wrapping text and deciding which version
            of the user-defined-candidates-displayed board to output.

        """
        def __init__(self):
            # The leading space in the expansion of patterns that can begin
            # either at the start of the line ('^') or with whitespace
            # ('\s') is needed to avoid expanding something like 'help s'
            # into 'helpstep '. (The spaces will be stripped when dealing
            # with '^' matches, so distinguishing between it and the '\s'
            # matches with slightly different patterns is unnecessary.)
            self.aliases = {r'(^|\s)s(\s|$)': r' step ',
                            r'(^|\s)sb(\s|$)': r' stepb ',
                            r'(^|\s)sc(\s|$)': r' stepc ',
                            r'(^|\s)sr(\s|$)': r' stepr ',
                            r'(^|\s)sm(\s|$)': r' stepm ',
                            r'(^\s*\d\s*\d\s*\d)': r'stepm \1'}

            self.prompt = '(sudb) '
            self.comment_char = '#'

            self.move_type_colormap = {Solver.MoveType.GUESSED: frmt.Color.GREEN,
                                       Solver.MoveType.MANUAL: frmt.Color.CYAN,
                                       Solver.MoveType.CORRECTED: frmt.Color.RED,
                                       Solver.MoveType.DIFFERENCE: frmt.Color.YELLOW,
                                       Solver.MoveType.REASON: frmt.Color.MAGENTA}
            self.default_color = frmt.Color.BLUE

            self.ascii = False
            self.assume_yes = False
            self.markview = False
            self.guessbreak = False

            self.width = 0


    def __init__(self, puzzle, init_commands=None, command_queue=None, options=None):
        self.cmd = CommandMapper(obj=self, pattern='^_(sub)?cmd_', use_trailing_sep=False)

        # A separate completer that can be added to in order to improve
        # what can be tab-completed without borking command completion
        self._tabcmd = CommandMapper(use_trailing_sep=True)
        self._tabcmd.commands = self.cmd.commands.copy()
        for command in self.cmd.commands:
            self._tabcmd.commands['help {}'.format(command)] = None
        self._setup_tab_completion()

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

    def _setup_tab_completion(self):
        # The default delims prevent completion of commands with spaces
        readline.set_completer_delims('\n')
        readline.set_completer(self._tabcmd.complete)
        readline.parse_and_bind('tab: complete')


    def solve(self):
        """Interactively solve the puzzle.

        Interpret commands entered by the user and work toward moving the
        instance's `puzzle` to its solved state.

        Returns
        -------
        bool
            True if `puzzle` was successfully solved, and False if not.

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
                        command = input()
                        # Mimic how this would look if input from terminal
                        print(self.options.prompt, command, sep='')
                    else:
                        command = input(self.options.prompt).lower()
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
                # The solver is stuck (no solution possible or solved
                # already). NB: this can change if user, e.g., does an
                # unstep, stepm, or restart
                if self.puzzle.is_complete() and self.puzzle.is_consistent():
                    print('The puzzle is solved.')
                else:
                    print('The solver is stuck. Try restarting.')

        # Even if solved at some point during session, it may not be solved
        # at quit time
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
            # Hack to get the prompt with literal everything (whitespace
            # and comments) to `set prompt`
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

            # E.g., `[['s', 'e', 't'], ['s', 'e', 't', ' ', 'w', 'i', 'd', 't', 'h']]`
            command_char_arrays = [list(cmd) for cmd in possible_commands]
            # E.g., `[{'s'}, {'e'}, {'t'}]`
            prefixes = [set(nth_chars) for nth_chars in zip(*command_char_arrays)]
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
                # Check if list similiar to ['print candidates',
                # 'print checkpoints'], so common name can be used in error
                # message
                base_names = set([cmd.split()[0] for cmd in possible_commands])
                base_command_name = '{} '.format(base_names.pop()) if len(base_names) == 1 else ''
                print('Ambiguous {}command "{}":'.format(base_command_name, command), end='')
                print(' {}.'.format(', '.join(possible_commands)))
                return None, command_args
            elif not possible_commands:
                # There could never be an 'Undefined X command: "Y"' here
                # (for command X with bad subcommand Y): Y has to be
                # interpreted as args for X since command X may take
                # non-command-name arguments (e.g., `break` can take a
                # BREAKNO to delete).
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
            it should be treated as; False if not (default False).

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
        if locations and treat_move_type_as_reason or move_type == Solver.MoveType.REASON:
            title += ' (reasons)'
            # If `move_type` is `REASON`, the move type to use in
            # interpreting the reasons is `self.solver.last_move_type()`
            colormap = self._get_reasons_colormap(locations, move_type, solver=solver)
        elif locations:
            if move_type == Solver.MoveType.GUESSED:
                title += ' (guessed)'
            elif move_type == Solver.MoveType.MANUAL:
                title += ' (manual)'
            elif move_type == Solver.MoveType.CORRECTED:
                title += ' (corrected)'
            elif move_type == Solver.MoveType.DIFFERENCE:
                title += ' (differences)'

            try:
                color = self.options.move_type_colormap[move_type]
            except KeyError:
                color = self.options.default_color
            colormap = frmt.get_colormap(locations, color)

        show_axes = True
        if candidate_map is not None:
            title = ''
            show_axes = False
        else:
            title += '\n'

        if self.options.markview and not candidate_map:
            candidate_map = self.marks

        puzzle_str = frmt.strfboard(puzzle, colormap=colormap, candidate_map=candidate_map,
                                    show_axes=show_axes, terminal_width=self.options.width,
                                    ascii_mode=self.options.ascii, ansi_mode=True)

        output = separator + title + puzzle_str + '\n'
        print(output)

    def _get_reasons_colormap(self, locations, reported_move_type, solver=None):
        reason_color = self.options.move_type_colormap[Solver.MoveType.REASON]
        nonviable_blank_color = frmt.Color.INVERT + reason_color

        if solver is None:
            solver = self.solver

        actual_move_type = solver.last_move_type()
        if reported_move_type == Solver.MoveType.REASON:
            reported_move_type = actual_move_type

        colormap = frmt.get_colormap(locations, reason_color)
        if actual_move_type == Solver.MoveType.NONE:
            return colormap

        _, original_row, original_col = solver.moves()[-1]

        # The color of the move to explain is always based on the actual
        # move type
        try:
            actual_color = self.options.move_type_colormap[actual_move_type]
        except KeyError:
            actual_color = self.options.default_color
        colormap[(original_row, original_col)] = actual_color

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
                            colormap[(original_row, box_col)] = nonviable_blank_color
                elif self.puzzle.get_cell(original_row, col) == Board.BLANK:
                    colormap[(original_row, col)] = nonviable_blank_color
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
                            colormap[(box_row, original_col)] = nonviable_blank_color
                elif self.puzzle.get_cell(row, original_col) == Board.BLANK:
                    colormap[(row, original_col)] = nonviable_blank_color
        elif reported_move_type == Solver.MoveType.BOXWISE:
            original_box, _ = Board.box_containing_cell(original_row, original_col)
            box_cells = Board.cells_in_box(original_box)

            original_band = Board.band_containing_cell(original_row, original_col)
            original_stack = Board.stack_containing_cell(original_row, original_col)

            for row, col in locations:
                band = Board.band_containing_cell(row, col)
                stack = Board.stack_containing_cell(row, col)
                for box_row, box_col in box_cells:
                    box_number = self.solver.puzzle.get_cell(box_row, box_col)
                    if box_number == Board.BLANK:
                        if band == original_band and box_row == row:
                            colormap[(row, box_col)] = nonviable_blank_color
                        if stack == original_stack and box_col == col:
                            colormap[(box_row, col)] = nonviable_blank_color

        return colormap


    # START OF COMMAND METHODS
    ##########################################################################

    def cmdhelp(overview_msg, usage_msg, extra_msg=None):
        """Return method with help-message code generated.

        A decorator that adds code for outputting a command-style method's
        short and long help messages when the `print_help` parameter of the
        that method is 1 or 2 respectively.

        Parameters
        ----------
        overview_msg : str
            A short summary of the command-style method being decorated
            (e.g., 'Step for one or more moves.').
        usage_msg : str
            An indication of how the command-style method being decorated
            is to be called (e.g., 'step [INTEGER]').
        extra_msg : str, optional
            Any additional notes on the command-style method being
            decorated (e.g., 'If INTEGER is not given, 1 is assumed.')
            (default None).

        Returns
        -------
        method
            The command-style method with help-message code added.

        """
        # pylint: disable=no-self-argument; it can't be an instance method
        # and it can't (without unnecessary complexity) be static---and nor
        # should it since the decorator only targets private methods
        def _cmdhelp_decorator(cmd_func):

            def _decorator(self, argv, print_help=0):
                if print_help == 1:
                    print(overview_msg)
                    return self.Status.OK
                elif print_help == 2:
                    print(overview_msg)
                    print('Usage:', usage_msg)
                    if extra_msg:
                        print()
                        self.printwrap(extra_msg)
                    return self.Status.OK
                status = cmd_func(self, argv)
                return status

            return wraps(cmd_func)(_decorator)

        return _cmdhelp_decorator


    @cmdhelp('Set breakpoint at specified location.',
             'break ROW COL',
             'ROW COL indicates the location in the puzzle to break at once the value of the'\
             + ' cell at that location is known.')
    def _cmd_break(self, argv):
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
        # Note that the location is the user-specified, not the actual,
        # one. If the breakpoint already exists, overwrite it.
        self.breakpoints[(row, col)] = self.breakno

        print('Breakpoint {} at {}, {}'.format(self.breakno, row, col), end='')
        if self.puzzle.get_cell(actual_row, actual_col) != Board.BLANK:
            print(' (already passed)', end='')
        print('.')

        return status | self.Status.OK


    @cmdhelp('Save the current board state at a given or default label.',
             'checkpoint [CHECKPOINT]',
             'If CHECKPOINT is not given, the current move number will be used.'\
             + ' Anything after whitespace in CHECKPOINT is ignored.'\
             + ' Use "restart CHECKPOINT" to restore this state of the board.')
    def _cmd_checkpoint(self, argv):
        try:
            checkpoint = argv[1]
        except IndexError:
            # Default checkpoint label is the move number
            checkpoint = str(self.solver.move_count())

        try:
            moveno = self.checkpoints[checkpoint].move_count()
            print('Note: redefined from checkpoint at move {}.'.format(moveno))
        except KeyError:
            pass

        saved_solver = self.solver.duplicate()
        self.checkpoints[checkpoint] = saved_solver

        for checkpoint_arg_command in ['restart', 'delete checkpoints',
                                       'info checkpoints', 'print checkpoints']:
            # Add commands with custom checkpoint name to tab completion
            self._tabcmd.commands[checkpoint_arg_command + ' ' + checkpoint] = None

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

    @cmdhelp('Delete all or matching breakpoints.',
             'delete breakpoints [BREAKNO [BREAKNO ...]]',
             'BREAKNO can be a number or a hyphen-specified range. If not given, all breakpoints'\
             + ' will be deleted. The two commands "delete breakpoints BREAKNO" and'\
             + ' "delete BREAKNO" are equivalent; that is, the "breakpoints" is optional.')
    def _subcmd_delete_breakpoints(self, argv):
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
            # For Python 3 compatibility, make sure `items` is a list so
            # the dict it is drawn from can be modified while iterating
            for loc, loc_bno in list(self.breakpoints.items()):
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

    @cmdhelp('Delete all or matching checkpoints.',
             'delete checkpoints [CHECKPOINT [CHECKPOINT ...]]',
             'If no CHECKPOINT is given, all checkpoints will be deleted.')
    def _subcmd_delete_checkpoints(self, argv):
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
                for checkpoint_arg_command in ['restart', 'delete checkpoints',
                                               'info checkpoints', 'print checkpoints']:
                    # Delete commands with custom checkpoint name from tab
                    # completion
                    del self._tabcmd.commands[checkpoint_arg_command + ' ' + checkpoint]
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

    @cmdhelp('Delete all or matching user-defined candidates.',
             'delete marks [ROW COL [NUMBER [NUMBER ...]]]',
             'If ROW, COL, and one or more NUMBER are given, delete each valid NUMBER from'\
             + ' the user-defined candidate list for that location. If only ROW and COL are'\
             + ' given, delete all numbers from that list. If no arguments are given, delete'\
             + ' all marks.')
    def _subcmd_delete_marks(self, argv):
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


    @cmdhelp('Indicate the reason for the last move.',
             'explain')
    def _cmd_explain(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        status = self.Status.REPEAT

        move_type = self.solver.last_move_type()
        if move_type == Solver.MoveType.NONE:
            print('The initial board is given.')
            return status | self.Status.OK
        elif move_type == Solver.MoveType.GUESSED:
            print('A guess pulled from a solved version of the board.')
            return status | self.Status.OK

        # See if a simple last-blank-in-{row,column,box} explanation is
        # possible
        elimination_explanation = self._get_elimination_explanation()
        if elimination_explanation:
            print(elimination_explanation)
            return status | self.Status.OK
        elif move_type == Solver.MoveType.ELIMINATION:
            print('It was the only possible number for the location.')
            return status | self.Status.OK

        locations = set()

        # `move_type` can change when searching for reasons for manual move
        actual_move_type_is_manual = (move_type == Solver.MoveType.MANUAL)
        if actual_move_type_is_manual:
            # See if manual move is explainable by known deductive methods
            max_locations = 0
            for deductive_type in Solver.DEDUCTIVE_MOVE_TYPES:
                #TODO: max reasons does not necessarily equal best
                # explanation: a single location may make nonviable all
                # other locations in a box, whereas two location may make
                # nonviable less than all locations in a column or row
                possible_reasons = self.solver.reasons(override_move_type=deductive_type)
                if len(possible_reasons) > max_locations:
                    # Try to find explanation with most locations (NB: this
                    # means the manual and deduced explanation may differ)
                    max_locations = len(possible_reasons)
                    locations = possible_reasons
                    move_type = deductive_type
        else:
            locations = self.solver.reasons()

        if locations:
            if actual_move_type_is_manual:
                # Here `move_type` is the move type to be used in
                # interpreting the reasons found
                self.print_puzzle(move_type=move_type, locations=locations,
                                  treat_move_type_as_reason=True)
                print('Possible reasons for manual move.')
            else:
                # Here the move type to use for interpreting the reasons
                # will simply be `self.solver.last_move_type()`
                self.print_puzzle(move_type=Solver.MoveType.REASON, locations=locations)

            return status | self.Status.OK

        #TODO: A manual move with no reasons except for its own location
        # (e.g., `MoveType.ELIMINATION`) should output this, not the board
        # with just the move itself highlighted
        print('No reason found for ', end='')
        print('{}move.'.format('manual ' if actual_move_type_is_manual else ''))
        return status | self.Status.OTHER

    def _get_elimination_explanation(self):
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

        return output


    @cmdhelp('Step until stuck or at solution or breakpoint.',
             'finish')
    def _cmd_finish(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
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
        for command_name in sorted(self.cmd.commands):
            command = self.cmd.commands[command_name]
            print('{} -- '.format(command_name), end='')
            command([], print_help=1)
        return status | self.Status.OK

    def _subcmd_help_delete(self, argv, print_help=0, print_title=False):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        return self._abstract_subcmd_help('delete', print_help=print_help, print_title=print_title)

    def _subcmd_help_help(self, argv, print_help=0, print_title=False):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        return self._abstract_subcmd_help('help', print_help=print_help, print_title=print_title)

    def _subcmd_help_info(self, argv, print_help=0, print_title=False):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        return self._abstract_subcmd_help('info', print_help=print_help, print_title=print_title)

    def _subcmd_help_print(self, argv, print_help=0, print_title=False):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        return self._abstract_subcmd_help('print', print_help=print_help, print_title=print_title)

    def _subcmd_help_set(self, argv, print_help=0, print_title=False):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
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

        for subcommand_name in sorted(self.cmd.commands):
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

    @cmdhelp('Show all or matching breakpoints.',
             'info break [BREAKNO [BREAKNO ...]]',
             'BREAKNO can be a number or a hyphen-specified range. If not given, all'\
             + ' breakpoints will be shown.')
    def _subcmd_info_breakpoints(self, argv):
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
                # str(bno) instead of just bno because strings left align,
                # numbers don't
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

    @cmdhelp('Show all or matching checkpoints.',
             'info checkpoint [CHECKPOINT [CHECKPOINT ...]]',
             'If no CHECKPOINT is given, the move numbers of all checkpoints will be shown.')
    def _subcmd_info_checkpoints(self, argv):
        checkpoints = argv[1:]
        if not checkpoints:
            # Since order cannot be taken from arg order, order by move number and then label
            # First sort labels so those with same moveno display in alphabetical order
            label_sorted_checks = sorted(self.checkpoints.items())
            checkpoints = sorted(label_sorted_checks, key=lambda x: x[1].move_count())
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

    @cmdhelp('Show all or matching user-defined candidates.',
             'info mark [ROW COL [ROW COL ...]]',
             'Show the candidates for each ROW COL location. If none given, show all'\
             + ' user-defined candidates.')
    def _subcmd_info_marks(self, argv):
        args = argv[1:]

        locations = []
        if args:
            # The locations will be validated manually below
            locations = self._get_locations(args, validate_cells=False)
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
                location_info = '{}, {}\t{}'.format(row, col, sorted(candidates))
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


    @cmdhelp('Mark one or more numbers as candidates for the given cell.',
             'mark ROW COL NUMBER [NUMBER ...]',
             'Add every valid NUMBER to a list of candidates for the location defined by ROW COL.'\
             + ' For viewing these candidates, see "print marks" and "info marks". For viewing'\
             + ' candidates set by the computer, see "print candidates" and "x".')
    def _cmd_mark(self, argv):
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

    @cmdhelp('Print board with generated candidates noted.',
             'print candidates')
    def _subcmd_print_candidates(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        candidate_map = {}
        for (actual_row, actual_col) in Board.SUDOKU_CELLS:
            candidate_map[(actual_row, actual_col)] = self.solver.candidates(actual_row,
                                                                             actual_col)
        self.print_puzzle(candidate_map=candidate_map)

        return self.Status.OK

    @cmdhelp('Print the state of the board at the given checkpoint.',
             'print checkpoint CHECKPOINT')
    def _subcmd_print_checkpoints(self, argv):
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

    @cmdhelp('Print board with user-defined candidates noted.',
             'print marks')
    def _subcmd_print_marks(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        self.print_puzzle(candidate_map=self.marks)
        return self.Status.OK

    # PRINT COMMANDS END


    @cmdhelp('Quit the solver.',
             'quit')
    def _cmd_quit(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        status = self.Status.REPEAT

        if self.puzzle.is_complete() and self.puzzle.is_consistent():
            return status | self.Status.QUIT

        print('The puzzle has not been solved.')
        if self._confirm('Quit anyway?'):
            return status | self.Status.QUIT
        return status | self.Status.OK

    @cmdhelp('Restart from beginning or from state at a given checkpoint.',
             'restart [CHECKPOINT]',
             'If CHECKPOINT is not given, restart from beginning. Note that the current board'\
             + ' state will be lost upon restarting unless it is also checkpointed. Use'\
             + ' "checkpoint" to define the checkpoint.')
    def _cmd_restart(self, argv):
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
            # The original solver can't be changed in case of another
            # restart here
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

    @cmdhelp('Toggle whether to use UTF-8 in output.',
             'set ascii')
    def _subcmd_set_ascii(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        ascii_mode = not self.options.ascii
        self.options.ascii = ascii_mode
        print('UTF-8 output {}.'.format('enabled' if not ascii_mode else 'disabled'))
        return self.Status.OK

    @cmdhelp('Toggle whether to break on guesses.',
             'set guessbreak')
    def _subcmd_set_guessbreak(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        guessbreak = not self.options.guessbreak
        self.options.guessbreak = guessbreak

        print('Break on guesses {}.'.format('enabled' if guessbreak else 'disabled'))
        return self.Status.OK

    @cmdhelp('Toggle whether to always print the board with marks noted.',
             'set markview')
    def _subcmd_set_markview(self, argv):
        # pylint: disable=unused-argument; argv included so every
        # `_cmd`-style method can be called in the same way
        markview = not self.options.markview
        self.options.markview = markview

        print('Always print marks {}.'.format('enabled' if markview else 'disabled'))
        return self.Status.OK

    @cmdhelp('Set the solver\'s prompt.',
             'set prompt PROMPT')
    def _subcmd_set_prompt(self, argv):
        args = argv[1:]
        prompt = ''.join(args)
        self.options.prompt = prompt
        return self.Status.OK

    @cmdhelp('Set the width to use for output.',
             'set width WIDTH',
             'Use 0 for the WIDTH to restore defaults.')
    def _subcmd_set_width(self, argv):
        args = argv[1:]

        try:
            width = int(args[0])
        except ValueError:
            print('Argument must be an integer.')
            return self.Status.OTHER
        except IndexError:
            print('One argument required.')
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


    @cmdhelp('Run commands from the given file.',
             'source FILE')
    def _cmd_source(self, argv):
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
            with open(filename, 'r') as source:
                self.command_queue.extend([line for line in source.read().split('\n') if line])
        except IOError as err:
            # pylint: disable=no-member; `strerror` as a `str` has `lower`
            print('Error reading "{}": {}.'.format(filename, err.strerror.lower()))
            return status | self.Status.OTHER

        return status | self.Status.OK


    # STEP COMMANDS START

    @cmdhelp('Step for one or more moves.',
             'step [INTEGER]',
             'Argument INTEGER means to step at most INTEGER times; if the solver becomes stuck'\
             + ' or arrives at a breakpoint first, it may stop earlier. If INTEGER is not given,'\
             + ' 1 is assumed.'\
             + ' Regardless of any ambiguity, "s" may be used for "step".')
    def _cmd_step(self, argv):
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


    @cmdhelp('Manually set cell at given location to given number.',
             'stepm ROW COL NUMBER',
             'The two commands "stepm ROW COL NUMBER" and "ROW COL NUMBER" are equivalent;'\
             + ' that is, the "stepm" is optional. Regardless of any ambiguity, "sm" may be'\
             + ' used for "stepm".')
    def _cmd_stepm(self, argv):
        args = argv[1:]

        move = ''.join(args)
        try:
            # Allow the arguments to be given by a single 3-digit number
            row, col, number = [int(digit) for digit in move][:3]
        except ValueError:
            if len(move) == 3:
                print('Arguments must be integers.')
            else:
                print('Three arguments required.')
            return self.Status.OTHER

        if not self._valid_cell(row, col):
            return self.Status.OTHER

        actual_row, actual_col = self._zero_correct(row, col)

        if not self.solver.step_manual(number, actual_row, actual_col):
            print('Move left board inconsistent. Ignored.')
            return self.Status.OTHER

        self.print_puzzle(move_type=Solver.MoveType.MANUAL, locations=[(actual_row, actual_col)])

        if self._is_breakpoint(row, col):
            return self.Status.BREAK

        return self.Status.OK

    @cmdhelp('Step for one or more moves in given box if possible.',
             'stepb BOX [INTEGER]',
             'Argument INTEGER means to step at most INTEGER times; if the solver becomes stuck'\
             + ' or arrives at a breakpoint first, it may stop earlier. If INTEGER is not given,'\
             + ' 1 is assumed.'\
             + ' Boxes are numbered from 1 to 9 starting with 1 in the top left box, moving from'\
             + ' left to right, and ending with 9 in the bottom right box.'\
             + ' Regardless of any ambiguity, "sb" may be used for "stepb".')
    def _cmd_stepb(self, argv):
        args = argv[1:]

        try:
            box_str = args[0]
            if len(box_str) > 1:
                # Interpret `stepb 82` as `stepb 8 2`
                repeat_arg = box_str[1:]
                args.insert(1, repeat_arg)
                box_str = box_str[0]
            box = int(box_str)
            assert Board.SUDOKU_ROWS == Board.SUDOKU_BOXES
            actual_box = self._zero_correct_row(box)
            if actual_box not in Board.SUDOKU_BOXES:
                raise ValueError
        except IndexError:
            print('Box argument required.')
            return self.Status.OTHER
        except ValueError:
            print('Invalid box {}'.format(box_str))
            return self.Status.OTHER

        cells = Board.cells_in_box(actual_box)
        return self._priority_step_backend(args, cells)

    @cmdhelp('Step for one or more moves in given column if possible.',
             'stepc COL [INTEGER]',
             'Argument INTEGER means to step at most INTEGER times; if the solver becomes stuck'\
             + ' or arrives at a breakpoint first, it may stop earlier. If INTEGER is not given,'\
             + ' 1 is assumed.'\
             + ' Regardless of any ambiguity, "sc" may be used for "stepc".')
    def _cmd_stepc(self, argv):
        args = argv[1:]

        try:
            col_str = args[0]
            if len(col_str) > 1:
                repeat_arg = col_str[1:]
                args.insert(1, repeat_arg)
                col_str = col_str[0]
            col = int(col_str)
            actual_col = self._zero_correct_column(col)
            if actual_col not in Board.SUDOKU_COLS:
                raise ValueError
        except IndexError:
            print('Column argument required.')
            return self.Status.OTHER
        except ValueError:
            print('Invalid column {}'.format(col_str))
            return self.Status.OTHER

        cells = Board.cells_in_column(actual_col)
        return self._priority_step_backend(args, cells)

    @cmdhelp('Step for one or more moves in given row if possible.',
             'stepr ROW [INTEGER]',
             'Argument INTEGER means to step at most INTEGER times; if the solver becomes stuck'\
             + ' or arrives at a breakpoint first, it may stop earlier. If INTEGER is not given,'\
             + ' 1 is assumed.'\
             + ' Regardless of any ambiguity, "sr" may be used for "stepr".')
    def _cmd_stepr(self, argv):
        args = argv[1:]

        try:
            row_str = args[0]
            if len(row_str) > 1:
                repeat_arg = row_str[1:]
                args.insert(1, repeat_arg)
                row_str = row_str[0]
            row = int(row_str)
            actual_row = self._zero_correct_row(row)
            if actual_row not in Board.SUDOKU_ROWS:
                raise ValueError
        except IndexError:
            print('Row argument required.')
            return self.Status.OTHER
        except ValueError:
            print('Invalid row {}'.format(row_str))
            return self.Status.OTHER

        cells = Board.cells_in_row(actual_row)
        return self._priority_step_backend(args, cells)

    def _priority_step_backend(self, args, priority_cells):
        status = self.Status.REPEAT

        args[0] = 'step'
        repeats = self._get_repeats(args)
        args = args[:1]

        # Save original `step_order`
        saved_step_order = self.solver.step_order.copy()
        self.solver.prioritize_cells(priority_cells)

        for _ in range(repeats):
            # Avoid getting hung up on cached moves outside of location
            self.solver.flush_step_cache()
            status = status | self._cmd_step(args)
            # pylint: disable=superfluous-parens; parens for clarity
            if not (status & self.Status.OK):
                break

        # Restore original `step_order`
        self.solver.step_order = saved_step_order

        return status | self.Status.OK


    @cmdhelp('Undo one or more steps.',
             'unstep [INTEGER]',
             'Argument INTEGER means to unstep the last [INTEGER] steps. If not given, 1 is'\
             + ' assumed. This works on all step variants. Note that unstepping does not'\
             + ' trigger breakpoints.')
    def _cmd_unstep(self, argv):
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


    @cmdhelp('Examine the generated candidates at one or more locations.',
             'info ROW COL [ROW COL ...]',
             'See also "print candidates" for displaying all generated candidates inline.'\
             + ' Note that these candidates are distinct from those set via the "mark" command.')
    def _cmd_x(self, argv):
        status = self.Status.REPEAT
        args = argv[1:]

        # Manual validation of locations is done below
        locations = self._get_locations(args, validate_cells=False)
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
                location_info = '{}, {}\t{}'.format(row, col, sorted(candidates))
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

    def _confirm(self, message):
        confirmation_message = '{} (y or n) '.format(message)

        if self.options.assume_yes:
            print('{}[assumed Y]'.format(confirmation_message))
            return True

        while True:
            try:
                confirm = input(confirmation_message).lower()
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


    @staticmethod
    def _valid_cell(row, col):
        actual_row, actual_col = SolverController._zero_correct(row, col)

        if actual_row not in Board.SUDOKU_ROWS:
            print('Invalid row {0} in ({0}, {1}).'.format(row, col))
            return False
        if actual_col not in Board.SUDOKU_COLS:
            print('Invalid column {1} in ({0}, {1}).'.format(row, col))
            return False

        return True


    @staticmethod
    def _zero_correct(row, col, inverted=False):
        actual_row = SolverController._zero_correct_row(row, inverted=inverted)
        actual_col = SolverController._zero_correct_column(col, inverted=inverted)
        return actual_row, actual_col

    @staticmethod
    def _zero_correct_row(row, inverted=False):
        actual_row = row
        if Board.SUDOKU_ROWS[0] == 0:
            actual_row += -1 if not inverted else 1
        return actual_row

    @staticmethod
    def _zero_correct_column(col, inverted=False):
        actual_col = col
        if Board.SUDOKU_COLS[0] == 0:
            actual_col += -1 if not inverted else 1
        return actual_col


    @staticmethod
    def _get_repeats(argv):
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

    @staticmethod
    def _get_locations(args, validate_cells=True):
        try:
            locations = ''.join(args)
            if len(locations) < 2:
                print('Too few arguments.')
                return None
            possible_rows = [int(r) for r in locations[::2]]
            possible_cols = [int(c) for c in locations[1::2]]
            locations = list(zip(possible_rows, possible_cols))
            for (row, col) in locations:
                if validate_cells and not SolverController._valid_cell(row, col):
                    return None
            return locations
        except ValueError:
            print('Location arguments must be integer pairs.')
            return None

    @staticmethod
    def _get_numbers(args, sudoku_numbers=False):
        numbers = []

        for arg in args:
            try:
                if '-' in arg:
                    min_num, max_num = [int(n) for n in arg.split('-')]
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

    @staticmethod
    def _get_locations_and_numbers(args, validate_cells=True):
        new_args = [''.join(list(tup)) for tup in re.findall(r'(.-.)|(.)', ''.join(args))]

        try:
            locations = SolverController._get_locations(new_args[:2],
                                                        validate_cells=validate_cells)
            row, col = locations[0]
        except TypeError:
            # _get_locations returned None
            return None

        numbers = SolverController._get_numbers(new_args[2:], sudoku_numbers=True)

        return row, col, numbers
