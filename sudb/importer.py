# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""Functions for importing 9x9 Sudokus from files or random seeds.

Examples
--------
>>> import importer
>>> import formatter as frmt
>>> puzzle_str = 'My Puzzle\n' # Lines with whitespace are ignored
>>> puzzle_str += '003020600\n9__3_5__1\n**18*64**\n' # Not 1-9, then blank
>>> puzzle_str += '++81+29++\nrandom line\n7!@#$%^&8\n--67-82--\n'
>>> puzzle_str += 'bl26a95nk\n8bb2b3bb9\n\n\nXX5X1X3XX\n'
>>> puzzle_str += '12345678' # Lines with line length != 9 chars are ignored
>>> puzzles = importer.get_puzzles(lines=puzzle_str.split('\n'), seeds=[0])
>>> for puzzle in puzzles:
    ...     print '{}{}\n'.format(frmt.strfboard(puzzle, ascii_mode=True), puzzle.name)
    ... 
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
    lines argument

    .........................
    ! _ 4 _ ! 3 7 _ ! _ _ 9 !
    ! _ 5 7 ! _ _ 9 ! 6 _ _ !
    ! _ _ 8 ! 6 _ _ ! _ _ 3 !
    !.......!.......!.......!
    ! 5 _ _ ! 7 _ _ ! _ _ _ !
    ! _ 6 _ ! 5 9 2 ! _ _ 8 !
    ! _ 9 _ ! _ _ _ ! _ _ _ !
    !.......!.......!.......!
    ! 6 8 _ ! _ _ 5 ! _ 7 _ !
    ! _ _ _ ! _ _ _ ! _ 8 6 !
    ! 4 2 _ ! _ _ 7 ! _ _ _ !
    !.......!.......!.......!
    seed 0

