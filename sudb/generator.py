# -*- coding: utf-8 -*-

# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""Functions for generating 9x9 Sudokus from seed or from other puzzles.

Examples
--------
>>> import sudb.generator as generator
>>> import sudb.formatter as frmt
>>> generator.using_numpy_random() # These examples assume this is True
True
>>> seed = 3
>>> puzzle = generator.solved_puzzle(seed)
>>> print(frmt.strfboard(puzzle))
┌───────┬───────┬───────┐
│ 3 4 6 │ 1 5 8 │ 2 7 9 │
│ 1 2 5 │ 9 7 3 │ 4 6 8 │
│ 7 8 9 │ 2 4 6 │ 5 1 3 │
├───────┼───────┼───────┤
│ 4 6 3 │ 5 1 7 │ 9 8 2 │
│ 5 9 2 │ 8 6 4 │ 1 3 7 │
│ 8 1 7 │ 3 9 2 │ 6 5 4 │
├───────┼───────┼───────┤
│ 9 7 1 │ 4 8 5 │ 3 2 6 │
│ 2 5 8 │ 6 3 9 │ 7 4 1 │
│ 6 3 4 │ 7 2 1 │ 8 9 5 │
└───────┴───────┴───────┘
>>> puzzle = generator.similar_puzzle(puzzle, seed)
>>> print(frmt.strfboard(puzzle))
┌───────┬───────┬───────┐
│ □ □ □ │ □ 5 3 │ 2 □ 9 │
│ 1 6 □ │ 9 4 □ │ □ □ 8 │
│ □ □ 5 │ □ □ 6 │ □ 1 □ │
├───────┼───────┼───────┤
│ □ □ □ │ □ □ 7 │ □ 8 2 │
│ 5 1 □ │ 3 □ □ │ □ □ □ │
│ 8 □ 7 │ □ □ □ │ □ 5 4 │
├───────┼───────┼───────┤
│ □ □ □ │ 7 □ □ │ □ □ 6 │
│ □ □ □ │ □ □ 9 │ □ □ □ │
│ □ □ 4 │ □ 2 □ │ □ □ □ │
└───────┴───────┴───────┘
>>> minimized_puzzle = puzzle.duplicate()
>>> generator.minimize(minimized_puzzle)
-3
>>> print(frmt.strfboard(minimized_puzzle))
┌───────┬───────┬───────┐
│ □ □ □ │ □ □ □ │ 2 □ 9 │
│ 1 6 □ │ 9 4 □ │ □ □ 8 │
│ □ □ 5 │ □ □ 6 │ □ 1 □ │
├───────┼───────┼───────┤
│ □ □ □ │ □ □ □ │ □ 8 2 │
│ 5 1 □ │ 3 □ □ │ □ □ □ │
│ 8 □ 7 │ □ □ □ │ □ 5 4 │
├───────┼───────┼───────┤
│ □ □ □ │ 7 □ □ │ □ □ 6 │
│ □ □ □ │ □ □ 9 │ □ □ □ │
│ □ □ 4 │ □ 2 □ │ □ □ □ │
└───────┴───────┴───────┘
>>> symmetric_puzzle = puzzle.duplicate()
>>> generator.make_rotationally_symmetric(symmetric_puzzle, minimized=True)
3
>>> print(frmt.strfboard(symmetric_puzzle))
┌───────┬───────┬───────┐
│ □ □ □ │ □ 5 □ │ 2 □ □ │
│ 1 6 □ │ 9 4 □ │ □ □ 8 │
│ □ □ 5 │ □ □ 6 │ □ 1 □ │
├───────┼───────┼───────┤
│ 3 □ □ │ □ □ □ │ □ 8 2 │
│ □ 1 □ │ 3 □ 4 │ □ 9 □ │
│ 8 9 □ │ □ □ □ │ □ □ 4 │
├───────┼───────┼───────┤
│ □ 3 □ │ 7 □ □ │ 8 □ □ │
│ 6 □ □ │ □ 3 9 │ □ 2 5 │
│ □ □ 4 │ □ 2 □ │ □ □ □ │
└───────┴───────┴───────┘

