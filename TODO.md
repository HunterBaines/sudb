TODO
====

/
-
* 9e9c458: ~~Document `stepb`, `stepc`, and `stepr` in README~~

* Transition as much as possible to python-3-style code without breaking
  python 2 compatibility.


/sudb
-----
* fff7a48: ~~Add to `SolverController.Options` an option for defining color
  mappings (e.g., `Solver.MoveType.GUESSED` -> `formatter.Color.GREEN`,
  etc.) and update the rest of `SolverController` to use these mappings.~~

* 835fb0e: ~~Python 3 compatibility: fix uses of `map`, `filter`, and `zip`
  that expect a list to be returned instead of, as in Python 3, an
  iterator.~~

* c8b1852: ~~Python 3 compatibility: use `input`, not `raw_input`, e.g. by
  using `from builtins import input`.~~

* Python 3 compatibility: adapt to changes to `urllib` in Python 3 (note
  that Python 3's `urlretrieve` no longer handles filenames).

* Python 3 compatibility: adapt to `random` not generating same values
  given same seed across Python 2 and 3

* 9d2f13e: ~~Python 3 compatibility: figure out why the puzzle associated
  with a given seed is not stable in Python 3 (it definitely involves the
  Solver method `autosolve_without_history`---and ultimately, it seems, the
  backend `_exact_hitting_set` in particular)~~

* Add a new `set` subcommand (maybe `set explainview`) that defaults to
  printing the board with the reasons for the last move highlighted after
  each step.

* 6a6ffc1: ~~Tab complete user-defined strings like checkpoint labels.~~

* Consider moving some static methods and inner classes to the module level
  instead of tucking them away inside the module's primary class.

* Consider adding a `watch ROW COL [ROW COL ...]` command to
  `SolverController` that breaks stepping when the candidate list for a
  location changes.

* Consider adding an `alias` command.

* When using step variants that prioritize (`stepb`, `stepc`, `stepr`),
  consider prioritizing other locations that might allow deductions to be
  found sooner in the target locations (e.g., for `stepb 1`, the other
  boxes in the same band and stack could be prioritized behind box 1) or
  even peek at the candidate lists for the target locations and prioritize
  other locations whose own candidate lists suggest that they could help
  thin out the original lists if their clues could be determined.


/test
-----
* Write a README for testing

* Write tests for "\_\_main\_\_.py" (specifically for its commandline
  options)

* Write tests for "board.py"

* Write tests for "importer.py"

* Once "controller.py", "\_\_main\_\_.py", "board.py", and "importer.py" have
  tests, write tests for any other files with poor test coverage


### /test/test\_controller\_\*.py ###
* c28eb89: ~~Write output test for `checkpoint`-related commands:
  `checkpoint`, `restart`, `delete checkpoint`, `print checkpoint`, and
  `info checkpoint`.~~

* 722ec16: ~~Write output test for `breakpoint`-related commands:
  `breakpoint`, `delete`/`delete breakpoint`, and `info breakpoint`~~

* 8728dcd: ~~Write output test for everything that can be set with `set`~~

* 597bb9e: ~~Write output test(s) for all step variants: `step`, `stepm`,
  `stepb`, `stepc`, and `stepr`. Make sure all break on breakpoints.~~

* 597bb9e: ~~Write output test for `unstep` (if not already sufficiently
  tested in step-variant tests)~~

* Write output test for candidate-related commands: `x` and `print
  candidates`.

* Write output test for `explain` command
