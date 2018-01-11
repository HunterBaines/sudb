# -*- coding: utf-8 -*-

# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""Functions for importing 9x9 Sudokus from files or random seeds.

Examples
--------
>>> # Examples involving seeds may vary if `numpy.random` isn't installed
>>> import sudb.importer as importer
>>> import sudb.formatter as frmt
>>> puzzle_str = 'My Puzzle\n' # ignore lines w/ whitespace
>>> puzzle_str += '12345678\n' # ignore lines w/o 9 chars
>>> puzzle_str += '003020600\n' # to represent blanks, use 0 or
>>> puzzle_str += '9__3_5__1\n' # a non-whitespace, non-digit char
>>> puzzle_str += '**18*64**\n' # the blank char can change row-by-row
>>> puzzle_str += '+-81+29-+\n' # or even within the same row
>>> puzzle_str += '7!@#$%^&8\n'
>>> puzzle_str += '--67-82--\n'
>>> puzzle_str += 'bl26a95nk\n'
>>> puzzle_str += '8bb2b3bb9\n'
>>> puzzle_str += 'XX5X1X3XX\n'
>>> puzzles = importer.get_puzzles(lines=puzzle_str.split('\n'), seeds=[0])
>>> for puzzle in puzzles:
...     print('{}\n{}\n'.format(frmt.strfboard(puzzle), puzzle.name))
... 
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
lines argument
<BLANKLINE>
┌───────┬───────┬───────┐
│ 1 □ 5 │ □ □ □ │ □ □ □ │
│ □ □ □ │ □ 9 □ │ □ □ 1 │
│ □ 2 □ │ □ 8 □ │ □ □ 5 │
├───────┼───────┼───────┤
│ 9 □ □ │ 6 □ □ │ 5 □ 4 │
│ □ □ □ │ □ 3 □ │ 9 □ □ │
│ □ 8 □ │ 9 □ 4 │ □ □ 2 │
├───────┼───────┼───────┤
│ □ 1 □ │ 4 □ □ │ □ 2 □ │
│ □ □ □ │ □ □ □ │ 4 □ 6 │
│ □ 9 3 │ □ □ 5 │ □ □ □ │
└───────┴───────┴───────┘
seed 0
<BLANKLINE>

"""
from hashlib import sha1
from os import path
from tempfile import gettempdir
from urllib.error import URLError, HTTPError
from urllib.request import urlretrieve

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
                error.error('importing from image will likely work only on'
                            ' cleanly cropped images with sharp text and a'
                            ' high-contrast grid, and even then the resulting'
                            ' puzzle may have missing or incorrect clues.\n',
                            prelude='warning')
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
    """Return a list of puzzles drawn from a file, URL, or user input.

    Return a list of puzzles from the path or URL given in `filename`. If a
    text file, construct the lines in each puzzle from lines in the file of
    this form (where any non-numeric, non-whitespace character can be used
    instead of 0 to represent blanks in the puzzle):

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
        The path or URL to the image (PNG, JPEG, or GIF) file containing a
        puzzle or the text file containing one or more puzzles (default
        None).

    Returns
    -------
    list of Board instance
        A list of all puzzles found in the given file or entered by the
        user.

    """
    lines = []
    specify_lineno_in_name = True

    if filename is not None:
        filename = _retrieve_location(filename)
        if filename is None:
            return []

        if _is_image(filename):
            specify_lineno_in_name = False
            try:
                from sudb import sudokuimg
                lines = sudokuimg.puzzle_lines(filename)
            except ImportError as err:
                error.error(str(err).lower(), prelude=filename)
                return []
        else:
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
                row = input()
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
        True if the line number the puzzle begins at should be included in
        its name (e.g., 'puzzle.txt:1'), and False if not (default False).

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


def _retrieve_location(location):
    # Return given path or, if URL given, path to file downloaded from URL.
    io_error_msg = None

    try:
        # Assume `location` is local path and try to open it for reading
        with open(location, 'r') as _:
            pass
        return location
    except IOError as err:
        # pylint: disable=no-member; `strerror` as a `str` has `lower`
        # If treating `location` as a URL also fails, `io_error_msg` will
        # be shown; `strerror` allows for nicer formatting than `str(err)`
        io_error_msg = err.strerror.lower()

    # A consistently named (to ease testing output) tempfile that includes
    # the original extension (to ease detecting if an image)
    ideal_location = _get_temp_filename(location)
    try:
        # Assume `location` is a URL
        download_location, _ = urlretrieve(location, filename=ideal_location)
    except ValueError as err:
        if io_error_msg is None:
            # This should never occur
            io_error_msg = str(err).lower()
        error.error(io_error_msg, prelude=location)
        return None
    except (URLError, HTTPError) as err:
        # The `reason` attribute for these is not guaranteed to be a `str`
        error.error(str(err.reason).lower(), prelude=location)
        return None

    return download_location


def _get_temp_filename(location):
    # Return a unique, consistent filename that preserves the extension.
    _, location_ext = path.splitext(location)
    location_hash = sha1(location.encode()).hexdigest()[:7]
    location_filename = 'sudb_{hash}{ext}'.format(hash=location_hash, ext=location_ext)
    location_directory = gettempdir()
    return path.join(location_directory, location_filename)
