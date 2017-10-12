# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import random
import unittest

import sudb.generator as generator
from sudb.board import Board
from sudb.solver import Solver


class TestGeneratorMethods(unittest.TestCase):

    MINIMIZABLE_SEEDS = [1, 2, 3]
    # Seeds that, when generated with `minimized=True`, yield puzzles that require guessing
    NONSATISFACTORY_SEEDS = [3, 5, 12]

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

        # Test that it removes no clues if puzzle's clue count is <= `threshold`
        original_puzzle = Board()
        minimized_puzzle = original_puzzle.duplicate()
        clues_removed = generator.minimize(minimized_puzzle, threshold=17)
        self.assertFalse(clues_removed)

        # Test that it minimizes puzzle and returns difference of clue count
        for seed in self.MINIMIZABLE_SEEDS:
            original_puzzle = generator.solved_puzzle(seed)
            minimized_puzzle = original_puzzle.duplicate()
            clues_removed = generator.minimize(minimized_puzzle)
            self.assertGreater(clues_removed, 0)
            clue_difference = original_puzzle.clue_count() - minimized_puzzle.clue_count()
            self.assertEqual(clues_removed, clue_difference)

    def test_random_seed(self):
        # Just some basic tests
        self.assertEqual(generator.random_seed(rand_min=0, rand_max=0), 0)
        with self.assertRaises(ValueError):
            generator.random_seed(rand_min=1, rand_max=0)

    def test_similar_puzzle(self):
        # Test that it fails when the puzzle has fewer clues than `min_clues`
        similar_puzzle = generator.similar_puzzle(Board(), random.random(), min_clues=17)
        self.assertFalse(similar_puzzle)

        # Test that the similar puzzle has at least `min_clues` from original
        original_puzzle = generator.solved_puzzle(random.random())
        original_clues = set(original_puzzle.clues())
        min_seed = generator.random_seed()
        # Small to keep the test short
        test_seed_count = 50
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
