# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import unittest

import sudb.generator as generator


class TestGeneratorUniqueness(unittest.TestCase):
    """Test if a range of seeds ever generate the same puzzle.

    """

    START_SEED = 0
    # A small amount so this doesn't hold back `python -m unittest discover`
    END_SEED = 5

    def test_uniqueness(self):
        # NB: Testing this well requires generating from many seeds, which takes a long time
        # (on my machine, running this test with 1001 seeds takes about 11.3 minutes). As of
        # 2017 November 6, the test passes for seeds between 0 and 10000 inclusive.
        puzzle_hash_dict = {}
        repeated_puzzles = []

        for seed in range(self.START_SEED, self.END_SEED + 1):
            # A waste of time to duplicate puzzle; a waste of space to store it in dict
            puzzle_hash = hash(generator.generate(seed))
            try:
                puzzle_hash_dict[puzzle_hash].add(seed)
                repeated_puzzles.append(puzzle_hash)
            except KeyError:
                puzzle_hash_dict[puzzle_hash] = {seed}

        repeated_seeds = [puzzle_hash_dict[p] for p in repeated_puzzles]
        # Designed to show `repeated_seeds` if assertion fails
        self.assertEqual(repeated_seeds, [])

        max_unique_puzzles = self.END_SEED - self.START_SEED + 1
        # Designed to show number of unique puzzles relative to number possible if assertion fails
        self.assertEqual(len(puzzle_hash_dict), max_unique_puzzles)