"""
from __future__ import absolute_import, print_function

from os import path
import urllib

from sudb import generator
from sudb import error
from sudb.board import Board


def get_puzzles(lines=None, filenames=None, seeds=None, logger=None):
    """Return puzzles from lines, files, or seeds with optional logging.

    Return a list of puzzles imported from the lines, filenames, and seeds
    provided (or from stdin if none provided), and optionally store any
    errors in the passed error logger.

    Parameters
    ----------
    lines : list of iterable, optional
        A list of 9 or more iterables (e.g., str, list, tuple), each of
        which is imported as a row in a puzzle if it contains exactly 9
        elements and no whitespace (default None).
    filenames : list of str, optional
        A list of paths to text or image files from which to import
        puzzles (default None).
    seeds : list of int, long, or hashable, optional
        A list of seeds from which to generate puzzles (default None).
    logger : ErrorLogger instance, optional
        The logger to use for error accumulating (default None).

    Returns
    -------
    list of Board instance
        A list of all puzzles imported from `filenames` and `seeds` (or
        from stdin if neither given).

    Notes
    -----
    Aside from the addition of error logging, this is just an integrated
    version of the other methods available in the module.

    """
    if logger is not None:
        import_error = error.Error('import error')
        logger.add_error(import_error)

    puzzles = []
    get_from_stdin = True

    if lines is not None:
        get_from_stdin = False
        puzzles.extend(get_puzzles_from_lines(lines, name='lines argument'))

    warned_about_image_import = False
    if filenames is not None:
        get_from_stdin = False
        for filename in filenames:
            if not warned_about_image_import and _is_image(filename):
                msg = 'importing from image will likely work only on cleanly'
                msg += ' cropped images with sharp text and a high-contrast'
                msg += ' grid, and even then sometimes the resultant puzzle'
                msg += ' may have missing or incorrect clues.'
                error.error(msg, prelude='warning')
                warned_about_image_import = True
            file_puzzles = get_puzzles_from_file(filename)
            if logger is not None and not file_puzzles:
                logger.log_error(filename, import_error)
            puzzles.extend(file_puzzles)

    if seeds is not None:
        get_from_stdin = False
        puzzles.extend(get_puzzles_from_seeds(seeds))

    if get_from_stdin:
        puzzles = get_puzzles_from_file()

    return puzzles


def get_puzzles_from_seeds(seeds):
    """Return a list of puzzles generated from the given seeds.

    For each seed in `seeds`, generate a puzzle based on that seed and add
    it to a list of puzzles; return that list.

    Parameters
    ----------
    seeds : list of int, long, or hashable
        A list containing the seeds to be used for puzzle generation.

    Returns
    -------
    list of Board instance
        A list of all puzzles generated from `seeds`.

    """
    puzzles = []

    for seed in seeds:
        puzzle = generator.generate(seed)
        puzzle.name = 'seed {}'.format(seed)
        puzzles.append(puzzle)

    return puzzles


def get_puzzles_from_file(filename=None):
    """Return a list of puzzle lines drawn from a file or user input.

    If a filename is specified, determine if the file is an image or text
    file. If a text file, construct the lines in each puzzle from lines in
    the file of this form (where any non-numeric, non-whitespace character
    can be used instead of 0 to represent blanks in the puzzle):

    003020600
    900305001
    001806400
    008102900
    700000008
    006708200
    002609500
    800203009
    005010300

    If no filename is given, get the puzzle lines directly from the user.

    Parameters
    ----------
    filename : str, optional
        The path to the image (PNG, JPEG, or GIF) file containing a
        puzzle or the text file containing one or more puzzles (default
        None).

    Returns
    -------
    list of Board instance
        A list of all puzzles found in the given file or entered by the
        user.

    """
    lines = []
    specify_lineno_in_name = False

    if filename is not None:
        try:
            # If path, it returns that; if url, it downloads then returns
            # path to downloaded copy
            filename = urllib.urlretrieve(filename)[0]
        except IOError as err:
            # pylint: disable=no-member; `strerror` as a `str` has `lower`
            # `strerror` is more descriptive than `message` for the
            # exceptions that have this attribute
            error.error(err.strerror.lower(), prelude=filename)
            return []

        if _is_image(filename):
            try:
                from sudb import sudokuimg
                lines = sudokuimg.puzzle_lines(filename)
            except ImportError as err:
                error.error(err.message.lower(), prelude=filename)
                return []
        else:
            specify_lineno_in_name = True
            # If we made it past urllib.urlretrieve, this shouldn't raise
            # an IOError
            with open(filename, 'r') as puzzle_file:
                lines = puzzle_file.read().split('\n')
    else:
        print('Enter the 9 characters in each row of the puzzle(s) from top to',
              'bottom. Use 0 or any non-numerical, non-whitespace character to',
              'represent a blank in the puzzle. When done, type a period on a',
              'line by itself (or just type EOF, e.g., ctrl-D).', sep='\n')
        print()

        row = ''
        while row != '.':
            try:
                row = raw_input()
                lines.append(row)
            except EOFError:
                break
        print()

    return get_puzzles_from_lines(lines, name=filename, specify_lineno=specify_lineno_in_name)


def get_puzzles_from_lines(lines, name=None, specify_lineno=False):
    """Return a list of puzzles formed from the given lines.

    Parameters
    ----------
    lines : list of iterable
        A list of 9 or more iterables (e.g., str, list, tuple), each of
        which is interpreted as a row in a puzzle if the iterable contains
        exactly 9 elements and no whitespace.
    name : str, optional
        The name to save in the Board instances (default 'stdin').
    specify_lineno : bool, optional
        Whether to specify the line number the puzzle begins at in the
        puzzle's name (e.g., 'puzzle.txt:1') (default False).

    Returns
    -------
    list of Board instance
        A list of all puzzles found in the given lines.

    """
    if name is None:
        name = 'stdin'

    puzzles = []
    start_lineno = 0

    puzzle_lines = []
    for i, line in enumerate(lines):
        if len(line) != 9 or ' ' in line:
            continue

        if specify_lineno and start_lineno == 0:
            start_lineno = i + 1
        puzzle_lines.append(line)

        if len(puzzle_lines) == 9:
            final_name = name
            if specify_lineno:
                final_name += ':{}'.format(start_lineno)
                start_lineno = 0

            puzzle = Board(lines=puzzle_lines, name=final_name)
            if puzzle is not None:
                puzzles.append(puzzle)
            puzzle_lines = []

    return puzzles


def _is_image(filename):
    _, ext = path.splitext(filename)
    return ext.lower() in ['.png', '.jpg', '.jpeg', '.gif']
