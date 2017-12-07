# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""The module containing the Solver class.

"""
from __future__ import absolute_import, division, print_function

from collections import namedtuple, OrderedDict
import itertools
from enum import IntEnum, unique

from sudb.board import Board


class Solver(object):
    """A 9x9 Sudoku solver with a move history.

    Parameters
    ----------
    puzzle : Board instance
        The puzzle board to use in the solver.

    Attributes
    ----------
    MoveType : class
        A class containing constants for labeling the type of a move.
    Move : namedtuple
        A namedtuple with the following fields: number (the value put in
        the cell in this move), row (the row of the cell), column (the
        column of the cell), replaced (the value in the cell before this
        move), and move_type (the MoveType constant associated with the
        move).
    DEDUCTIVE_MOVE_TYPES : list of MoveType constant
        A list of MoveType constants that indicate a deduced move.
    puzzle : Board instance
        The puzzle board to solve.
    solved_puzzle : Board instance
        The solved version of `puzzle` from which to draw guesses.
    move_history : list of namedtuple
        A list of Move namedtuples describing the moves made in order from
        oldest to latest.
    step_order : OrderedDict of int tuple to None
        An OrderedDict mapping (row, column) locations to None; `step` will
        attempt deductions proceeding backwards starting from the location
        at the end of this dict.

    """
    @unique
    class MoveType(IntEnum):
        """Constants for labeling the type of a move.

        Attributes
        ----------
        NONE : int
            No move type.
        ROWWISE : int
            A deductive move type based on a number having only one viable
            location in a row.
        COLWISE : int
            A deductive move type based on a number having only one viable
            location in a column.
        BOXWISE : int
            A deductive move type based on a number having only one viable
            location in a box.
        ELIMINATION : int
            A deductive move type based on a location having only one
            viable number.
        GUESSED : int
            A move type for a move that was not deduced (and not manually
            made).
        MANUAL : int
            A move type for manual moves.
        CORRECTED : int
            A relative move type indicating the move corrects some other
            move.
        REASON : int
            A relative move type indicating the move makes necessary some
            other move.
        DIFFERENCE : int
            A relative move type indicating the move, while not necessarily
            correcting some other move, does differ from it.

        Notes
        -----
        While `MoveType = IntEnum('MoveType, ['NONE', ...]', start=0)`
        would be more concise, it will make Pylint complain whenever any
        member of `MoveType` is referenced, and it is more convoluted to
        document.

        """
        NONE = 0
        ROWWISE = 1
        COLWISE = 2
        BOXWISE = 3
        ELIMINATION = 4
        GUESSED = 5
        MANUAL = 6
        CORRECTED = 7
        REASON = 8
        DIFFERENCE = 9

    Move = namedtuple('Move', 'number row column replaced move_type')

    DEDUCTIVE_MOVE_TYPES = [MoveType.ROWWISE, MoveType.COLWISE, MoveType.BOXWISE,
                            MoveType.ELIMINATION]


    def __init__(self, puzzle):
        assert isinstance(puzzle, Board)
        # Other methods rely on these assumptions
        assert Board.SUDOKU_ROWS == Board.SUDOKU_COLS
        assert Board.SUDOKU_ROWS == Board.SUDOKU_BOXES

        self.puzzle = puzzle
        self.solved_puzzle = None
        self.move_history = []

        # For fast, key-based delete and append
        self.step_order = OrderedDict()
        # `step` iterates through `step_order` in reverse
        for row, col in reversed(Board.SUDOKU_CELLS):
            # The value doesn't matter; `step_order` is used like an
            # ordered set
            self.step_order[(row, col)] = None

        self._necessary_move_cache = {}
        self._puzzle_hash_cache = None

    def __key(self):
        return (hash(self.puzzle), hash(self.solved_puzzle), hash(tuple(self.move_history)),
                hash(tuple(self.step_order)))

    def __eq__(self, other):
        # pylint: disable=protected-access
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.__key())


    def duplicate(self):
        """Return a duplicate of the solver instance.

        Returns
        -------
        Solver instance
            An instance identical to this instance except with its own
            unique copies of objects.

        """
        new_puzzle = self.puzzle.duplicate()
        new_solver = Solver(new_puzzle)
        if self.solved_puzzle:
            new_solver.solved_puzzle = self.solved_puzzle.duplicate()
        new_solver.move_history = self.move_history[:]
        new_solver.step_order = self.step_order.copy()
        return new_solver


    def move_count(self):
        """Return the number of moves taken so far.

        Returns
        -------
        int

        """
        return len(self.move_history)


    def annotated_moves(self):
        """Return a list of all moves in order with each's move type noted.

        Returns
        -------
        list of tuple
            A list with tuples of the form (number, row, column, type),
            where row, column are ints that give a location in `puzzle`,
            number is an int that gives the value that location was
            assigned, and type is a MoveType constant describing what type
            of move this one was (e.g., normal, guessed, or manual).

        """
        moves = []
        for (num, row, col, _, move_type) in self.move_history:
            moves.append((num, row, col, move_type))
        return moves

    def moves(self):
        """Return a list of all moves made ordered from first to last.

        Returns
        -------
        list of int tuple
            A list with tuples of the form (number, row, column), where
            row, column is a location in `puzzle` and number is the value
            that location was assigned.

        """
        moves = []
        for (num, row, col, _, _) in self.move_history:
            moves.append((num, row, col))
        return moves

    def deduced_moves(self):
        """Return a list of all deduced moves ordered from first to last.

        Returns
        -------
        list of int tuple
            A list with tuples of the form (number, row, column), where
            row, column is a location in `puzzle` and number is the value
            that location was assigned based on a deduction.

        """
        return self._filtered_moves(self.DEDUCTIVE_MOVE_TYPES)

    def guessed_moves(self):
        """Return a list of all guessed moves ordered from first to last.

        Returns
        -------
        list of int tuple
            A list with tuples of the form (number, row, column), where
            row, column is a location in `puzzle` and number is the value
            that location was assigned based on a hypothesis.

        """
        move_types = [self.MoveType.GUESSED]
        return self._filtered_moves(move_types)

    def manual_moves(self):
        """Return a list of all guessed moves ordered from first to last.

        Returns
        -------
        list of int tuple
            A list with tuples of the form (number, row, column), where
            row, column is a location in `puzzle` and number is the value
            that location was assigned manually (e.g., via a call to
            `step_manual`).

        """
        move_types = [self.MoveType.MANUAL]
        return self._filtered_moves(move_types)

    def _filtered_moves(self, target_types):
        moves = []
        for (num, row, col, _, move_type) in self.move_history:
            if move_type in target_types:
                moves.append((num, row, col))
        return moves


    def last_move_type(self):
        """Return the type of the last move made.

        Returns
        -------
        MoveType constant
            The move type associated with the last move made (MoveType.NONE
            if no move has been made).

        """
        if self.move_count() == 0:
            return self.MoveType.NONE
        return self.move_history[-1].move_type


    def prioritize_row(self, row):
        """Prioritize the cells in the given row when stepping.

        Parameters
        ----------
        row : int
            The row to prioritize, which must be in `Board.SUDOKU_ROWS`.

        Raises
        ------
        ValueError
            When `row` is not in `Board.SUDOKU_ROWS`.

        """
        self.prioritize_cells(Board.cells_in_row(row))

    def prioritize_column(self, col):
        """Prioritize the cells in the given column when stepping.

        Parameters
        ----------
        col : int
            The column to prioritize, which must be in `Board.SUDOKU_COLS`.

        Raises
        ------
        ValueError
            When `col` is not in `Board.SUDOKU_COLS`.

        """
        self.prioritize_cells(Board.cells_in_column(col))

    def prioritize_box(self, box):
        """Prioritize the cells in the given box when stepping.

        Parameters
        ----------
        box : int
            The box to prioritize, which must be `Board.SUDOKU_BOXES`.

        Raises
        ------
        ValueError
            When `box` is not in `Board.SUDOKU_BOXES`.

        """
        self.prioritize_cells(Board.cells_in_box(box))

    def prioritize_cells(self, cells):
        """Prioritize the given cells when stepping.

        Parameters
        ----------
        cells : iterable of int tuple
            An iterable of (row, column) locations to prioritize, which
            each must be in `Board.SUDOKU_CELLS`.

        Raises
        ------
        ValueError
            When an int tuple in `cells` is not in `Board.SUDOKU_CELLS`.

        """
        for location in reversed(cells):
            if location not in Board.SUDOKU_CELLS:
                raise ValueError('invalid location {}'.format(location))
            del self.step_order[location]
            # Add to end of dict (which is where `step` starts)
            self.step_order[location] = None


    def autosolve(self, allow_guessing=True):
        """Solve the puzzle while maintaining a move history.

        Attempt to solve the puzzle first using deduction and, if that
        proves insufficient, using guesses drawn from the solved board.

        Parameters
        ----------
        allow_guessing : bool, optional
            False if all moves should be deduced or True if some may be
            guessed (i.e., pulled from a version of the board solved by
            non-deductive means) (default True).

        Returns
        -------
        bool
            True if `puzzle` was successfully solved, and False if not.

        """
        self.step_until_stuck()
        # The solver can't make an inconsistent move, so only completion
        # needs to be checked
        solved = self.puzzle.is_complete()

        while not solved:
            # If here, a guess is in order
            if not allow_guessing or not self.step_best_guess():
                # The last move can't be a guess, so if here is_complete()
                # would also be False
                return False
            self.step_until_stuck()
            solved = self.puzzle.is_complete()

        return True


    def step_until_stuck(self):
        """Step the puzzle until no new deductions can be made.

        Returns
        -------
        int
            The number of successful steps made before becoming stuck.

        """
        steps_made = 0
        stuck = False
        while not stuck:
            if not self.step():
                stuck = True
            else:
                steps_made += 1
        return steps_made

    def step(self):
        """Set a location in puzzle to its necessary value; return location.

        Change the value of a blank location in `puzzle` to the number it
        must assume and return that location or, if no such location found,
        an empty tuple.

        Returns
        -------
        int tuple
            The (row, column) location changed, or an empty tuple if
            nothing changed.

        See Also
        --------
        unstep : the undo method for this method.

        """
        if not self._necessary_move_cache_is_valid():
            # Start over clean in case here because
            # `self._puzzle_hash_cache` didn't match current hash: this
            # could be because the puzzle has been unstepped or clues have
            # otherwise been removed, so `self._necessary_move_cache` may
            # suggests deductions no longer necessary on the new board with
            # fewer clues; or it could be because a known clue was
            # overwritten or some other bad clue was added---too much can
            # go wrong to make flushing the cache conditionally worth it
            self.flush_step_cache()
            self._fill_necessary_move_cache()

        for row, col in reversed(self.step_order):
            try:
                number, move_type = self._necessary_move_cache[(row, col)]
                self._install_move(number, row, col, move_type)

                # Update row/column/boxes that the move may have affected
                box, _ = Board.box_containing_cell(row, col)
                self._fill_necessary_move_cache(rows=[row], columns=[col], boxes=[box])
                del self._necessary_move_cache[(row, col)]

                return (row, col)
            except KeyError:
                pass

        return ()

    def flush_step_cache(self):
        """Remove all cached necessary moves.

        Notes
        -----
        This, unlike other methods operating on `_necessary_move_cache`, is
        public because flushing the cache can be useful, for example, when
        trying to prevent `step` from getting hung up on cached moves while
        trying to prioritize some locations.

        """
        self._necessary_move_cache = {}

    def _necessary_move_cache_is_valid(self):
        if not self._necessary_move_cache:
            return False
        if self._puzzle_hash_cache != hash(self.puzzle):
            return False
        return True

    def _fill_necessary_move_cache(self, numbers=None, rows=None, columns=None, boxes=None):
        numbers = Board.SUDOKU_NUMBERS if numbers is None else numbers
        rows = Board.SUDOKU_ROWS if rows is None else rows
        columns = Board.SUDOKU_COLS if columns is None else columns
        boxes = Board.SUDOKU_BOXES if boxes is None else boxes

        for number in numbers:
            columns_to_skip = set()
            boxes_to_skip = set()

            for row in rows:
                locations = self.possible_locations_in_row(number, row)
                if len(locations) == 1:
                    move_row, move_col = locations.pop()
                    move_type = self.MoveType.ROWWISE
                    self._necessary_move_cache[(move_row, move_col)] = (number, move_type)
                    columns_to_skip.add(move_col)
                    box, _ = Board.box_containing_cell(move_row, move_col)
                    boxes_to_skip.add(box)

            for col in columns:
                if col in columns_to_skip:
                    continue
                locations = self.possible_locations_in_column(number, col)
                if len(locations) == 1:
                    move_row, move_col = locations.pop()
                    move_type = self.MoveType.COLWISE
                    self._necessary_move_cache[(move_row, move_col)] = (number, move_type)
                    box, _ = Board.box_containing_cell(move_row, move_col)
                    boxes_to_skip.add(box)

            for box in boxes:
                if box in boxes_to_skip:
                    continue
                locations = self.possible_locations_in_box(number, box)
                if len(locations) == 1:
                    move_row, move_col = locations.pop()
                    move_type = self.MoveType.BOXWISE
                    self._necessary_move_cache[(move_row, move_col)] = (number, move_type)

        cells = set(itertools.product(rows, columns))
        for box in boxes:
            cells = cells.union(set(Board.cells_in_box(box)))

        for (row, col) in cells:
            if self.puzzle.get_cell(row, col) != Board.BLANK:
                continue

            possibilities = self.puzzle.possibilities(row, col)
            if len(possibilities) == 1:
                move_type = self.MoveType.ELIMINATION
                number = possibilities.pop()
                # Even if already defined in cache, redefine to be of type
                # `ELIMINATION`
                self._necessary_move_cache[(row, col)] = (number, move_type)

        self._puzzle_hash_cache = hash(self.puzzle)

    def _install_move(self, number, row, col, move_type):
        replaced = self.puzzle.get_cell(row, col)
        self.puzzle.set_cell(number, row, col)
        move = self.Move(number, row, col, replaced, move_type)
        self.move_history.append(move)
        return (row, col)


    def unstep(self):
        """Restore that last stepped location; return location.

        Undo the move made in the last call to step and return the location
        of the reversion if successful or an empty tuple on failure (e.g.,
        if no moves left to unstep). If the location was replaced via a
        call to, for example, `step_manual`, it will be set to the number
        it had beforehand; otherwise, it will be set to a blank.

        Returns
        -------
        int tuple
            The (row, column) location changed, or an empty tuple if
            nothing changed.

        See Also
        --------
        step : the do method for this undo method.

        """
        if self.move_count() == 0:
            return ()

        (_, row, col, old_number, _) = self.move_history.pop()
        self.puzzle.set_cell(old_number, row, col)

        return (row, col)


    def step_manual(self, number, row, col):
        """Set the location in puzzle to a specified value; return location.

        Change the value of a location in `puzzle` specified by (`row`,
        `col`) to `number` and return that location.

        Parameters
        ----------
        number : int
            The value to set the cell at (`row`, `col`) to, which should be
            be in Board.SUDOKU_NUMBERS unless the value represents a blank,
            in which case, anything else will work, though 0 is preferred.
        row : int
            The row in `puzzle` to change, which must be in
            Board.SUDOKU_ROWS.
        col : int
            The column in `puzzle` to change, which must be in
            Board.SUDOKU_COLS.

        Returns
        -------
        int tuple
            The (row, column) location changed, or an empty tuple if no
            location changed (e.g., if the move would have left the board
            inconsistent).

        Raises
        ------
        ValueError
            When `row` or `col` is outside Board.SUDOKU_ROWS or
            Board.SUDOKU_COLS, respectively.

        See Also
        --------
        step : the automatic version of this method.

        """
        if row not in Board.SUDOKU_ROWS:
            raise ValueError('invalid row value {}'.format(row))
        if col not in Board.SUDOKU_COLS:
            raise ValueError('invalid column value {}'.format(col))

        replaced = self.puzzle.get_cell(row, col)
        self.puzzle.set_cell(number, row, col)
        if not self.puzzle.is_consistent():
            self.puzzle.set_cell(replaced, row, col)
            return ()

        move = self.Move(number, row, col, replaced, self.MoveType.MANUAL)
        self.move_history.append(move)

        return (row, col)


    def step_best_guess(self):
        """Set a location in puzzle to a guessed value; return location.

        Pick a blank location in `puzzle` such that knowing the value at
        that location allows for the most new deductions. Set that location
        to value it has in the solved puzzle, and return the location. If
        no guesses are left, return an empty tuple.

        Returns
        -------
        int tuple
            The (row, column) location changed, or an empty tuple if
            nothing changed.

        """
        guess = self.best_guess()
        if not guess:
            return ()
        number, row, col = guess
        return self._install_move(number, row, col, self.MoveType.GUESSED)

    def best_guess(self):
        """Return the move that allows for the most new deductions.

        Consider all moves in the solved board not in the current board,
        and return the move whose addition to the latter allows for the
        greatest number of new deductions.

        Returns
        -------
        int tuple
            The (number, row, col) move opening the gates to the most new
            deductions, or an empty tuple if none found.

        """
        if self.solved_puzzle is None:
            # This method pulls guesses from a solved version of the puzzle
            self.solved_puzzle = self.puzzle.duplicate()
            subsolver = Solver(self.solved_puzzle)
            if not subsolver.autosolve_without_history():
                return ()

        move_of_max_progress = ()
        max_step_progress = 0
        possible_locations = self.puzzle.differences(self.solved_puzzle)
        subsolver = Solver(self.puzzle.duplicate())

        for (row, col) in possible_locations:
            number = self.solved_puzzle.get_cell(row, col)
            subsolver.step_manual(number, row, col)
            steps_made = subsolver.step_until_stuck()
            if steps_made > max_step_progress:
                max_step_progress = steps_made
                move_of_max_progress = (number, row, col)
            # Undo all automatic steps and the one manual one
            for _ in range(steps_made+1):
                subsolver.unstep()

        return move_of_max_progress


    def possible_next_moves(self):
        """Return viable moves reachable in one step from current board.

        Returns
        -------
        dict of int tuple to set
            A mapping of (row, col) locations to the set of numbers that
            could be placed at those locations without leaving the board in
            an inconsistent state.

        """
        next_moves = {location: set() for location in Board.SUDOKU_CELLS}

        for number in Board.SUDOKU_NUMBERS:
            locations_for_number = set()

            for row in Board.SUDOKU_ROWS:
                locations = self.possible_locations_in_row(number, row)
                locations_for_number = locations_for_number.union(locations)

            for col in Board.SUDOKU_COLS:
                locations = self.possible_locations_in_column(number, col)
                locations_for_number = locations_for_number.union(locations)

            for box in Board.SUDOKU_BOXES:
                locations = self.possible_locations_in_box(number, box)
                locations_for_number = locations_for_number.union(locations)

            for (row, col) in locations_for_number:
                next_moves[(row, col)].add(number)

        return next_moves


    def possible_locations_in_box(self, number, box):
        """Return viable locations for number in a specified box.

        Parameters
        ----------
        number : int
            The value in Board.SUDOKU_NUMBERS to attempt to find viable
            locations in the box for.
        box : int
            The box to try placing `number` in, which must be in
            Board.SUDOKU_BOXES.

        Returns
        -------
        set of int tuple
            A set of (row, column) locations in the `box` where `number`
            could be placed in `puzzle` without making the board
            inconsistent.

        Raises
        ------
        ValueError
            When `number` is not in Board.SUDOKU_NUMBERS or `box` is not in
            Board.SUDOKU_BOXES.

        """
        if number not in Board.SUDOKU_NUMBERS:
            min_val, max_val = min(Board.SUDOKU_NUMBERS), max(Board.SUDOKU_NUMBERS)
            raise ValueError('number must be between {} and {} inclusive'.format(min_val, max_val))

        if box not in Board.SUDOKU_BOXES:
            min_val, max_val = min(Board.SUDOKU_BOXES), max(Board.SUDOKU_BOXES)
            raise ValueError('box must be between {} and {} inclusive'.format(min_val, max_val))

        possible_locations = set()

        rows = self.puzzle.rows()
        columns = self.puzzle.columns()

        for (row, col) in Board.cells_in_box(box):
            cell_number = self.puzzle.get_cell(row, col)
            if cell_number == Board.BLANK:
                if number not in rows[row] and number not in columns[col]:
                    possible_locations.add((row, col))
            elif cell_number == number:
                # Number already in box
                return set()

        return possible_locations

    def possible_locations_in_row(self, number, row):
        """Return viable locations for number in a specified row.

        Parameters
        ----------
        number : int
            The value in Board.SUDOKU_NUMBERS to attempt to find viable
            locations in the row for.
        row : int
            The row to try placing `number` in, which must be in
            Board.SUDOKU_ROWS.

        Returns
        -------
        set of int tuple
            A set of (row, column) locations in the `row` where `number`
            could be placed in `puzzle` without making the board
            inconsistent.

        Raises
        ------
        ValueError
            When `number` is not in Board.SUDOKU_NUMBERS or `row` is not in
            Board.SUDOKU_ROWS.

        See Also
        --------
        possible_locations_in_column : the column version of this method
        _possible_locations_in_line : the backend for this method

        """
        return self._possible_locations_in_line(number, row, True)

    def possible_locations_in_column(self, number, col):
        """Return viable locations for number in a specified column.

        Parameters
        ----------
        number : int
            The value in Board.SUDOKU_NUMBERS to attempt to find viable
            locations in the row for.
        col : int
            The column to try placing `number` in, which must be in
            Board.SUDOKU_COLS.

        Returns
        -------
        set of int tuple
            A set of (row, column) locations in the `col` where `number`
            could be placed in `puzzle` without making the board
            inconsistent.

        Raises
        ------
        ValueError
            When `number` is not in Board.SUDOKU_NUMBERS or `col` is not in
            Board.SUDOKU_COLS.

        See Also
        --------
        possible_locations_in_row : the row version of this method
        _possible_locations_in_line : the backend for this method

        """
        return self._possible_locations_in_line(number, col, False)

    def _possible_locations_in_line(self, number, line, rowwise):
        if number not in Board.SUDOKU_NUMBERS:
            min_val, max_val = min(Board.SUDOKU_NUMBERS), max(Board.SUDOKU_NUMBERS)
            raise ValueError('number must be between {} and {} inclusive'.format(min_val, max_val))

        if rowwise:
            if line not in Board.SUDOKU_ROWS:
                min_val, max_val = min(Board.SUDOKU_ROWS), max(Board.SUDOKU_ROWS)
                raise ValueError('row must be between {} and {} inclusive'.format(min_val,
                                                                                  max_val))
            chosen_line = self.puzzle.rows()[line]
            other_lines = self.puzzle.columns()
        else:
            if line not in Board.SUDOKU_COLS:
                min_val, max_val = min(Board.SUDOKU_COLS), max(Board.SUDOKU_COLS)
                raise ValueError('column must be between {} and {} inclusive'.format(min_val,
                                                                                     max_val))
            chosen_line = self.puzzle.columns()[line]
            other_lines = self.puzzle.rows()

        possible_locations = set()
        if number in chosen_line:
            # Number already in row
            return possible_locations

        boxes = self.puzzle.boxes()
        for other, value in enumerate(chosen_line):
            location = (line, other) if rowwise else (other, line)
            box, _ = self.puzzle.box_containing_cell(*location)
            if value == 0 and number not in other_lines[other] and number not in boxes[box]:
                # Number is blank and not already in other line (row or
                # col) or box
                possible_locations.add(location)

        return possible_locations


    def candidates(self, row, col):
        """Return all viable numbers for the location based on analysis.

        Parameters
        ----------
        row : int
            The row of the cell to find candidates for.
        col : int
            The column of the cell to find candidates for.

        Returns
        -------
        set of int
            The set of numbers that could be placed at the cell at `row`,
            `col` without leaving the board inconsistent or contradicting
            other information about the puzzle gleaned from analysis; if
            the given location already has a number in its cell, that
            number alone will be in the returned set.

        """
        if not self._necessary_move_cache_is_valid():
            self.flush_step_cache()
            self._fill_necessary_move_cache()

        try:
            number, _ = self._necessary_move_cache[(row, col)]
            return {number}
        except KeyError:
            number = self.puzzle.get_cell(row, col)
            if number != Board.BLANK:
                return {number}
            return self.possible_next_moves()[(row, col)]


    def reasons(self, override_move_type=None):
        """Return a set of locations that necessitated the last move.

        Parameters
        ----------
        override_move_type : MoveType constant, optional
            A MoveType constant to use in place of the actual move type,
            which can be used to find reasons for move types that cannot
            otherwise be explained (e.g., MoveType.MANUAL) (default None).

        Returns
        -------
        set of int tuple
            The (row, column) locations that prevented the number in the
            last move from being placed at any row or column but the one it
            ended up in.

        """
        move_type = self.last_move_type() if override_move_type is None else override_move_type

        if move_type not in self.DEDUCTIVE_MOVE_TYPES:
            # No moves, or the move type is itself the reason for the move
            return set()
        # `move_type` would have been MoveType.NONE if no moves
        number, move_row, move_col, _, _ = self.move_history[-1]

        reasons_for_last_move = set()
        rows = self.puzzle.rows()
        columns = self.puzzle.columns()
        boxes = self.puzzle.boxes()

        if move_type == self.MoveType.ROWWISE:
            chosen_line = rows[move_row]
            other_lines = columns
            rowwise = True
        elif move_type == self.MoveType.COLWISE:
            chosen_line = columns[move_col]
            other_lines = rows
            rowwise = False
        elif move_type == self.MoveType.BOXWISE:
            move_box, _ = Board.box_containing_cell(move_row, move_col)
            for (row, col) in Board.cells_in_box(move_box):
                if self.puzzle.get_cell(row, col) != Board.BLANK:
                    continue

                if number in rows[row]:
                    associated_col = rows[row].index(number)
                    reasons_for_last_move.add((row, associated_col))

                if number in columns[col]:
                    associated_row = columns[col].index(number)
                    reasons_for_last_move.add((associated_row, col))
            # Remove location of move from set if its in there
            reasons_for_last_move -= {(move_row, move_col)}
            return reasons_for_last_move
        elif move_type == self.MoveType.ELIMINATION:
            # Return move itself to indicate number was only viable one for
            # location
            return {(move_row, move_col)}
        else:
            # This should never occur
            raise NotImplementedError('no code to handle deductive move type {}'.format(move_type))

        for other, value in enumerate(chosen_line):
            location = (move_row, other) if rowwise else (other, move_col)
            box, _ = self.puzzle.box_containing_cell(*location)
            if value == 0:
                if number in other_lines[other]:
                    index_in_other = other_lines[other].index(number)
                    other_cell = (index_in_other, other) if rowwise else (other, index_in_other)
                    reasons_for_last_move.add(other_cell)
                if number in boxes[box]:
                    boxes_i = boxes[box].index(number)
                    row_in_box = 3 * (box // 3) + boxes_i // 3
                    col_in_box = 3 * (box % 3) + boxes_i % 3
                    reasons_for_last_move.add((row_in_box, col_in_box))

        reasons_for_last_move = reasons_for_last_move - set([(move_row, move_col)])

        return reasons_for_last_move


    def all_solutions(self, algorithm=None):
        """Yield each solution to the puzzle.

        Yield each solution without keeping a move history or altering the
        current state of the board.

        Parameters
        ----------
        algorithm : str, optional
            The name of the algorithm to use to find the solutions (if an
            invalid or no name is specified, Algorithm X is used.)

        Yields
        ------
        Board instance
            A board representing a solution to the puzzle.

        """
        if algorithm and algorithm == 'backtrack':
            temp_puzzle = self.puzzle.duplicate()
            # Force `_backtrack` to have a stable yield order for
            # consistency with `_algorithm_x`
            for puzzle in self._backtrack(puzzle=temp_puzzle, stable_yield_order=True):
                yield puzzle
        else:
            seen_puzzles = {}
            # `_algorithm_x` always has a stable yield order
            for puzzle in self._algorithm_x():
                try:
                    seen_puzzles[puzzle]
                except KeyError:
                    seen_puzzles[puzzle] = True
                    yield puzzle

    def solution_count(self, algorithm=None, limit=0):
        """Return the number of solutions possible for the puzzle.

        Count the number of solutions the puzzle has without keeping a move
        history or altering the current state of the board.

        Parameters
        ----------
        algorithm : str, optional
            The name of the algorithm to use to find the solutions (if an
            invalid or no name is specified, Algorithm X is used).
        limit : int, optional
            The number of solutions after which no additional solutions
            should be sought, where 0 represents no limit (default 0).

        Returns
        -------
        int
            The number of solutions possible for the puzzle (a proper
            puzzle will have only one).

        """
        count = 0

        if algorithm and algorithm == 'backtrack':
            # The backtrack algorithm used never returns duplicates so this
            # code can be simpler than the algorithm X version
            temp_puzzle = self.puzzle.duplicate()
            # Turn off `stable_yield_order` to speed up calculation since
            # we only care about the number, not the order, yielded anyway
            for _ in self._backtrack(puzzle=temp_puzzle, stable_yield_order=False):
                count += 1
                if limit and count == limit:
                    return limit
        else:
            col_dict = self._puzzle_constraint_subsets()
            row_dict = self._puzzle_universe(col_dict)
            solution = []
            # The moves can be the same, but in different order
            unique_hitting_sets = set()
            for hitting_set in self._exact_hitting_set(col_dict, row_dict, solution):
                unique_hitting_sets.add(tuple(sorted(hitting_set)))
                if limit and len(unique_hitting_sets) == limit:
                    return limit
            count = len(unique_hitting_sets)

        return count


    def autosolve_without_history(self, algorithm=None):
        """Quickly solve the puzzle by not keeping a move history.

        Solve the puzzle using means other than those available to human
        solvers, with the downside that the solver instance will be unable
        to report what deductive steps a human could take to solve the
        puzzle for themselves.

        Parameters
        ----------
        algorithm : str, optional
            The name of the algorithm to use to find the solution (if an
            invalid or no name is specified, Algorithm X is used.)

        Returns
        -------
        bool
            True if `puzzle` was successfully solved, and False if not.

        Notes
        -----
        Algorithm X is the default because it tends to be faster than
        backtracking, and the time it does take tends to be similar for
        most boards.

        """
        if algorithm and algorithm == 'backtrack':
            return self._solve_backtrack()
        return self._solve_algorithm_x()


    def _solve_backtrack(self):
        """Solve the puzzle using backtracking.

        Returns
        -------
        bool
            True if `puzzle` was successfully solved, and False if not.

        See Also
        --------
        _backtrack : the backend for this method.

        """
        # Use `stable_yield_order` to guarantee the same puzzle is copied
        # if more than one solution exists
        for puzzle in self._backtrack(stable_yield_order=True):
            self.puzzle.copy(puzzle)
            return self.puzzle.is_complete() and self.puzzle.is_consistent()
        return False

    def _backtrack(self, puzzle=None, row=0, col=0, stable_yield_order=False):
        if puzzle is None:
            puzzle = self.puzzle.duplicate()

        if col > 8:
            row += 1
            col = 0

        if row > 8:
            yield puzzle.duplicate()
        else:
            possible_numbers = puzzle.possibilities(row, col)
            if not possible_numbers:
                yield None
            elif stable_yield_order:
                # Guarantee iteration order over (by definition, unordered)
                # set by converting to sorted list
                possible_numbers = sorted(possible_numbers)

            for num in possible_numbers:
                original_num = puzzle.get_cell(row, col)
                puzzle.set_cell(num, row, col)
                for new_puzzle in self._backtrack(puzzle=puzzle, row=row, col=col+1,
                                                  stable_yield_order=stable_yield_order):
                    if new_puzzle:
                        yield new_puzzle
                puzzle.set_cell(original_num, row, col)


    def _solve_algorithm_x(self):
        """Solve the puzzle using Algorithm X.

        Returns
        -------
        bool
            True if `puzzle` was successfully solved, and False if not.

        Notes
        -----
        This method solves the puzzle by treating it as a variant of the
        exact cover problem known as the exact hitting set problem. The
        idea is that you have some universe and a collection of subsets
        of that universe, and you want to find the exact hitting set, that
        is, the subset of that universe whose intersection with any given
        subset from the collection is a set with a single element. In other
        word, each subset in the collection contains exactly one element
        that is in the exact hitting set.

        So for Sudoku, assume you have a universe specifying all possible
        numbers at all possible cells in a Sudoku board. For example, 321
        might be an element in that universe representing the number 1 at
        row 3 and column 2. Then, for the collection, you have various
        subsets representing which cells, rows, columns, and boxes can
        contain a given element.

        Knowing that each set will ultimately get to have only one element
        in the hitting set, and remembering that each element in the set
        represents what number to place at what location, the types of
        subsets should be chosen such that the rules of Sudoku guarantee
        that only one number-location combination in each set can be
        valid---that way the hitting set will represent the solution to the
        puzzle.

        With this in mind, it is possible to select the subsets in the
        collection. First, since each row must contain each number but only
        once, all those subsets containing number-locations for a given row
        and given number (e.g., {321, 361, 371} for row 3 and number 1)
        should be included in the collection. Likewise, each column must
        contain each number just once, so subsets like {367, 467, 567, 867}
        for column 6 and number 7 should also be included. And, once again,
        because each box in the puzzle must contain each number once, all
        the subsets with number-locations for a given number and row/column
        combinations from a single box (e.g., {119, 329} for the number 9
        and the top left box) should be in the collection, too. Finally,
        though the rule would be easy to overlook, each cell can only
        contain a single number, so it makes sense to include a subset for
        each cell which lists what number-locations can be applied to it
        (e.g., {254, 257, 259} for the cell at row 2 and column 5).

        Once this collection of subsets has been generated for a particular
        puzzle (see `_puzzle_constraint_subsets` for details), the exact
        hitting set for the collection and universe is a set of what
        numbers go where in the puzzle---i.e., the solution to the puzzle.

        See Also
        --------
        _algorithm_x : the backend for this method.

        """
        for puzzle in self._algorithm_x():
            self.puzzle.copy(puzzle)
            return self.puzzle.is_complete() and self.puzzle.is_consistent()
        return False

    def _algorithm_x(self):
        col_dict = self._puzzle_constraint_subsets()
        row_dict = self._puzzle_universe(col_dict)
        solution = []

        for hitting_set in self._exact_hitting_set(col_dict, row_dict, solution):
            temp_puzzle = self.puzzle.duplicate()
            for possibility_code in hitting_set:
                row, col, num = [int(digit) for digit in possibility_code]
                temp_puzzle.set_cell(num, row, col)
            yield temp_puzzle

    def _exact_hitting_set(self, col_dict, row_dict, solution):
        """Yield all exact hitting sets for the given matrix.

        Yield the hitting sets for the matrix formed by the mutually
        referencing `col_dict` and `row_dict`, where `col_dict` is a
        mapping of set names (each heading a column) to a subset of
        elements from the universe and `row_dict` is a mapping of all
        elements from the universe (each heading a row) to a list of set
        names containing that element. In other words, if the two
        dictionaries are thought of as a matrix where 1 represents
        membership, `col_dict` maps a given column to all rows where the
        intersection is a 1, and `row_dict` maps a given row to all columns
        where the intersection is a 1.

        Parameters
        ----------
        col_dict : dict of str to set
            A mapping of a set name to a subset of the elements in the
            universe.
        row_dict : dict of str to set
            A mapping of an element from the universe to a list of set
            names whose corresponding set contains the element.
        solution : list of str
            A list of elements from the universe that is recursively
            constructed.

        Yields
        ------
        list of str
            A list of elements from the universe such that each subset
            defined in `col_dict` contains exactly one element in the list;
            N.B. that the lists yielded may be identical aside from the
            order of elements.

        See Also
        --------
        _delete_columns : helper method for deleting columns from
                          `col_dict`.
        _restore_columns : helper method for restoring columns deleted by
                           `_delete_columns` back into `col_dict`.

        Notes
        -----
        This implementation, along with its two helper methods for deleting
        and restoring columns, is Ali Assaf's implementation[1]_ of Knuth's
        Algorithm X with slightly more informative variable names and some
        comments. Also, some collections not sorted in the original are
        sorted here to help guarantee that the lists are always yielded in
        the same order.

        References
        ----------
        .. [1] Assaf, A. "Algorithm X in 30 lines!". Available at:
           http://www.cs.mcgill.ca/~aassaf9/python/algorithm_x.html
           [Accessed 23 Jun. 2017].

        """
        if not col_dict:
            # The last matrix had exactly one entry in every column
            yield list(solution)
        else:
            # Pick column with fewest members; the sort is needed to make
            # method always return lists in same order since without it
            # `min` may not always return the same value in case of ties
            set_id, _ = min(sorted(col_dict.items()), key=lambda pair: len(pair[1]))
            # Consider the rows in any order (where elem is an element from
            # the universe); sorted order is used so the order lists are
            # returned in doesn't vary from one call to another
            for elem in sorted(col_dict[set_id]):
                # Add row to partial solution list
                solution.append(elem)
                saved_columns = self._delete_columns(col_dict, row_dict, elem)
                # Try to solve reduced board
                for partial_solution in self._exact_hitting_set(col_dict, row_dict, solution):
                    # Branch succeeded
                    yield partial_solution
                # Branch failed, remove row from solutions, and restore
                # columns
                self._restore_columns(col_dict, row_dict, elem, saved_columns)
                solution.pop()

    @staticmethod
    def _delete_columns(col_dict, row_dict, chosen_row):
        columns_deleted = []
        # For each column asserted in the chosen row (sorted to guarantee
        # the order elements are added to `columns_deleted`)
        for col in sorted(row_dict[chosen_row]):
            # Consider all other rows where that column is also asserted
            for other_row in col_dict[col]:
                # Then consider each other asserted column in those rows
                for other_col in [c for c in row_dict[other_row] if c != col]:
                    # And delete any mention of that row (effectively
                    # deleting row)
                    col_dict[other_col].remove(other_row)
            # And lastly delete the column itself
            columns_deleted.append(col_dict.pop(col))
        return columns_deleted

    @staticmethod
    def _restore_columns(col_dict, row_dict, chosen_row, columns_to_restore):
        # Iterate in the reverse of the order used in `_delete_columns`
        for col in reversed(sorted(row_dict[chosen_row])):
            col_dict[col] = columns_to_restore.pop()
            for other_row in col_dict[col]:
                for other_col in [c for c in row_dict[other_row] if c != col]:
                    col_dict[other_col].add(other_row)

    @staticmethod
    def _puzzle_universe(constraint_subsets_dict):
        """Return a mapping of all possible row, col, num combinations.

        Return a mapping of all possible combinations of row, column, and
        number in Sudoku (each encoded as a 3-char str) to a list of the
        names of puzzle-derived subsets (from in `constraint_subsets_dict`)
        that contain that combination.

        Parameters
        ----------
        constraint_subsets_dict : dict of str to set
            A mapping of a set name to a subset of the str-encoded row,
            column, number combinations in the (to use set theory
            terminology) universe for Sudoku.

        Returns
        -------
        dict of str to set
            A mapping of the str-encoded row, column, number combinations
            to a list of set names in which that combination exists.

        See Also
        --------
        _puzzle_constraint_subsets : the method that generates a
                                     `constraint_subsets_dict`

        """
        universe_dict = {}

        for row in Board.SUDOKU_ROWS:
            for col in Board.SUDOKU_COLS:
                for number in Board.SUDOKU_NUMBERS:
                    # Str so this still works even if row is zero-indexed
                    possibility_code = '{}{}{}'.format(row, col, number)
                    universe_dict[possibility_code] = set()

        for set_id, subset in constraint_subsets_dict.items():
            for possibility_code in subset:
                universe_dict[possibility_code].add(set_id)

        return universe_dict

    def _puzzle_constraint_subsets(self):
        """Return a collection of subsets representing the puzzle.

        Return a mapping of set names to subsets drawing str-encoded
        elements from all the possible combinations of row, column, and
        number in Sudoku. The subsets are of four types:

        1. row-column ('e' prefix): one for each cell, contains integers of
        the form RCN where R is the row, C is the col, and N is any digit
        that can be placed at that (row, column) location on the board while
        maintaining its consistency; only the N varies among elements in
        one of these sets.

        2. row-number ('r' prefix): one for each combination of row and
        number, contains integers of the RCN form where only col C varies
        to represent viable columns in the row where the number can be
        placed.

        3. column-number ('c' prefix): one for each combination of column
        and number, contains integers of the RCN form where only row R
        varies to represent viable rows in the column where the number can
        be placed.

        4. box-number ('b' prefix): one for each combination of box and
        number, contains integers of the RCN form where row R and col C
        vary to represent viable cells within the box where the number can
        be placed.

        Each represents one of the four constraints in Sudoku: each cell
        can have only one number placed in it (row-column); each row can
        only have one of a given number; each column can only have one of a
        given number; and each box can only have one of a given number.

        Returns
        ----------
        dict of str to set
            A mapping of a set name to a subset of the str-encoded row,
            column, number combinations in the (to use set theory
            terminology) universe for Sudoku.

        See Also
        --------
        _puzzle_universe : a method that uses the `constraint_subsets_dict`
                           this method returns to generate a mapping of
                           each combination in the Sudoku universe to the
                           names of sets in `constraint_subsets_dict` that
                           contain that combination.

        """
        constraint_subsets_dict = {}

        for row in Board.SUDOKU_ROWS:
            for col in Board.SUDOKU_COLS:
                possible_numbers = self.puzzle.possibilities(row, col)
                for number in possible_numbers:
                    possibility_code = '{}{}{}'.format(row, col, number)

                    rowcol_key = 'e{}{}'.format(row, col)
                    rownum_key = 'r{}{}'.format(row, number)
                    colnum_key = 'c{}{}'.format(col, number)
                    box, _ = self.puzzle.box_containing_cell(row, col)
                    boxnum_key = 'b{}{}'.format(box, number)
                    keys = [rowcol_key, rownum_key, colnum_key, boxnum_key]

                    for key in keys:
                        try:
                            constraint_subsets_dict[key].add(possibility_code)
                        except KeyError:
                            constraint_subsets_dict[key] = {possibility_code}

        return constraint_subsets_dict
