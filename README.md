sudb
====

sudb is a Sudoku solver that can solve puzzles automatically or
interactively using GDB-style commands to query or control the solver.
Puzzles can be entered row by row, imported from text or image files, or
generated from a random seed. These puzzles can also be made harder by
removing unnecessary clues or easier by adding in clues that seem to
require guessing.


Running
-------
Add execute permission to the file sudb.py (e.g., `chmod +x sudb.py`) and
then invoke that file directly. For a quick demo, try this:

```
./sudb.py --auto --difference --file https://projecteuler.net/project/resources/p096_sudoku.txt
```

(The `--auto` option tells the program to solve the puzzles without
interaction; `--difference` tells it to colorize the cells in its solved
puzzle output that were originally blank.)


Importing
---------
To enter lines manually via stdin, invoke sudb without any import option
(e.g., `--lines`, `--file`, or `--random`). Each puzzle entered this way
should specify one row of the puzzle per line with 0 or any non-numeric,
non-whitespace character used for blank cells. Here is an example using '0'
as the character representing blanks:

```
100624008
360700520
400000009
000207000
000000037
030180090
209310000
000006100
070000000
```

The option `--lines LINE1 LINE2 ...` imports a Sudoku from the nine rows of
the puzzle passed to it as arguments (using the puzzle format just
described). One could import the above puzzle using this:

```
./sudb.py --lines 100624008 360700520 400000009 000207000 000000037 030180090 209310000 000006100 070000000
```

The option `--file FILENAME` imports puzzles from text or image files (or
URLs to either). Text files should follow the same format described above.
Multiple puzzles may be included in the same file, and the importer will do
its best to ignore lines that don't appear to part of the puzzles. Image
files should be cleanly cropped to the border of the puzzle with sharp text
and a high-contrast grid for best results---and even then the importer may
miss clues. Importing from images requires numpy, PIL, and pytesseract.

The option `--random [SEED]` generates a puzzle given one or more integer
seeds (or from a random seed if none is given).


Interacting
-----------
sudb defaults to an interactive mode in which one controls the solver using
an interface and commands modeled after the GNU Debugger. This is a brief
overview of some of those commands. To play along, import a puzzle without using
`--auto` (`./sudb.py --random 1979` will work just fine).

Note that all commands can be shortened if doing so causes no ambiguity. 


### Basic Commands ###
The command `help` displays a list of all commands, and `help COMMAND` gives a
brief description of what COMMAND does and how to use it.

The command `quit` exits the session associated with the current puzzle (though
not necessarily the program itself if any puzzles are left to be solved).


### Commands for Controlling the Solver ###
The command `step` (or `s`) moves the solver one clue forward. You can also
use something like `step 3` or `step 10` to move the solver a specified
number of steps forward.

The command `finish` steps until the puzzle is solved or the solver is at a
breakpoint.

The command `break ROW COLUMN` sets a breakpoint at the given row and column in
the puzzle, which will force the solver to pause itself if it discovers the
number that goes in the cell at that row and column. (Breakpoints can be listed
via `info breakpoint`.)

The command `x ROW COLUMN` lists all candidates the solver is currently
entertaining for a given cell. (The command `print candidates` does the
same but inline and for all cells.)

The command `explain` indicates how the solver deduced the previous move.


### Commands for Playing Along ###
The command `stepm ROW COLUMN NUMBER` (or `sm ROW COLUMN NUMBER` or simply `ROW
COLUMN NUMBER`) sets the value at the cell specified by (ROW, COLUMN) to NUMBER.

The command `unstep` undoes the last step (whether made via `step` or `stepm`).

The command `checkpoint LABEL` saves the board state under the given LABEL,
which can be returned to using `restart LABEL`. (Checkpoints can be listed via
`info checkpoint`.)

The command `mark ROW COLUMN NUMBER` stores NUMBER as a candidate for the cell
at the given location. This collection of candidates is kept separate from the
solver's.

The command `info mark ROW COL` lists all user-defined candidates at the given
location. (The command `print marks` does the same but inline and for all
cells.)

