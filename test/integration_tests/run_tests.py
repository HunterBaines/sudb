import os
import sys


def main():
    #interpreter = 'python'
    interpreter = 'coverage run --append --omit="/usr/local/lib/*"'
    executable = '../../sudb/sudb.py'
    test_all(interpreter, executable)


def run(command, print_command=True):
    if print_command:
        # To help with figuring out where things went wrong
        sys.stderr.write('$ {}\n'.format(command))
    os.system(command)


def test_all(interpreter, executable):
    base_command = '{} {}'.format(interpreter, executable)

    puzzle = 'puzzle1.txt'
    # Test auto mode
    command = '{} --file {} --auto --difference --ascii'.format(base_command, puzzle)
    run(command)

    # Test interactive mode
    script = 'puzzle1_test_script.txt'
    command = '{} --file {} --execute "source {}"'.format(base_command, puzzle, script)
    run(command)

    # Test line import
    lines = '100624008 360700520 400000009 000207000 000000037'
    lines += ' 030180090 209310000 000006100 070000000'
    command = '{} --lines {} --auto'.format(base_command, lines)
    run(command)

    # Test minimizing
    command = '{} --file {} --minimize --auto'.format(base_command, puzzle)
    run(command)

    # Test guessing
    puzzle = 'puzzle2.txt'
    script = 'puzzle2_test_script.txt'
    command = '{} --file {} --execute "source {}"'.format(base_command, puzzle, script)
    run(command)

    # Test making satisfactory
    command = '{} --file {} --satisfactory --auto'.format(base_command, puzzle)
    run(command)

    # Test minimizing and making satisfactory
    command = '{} --file {} --minimize --satisfactory --auto'.format(base_command, puzzle)
    run(command)

    # Test generating
    command = '{} --random 12345 --auto'.format(base_command)
    run(command)
    command = '{} --random 1 2 3 4 5 --auto'.format(base_command)
    run(command)

    # Test importing from image
    puzzle = 'puzzle3.png'
    command = '{} --file {} --auto'.format(base_command, puzzle)
    run(command)

    # Test importing from stdin
    puzzle = 'puzzle4.txt'
    command = 'cat {} | {} --auto'.format(puzzle, base_command)
    run(command)

    # Test importing multiple puzzles with alternate formats and titles
    puzzle = 'puzzle5.txt'
    command = '{} --file {} --auto'.format(base_command, puzzle)
    run(command)

    # Test importing from non-existent file
    puzzle = 'fakefile.txt'
    command = '{} --file {} --auto'.format(base_command, puzzle)
    run(command)

    # Test importing inconsistent puzzle
    puzzle = 'puzzle6.txt'
    command = '{} --file {} --auto'.format(base_command, puzzle)
    run(command)

    # Test importing improper puzzle
    puzzle = 'puzzle7.txt'
    command = '{} --file {} --auto'.format(base_command, puzzle)
    run(command)

    # Test importing and running script from stdin
    puzzle = 'puzzle8.txt'
    command = 'cat {} | {}'.format(puzzle, base_command)
    run(command)


if __name__ == '__main__':
    main()
