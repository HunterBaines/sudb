# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import random
import unittest

import numpy as np

import sudb.generator as generator
from sudb.board import Board
from sudb.solver import Solver


class TestGeneratorMethods(unittest.TestCase):

    MINIMIZABLE_SEEDS = [1, 5, 6]
    # Seeds that, when generated with `minimized=True`, yield puzzles that
    # require guessing
    NONSATISFACTORY_SEEDS = [3, 13, 15]


    @classmethod
    def setUpClass(cls):
        # For reproducible tests, initialize `random` with predefined seed
        cls.seed = 198404
        #cls.seed = random.random()
        random.seed(cls.seed)


    def test_generate(self):
        # Test that the same seed generates the same puzzle
        seed = random.random()
        puzzle1 = generator.generate(seed)
        puzzle2 = generator.generate(seed)
        self.assertEqual(puzzle1, puzzle2)

        # Test that `minimized` parameter works
        seed = self.MINIMIZABLE_SEEDS[0]
        puzzle1 = generator.generate(seed, minimized=True)
        puzzle2 = generator.generate(seed, minimized=False)
        self.assertLess(puzzle1.clue_count(), puzzle2.clue_count())

        # Test that `symmetric` parameter works
        puzzle2 = generator.generate(seed, symmetric=True)
        rows = map(tuple, np.array(self._binarize_rows(puzzle2.rows())))
        # `k=-2` means 180-degree, clockwise rotation
        rot_rows = map(tuple, np.rot90(rows, k=-2))
        self.assertEqual(rows, rot_rows)


    def test_make_rotationally_symmetric(self):
        for seed in self.MINIMIZABLE_SEEDS:
            puzzle = generator.generate(seed)
            prev_clue_count = 0
            for minimized in [False, True]:
                iter_info = 'for seed={} and minimized={}'.format(seed, minimized)
                symmetric_puzzle = puzzle.duplicate()
                # Test that the reported clue difference is correct
                clue_difference = generator.make_rotationally_symmetric(symmetric_puzzle,
                                                                        minimized=minimized)
                expected_clue_difference = symmetric_puzzle.clue_count() - puzzle.clue_count()
                assertion_msg = '{} != {} {}'.format(clue_difference, expected_clue_difference,
                                                     iter_info)
                self.assertEqual(clue_difference, expected_clue_difference, assertion_msg)

                clue_count = symmetric_puzzle.clue_count()
                if prev_clue_count:
                    # Test that the minimized puzzle has no more clues than
                    # the symmetric one (NB `MINIMIZABLE_SEEDS` are not
                    # necessarily minimizable while also maintaining
                    # symmetry)
                    assertion_msg = '{} > {} {}'.format(clue_count, prev_clue_count, iter_info)
                    self.assertLessEqual(clue_count, prev_clue_count, assertion_msg)
                    prev_clue_count = 0
                prev_clue_count = 0 if minimized else clue_count

                # Test that the puzzle is actually symmetric
                rows = map(tuple, np.array(self._binarize_rows(symmetric_puzzle.rows())))
                rot_rows = map(tuple, np.rot90(rows, k=-2))
                assertion_msg = '{} != {} {}'.format(rows, rot_rows, iter_info)
                self.assertEqual(rows, rot_rows, assertion_msg)

        puzzle = generator.generate(self.NONSATISFACTORY_SEEDS[0], minimized=True)
        satisfactory_puzzle = puzzle.duplicate()
        clue_difference = generator.make_satisfactory(satisfactory_puzzle)
        puzzle_differences = puzzle.differences(satisfactory_puzzle)
        # Test that clues were added
        self.assertGreater(puzzle_differences, 0)
        # Make puzzle symmetric while keeping it satisfactory
        generator.make_rotationally_symmetric(satisfactory_puzzle, minimized=True,
                                              keep_satisfactory=True)

        # Test that the puzzle is now actually symmetric
        rows = map(tuple, np.array(self._binarize_rows(satisfactory_puzzle.rows())))
        rot_rows = map(tuple, np.rot90(rows, k=-2))
        self.assertEqual(rows, rot_rows)

        # Test that the puzzle is still satisfactory
        solver = Solver(satisfactory_puzzle)
        solver.autosolve()
        self.assertFalse(len(solver.guessed_moves()))

    @staticmethod
    def _binarize_rows(rows):
        return [[True if val != Board.BLANK else False for val in row] for row in rows]


    def test_make_satisfactory(self):
        # Test that the return value is 0 when nothing can be added
        solved_puzzle = generator.solved_puzzle(random.random())
        clues_added = generator.make_satisfactory(solved_puzzle)
        self.assertFalse(clues_added)

        for seed in self.NONSATISFACTORY_SEEDS:
            original_puzzle = generator.generate(seed, minimized=True)
            satisfactory_puzzle = original_puzzle.duplicate()

            # Test that it added clues
            clues_added = generator.make_satisfactory(satisfactory_puzzle)
            self.assertGreater(clues_added, 0)

            # Test that the reported number of clues added is accurate
            clue_difference = satisfactory_puzzle.clue_count() - original_puzzle.clue_count()
            self.assertEqual(clues_added, clue_difference)

            # Test that it actually eliminated guesses
            solver = Solver(satisfactory_puzzle)
            solver.autosolve()
            self.assertFalse(len(solver.guessed_moves()))

    def test_minimize(self):
        # Test that it removes no clues if `threshold` is below 17
        original_puzzle = generator.solved_puzzle(random.random())
        minimized_puzzle = original_puzzle.duplicate()
        clues_removed = generator.minimize(minimized_puzzle, threshold=16)
        self.assertFalse(clues_removed)

        # Test that it removes no clues if puzzle's clue count is <=
        # `threshold`
        original_puzzle = Board()
        minimized_puzzle = original_puzzle.duplicate()
        clues_removed = generator.minimize(minimized_puzzle, threshold=17)
        self.assertFalse(clues_removed)

        # Test that it minimizes puzzle and returns difference of clue
        # count
        for seed in self.MINIMIZABLE_SEEDS:
            original_puzzle = generator.solved_puzzle(seed)
            minimized_puzzle = original_puzzle.duplicate()
            clues_removed = generator.minimize(minimized_puzzle)
            self.assertLess(clues_removed, 0)
            clue_difference = minimized_puzzle.clue_count() - original_puzzle.clue_count()
            self.assertEqual(clues_removed, clue_difference)

    def test_random_seed(self):
        # Just some basic tests
        self.assertEqual(generator.random_seed(rand_min=0, rand_max=0), 0)
        with self.assertRaises(ValueError):
            generator.random_seed(rand_min=1, rand_max=0)

    def test_similar_puzzle(self):
        # Test that it fails when the puzzle has fewer clues than
        # `min_clues`
        similar_puzzle = generator.similar_puzzle(Board(), random.random(), min_clues=17)
        self.assertFalse(similar_puzzle)

        # Test that the similar puzzle has at least `min_clues` from
        # original
        original_puzzle = generator.solved_puzzle(random.random())
        original_clues = set(original_puzzle.clues())
        min_seed = generator.random_seed()
        # Small to keep the test short
        test_seed_count = 5
        for seed in range(min_seed, min_seed + test_seed_count + 1):
            min_clues = random.randint(17, 34)
            similar_puzzle = generator.similar_puzzle(original_puzzle, seed, min_clues=min_clues)
            similar_clues = set(similar_puzzle.clues())
            self.assertGreaterEqual(len(original_clues.intersection(similar_clues)), min_clues)

    def test_solved_puzzle(self):
        # Test that the generated puzzle is actually solved
        min_seed = generator.random_seed()
        # Small to keep the test short
        test_seed_count = 100
        for seed in range(min_seed, min_seed + test_seed_count + 1):
            puzzle = generator.solved_puzzle(seed)
            self.assertTrue(puzzle.is_consistent() and puzzle.is_complete())