"""
from sudb.board import Board
from sudb.solver import Solver

_USING_NUMPY_RANDOM = False
try:
    # Prefer `numpy.random` because the builtin `random` yields different
    # results for the same seeds in Python 2 and 3, which makes testing
    # across versions difficult. All examples and tests use `numpy.random`.
    from numpy import random
    _USING_NUMPY_RANDOM = True
except ImportError:
    import random


def generate(seed, minimized=False, symmetric=False):
    """Return a puzzle generated from the provided seed.

    Return a satisfactory puzzle generated from `seed` with optional
    minimization if `minimized` is True and optional 180-degree symmetry if
    `symmetric` is True.

    Parameters
    ----------
    seed : int, long, or hashable
        The seed to use for generating the puzzle.
    minimized : bool, optional
        True if any redundant clues should be removed from the generated
        puzzle (at the expense of additional time for generation), and
        False if they may be left in (default False).
    symmetric : bool, optional
        True if the puzzle should be given 180-degree rotational symmetry
        (at the expense of likely adding redundant clues), and False if it
        should be left, in all likelihood, asymmetrical (default False).

    Returns
    -------
    Board instance
        The puzzle generated from the given seed.

    """
    puzzle = solved_puzzle(seed)
    puzzle = similar_puzzle(puzzle, seed)
    if minimized and not symmetric:
        # If `symmetric`, symmetry-maintaining minimization will be done
        # within the function `make_rotationally_symmetric`
        minimize(puzzle, threshold=20)
    elif symmetric:
        make_rotationally_symmetric(puzzle, minimized=minimized)
    return puzzle


def solved_puzzle(seed):
    """Return a random, solved puzzle generated from the provided seed.

    Parameters
    ----------
    seed : int, long, or hashable
        The seed to use for generating the solved board.

    Returns
    -------
    Board instance
        The solved puzzle generated from the given seed.

    """
    # Decreasing this allows for more randomness but can also increase the
    # time required to generate from some seeds
    min_start_clues = 3

    random.seed(seed)
    target_row = random.choice(Board.SUDOKU_ROWS)
    columns = Board.SUDOKU_COLS[:]
    random.shuffle(columns)

    # `numpy.random` excludes upper limit; builtin `random` includes it
    upper_limit_adjustment = 1 if using_numpy_random() else 0
    column_count = random.randint(min_start_clues, len(columns)+upper_limit_adjustment)

    # Initialize a blank board
    puzzle = Board(name=str(seed))

    # To get the solver started and insert randomness
    for i, target_col in enumerate(columns[:column_count]):
        target_number = Board.SUDOKU_NUMBERS[i]
        puzzle.set_cell(target_number, target_row, target_col)

    solver = Solver(puzzle)
    solver.autosolve_without_history()

    return puzzle


def similar_puzzle(puzzle, seed, min_clues=17):
    """Return a puzzle similar to the given one using the provided seed.

    Return a satisfactory puzzle initialized with at least `min_clues`
    clues randomly selected from `puzzle` according to `seed`.

    Parameters
    ----------
    puzzle : Board instance
        The puzzle to base the new puzzle off of.
    seed : int, long, or hashable
        The seed to use for deriving the puzzle.
    min_clues : int, optional
        The minimum number of clues guaranteed to be in the derived puzzle
        (default 17).

    Returns
    -------
    Board instance
        The puzzle derived or None if `puzzle` had fewer clues than
        `min_clues`.

    See Also
    --------
    minimize : another method for generating a puzzle from a given puzzle
               that is (unlike this one) likely to generate a puzzle with
               the same solution as the original.

    Notes
    -----
    For an explanation of the default for `min_clues`, see the notes in
    `minimize`.

    """
    clues = puzzle.clues()
    if len(clues) < min_clues:
        return None

    random.seed(seed)
    random.shuffle(clues)

    new_puzzle = Board()
    for (num, row, col) in clues[:min_clues]:
        new_puzzle.set_cell(num, row, col)
    make_satisfactory(new_puzzle)

    return new_puzzle


def make_satisfactory(puzzle):
    """Add all clues that seem to require guessing; return amount added.

    Parameters
    ----------
    puzzle : Board instance
        The puzzle to make satisfactory by adding in non-deducible moves.

    Returns
    -------
    int
        The difference between the puzzle's new clue count and its old.

    See Also
    --------
    minimize : a method that makes puzzles harder by removing clues.

    """
    clues_added = 0
    solver = Solver(puzzle.duplicate())
    solver.autosolve()
    for move in solver.guessed_moves():
        puzzle.set_cell(*move)
        clues_added += 1
    return clues_added


def minimize(puzzle, threshold=17):
    """Remove clues not needed for a unique solution; return amount removed.

    Remove all clues from `puzzle` that are not needed for it to have a
    single solution (provided it's initial clue count is above
    `threshold`).

    Parameters
    ----------
    puzzle : Board instance
        The puzzle from which to remove unnecessary clues.
    threshold : int, optional
        Puzzles with their number of clues less than or equal to this value
        will not be minimized further (default 17).

    Returns
    -------
    int
        The difference between the puzzle's new clue count and its old.

    See Also
    --------
    make_satisfactory : a method that makes puzzles easier by adding clues.

    Notes
    -----
    The default for `threshold` is 17 because that's the minimum number of
    clues needed to guarantee a unique solution to the puzzle.[1]_ This
    function does not check that the minimized puzzle has the same solution
    as the original one, but that outcome should be inevitable: the
    function only ever removes clues, and removing a clue from a Sudoku
    will never remove a solution from the solution set; at most, doing so
    adds one or more new solutions, and since the function undoes any
    removals that increase the size of the solution set, the solution sets
    of the original and the minimized puzzle have to be the same.

    References
    ----------
    .. [1] G. McGuire, B. Tugemann and G. Civario, "There Is No 16-Clue
    Sudoku: Solving the Sudoku Minimum Number of Clues Problem via
    Hitting Set Enumeration", Experimental Mathematics, vol. 23, no. 2,
    pp. 190-217, 2012. Available at: https://arxiv.org/abs/1201.0749
    [Accessed 25 Jun. 2017].

    """
    original_clue_count = puzzle.clue_count()

    if threshold < 17 or original_clue_count <= threshold:
        return 0

    solver = Solver(puzzle)
    while True:
        clues_removed = 0
        for (num, row, col) in puzzle.clues():
            puzzle.set_cell(Board.BLANK, row, col)
            if solver.solution_count(limit=2) != 1:
                # Multiple solutions after this change, so reset
                puzzle.set_cell(num, row, col)
            else:
                clues_removed += 1
        if not clues_removed:
            break

    return puzzle.clue_count() - original_clue_count


def make_rotationally_symmetric(puzzle, minimized=False, keep_satisfactory=False):
    """Give puzzle 180-deg rotational symmetry; return clue count change.

    Add and, if `minimized` is True, remove clues from `puzzle` such that,
    if this new puzzle were rotated 180 degrees, the cells with clues in
    them in the rotated and non-rotated puzzles would be the same.

    Parameters
    ----------
    puzzle : Board instance
        The puzzle to make symmetric by adding or removing clues.
    minimized : bool, optional
        True if clues may be removed from the puzzle provided this can be
        done while preserving symmetry and properness, and False if
        symmetry may only be created by adding clues (default False).
    keep_satisfactory : bool, optional
        Used when `minimized` is True to determine if clues whose removal
        introduce guessing may still be removed (`keep_satisfactory=True`)
        or if that should be prevented (`keep_satisfactory=False`) (default
        False).

    Returns
    -------
    int
        The difference between the puzzle's new clue count and its old.

    """
    clues = puzzle.clues()
    original_clue_count = len(clues)

    original_guess_count = 0
    if keep_satisfactory:
        temp_solver = Solver(puzzle.duplicate())
        temp_solver.autosolve()
        original_guess_count = len(temp_solver.guessed_moves())

    solver = Solver(puzzle.duplicate())
    solver.autosolve_without_history()

    for (num, row, col) in clues:
        rot_row, rot_col = _rotated_location(row, col)
        rot_num = solver.puzzle.get_cell(rot_row, rot_col)

        if not minimized:
            puzzle.set_cell(rot_num, rot_row, rot_col)
            continue

        # See if the puzzle still has a unique solution with the clues at
        # the original location and its rotational partner location removed
        puzzle.set_cell(Board.BLANK, row, col)
        puzzle.set_cell(Board.BLANK, rot_row, rot_col)

        temp_solver = Solver(puzzle.duplicate())
        if temp_solver.solution_count(limit=2) != 1 or keep_satisfactory:
            new_guess_count = 0
            if keep_satisfactory:
                # Check if changes introduced additional guesses
                temp_solver.autosolve()
                new_guess_count = len(temp_solver.guessed_moves())

            if not keep_satisfactory or new_guess_count > original_guess_count:
                # Puzzle no longer has a unique solution or now has more
                # guesses than before; undo changes
                puzzle.set_cell(num, row, col)
                puzzle.set_cell(rot_num, rot_row, rot_col)

    return puzzle.clue_count() - original_clue_count


def _rotated_location(row, col, rotations=2):
    # Return location if rotated by `rotations`*90 degrees
    max_row = max(Board.SUDOKU_ROWS)
    rot_row = row
    rot_col = col

    for _ in range(rotations % 4):
        rot_row = col
        rot_col = max_row - row
        row, col = rot_row, rot_col

    return (rot_row, rot_col)


def random_seed(rand_min=0, rand_max=2147483647):
    """Return a random integer between the given min and max inclusive.

    Parameters
    ----------
    rand_min : int, optional
        The minimum seed (default 0).
    rand_max : int, optional
        The maximum seed (default 2**31 - 1).

    """
    # Effectively include `rand_max` if using `numpy.random`
    upper_limit_adjustment = 1 if using_numpy_random() else 0
    return random.randint(rand_min, rand_max+upper_limit_adjustment)


def using_numpy_random():
    """Return True if `numpy.random`, not builtin `random`, is being used.

    Returns
    -------
    bool
        True if RNG is provided by `numpy.random`, and False if provided by
        Python's builtin `random`.

    """
    return _USING_NUMPY_RANDOM
