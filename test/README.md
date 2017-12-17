Testing
=======
Make sure all the [requirements](#requirements) below are satisfied and
that you are in the project's root directory. Then see the relevant section
for the type of tests you want to perform:

* [Manual Testing](#manual-testing)
* [Unit Testing](#unit-testing)
* [Coverage Testing](#coverage-testing)


Requirements
------------
* A terminal configured for UTF-8 output
* Python 3 Modules:
    + `numpy`
    + `scipy`
    + `PIL`
    + `pytesseract`
* Programs:
    + `tesseract-ocr`
    + `python3-coverage` (if doing coverage testing)


Manual Testing
--------------
To manually test `sudb` without installing it, call it from the project's
root directory as follows (plus whatever commandline options you need):

```shell
$ python3 -m sudb
```


Unit Testing
------------
Unit tests use Python's builtin `unittest` module. If already in the
project's root directory, the following examples should work:

```shell
# run all tests
$ python3 -m unittest discover --verbose

# run all controller tests
$ python3 -m unittest discover --verbose --pattern test_controller*.py

# run tests from "test/test_solver.py" only
$ python3 -m unittest --verbose test.test_solver
```


Coverage Testing
----------------
If the Python 3 version of `coverage` is installed, all of the commands for
unit testing should work using `coverage run --append` instead of
`python3`. Here is an example session using `coverage` (again, in the
project's root directory):

```shell
# clear previous results
$ coverage erase

# run all tests while keeping track of test coverage
$ coverage run --append -m unittest discover --verbose

# report coverage results in terminal
$ coverage report --include=sudb/*.py

# generate HTML results
$ coverage html --include=sudb/*.py

# view HTML results in browser
$ xdg-open "$(pwd)/htmlcov/index.html"
```

If coverage on "sudb/\_\_main\_\_.py" is low (or non-existent), make sure
you used `coverage run --append`, not just `coverage run`. If that was
already the case, try rerunning with `SUDB_COVERAGE= coverage run
--append`. The tests for this file themselves call an interpreter to run
`sudb`, which needs to be `coverage run --append` (instead of `python3`)
for those calls to count toward the overall coverage. By default, these
tests will try to detect if they are being run via `coverage`, but that
[won't work in all
shells](https://github.com/HunterBaines/sudb/blob/4a6ce2cf07dd6996c4bd4747d331da40b4e74e53/test/main_tester.py#L29).
