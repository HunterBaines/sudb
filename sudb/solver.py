# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

from collections import namedtuple
from enum import IntEnum

from board import Board


class Solver(object):
    """A Sudoku solver with a move history.

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
    """

    class MoveType(IntEnum):
        """Constants for labeling the type of a move.

        """

        NONE = 0
        ROWWISE = 1
        COLWISE = 2
        GUESSED = 3
        MANUAL = 4
        CORRECTED = 5
        REASON = 6
        DIFFERENCE = 7

    Move = namedtuple('Move', 'number row column replaced move_type')

    DEDUCTIVE_MOVE_TYPES = [MoveType.ROWWISE, MoveType.COLWISE]


    def __init__(self, puzzle):
        self.puzzle = puzzle
        self.solved_puzzle = None
        self.move_history = []

    def __key(self):
        return (hash(self.puzzle), hash(self.solved_puzzle), hash(tuple(self.move_history)))

    def __eq__(self, other):
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


    def autosolve(self, allow_guessing=True):
        """Solve the puzzle while maintaining a move history.

        Attempt to solve the puzzle first using deduction and, if that
        proves insufficient, using guesses drawn from the solved board.

        Parameters
        ----------
        allow_guessing : bool
            False if all moves should be deduced or True if some may be
            guessed (i.e., pulled from a version of the board solved by
            non-deductive means).

        Returns
        -------
        bool
            True if `puzzle` was successfully solved or False otherwise.
        """

        self.step_until_stuck()
        # The solver can't make an inconsistent move, so only completion needs to be checked
        solved = self.puzzle.is_complete()

        while not solved:
            # If here, a guess is in order
            #TODO: flip order to avoid unnecessary work
            if not self.step_best_guess() or not allow_guessing:
                # The last move can't be a guess, so if here is_complete() would also be False
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

        for row in Board.SUDOKU_ROWS:
            for number in Board.SUDOKU_NUMBERS:
                move_type = self.MoveType.ROWWISE
                possible_locations = self.possible_locations_in_row(number, row)
                if len(possible_locations) != 1 and row in Board.SUDOKU_COLS:
                    # Row-wise deduction failed, so try column-wise
                    move_type = self.MoveType.COLWISE
                    possible_locations = self.possible_locations_in_column(number, row)

                if len(possible_locations) == 1:
                    move_row, move_col = possible_locations.pop()
                    return self._install_move(number, move_row, move_col, move_type)

        # Finish up any column numbers not already seen in Board.SUDOKU_ROWS
        unique_cols = set(Board.SUDOKU_COLS) - set(Board.SUDOKU_ROWS)
        for col in unique_cols:
            for number in Board.SUDOKU_NUMBERS:
                possible_locations = self.possible_locations_in_column(number, col)
                if len(possible_locations) == 1:
                    move_row, move_col = possible_locations.pop()
                    return self._install_move(number, move_row, move_col, self.MoveType.COLWISE)

        return ()

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
        set of int tuple
            A set of number, row, column tuples that represent moves one
            step removed from the current board that do not leave the board
            in an inconsistent state.
        """

        next_moves = set()

        for row in Board.SUDOKU_ROWS:
            for number in Board.SUDOKU_NUMBERS:
                possible_locations = self.possible_locations_in_row(number, row)
                if row in Board.SUDOKU_COLS:
                    other_possible_locations = self.possible_locations_in_column(number, row)
                    possible_locations = possible_locations.union(other_possible_locations)
                possible_moves = set([(number, r, c) for (r, c) in possible_locations])
                next_moves = next_moves.union(possible_moves)

        # Finish up any column numbers not already seen in Board.SUDOKU_ROWS
        unique_cols = set(Board.SUDOKU_COLS) - set(Board.SUDOKU_ROWS)
        for col in unique_cols:
            for number in Board.SUDOKU_NUMBERS:
                possible_locations = self.possible_locations_in_column(number, col)
                possible_moves = set([(number, r, c) for (r, c) in possible_locations])
                next_moves = next_moves.union(possible_moves)

        return next_moves

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
            A set of (row, column) locations in the box where `number`
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
            A set of (row, column) locations in the box where `number`
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
                # Number is blank and not already in other line (row or col) or box
                possible_locations.add(location)

        return possible_locations


    def candidates(self, row, col, _depth=0):
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
            other information about the puzzle gleaned from analysis.
        """

        possible_numbers = self.puzzle.possibilities(row, col)
        location_set = {(row, col)}

        for number in Board.SUDOKU_NUMBERS:
            number_set = {number}

            locations = self.possible_locations_in_row(number, row)
            if len(locations) == 1:
                if locations == location_set:
                    return number_set
                else:
                    possible_numbers -= number_set
                    continue

            locations = self.possible_locations_in_column(number, col)
            if len(locations) == 1:
                if locations == location_set:
                    return number_set
                else:
                    possible_numbers -= number_set

        # If all other cells lack a number in the candidates for the target
        # cell, that number must be what goes in that cell
        other_cells_universe = set()
        if _depth < 2:
            box, _ = Board.box_containing_cell(row, col)
            for location in Board.cells_in_box(box):
                if location != (row, col):
                    numbers = self.candidates(*location, _depth=_depth+1)
                    other_cells_universe = other_cells_universe.union(numbers)
                    if len(numbers) == 1:
                        possible_numbers -= numbers

        if len(possible_numbers - other_cells_universe) == 1:
            possible_numbers -= other_cells_universe

        return possible_numbers


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
        else:
            # This should never occur
            return set()

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
                    row_in_box = 3 * (box / 3) + boxes_i / 3
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
            for puzzle in self._backtrack(temp_puzzle):
                yield puzzle
        else:
            seen_puzzles = {}
            for puzzle in self._algorithm_x():
                try:
                    seen_puzzles[puzzle]
                except KeyError:
                    seen_puzzles[puzzle] = True
                    yield puzzle

    def solution_count(self, algorithm=None):
        """Return the number of solutions possible for the puzzle.

        Count the number of solutions the puzzle has without keeping a move
        history or altering the current state of the board.

        Parameters
        ----------
        algorithm : str, optional
            The name of the algorithm to use to find the solutions (if an
            invalid or no name is specified, Algorithm X is used.)

        Returns
        -------
        int
            The number of solutions possible for the puzzle (a proper
            puzzle will have only one).
        """

        count = 0

        if algorithm and algorithm == 'backtrack':
            for _ in self.all_solutions(algorithm=algorithm):
                count += 1
        else:
            col_dict = self._puzzle_constraint_subsets()
            row_dict = self._puzzle_universe(col_dict)
            solution = []
            # The moves can be the same, but in different order
            unique_hitting_sets = set()
            for hitting_set in self._exact_hitting_set(col_dict, row_dict, solution):
                unique_hitting_sets.add(tuple(sorted(hitting_set)))
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
            True if `puzzle` was successfully solved or False otherwise.

        Notes
        -----
        Algorithm X is the default because it tends to be faster than
        backtracking, and the time it does take tends to be similar for
        most boards.
        """

        if algorithm and algorithm == 'backtrack':
            return self._solve_backtrack()
        else:
            return self._solve_algorithm_x()


    def _solve_backtrack(self):
        """Solve the puzzle using backtracking.

        Returns
        -------
        bool
            True if `puzzle` was successfully solved or False otherwise.

        See Also
        --------
        _backtrack : the backend for this method.
        """

        for puzzle in self._backtrack():
            self.puzzle.copy(puzzle)
            return self.puzzle.is_complete() and self.puzzle.is_consistent()
        return False

    def _backtrack(self, puzzle=None, row=0, col=0):
        if puzzle is None:
            puzzle = self.puzzle.duplicate()

        if col > 8:
            row += 1
            col = 0

        if row > 8:
            yield puzzle.duplicate()
        else:
            possible_numbers = list(puzzle.possibilities(row, col))
            if not possible_numbers:
                yield None
            for num in possible_numbers:
                original_num = puzzle.get_cell(row, col)
                puzzle.set_cell(num, row, col)
                for new_puzzle in self._backtrack(puzzle=puzzle, row=row, col=col+1):
                    if new_puzzle:
                        yield new_puzzle
                puzzle.set_cell(original_num, row, col)


    def _solve_algorithm_x(self):
        """Solve the puzzle using Algorithm X.

        Returns
        -------
        bool
            True if `puzzle` was successfully solved or False otherwise.

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
        comments.

        References
        ----------
        .. [1] Assaf, A. "Algorithm X in 30 lines!". Available at:
           http://www.cs.mcgill.ca/~aassaf9/python/algorithm_x.html
           [Accessed 23 Jun. 2017].
        """

        #TODO figure out how to have it return only one version of each set
        if not col_dict:
            # The last matrix had exactly one entry in every column
            yield list(solution)
        else:
            # Pick column with fewest members
            set_id = min(col_dict, key=lambda sid: len(col_dict[sid]))
            # Consider the rows in any order (where elem is an element from the universe)
            for elem in col_dict[set_id]:
                # Add row to partial solution list
                solution.append(elem)
                saved_columns = self._delete_columns(col_dict, row_dict, elem)
                # Try to solve reduced board
                for partial_solution in self._exact_hitting_set(col_dict, row_dict, solution):
                    # Branch succeeded
                    yield partial_solution
                # Branch failed, remove row from solutions, and restore columns
                self._restore_columns(col_dict, row_dict, elem, saved_columns)
                solution.pop()

    def _delete_columns(self, col_dict, row_dict, chosen_row):
        columns_deleted = []
        # For each column asserted in the chosen row
        for col in row_dict[chosen_row]:
            # Consider all other rows where that column is also asserted
            for other_row in col_dict[col]:
                # Then consider each other asserted column in those rows
                for other_col in [c for c in row_dict[other_row] if c != col]:
                    # And delete any mention of that row (effectively deleting row)
                    col_dict[other_col].remove(other_row)
            # And lastly delete the column itself
            columns_deleted.append(col_dict.pop(col))
        return columns_deleted

    def _restore_columns(self, col_dict, row_dict, chosen_row, columns_to_restore):
        for col in reversed(list(row_dict[chosen_row])):
            col_dict[col] = columns_to_restore.pop()
            for other_row in col_dict[col]:
                for other_col in [c for c in row_dict[other_row] if c != col]:
                    col_dict[other_col].add(other_row)

    def _puzzle_universe(self, constraint_subsets_dict):
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
                    # Str means this still works even if row is zero-indexed
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
