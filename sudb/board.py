# -*- coding: utf-8 -*-

# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""The module containing the Board class.

"""
from __future__ import division


class Board(object):
    """A 9x9 Sudoku board.

    Parameters
    ----------
    lines : list of iterable, optional
        A list of 9 iterables (e.g., str, list, tuple), each representing a
        row in the board, with each iterable containing 9 elements whose
        stringified version should be in `SUDOKU_STRINGS` to represent a
        number or should be anything other than whitespace to represent a
        blank.
    board : Board instance, optional
        Another Board instance defining what instance variables to use in
        this Board instance.
    name : str, optional
        A string to associate with this board (default None).

    Attributes
    ----------
    SUDOKU_NUMBERS : list of int
        A list of valid numbers in a Sudoku board.
    SUDOKU_STRINGS : list of str
        A list of valid numbers in a Sudoku board (as strings).
    SUDOKU_ROWS : list of int
        A list of row numbers that methods with a `row` parameter will
        accept.
    SUDOKU_COLS : list of int
        A list of column numbers that methods with a `col` parameter will
        accept.
    SUDOKU_BOXES : list of int
        A list of box numbers that methods with a `box` parameter will
        accept.
    SUDOKU_BANDS : list of int
        A list of band numbers that methods with a `band` parameter will
        accept.
    SUDOKU_STACKS : list of int
        A list of stack numbers that methods with a `stack` parameter will
        accept.
    SUDOKU_CELLS : list of int tuple
        A list of (row, column) pairs representing the locations for every
        cell in the board.
    BLANK : int
        The number used internally to represent the value in a blank cell.
    board : list of list of int
        The data structure containing all the numbers and blanks (stored as
        0s) in the Board instance. Each inner list represents a row in the
        puzzle.
    name : str
        An optional string to associate with this board.

    Notes
    -----
    Though both `lines` and `board` are optional in `__init__`, if neither
    is specified, a blank board will be initialized.

    """
    # Calling these SUDOKU_X instead of just X to avoid any ambiguity over
    # whether the X applies to the instance or the class itself
    SUDOKU_NUMBERS = range(1, 10)
    SUDOKU_STRINGS = map(str, SUDOKU_NUMBERS)
    # The rows and columns are zero-indexed
    SUDOKU_ROWS = range(9)
    SUDOKU_COLS = SUDOKU_ROWS
    SUDOKU_BOXES = SUDOKU_ROWS
    SUDOKU_BANDS = range(3)
    SUDOKU_STACKS = SUDOKU_BANDS
    SUDOKU_CELLS = [(row, col) for row in SUDOKU_ROWS for col in SUDOKU_COLS]
    BLANK = 0

    @staticmethod
    def box_containing_cell(row, col):
        """Return the indices of and into the box with the location given.

        Parameters
        ----------
        row : int
            A row of the board, which must be in the range defined in
            SUDOKU_ROWS.
        col : int
            A column of the board, which must be in the range defined in
            SUDOKU_COLS.

        Returns
        -------
        int tuple
            A pair of ints both between 0 and 8 inclusive, where the first
            is the index into the list returned by `boxes` pointing to the
            sublist where the given location resides, and the second is the
            index into that sublist to the specific location.

        Raises
        ------
        KeyError
            When `row` or `col` is not in SUDOKU_ROWS or SUDOKU_COLS,
            respectively.

        """
        try:
            box, box_i = Board.box_containing_cell.cell_box_map[(row, col)]
            return (box, box_i)
        except AttributeError:
            Board.box_containing_cell.cell_box_map = {}
            for row_ in Board.SUDOKU_ROWS:
                for col_ in Board.SUDOKU_COLS:
                    box = 3 * (row_ // 3) + ((col_ // 3) % 3)
                    box_i = 3 * (row_ % 3) + (col_ % 3)
                    Board.box_containing_cell.cell_box_map[(row_, col_)] = (box, box_i)
            return Board.box_containing_cell(row, col)

    @staticmethod
    def band_containing_cell(row, col):
        """Return the id of the band containing the given location.

        Parameters
        ----------
        row : int
            A row of the board, which must be in the range defined in
            SUDOKU_ROWS.
        col : int
            A column of the board, which must be in the range defined in
            SUDOKU_COLS.

        Returns
        -------
        int
            An int between 0 and 2 inclusive that identifies which band the
            location occurs in (where 0 is the topmost band, 1 is the
            middle, and 2 is the bottommost).

        Raises
        ------
        KeyError
            When `row` or `col` is not in SUDOKU_ROWS or SUDOKU_COLS,
            respectively.

        """
        box, _ = Board.box_containing_cell(row, col)
        return box // 3

    @staticmethod
    def stack_containing_cell(row, col):
        """Return the id of the stack containing the given location.

        Parameters
        ----------
        row : int
            A row of the board, which must be in the range defined in
            SUDOKU_ROWS.
        col : int
            A column of the board, which must be in the range defined in
            SUDOKU_COLS.

        Returns
        -------
        int
            An int between 0 and 2 inclusive that identifies which stack
            the location occurs in (where 0 is the leftmost band, 1 is the
            middle, and 2 is the rightmost).

        Raises
        ------
        KeyError
            When `row` or `col` is not in SUDOKU_ROWS or SUDOKU_COLS,
            respectively.

        """
        box, _ = Board.box_containing_cell(row, col)
        return box % 3


    @staticmethod
    def cells_in_box(box):
        """Return a list of cell locations in the given box.

        Parameters
        ----------
        box : int
            The box index to get locations for, which must be in
            SUDOKU_BOXES.

        Returns
        -------
        list of int tuple
            A list of (row, column) tuples representing cell locations that
            lie within the given box.

        Raises
        ------
        ValueError
            When `box` is not in SUDOKU_BOXES.

        """
        try:
            return Board.cells_in_box.box_cells_map[box]
        except AttributeError:
            Board.cells_in_box.box_cells_map = {b: [] for b in range(9)}
            for row in Board.SUDOKU_ROWS:
                for col in Board.SUDOKU_COLS:
                    box_, _ = Board.box_containing_cell(row, col)
                    Board.cells_in_box.box_cells_map[box_].append((row, col))
            return Board.cells_in_box(box)
        except KeyError:
            raise ValueError('invalid box argument {}'.format(box))

    @staticmethod
    def cells_in_band(band):
        """Return a list of cell locations in the given band.

        Parameters
        ----------
        band : int
            The band id to get locations for, which must be in
            SUDOKU_BANDS.

        Returns
        -------
        list of int tuple
            A list of (row, column) tuples representing cell locations that
            lie within the given band.

        Raises
        ------
        ValueError
            When `band` is not in SUDOKU_BANDS.

        """
        if band not in Board.SUDOKU_BANDS:
            raise ValueError('invalid band argument {}'.format(band))

        cells = []
        leftmost_box = band * 3
        # Map band=0 to boxes=[0,1,2]; band=1 to boxes=[3,4,5]; etc.
        for box in range(leftmost_box, leftmost_box + 3):
            cells.extend(Board.cells_in_box(box))

        return cells

    @staticmethod
    def cells_in_stack(stack):
        """Return a list of cell locations in the given stack.

        Parameters
        ----------
        stack : int
            The stack id to get locations for, which must be in
            SUDOKU_STACKS.

        Returns
        -------
        list of int tuple
            A list of (row, column) tuples representing cell locations that
            lie within the given stack.

        Raises
        ------
        ValueError
            When `stack` is not in SUDOKU_STACKS.

        """
        if stack not in Board.SUDOKU_STACKS:
            raise ValueError('invalid stack argument {}'.format(stack))

        cells = []
        uppermost_box = stack
        # Map stack=0 o boxes=[0,3,6]; stack=1 to boxes=[1,4,7]; etc.
        for box in range(uppermost_box, uppermost_box + 7, 3):
            cells.extend(Board.cells_in_box(box))

        return cells

    @staticmethod
    def cells_in_row(row):
        """Return a list of cell locations in the given row.

        Parameters
        ----------
        stack : int
            The row index to get locations for, which must be in
            SUDOKU_ROWS.

        Returns
        -------
        list of int tuple
            A list of (row, column) tuples representing cell locations that
            lie within the given row.

        Raises
        ------
        ValueError
            When `row` is not in SUDOKU_ROWS.

        """
        if row not in Board.SUDOKU_ROWS:
            raise ValueError('invalid row argument {}'.format(row))
        return [(row, col) for col in Board.SUDOKU_COLS]

    @staticmethod
    def cells_in_column(col):
        """Return a list of cell locations in the given column.

        Parameters
        ----------
        stack : int
            The column index to get locations for, which must be in
            SUDOKU_COLS.

        Returns
        -------
        list of int tuple
            A list of (row, column) tuples representing cell locations that
            lie within the given column.

        Raises
        ------
        ValueError
            When `col` is not in SUDOKU_COLS.

        """
        if col not in Board.SUDOKU_COLS:
            raise ValueError('invalid column argument {}'.format(col))
        return [(row, col) for row in Board.SUDOKU_ROWS]


    def __init__(self, lines=None, board=None, name=None):
        self.board = None

        if lines is not None:
            self._board_from_lines(lines)
        elif board is not None:
            self.copy(board)

        if self.board is None:
            # Initialize blank board
            lines = [str(self.BLANK) * len(self.SUDOKU_COLS) for _ in range(len(self.SUDOKU_ROWS))]
            self._board_from_lines(lines)

        self.name = name

        # Each of these is used as a cache
        self._rows = None
        self._columns = None
        self._boxes = None

    def __str__(self):
        board_str = ''
        rows = self.rows()
        for i, row in enumerate(rows):
            board_str += ''.join(map(str, row))
            if i + 1 < len(rows):
                board_str += '\n'
        return board_str

    def __repr__(self):
        return str(self.board)

    def __key(self):
        return tuple(map(tuple, self.rows()))

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.__key())


    def _board_from_lines(self, lines):
        puzzle_lines = []
        for line in lines:
            if len(line) != 9 or ' ' in line:
                continue

            standard_line = [int(c) if str(c) in self.SUDOKU_STRINGS else self.BLANK for c in line]
            puzzle_lines.append(standard_line)

            if len(puzzle_lines) == 9:
                self.board = puzzle_lines
                break


    def copy(self, board_instance):
        """Copy the board in board instance to the current board.

        Parameters
        ----------
        board_instance : Board instance
            The Board instance with `board` instance variable to copy.

        """
        # Reset cached versions of rows, columns, and boxes
        self._rows = self._columns = self._boxes = None
        self.board = [row[:] for row in board_instance.board]

    def duplicate(self):
        """Return a duplicate of the board instance.

        Returns
        -------
        Board instance
            An instance identical to this instance.

        """
        return Board(board=self, name=self.name)


    def get_cell(self, row, col):
        """Return the value at the given location of the board.

        Parameters
        ----------
        row : int
            A row of the board, which must be in the range defined in
            SUDOKU_ROWS.
        col : int
            A column of the board, which must be in the range defined in
            SUDOKU_COLS.

        Returns
        -------
        int
            The value at the given row, column of the board, which will be
            the value of BLANK if the location is empty.

        Raises
        ------
        IndexError
            When `row` or `col` is not in SUDOKU_ROWS or SUDOKU_COLS,
            respectively.

        """
        return self.board[row][col]

    def set_cell(self, number, row, col):
        """Set the location to a specified value.

        Parameters
        ----------
        number : int
            The value to set the cell at (`row`, `col`) to, which should be
            in SUDOKU_NUMBERS unless the value represents a blank, in which
            case, anything else will work, though BLANK is preferred.
        row : int
            The row in `board` to change, which must be in SUDOKU_ROWS.
            inclusive.
        col : int
            The column in `board` to change, which must be in SUDOKU_COLS.

        Raises
        ------
        IndexError
            When `row` or `col` is not in SUDOKU_ROWS or SUDOKU_COLS,
            respectively.

        """
        if str(number) not in self.SUDOKU_STRINGS:
            number = self.BLANK
        # This should already by an int, but make sure
        number = int(number)

        # Update cache
        if self._rows:
            self._rows[row][col] = number
        if self._columns:
            self._columns[col][row] = number
        if self._boxes:
            box, box_i = self.box_containing_cell(row, col)
            self._boxes[box][box_i] = number

        self.board[row][col] = number


    def boxes(self):
        """Return a list of the board's boxes flattened into lists.

        Returns
        -------
        list of list of int
            In which each inner list represents a box in the board,
            flattened such that its first three elements represent the
            topmost row, the next three its middle row, and the final three
            its bottom row. The inner lists themselves are ordered in the
            same way, mutatis mutandis.

        """
        # Return cached version if possible
        if self._boxes is not None:
            return self._boxes

        # Assumes the number of boxes equals the number of rows
        self._boxes = [[] for _ in self.SUDOKU_ROWS]

        for row, row_list in enumerate(self.rows()):
            for col in self.SUDOKU_COLS:
                number = row_list[col]
                box, _ = self.box_containing_cell(row, col)
                self._boxes[box].append(number)

        return self._boxes

    def rows(self):
        """Return a list of the board's rows.

        Returns
        -------
        list of list of int
            In which each inner list represents a row in the board, and
            those inner lists are ordered from topmost row to bottommost.

        """
        # Return cached version if possible
        if self._rows is not None:
            return self._rows
        self._rows = self.board[:]
        return self._rows

    def columns(self):
        """Return a list of the board's columns.

        Returns
        -------
        list of list of int
            In which each inner list represents a column in the board, and
            those inner lists are ordered from leftmost column to
            rightmost.

        """
        if self._columns is not None:
            return self._columns

        self._columns = map(list, zip(*self.rows()))
        return self._columns


    def clues(self):
        """Return a list of all cells with numbers in them.

        Returns
        -------
        list of int tuple
            A list with tuples of the form (number, row, column), where
            row, column is a location in the board and number is the value
            that location was assigned.

        """
        #TODO: cache clues?
        clues = []
        for (row, col) in self.SUDOKU_CELLS:
            number = self.get_cell(row, col)
            if number != self.BLANK:
                clues.append((number, row, col))
        return clues

    def clue_count(self):
        """Return the number of cells that contain a number.

        Returns
        -------
        int
            The number of cells in the puzzle that are not blank.

        """
        return len(self.clues())


    def is_complete(self):
        """Return whether the board has no blank cells.

        Returns
        -------
        bool
            False if blanks found, True otherwise.

        """
        return self.clue_count() == len(self.SUDOKU_CELLS)

    def is_consistent(self):
        """Return whether any inconsistencies exist in the board.

        Check for row, columns, or boxes with duplicate numbers and
        return False if any are found or True otherwise.

        Returns
        -------
        bool
            False if inconsistencies found, True otherwise.

        """
        # Look for duplicates in each box
        for box in self.boxes():
            digit_box = [digit for digit in box if digit in self.SUDOKU_NUMBERS]
            if len(digit_box) != len(set(digit_box)):
                return False

        # Look for duplicates in each row
        for row in self.rows():
            digit_row = [digit for digit in row if digit in self.SUDOKU_NUMBERS]
            if len(digit_row) != len(set(digit_row)):
                return False

        # Look for duplicates in each column
        for column in self.columns():
            digit_column = [digit for digit in column if digit in self.SUDOKU_NUMBERS]
            if len(digit_column) != len(set(digit_column)):
                return False

        return True


    def inconsistencies(self):
        """Return inconsistent locations.

        Check for row, columns, or boxes with duplicate numbers and
        return a list of all such locations found.

        Returns
        -------
        list of int tuple
            A list of (row, column) locations that are inconsistent
            according to the rules of Sudoku.

        """
        inconsistent_locations = []

        # Look for duplicates in each box
        for box_i, box in enumerate(self.boxes()):
            for i, number in enumerate(box):
                if number in self.SUDOKU_NUMBERS and box.count(number) > 1:
                    bad_row = 3 * (box_i // 3) + (i // 3)
                    bad_col = 3 * (box_i % 3) + (i % 3)
                    inconsistent_locations.append((bad_row, bad_col))

        # Look for duplicates in each row
        for row_i, row in enumerate(self.rows()):
            for i, number in enumerate(row):
                if number in self.SUDOKU_NUMBERS and row.count(number) > 1:
                    bad_row = row_i
                    bad_col = i
                    inconsistent_locations.append((bad_row, bad_col))

        # Look for duplicates in each column
        for column_i, column in enumerate(self.columns()):
            for i, number in enumerate(column):
                if number in self.SUDOKU_NUMBERS and column.count(number) > 1:
                    bad_row = i
                    bad_col = column_i
                    inconsistent_locations.append((bad_row, bad_col))

        return inconsistent_locations

    def differences(self, board_instance):
        """Return differences between the instance and passed puzzle.

        Return a list of locations of any numbers that do not match in this
        instance's `board` and the `board` in `board_instance`.

        Parameters
        ----------
        board_instance : Board instance
            The Board instance with `board` instance variable to compare
            with this instance's `board`.

        Returns
        -------
        list of int tuple
            A list of (row, column) locations for which the numbers at
            those locations differ between the `board` of this instance and
            the `board` of `board_instance`.

        """
        diff_coordinates = []
        for (row, col) in self.SUDOKU_CELLS:
            if self.get_cell(row, col) != board_instance.get_cell(row, col):
                diff_coordinates.append((row, col))
        return diff_coordinates

    def possibilities(self, row, col):
        """Return all viable numbers for the given location.

        Return the set of all candidates for a given cell based on nothing
        more than what numbers are in the cell's buddies.

        Parameters
        ----------
        row : int
            A row of the board, which must be in the range defined in
            SUDOKU_ROWS.
        col : int
            A column of the board, which must be in the range defined in
            SUDOKU_COLS.

        Returns
        -------
        set of int
            The set of numbers that could be placed at the cell at `row`,
            `col` without leaving the board inconsistent.

        Raises
        ------
        IndexError
            When `row` or `col` is not in SUDOKU_ROWS or SUDOKU_COLS,
            respectively.

        Notes
        -----
        This method could reasonably be called `candidates`, but such a
        name might suggest more analysis than what this actually does.

        """
        current_number = self.get_cell(row, col)
        if current_number:
            return {current_number}

        row_numbers = [number for number in self.rows()[row] if number]
        col_numbers = [number for number in self.columns()[col] if number]
        box, _ = self.box_containing_cell(row, col)
        box_numbers = [number for number in self.boxes()[box] if number]

        possible_numbers = set(self.SUDOKU_NUMBERS) - set(row_numbers)
        possible_numbers -= set(col_numbers)
        possible_numbers -= set(box_numbers)

        return possible_numbers
