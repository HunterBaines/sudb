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

* Add a new `set` subcommand (maybe `set explainview`) that defaults to
  printing the board with the reasons for the last move highlighted after
  each step.

* 6a6ffc1: ~~Tab complete used-defined strings like checkpoint labels.~~

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

* Write tests for "sudb.py" (specifically for its commandline options)

* Write tests for "board.py"

* Write tests for "importer.py"

* Once "controller.py", "sudb.py", "board.py", and "importer.py" have
  tests, write tests for any other files with poor test coverage


### /test/test\_controller\_\*.py ###
* Write output test for `checkpoint`-related commands: `checkpoint`,
  `restart`, `delete checkpoint`, `print checkpoint`, and `info
  checkpoint`.

* Write output test for `breakpoint`-related commands: `breakpoint`,
  `delete`/`delete breakpoint`, `info breakpoint`, and all step variants as
  well as `finish` in so far as each should actually break on breakpoints

* Write output test for everything that can be set with `set`

* Write output test(s) for all step variants: `step`, `stepm`, `stepb`,
  `stepc`, and `stepr`

* Write output test for `unstep` (if not already sufficiently tested in
  step-variant tests)

* Write output test for candidate-related commands: `x` and `print
  candidates`.

* Write output test for `explain` command
