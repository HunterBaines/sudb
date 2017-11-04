# -*- coding: utf-8 -*-

# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""Functions for formatting Sudokus plus classes for colors and grid parts.

"""
from __future__ import absolute_import

import os
import subprocess

from sudb.board import Board


class GridComponentFormatter(object):
    """A tool for generating grid components for outputting Sudokus.

    Parameters
    ----------
    ascii_mode : bool, optional
        True if only ascii should be used in the values returned by all
        methods, and False if UTF-8 may be used (default False).

    Attributes
    ----------
    ascii_mode : bool
        Whether UTF-8 is allowed to be used in any strings returned by
        methods (default False).
    blankc : str
        The character to use for representing a blank.
    gridc : list of str
        The characters to use for constructing grid components.
    gridct : list of str
        The thicker variants of the characters in `gridc` (if possible).

    """
    def __init__(self, ascii_mode=False):
        self.ascii_mode = ascii_mode

        self.blankc = '□'
        self.gridc = ['─', '│', '┬', '┴', '┼', '┌', '┐', '└', '┘', '├', '┤']
        self.gridct = ['═', '║', '╦', '╩', '╬', '╔', '╗', '╚', '╝', '╠', '╣']

        if ascii_mode:
            self.blankc = '_'
            self.gridc = ['.', '!', '.', '!', '!', '.', '.', '!', '!', '!', '!']
            self.gridct = ['-', '|', '+', '+', '+', '+', '+', '+', '+', '+', '+']

    def band_seperator(self, width, placement, padding=0, thick=False):
        """Return a band separator of the given width and type.

        Return a horizontal separator for placing above, below, or between
        boxes with optional left padding and increased line thickness (if
        possible).

        Parameters
        ----------
        width : int
            The number of dash-like characters between each T- or L-like
            character in the band separator string.
        placement : str
            A string defining what type of separator to create: 'top' for
            separators like '┌─┬─┬─┐'; 'middle' for separators like
            '├─┼─┼─┤'; and 'bottom' for separators likes '└─┴─┴─┘'.
        padding : int, optional
            How many blank character to prepend to the separator's left
            side (default 0).
        thick : bool, optional
            True if the thicker variants of the grid characters, e.g., '║'
            instead of '│', should be used, and False otherwise (default
            False).

        Returns
        -------
        str
            The string representing the requested type of separator.

        """
        if thick:
            gridc = self.gridct
        else:
            gridc = self.gridc

        band = '' if not padding else ' ' * padding

        if placement == 'top':
            band += gridc[5] + gridc[0] * width
            for _ in range(2):
                band += gridc[2] + gridc[0] * width
            band += gridc[6]
        elif placement == 'middle':
            band += gridc[9] + gridc[0] * width
            for _ in range(2):
                band += gridc[4] + gridc[0] * width
            band += gridc[10]
        elif placement == 'bottom':
            band += gridc[7] + gridc[0] * width
            for _ in range(2):
                band += gridc[3] + gridc[0] * width
            band += gridc[8]

        return band

    def stack_separator(self, height, padding=0, thick=False):
        """Return a stack separator of the given height.

        Return `height` lines of the character used to demarcate the
        vertical border between boxes with optional left padding and
        increased line thickness (if possible).

        Parameters
        ----------
        height : int
            The number of lines of the stack separator character (e.g.,
            '│') to return.
        padding : int, optional
            How many blank character to prepend to each lines's left side
            (default 0).
        thick : bool, optional
            True if the thicker variants of the grid characters, e.g., '║'
            instead of '│', should be used, and False otherwise (default
            False).

        Returns
        -------
        str
            The string representing the requested number of separators.

        """
        if thick:
            gridc = self.gridct
        else:
            gridc = self.gridc

        stack = '' if not padding else ' ' * padding
        stack += '{}\n'.format(gridc[1]) * height
        # Remove trailing newline
        return stack[:-1]

    def box(self, height, width, blank_map=None, padding=0, thick=False):
        """Return a box of the given height and width.

        Return a box with `height` * `width` spaces inside (optionally
        replacing some or all of those spaces with values given in
        `blank_map`) with optional left padding and increased line
        thickness (if possible).

        Parameters
        ----------
        height : int
            The number of bar-like characters between the L-like characters
            at the box's corners.
        width : int
            The number of dash-like characters between the L-like
            characters at the box's corners.
        blank_map : dict of tuple to str, optional
            A mapping of row, column locations in the box to a string that
            should be used there in place of the default space; the
            location (0, 0) defines the upper left location, (0, 1) defines
            the location to the right of (0, 0), (1, 0) defines the
            location below (0, 0), etc. (default None).
        padding : int, optional
            How many blank character to prepend to each lines's left side
            (default 0).
        thick : bool, optional
            True if the thicker variants of the grid characters, e.g., '║'
            instead of '│', should be used, and False otherwise (default
            False).

        Returns
        -------
        str
            A box with `height` rows and `width` columns of spaces (or
            values defined in `blank_map`) within, or the instance's
            `blankc` if `height` or `width` was 0.

        """
        if height == 0 or width == 0:
            return self.blankc

        if thick:
            gridc = self.gridct
        else:
            gridc = self.gridc

        box = '' if not padding else ' ' * padding

        box += gridc[5] + gridc[0] * width + gridc[6] + '\n'
        for row in range(height):
            box += gridc[1]
            for col in range(width):
                try:
                    box += blank_map[(row, col)]
                except (TypeError, KeyError):
                    box += ' '
            box += gridc[1] + '\n'
        box += gridc[7] + gridc[0] * width + gridc[8]

        return box


class Color(object):
    """Constants for printing colored output.

    """
    RED = '\033[1;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[1;34m'
    MAGENTA = '\033[1;35m'
    CYAN = '\033[1;36m'
    BOLD = '\033[1m'
    DIM = '\033[1;2m'
    UNDERLINE = '\033[1;4m'
    INVERT = '\033[1;7m'
    RESET = '\033[00m'


def get_colormap(locations, color):
    """Return a mapping of the locations to the color.

    Parameters
    ----------
    locations : iterable of int tuple
        An iterable of row, column locations to associate with the given
        color.
    color : Color constant
        A string constant from Color to associate with the given locations.

    Returns
    -------
    dict of tuple to Color constant
        A mapping of each location in `locations` to `color`.

    """
    colormap = {}
    for location in locations:
        colormap[location] = color
    return colormap


def strfboard(board, colormap=None, candidate_map=None, terminal_width=0, show_axes=False,
              zero_indexed=False, ascii_mode=False, ansi_mode=False):
    """Return a formatted string version of the board.

    Return a string-formatted version of the board, optionally
    including row and column numbers and coloring locations according to
    the map of cell locations to colors, if given. If another mapping, this
    time from cell locations to candidates is provided, indicate the
    candidates inside the appropriate blank cell, and use `terminal_width`
    (calculated if not given) to determine which size of board to use.

    Parameters
    ----------
    board : Board instance
        The board to format into a string.
    colormap : dict of tuple to Color constant, optional
        A mapping of row, column locations to a string constant in the
        Color class (default None).
    candidate_map : dict of tuple to int set
        A mapping of row, column locations to the set of numbers
        representing possible values for that location (default None).
    terminal_width : int, optional
        Used when `candidate_map` is defined to determine whether the
        candidates should be fitted into a skinnier or wider version of the
        board; if this is zero, the width will be calculated (default 0).
    show_axes : bool, optional
        True if the rows and columns of the board should be numbered,
        and False otherwise (default False).
    zero_indexed : bool, optional
        Used when `show_axes` is True; True if the numbering on the rows
        and columns should begin at 0, and False if they should begin at 1
        (default False).
    ascii_mode : bool, optional
        True if only ascii should be used in the output string, and False
        if UTF-8 may be used (default False).
    ansi_mode : bool, optional
        True if ANSI escape sequences may be used to decorate cetain
        elements in the output string (e.g., making the axes dim), and
        False otherwise (default False); this option does not affect ANSI
        sequences defined in, e.g., the `colormap` parameter.

    Returns
    -------
    str
        The string representing the board formatted with the given options.

    Examples
    --------
    >>> import formatter as frmt
    >>> from board import Board
    >>> puzzle_lines = ['003020600', '900305001', '001806400']
    >>> puzzle_lines.extend(['008102900', '700000008', '006708200'])
    >>> puzzle_lines.extend(['002609500', '800203009', '005010300'])
    >>> puzzle = Board(lines=puzzle_lines)
    >>> print frmt.strfboard(puzzle, ascii_mode=True)
    .........................
    ! _ _ 3 ! _ 2 _ ! 6 _ _ !
    ! 9 _ _ ! 3 _ 5 ! _ _ 1 !
    ! _ _ 1 ! 8 _ 6 ! 4 _ _ !
    !.......!.......!.......!
    ! _ _ 8 ! 1 _ 2 ! 9 _ _ !
    ! 7 _ _ ! _ _ _ ! _ _ 8 !
    ! _ _ 6 ! 7 _ 8 ! 2 _ _ !
    !.......!.......!.......!
    ! _ _ 2 ! 6 _ 9 ! 5 _ _ !
    ! 8 _ _ ! 2 _ 3 ! _ _ 9 !
    ! _ _ 5 ! _ 1 _ ! 3 _ _ !
    !.......!.......!.......!

    >>> print frmt.strfboard(puzzle)
    ┌───────┬───────┬───────┐
    │ □ □ 3 │ □ 2 □ │ 6 □ □ │
    │ 9 □ □ │ 3 □ 5 │ □ □ 1 │
    │ □ □ 1 │ 8 □ 6 │ 4 □ □ │
    ├───────┼───────┼───────┤
    │ □ □ 8 │ 1 □ 2 │ 9 □ □ │
    │ 7 □ □ │ □ □ □ │ □ □ 8 │
    │ □ □ 6 │ 7 □ 8 │ 2 □ □ │
    ├───────┼───────┼───────┤
    │ □ □ 2 │ 6 □ 9 │ 5 □ □ │
    │ 8 □ □ │ 2 □ 3 │ □ □ 9 │
    │ □ □ 5 │ □ 1 □ │ 3 □ □ │
    └───────┴───────┴───────┘

    >>> print frmt.strfboard(puzzle, show_axes=True)
      ┌───────┬───────┬───────┐
    1 │ □ □ 3 │ □ 2 □ │ 6 □ □ │
    2 │ 9 □ □ │ 3 □ 5 │ □ □ 1 │
    3 │ □ □ 1 │ 8 □ 6 │ 4 □ □ │
      ├───────┼───────┼───────┤
    4 │ □ □ 8 │ 1 □ 2 │ 9 □ □ │
    5 │ 7 □ □ │ □ □ □ │ □ □ 8 │
    6 │ □ □ 6 │ 7 □ 8 │ 2 □ □ │
      ├───────┼───────┼───────┤
    7 │ □ □ 2 │ 6 □ 9 │ 5 □ □ │
    8 │ 8 □ □ │ 2 □ 3 │ □ □ 9 │
    9 │ □ □ 5 │ □ 1 □ │ 3 □ □ │
      └───────┴───────┴───────┘
        1 2 3   4 5 6   7 8 9

    """
    if candidate_map is not None:
        if not ascii_mode:
            terminal_width = terminal_width if terminal_width else _detect_terminal_width()
            widescreen = terminal_width >= 80 + (2 if show_axes else 0)
        else:
            widescreen = False

        height = 4 if widescreen else 5
        width = 25 if widescreen else 19
        size_id = 2 if widescreen else 1
        extra_padding = 1 if widescreen else 2
        col_padding = 7 if widescreen else 5
        row_index_target = 1 if widescreen else 2
        thick_lines = True
    else:
        height = 2
        width = 7
        size_id = 0
        extra_padding = 0
        col_padding = 1
        row_index_target = 0
        thick_lines = False

    padding = 0 if not show_axes else 2

    formatter = GridComponentFormatter(ascii_mode=ascii_mode)

    # Construct horizontal border between adjacent boxes
    band_border = formatter.band_seperator(width, 'middle', padding, thick=thick_lines)
    band_border += '\n'

    # The vertical border between cells in different boxes; no padding
    # because it has to be done later
    stack_border = formatter.stack_separator(height, thick=thick_lines)

    # Top border of board
    board_str = formatter.band_seperator(width, 'top', padding, thick=thick_lines)
    board_str += '\n'

    # Construct each row
    for row in Board.SUDOKU_ROWS:
        cell_row = []
        for col in Board.SUDOKU_COLS:
            if col % 3 == 0:
                cell_row.append(stack_border.split('\n'))

            # Check if color mapped to location
            try:
                color = colormap[(row, col)]
            except (TypeError, KeyError):
                color = None

            cell = _cell_str(board, row, col, formatter, size_id,
                             candidate_map=candidate_map, color=color, ansi_mode=ansi_mode)
            cell_row.append(cell.split('\n'))
        cell_row.append(stack_border.split('\n'))

        for i, line in enumerate(zip(*cell_row)):
            if show_axes and i == row_index_target:
                # If `ansi_mode`, make row label dim
                row_label = Color.DIM if ansi_mode else ''
                row_label += '{} '.format(row + (0 if zero_indexed else 1))
                row_label += Color.RESET if ansi_mode else ''
                board_str += row_label
            else:
                board_str += ' ' * padding
            board_str += ' '.join(line) + '\n'

        # Between two boxes, so insert horizontal band border
        if row + 1 < len(Board.SUDOKU_ROWS) and (row+1) % 3 == 0:
            board_str += band_border

    # Bottom border of board
    board_str += formatter.band_seperator(width, 'bottom', padding, thick=thick_lines)
    board_str += '\n'

    if show_axes:
        # Construct the column number label
        # If `ansi_mode`, make column label dim
        col_label = Color.DIM if ansi_mode else ''
        col_label += ' ' * padding + ' ' * extra_padding
        for col in Board.SUDOKU_COLS:
            if col % 3 == 0:
                # To compensate for stack border
                col_label += ' ' * 2
            col = col + 1 if not zero_indexed else col
            col_label += '{}{}'.format(col, ' ' * col_padding)
        col_label = col_label.rstrip()
        col_label += Color.RESET if ansi_mode else ''
        board_str += col_label + '\n'

    return board_str


def _cell_str(board, row, col, formatter, size_id,
              candidate_map=None, color=None, ansi_mode=False):
    if size_id == 0 or candidate_map is None:
        height, width = 0, 0
    elif size_id == 1:
        height, width = 3, 3
    else:
        height, width = 2, 5

    try:
        candidates = candidate_map[(row, col)]
    except (TypeError, KeyError):
        candidates = set()

    number = board.get_cell(row, col)
    cell_str = ''

    if number != Board.BLANK and (size_id == 0 or candidate_map is None):
        cell_str = str(number)
    elif number != Board.BLANK:
        blank_line = ' ' * (width + 2) + '\n'
        # If `ansi_mode`, make non-candidate number bold
        bold_number = Color.BOLD if ansi_mode else ''
        bold_number += str(number)
        bold_number += Color.RESET if ansi_mode else ''
        if size_id == 2:
            # Place number in upper left of imaginary box (center not possible)
            cell_str = blank_line
            cell_str += ' {}{}\n'.format(bold_number, ' ' * width)
            cell_str += (height-0) * blank_line
        else:
            # Place number in center of imaginary box
            cell_str = 2 * blank_line
            cell_str += '  {}  \n'.format(number)
            cell_str += (height-1) * blank_line
    elif not candidates:
        # An empty cell
        cell_str = formatter.box(height, width)
    else:
        # This will never occur if size_id is 0
        cell_chars = _candidate_cell_chars(candidates, size_id)
        if size_id == 2:
            locations = [(0, 1), (0, 3), (1, 1), (1, 3)]
        else:
            locations = [(row, col) for row in range(3) for col in range(3)]
        blank_map = dict(zip(locations, cell_chars))
        cell_str = formatter.box(height, width, blank_map=blank_map)

    if color is not None:
        color_cell_str = ''
        for line in cell_str.split('\n'):
            color_cell_str += color + line + Color.RESET + '\n'
        cell_str = color_cell_str[:-1]

    return cell_str


def _candidate_cell_chars(candidates, size_id):
    if size_id == 1:
        cell_chars = []
        for number in Board.SUDOKU_NUMBERS:
            if number in candidates:
                cell_chars.append(str(number))
            else:
                cell_chars.append(' ')
        return cell_chars

    cell_chars = [' '] * 4

    if 1 in candidates or 2 in candidates or 9 in candidates:
        if 9 in candidates:
            # 9 is represented by a circle
            if 1 in candidates and 2 not in candidates:
                cell_chars[0] = '①'
            elif 1 not in candidates and 2 in candidates:
                cell_chars[0] = '②'
            elif 1 in candidates and 2 in candidates:
                cell_chars[0] = '⑫'
            else:
                cell_chars[0] = '⑨'
        else:
            if 1 in candidates and 2 not in candidates:
                cell_chars[0] = '1'
            elif 1 not in candidates and 2 in candidates:
                cell_chars[0] = '2'
            else:
                cell_chars[0] = '½'

    if 3 in candidates or 4 in candidates:
        if 3 in candidates and 4 not in candidates:
            cell_chars[1] = '3'
        elif 3 not in candidates and 4 in candidates:
            cell_chars[1] = '4'
        else:
            cell_chars[1] = '¾'

    if 5 in candidates or 6 in candidates:
        if 5 in candidates and 6 not in candidates:
            cell_chars[2] = '5'
        elif 5 not in candidates and 6 in candidates:
            cell_chars[2] = '6'
        else:
            cell_chars[2] = '⅚'

    if 7 in candidates or 8 in candidates:
        if 7 in candidates and 8 not in candidates:
            cell_chars[3] = '7'
        elif 7 not in candidates and 8 in candidates:
            cell_chars[3] = '8'
        else:
            cell_chars[3] = '⅞'

    return cell_chars


def _detect_terminal_width():
    terminal_width = 80
    fnull = None

    try:
        fnull = open(os.devnull, 'w')
        _, terminal_width = subprocess.check_output(['stty', 'size'], stderr=fnull).split()
        terminal_width = int(terminal_width)
    except (IOError, OSError, subprocess.CalledProcessError):
        try:
            terminal_width = int(os.environ['COLUMNS'])
        except KeyError:
            pass

    if fnull is not None:
        fnull.close()

    return terminal_width
