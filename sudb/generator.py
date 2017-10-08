# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""Generate puzzles from seed or from other puzzles.

Examples
--------
>>> import generator
>>> import formatter as frmt
>>> seed = 4
>>> puzzle = generator.solved_puzzle(seed)
>>> print frmt.strfboard(puzzle, ascii_mode=True)
.........................
! 2 9 4 ! 8 7 6 ! 1 3 5 !
! 5 3 1 ! 2 9 4 ! 7 8 6 !
! 8 6 7 ! 5 3 1 ! 2 4 9 !
!.......!.......!.......!
! 3 1 6 ! 7 4 8 ! 9 5 2 !
! 9 2 5 ! 6 1 3 ! 8 7 4 !
! 4 7 8 ! 9 5 2 ! 6 1 3 !
!.......!.......!.......!
! 7 5 3 ! 1 2 9 ! 4 6 8 !
! 1 8 2 ! 4 6 5 ! 3 9 7 !
! 6 4 9 ! 3 8 7 ! 5 2 1 !
!.......!.......!.......!

>>> puzzle = generator.similar_puzzle(puzzle, seed)
>>> print frmt.strfboard(puzzle, ascii_mode=True)
.........................
! 2 _ 4 ! 8 9 5 ! _ _ _ !
! 9 _ _ ! 2 _ _ ! _ _ 6 !
! _ _ _ ! _ _ _ ! _ _ _ !
!.......!.......!.......!
! 3 _ 6 ! _ _ 8 ! _ 5 _ !
! _ _ _ ! 9 _ _ ! _ 1 _ !
! 4 _ _ ! _ _ _ ! 2 3 _ !
!.......!.......!.......!
! _ 5 _ ! _ 2 _ ! 4 _ _ !
! _ _ 2 ! _ 4 _ ! 3 9 7 !
! _ _ _ ! 3 _ 7 ! 5 _ _ !
!.......!.......!.......!

>>> generator.minimize(puzzle)
>>> print frmt.strfboard(puzzle, ascii_mode=True)
.........................
! 2 _ _ ! 8 9 5 ! _ _ _ !
! 9 _ _ ! 2 _ _ ! _ _ 6 !
! _ _ _ ! _ _ _ ! _ _ _ !
!.......!.......!.......!
! _ _ 6 ! _ _ 8 ! _ 5 _ !
! _ _ _ ! 9 _ _ ! _ 1 _ !
! 4 _ _ ! _ _ _ ! 2 _ _ !
!.......!.......!.......!
! _ 5 _ ! _ 2 _ ! 4 _ _ !
! _ _ _ ! _ 4 _ ! 3 9 7 !
! _ _ _ ! _ _ 7 ! _ _ _ !
!.......!.......!.......!

"""

import random

from board import Board
from solver import Solver


def generate(seed, minimized=False):
    """Return a puzzle generated from the provided seed.

    Return a satisfactory puzzle generated from `seed` with optional
    minimization if `minimized` is True.

    Parameters
    ----------
    seed : int, long, or hashable
        The seed to use for generating the puzzle.
    minimized : bool, optional
        Whether to attempt to remove redundant clues from generated puzzle
        (at the expense of additional time for generation) (default False).

    Returns
    -------
    Board instance
        The puzzle generated from the given seed.
    """

    puzzle = solved_puzzle(seed)
    puzzle = similar_puzzle(puzzle, seed)
    if minimized:
        minimize(puzzle, threshold=20)
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
    MIN_START_CLUES = 3

    random.seed(seed)
    target_row = random.choice(Board.SUDOKU_ROWS)
    columns = Board.SUDOKU_COLS[:]
    random.shuffle(columns)
    column_count = random.randint(MIN_START_CLUES, len(columns))

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
        The number of clues added.

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
        The number of clues removed.

    See Also
    --------
    make_satisfactory : a method that makes puzzles easier by adding clues.

    Notes
    -----
    This method does not guarantee that the minimized puzzle will have the
    same solution as the original, but that outcome is likely. The default
    for `threshold` is 17 because that's the minimum number of clues needed
    to guarantee a unique solution to the puzzle.[1]_

    References
    ----------
    .. [1] G. McGuire, B. Tugemann and G. Civario, "There Is No 16-Clue
    Sudoku: Solving the Sudoku Minimum Number of Clues Problem via
    Hitting Set Enumeration", Experimental Mathematics, vol. 23, no. 2,
    pp. 190-217, 2012. Available at: https://arxiv.org/abs/1201.0749
    [Accessed 25 Jun. 2017].
    """

    if threshold < 17 or puzzle.clue_count() <= threshold:
        return 0

    overall_clues_removed = 0
    solver = Solver(puzzle)

    while True:
        clues_removed = 0
        clues = puzzle.clues()
        for (num, row, col) in clues:
            puzzle.set_cell(Board.BLANK, row, col)
            if solver.solution_count() > 1:
                # Multiple solutions after this change, so reset
                puzzle.set_cell(num, row, col)
            else:
                clues_removed += 1
                overall_clues_removed += 1
        if not clues_removed:
            break

    return overall_clues_removed


def random_seed(rand_min=0, rand_max=2147483647):
    """Return a random integer between the given min and max.

    Parameters
    ----------
    rand_min : int, optional
        The minimum seed (default 0).
    rand_max : int, optional
        The maximum seed (default 2^31).
    """

    return random.randint(rand_min, rand_max)
