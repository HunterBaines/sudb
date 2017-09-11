# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""Extract digits from a Sudoku puzzle in an image.

Examples
--------
>>> import sudokuimg
>>> import formatter as frmt
>>> from board import Board
>>> puzzle_lines = sudokuimg.puzzle_lines('../puzzles/picpuz1.png')
>>> puzzle = Board(lines=puzzle_lines)
>>> print frmt.strfboard(puzzle, ascii_mode=True)
.........................
! _ _ _ ! _ 6 _ ! _ 3 _ !
! 2 4 _ ! _ _ _ ! 1 _ _ !
! _ _ 7 ! _ _ 2 ! _ _ 8 !
!.......!.......!.......!
! _ _ 1 ! 4 _ _ ! 3 _ 9 !
! 7 _ _ ! 3 1 9 ! _ _ 2 !
! 3 _ 6 ! _ _ 7 ! 5 _ _ !
!.......!.......!.......!
! 5 _ _ ! 7 _ _ ! 8 _ _ !
! _ _ 2 ! _ _ _ ! _ 1 3 !
! _ 7 _ ! _ 2 _ ! _ _ _ !
!.......!.......!.......!

"""

import os
import tempfile

import numpy
import pytesseract as tess
from PIL import Image


def puzzle_lines(filename):
    """Return a list of lines from the puzzle shown in the image file.

    Parameters
    ----------
    filename : str
        The path to the image of the Sudoku puzzle. It should be cleanly
        cropped with sharp text and a high-contrast grid, so photographs of
        a puzzle, for example, won't work, but even some nice, digitally
        produced images may be only partially readable.

    Returns
    -------
    list of str
        If successful, a list of 9 strings each with 9 characters. Each
        string represents a single row, and each character in the string
        represents a single entry in the puzzle (with '0' for blanks). If
        not successful, the list returned will be empty.
    """

    lines = []

    config_file = tempfile.NamedTemporaryFile()
    config_file.write("tessedit_char_whitelist 123456789")
    config_options = "-psm 10 {}".format(config_file.name)
    config_file.close()

    bw_filename = os.path.join(tempfile.gettempdir(), "bw_puzzle.png")
    if _binarize_image(filename, bw_filename):
        filename = bw_filename

    image = Image.open(filename)
    rows = _get_rows_from_grid(image, threshold=10)
    cols = _get_columns_from_grid(image, threshold=10)

    assert len(rows) >= 9, "Too few rows detected in puzzle."
    assert len(cols) >= 9, "Too few columns detected in puzzle."

    for (start_y, end_y) in rows:
        line = ""
        for (start_x, end_x) in cols:
            crop_area = (start_x+5, start_y+5, end_x-5, end_y-5)
            digit = image.crop(crop_area)
            digit = _autocropped(digit)
            digit_val = tess.image_to_string(digit, config=config_options)
            line += digit_val if digit_val else "0"
        lines.append(line)

    return lines


def _autocropped(image):
    """Return an autocropped version of the given PIL image object.

    Parameters
    ----------
    image : PIL ImageFile object
        A file opened via a call to PIL.Image.open(file).

    Returns
    -------
    PIL ImageFile object
        A version of `image` with any obvious border cropped out.
    """

    image.load()
    image_box = image.getbbox()
    cropped = image.crop(image_box)
    return cropped


def _uniform_pixels(pixels, threshold):
    """Return whether the pixels are uniform within the threshold.

    Parameters
    ----------
    pixels : list of int tuple
        A list of pixels of the form (red, green, blue).
    threshold : float
        The number the measure of deviation must be under for success to be
        reported.

    Returns
    -------
    bool
        True if the measure of deviation is less than `threshold` or False
        otherwise.
    """

    pixel_arr = numpy.array(pixels)
    stddev = numpy.std(pixel_arr)
    return True if stddev < threshold else False


def _binarize_image(image_filename, output_filename):
    """Convert an image to purely black and white.

    Parameters
    ----------
    image_filename : str
        The path to the input image.
    output_filename : str
        The path at which the output image should be saved.

    Returns
    -------
    bool
        True if `image_filename` was able to be converted and saved or
        False otherwise.

    Notes
    -----
    This was adapted from code posted by Martin Thoma on Stack
    Overflow[1]_.

    References
    ----------
    .. [1] https://www.stackoverflow.com/a/37497975
    """

    try:
        from scipy.misc import imsave
        image = Image.open(image_filename)
        # Convert image to monochrome
        image = image.convert("L")
        image_arr = numpy.array(image)
        image_arr = numpy.where(image_arr > 200, 255, 0)
        imsave(output_filename, image_arr)
    except (ImportError, IOError):
        return False

    return True


def _get_columns_from_grid(image, threshold=0):
    """Return a list pixel ranges between column markers.

    Return a list of start and end x-coordinates in `image` that lie
    between two uniformly colored vertical lines (column markers).

    Parameters
    ----------
    image : PIL ImageFile object
        A file opened via a call to PIL.Image.open(file).
    threshold : int, optional
        How much color variance is allowed among pixels in a column when
        deciding whether the column is uniformly colored; 0 means the
        pixels must all have the exact same RGB values (default 0).

    Returns
    -------
    list of int tuple
        A list of coordinate pairs in which the first value indicates the
        x-coordinate of the leftmost pixel between a given row marker pair
        and second value indicates the x-coordinate of the rightmost pixel
        between that same pair.
    """

    left = 0
    right = image.size[0]
    top = 0
    bottom = image.size[1]
    rgb_image = image.convert("RGB")

    columns = []
    start_x = 0
    in_cell = False

    for x in range(left, right):
        pixel_col = []
        for y in range(top, bottom):
            pixel = rgb_image.getpixel((x, y))
            pixel_col.append(pixel)
        if _uniform_pixels(pixel_col, threshold):
            if in_cell:
                # Each sudoku cell should be ~1/9 the width; ignore anything less than half that
                if x - start_x > right / 18:
                    columns.append((start_x, x-1))
                start_x = x
                in_cell = False
            else:
                start_x += 1
        elif not in_cell:
            in_cell = True

    return columns


def _get_rows_from_grid(image, threshold=0):
    """Return a list pixel ranges between row markers.

    Return a list of start and end y-coordinates in `image` that lie
    between two uniformly colored horizontal lines (row markers).

    Parameters
    ----------
    image : PIL ImageFile object
        A file opened via a call to PIL.Image.open(file).
    threshold : int, optional
        How much color variance is allowed among pixels in a row when
        deciding whether the row is uniformly colored; 0 means the pixels
        must all have the exact same RGB values (default 0).

    Returns
    -------
    list of int tuple
        A list of coordinate pairs in which the first value indicates the
        y-coordinate of the highest pixel between a given row marker pair
        and second value indicates the y-coordinate of the lowest pixel
        between that same pair.
    """

    left = 0
    right = image.size[0]
    top = 0
    bottom = image.size[1]
    rgb_image = image.convert("RGB")

    rows = []
    start_y = 0
    in_cell = False

    for y in range(top, bottom):
        pixel_row = []
        for x in range(left, right):
            pixel = rgb_image.getpixel((x, y))
            pixel_row.append(pixel)
        if _uniform_pixels(pixel_row, threshold):
            if in_cell:
                # Each sudoku cell should be ~1/9 the height; ignore anything less than half that
                if y - start_y > bottom / 18:
                    rows.append((start_y, y-1))
                start_y = y
                in_cell = False
            else:
                start_y += 1
        elif not in_cell:
            in_cell = True

    return rows

"""
def main():
    from sys import argv
    filename = argv[1]
    basename, ext = os.path.splitext(filename)
    target_filename = "{}_bw{}".format(basename, ext)
    _binarize_image(filename, target_filename)


if __name__ == "__main__":
    main()
"""
