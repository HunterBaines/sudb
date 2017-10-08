# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

import unittest

from sudb.board import Board
from sudb.solver import Solver


class TestSolverMethods(unittest.TestCase):

    PUZZLE_LINES = ['000003017', '015009008', '060000000', '100007000', '009000200',
                    '000500004', '000000020', '500600340', '340200000']
    SOLVED_LINES = ['294863517', '715429638', '863751492', '152947863', '479386251',
                    '638512974', '986134725', '521678349', '347295186']
    INITIAL_MOVE_TYPES = [Solver.MoveType.ROWWISE, Solver.MoveType.ROWWISE,
                          Solver.MoveType.COLWISE, Solver.MoveType.COLWISE,
                          Solver.MoveType.COLWISE, Solver.MoveType.GUESSED]
    # For each (num, row) key, a set of (row, col) locations where num can be placed
    POSSIBLE_IN_ROW = {(5, 0): {(0, 4), (0, 6)},
                       (7, 4): {(4, 0), (4, 1), (4, 7)},
                       (1, 8): {(8, 2), (8, 4), (8, 5), (8, 6), (8, 8)}}
    # For each (num, col) key, a set of (row, col) locations where num can be placed
    POSSIBLE_IN_COL = {(6, 0): {(4, 0), (5, 0), (6, 0)},
                       (9, 4): {(3, 4), (5, 4), (6, 4), (7, 4), (8, 4)},
                       (4, 6): {(0, 6), (1, 6), (2, 6)}}
    REASONS = {(1, 7): {(8, 0), (0, 5), (7, 6)},
               (2, 8): {(4, 6), (6, 7), (8, 3)}}
    SOLUTION_COUNT = 1


    def setUp(self):
        self.board = Board(lines=self.PUZZLE_LINES)
        self.solved_board = Board(lines=self.SOLVED_LINES)
        self.solver = Solver(self.board)
        self.algorithms = [None, 'backtrack']
        self.clue_difference = self.solved_board.clue_count() - self.board.clue_count()


    def test_eq(self):
        duplicate_solver = self.solver.duplicate()
        self.assertTrue(duplicate_solver == self.solver)
        self.assertFalse(duplicate_solver != self.solver)
        location = duplicate_solver.step()
        if not location:
            location = duplicate_solver.step_best_guess()
        self.assertTrue(location)
        self.assertTrue(duplicate_solver != self.solver)
        self.assertFalse(duplicate_solver == self.solver)

    def test_all_solutions(self):
        for alg in self.algorithms:
            duplicate_solver = self.solver.duplicate()
            solved_puzzle_count = 0
            for puzzle in duplicate_solver.all_solutions(algorithm=alg):
                solved_puzzle_count += 1
                self.assertEqual(puzzle, self.solved_board)
            self.assertEqual(solved_puzzle_count, self.SOLUTION_COUNT)

    def test_annotated_moves(self):
        duplicate_solver = self.solver.duplicate()
        manual_annotated_moves = []
        for expected_move_type in self.INITIAL_MOVE_TYPES:
            location = duplicate_solver.step()
            if not location:
                location = duplicate_solver.step_best_guess()
            row, col = location
            expected_num = self.solved_board.get_cell(row, col)
            manual_annotated_moves.append((expected_num, row, col, expected_move_type))
        self.assertEqual(manual_annotated_moves, duplicate_solver.annotated_moves())

    def test_autosolve(self):
        # Test with guesses allowed
        duplicate_solver = self.solver.duplicate()
        is_solved = duplicate_solver.autosolve()
        self.assertTrue(is_solved)
        self.assertEqual(duplicate_solver.puzzle, self.solved_board)
        self.assertEqual(duplicate_solver.move_count(), self.clue_difference)
        # Test without guesses allowed
        duplicate_solver = self.solver.duplicate()
        is_solved = duplicate_solver.autosolve(allow_guessing=False)
        if not is_solved:
            self.assertEqual(duplicate_solver.last_move_type(), Solver.MoveType.GUESSED)

    def test_autosolve_without_history(self):
        for alg in self.algorithms:
            duplicate_solver = self.solver.duplicate()
            initial_move_count = duplicate_solver.move_count()
            is_solved = duplicate_solver.autosolve_without_history(algorithm=alg)
            self.assertTrue(is_solved)
            final_move_count = duplicate_solver.move_count()
            self.assertEqual(initial_move_count, final_move_count)
            self.assertEqual(duplicate_solver.puzzle, self.solved_board)

    def test_best_guess(self):
        # Test "guess" part of "best guess"
        duplicate_solver = self.solver.duplicate()
        num, row, col = duplicate_solver.best_guess()
        self.assertEqual(duplicate_solver.puzzle.get_cell(row, col), Board.BLANK)
        expected_num = self.solved_board.get_cell(row, col)
        self.assertEqual(num, expected_num)
        # Test "best" part of "best guess"
        duplicate_solver.step_manual(num, row, col)
        max_steps_possible = len(Board.SUDOKU_CELLS) - duplicate_solver.puzzle.clue_count()
        steps_made = duplicate_solver.step_until_stuck()
        if steps_made != max_steps_possible:
            blank_locations = duplicate_solver.puzzle.differences(self.solved_board)
            for (temp_row, temp_col) in blank_locations:
                temp_num = self.solved_board.get_cell(temp_row, temp_col)
                temp_solver = self.solver.duplicate()
                temp_solver.step_manual(temp_num, temp_row, temp_col)
                temp_steps_made = duplicate_solver.step_until_stuck()
                self.assertLessEqual(temp_steps_made, steps_made)

    def test_candidates(self):
        for (row, col) in Board.SUDOKU_CELLS:
            duplicate_puzzle = self.board.duplicate()
            candidates = self.solver.candidates(row, col)
            actual_num = self.solved_board.get_cell(row, col)
            # Each candidate set should include the actual number at location in solved puzzle
            self.assertIn(actual_num, candidates)
            for num in candidates:
                duplicate_puzzle.set_cell(num, row, col)
                # No candidate should leave the puzzle inconsistent
                self.assertTrue(duplicate_puzzle.is_consistent())

    def test_deduced_moves(self):
        duplicate_solver = self.solver.duplicate()
        duplicate_solver.autosolve()
        actual_deduced_moves = duplicate_solver.deduced_moves()
        actual_deduced_moves.reverse()
        for (num, row, col, move_type) in duplicate_solver.annotated_moves():
            if move_type in [Solver.MoveType.ROWWISE, Solver.MoveType.COLWISE]:
                actual_move = actual_deduced_moves.pop()
                expected_move = (num, row, col)
                self.assertEqual(actual_move, expected_move)

    def test_duplicate(self):
        duplicate_solver = self.solver.duplicate()
        # Initially both should be equal
        self.assertEqual(self.solver, duplicate_solver)
        duplicate_solver.step()
        # Changing one should not change the other
        self.assertNotEqual(self.solver, duplicate_solver)
        duplicate_solver = self.solver.duplicate()
        # Test duplicating when `solved_puzzle` is defined
        duplicate_solver.solved_puzzle = self.solved_board.duplicate()
        new_duplicate_solver = duplicate_solver.duplicate()
        # Changing `solved_puzzle` here should not change it in `new_duplicate_solver`
        duplicate_solver.solved_puzzle.set_cell(Board.BLANK, 0, 0)
        self.assertEqual(new_duplicate_solver.solved_puzzle, self.solved_board)

    def test_guessed_moves(self):
        duplicate_solver = self.solver.duplicate()
        duplicate_solver.autosolve()
        actual_guessed_moves = duplicate_solver.guessed_moves()
        actual_guessed_moves.reverse()
        for (num, row, col, move_type) in duplicate_solver.annotated_moves():
            if move_type == Solver.MoveType.GUESSED:
                actual_move = actual_guessed_moves.pop()
                expected_move = (num, row, col)
                self.assertEqual(actual_move, expected_move)

    def test_last_move_type(self):
        duplicate_solver = self.solver.duplicate()
        # When no moves have been made, the move type should be NONE
        self.assertEqual(duplicate_solver.last_move_type(), Solver.MoveType.NONE)
        for given_move_type in self.INITIAL_MOVE_TYPES:
            location = duplicate_solver.step()
            if not location:
                duplicate_solver.step_best_guess()
            actual_move_type = duplicate_solver.last_move_type()
            self.assertEqual(given_move_type, actual_move_type)

    def test_manual_moves(self):
        duplicate_solver = self.solver.duplicate()
        duplicate_solver.autosolve()
        actual_manual_moves = duplicate_solver.manual_moves()
        actual_manual_moves.reverse()
        for (num, row, col, move_type) in duplicate_solver.annotated_moves():
            if move_type == Solver.MoveType.MANUAL:
                actual_move = actual_manual_moves.pop()
                expected_move = (num, row, col)
                self.assertEqual(actual_move, expected_move)

    def test_move_count(self):
        duplicate_solver = self.solver.duplicate()
        self.assertEqual(duplicate_solver.move_count(), 0)
        steps = 3
        for _ in range(steps):
            location = duplicate_solver.step()
            if not location:
                duplicate_solver.step_best_guess()
        self.assertEqual(duplicate_solver.move_count(), steps)
        unsteps = 1
        for _ in range(unsteps):
            duplicate_solver.unstep()
        self.assertEqual(duplicate_solver.move_count(), (steps - unsteps))

    def test_moves(self):
        duplicate_solver = self.solver.duplicate()
        expected_moves = set()
        blank_locations = duplicate_solver.puzzle.differences(self.solved_board)
        for (row, col) in blank_locations:
            num = self.solved_board.get_cell(row, col)
            expected_moves.add((num, row, col))
        duplicate_solver.autosolve()
        actual_moves = set(duplicate_solver.moves())
        self.assertEqual(actual_moves, expected_moves)

    def test_possible_locations_in_column(self):
        for ((num, col), expected_location_set) in self.POSSIBLE_IN_COL.items():
            actual_location_set = self.solver.possible_locations_in_column(num, col)
            self.assertEqual(actual_location_set, expected_location_set)

        with self.assertRaises(ValueError):
            # Invalid number
            self.solver.possible_locations_in_column(-1, 1)
        with self.assertRaises(ValueError):
            # Invalid column
            self.solver.possible_locations_in_column(1, -1)

    def test_possible_locations_in_row(self):
        for ((num, row), expected_location_set) in self.POSSIBLE_IN_ROW.items():
            actual_location_set = self.solver.possible_locations_in_row(num, row)
            self.assertEqual(actual_location_set, expected_location_set)

        with self.assertRaises(ValueError):
            # Invalid number
            self.solver.possible_locations_in_row(-1, 1)
        with self.assertRaises(ValueError):
            # Invalid row
            self.solver.possible_locations_in_row(1, -1)

    def test_possible_next_moves(self):
        expected_next_moves = set()
        for ((num, _), location_set) in self.POSSIBLE_IN_ROW.items():
            for (row, col) in location_set:
                expected_next_moves.add((num, row, col))
        for ((num, _), location_set) in self.POSSIBLE_IN_COL.items():
            for (row, col) in location_set:
                expected_next_moves.add((num, row, col))
        blank_locations = self.board.differences(self.solved_board)
        for (row, col) in blank_locations:
            num = self.solved_board.get_cell(row, col)
            expected_next_moves.add((num, row, col))
        actual_next_moves = self.solver.possible_next_moves()
        self.assertTrue(expected_next_moves.issubset(actual_next_moves))

    def test_reasons(self):
        duplicate_solver = self.solver.duplicate()
        locations = duplicate_solver.reasons()
        # If no move has been made, `reasons` should return empty set
        self.assertFalse(locations)

        breakpoints = self.REASONS.keys()
        while breakpoints and not duplicate_solver.puzzle.is_complete():
            location = duplicate_solver.step()
            if not location:
                location = duplicate_solver.step_best_guess()
            if location in breakpoints:
                del breakpoints[breakpoints.index(location)]
                expected_reasons = self.REASONS[location]
                actual_reasons = duplicate_solver.reasons()
                self.assertEqual(actual_reasons, expected_reasons)
        self.assertFalse(breakpoints)

    def test_solution_count(self):
        for alg in self.algorithms:
            self.assertEqual(self.solver.solution_count(algorithm=alg), self.SOLUTION_COUNT)

    def test_step(self):
        duplicate_solver = self.solver.duplicate()
        duplicate_solver.step()
        self.assertEqual(self.solver.move_count(), duplicate_solver.move_count() - 1)
        prev_num, prev_row, prev_col = duplicate_solver.moves()[-1]
        expected_num = int(self.SOLVED_LINES[prev_row][prev_col])
        self.assertEqual(prev_num, expected_num)

    def test_step_best_guess(self):
        # Just check that a guess has been installed (`test_best_guess` does rest)
        duplicate_solver = self.solver.duplicate()
        self.assertEqual(duplicate_solver.move_count(), 0)
        location = duplicate_solver.step_best_guess()
        self.assertTrue(location)
        self.assertEqual(duplicate_solver.move_count(), 1)
        self.assertEqual(duplicate_solver.last_move_type(), Solver.MoveType.GUESSED)

        # Test how it reacts to an unsolvable puzzle
        duplicate_solver.autosolve()
        correct_num = duplicate_solver.puzzle.get_cell(0, 0)
        inconsistent_num = (set(Board.SUDOKU_NUMBERS) - {correct_num}).pop()
        duplicate_solver.puzzle.set_cell(inconsistent_num, 0, 0)
        location = duplicate_solver.step_best_guess()
        # `step_best_guess` should return an empty tuple if `best_guess` fails
        self.assertFalse(location)

    def test_step_manual(self):
        duplicate_solver = self.solver.duplicate()

        with self.assertRaises(ValueError):
            # Invalid row
            duplicate_solver.step_manual(0, -1, 0)
        with self.assertRaises(ValueError):
            # Invalid column
            duplicate_solver.step_manual(0, 0, -1)

        blank_locations = duplicate_solver.puzzle.differences(self.solved_board)
        for (row, col) in blank_locations:
            num = self.solved_board.get_cell(row, col)
            duplicate_solver.step_manual(num, row, col)
        self.assertEqual(len(duplicate_solver.manual_moves()), len(blank_locations))
        self.assertEqual(duplicate_solver.puzzle, self.solved_board)

        correct_num = duplicate_solver.puzzle.get_cell(0, 0)
        inconsistent_num = (set(Board.SUDOKU_NUMBERS) - {correct_num}).pop()
        location = duplicate_solver.step_manual(inconsistent_num, 0, 0)
        # Test that `step_manual` rejects inconsistent moves by returning empty tuple
        self.assertFalse(location)
        # Test that the puzzle was not actually changed
        self.assertTrue(duplicate_solver.puzzle.is_consistent())


    def test_step_until_stuck(self):
        duplicate_solver = self.solver.duplicate()
        steps_made = duplicate_solver.step_until_stuck()

        try:
            index_of_first_guess = self.INITIAL_MOVE_TYPES.index(Solver.MoveType.GUESSED)
            self.assertEqual(steps_made, index_of_first_guess)
        except ValueError:
            pass

        if steps_made < self.clue_difference:
            location = duplicate_solver.step_best_guess()
            self.assertTrue(location)

    def test_unstep(self):
        duplicate_solver = self.solver.duplicate()
        # `unstep` should return empty tuple if nothing to unstep
        self.assertFalse(self.solver.unstep())
        location = duplicate_solver.step()
        if not location:
            duplicate_solver.step_best_guess()
        self.assertEqual(duplicate_solver.move_count(), 1)
        duplicate_solver.unstep()
        self.assertEqual(duplicate_solver.move_count(), 0)
        self.assertEqual(duplicate_solver, self.solver)


if __name__ == '__main__':
    unittest.main()
