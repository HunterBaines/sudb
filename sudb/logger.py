# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""The module containing the ErrorLogger class.

"""
from __future__ import absolute_import, division, print_function

from sudb import error


class ErrorLogger(object):
    """An error logger mapping hashable objects to user-defined errors.

    Parameters
    ----------
    errors : iterable of Error instance, optional
        An iterable containing any Error instances to initialize the
        `errors` attribute with (default None).

    Attributes
    ----------
    errors : set of Error instance
        A set containing all user-defined Errors to keep track of.
    log : dict of int to int
        A mapping of the hash of an object to an int representing which
        errors apply to that object.
    reverse_log : dict of int to set of int
        A mapping of an error number to the set of object hashes to which
        the error with that error number applies.

    """
    def __init__(self, errors=None):
        self.errors = set() if errors is None else set(errors)
        self.log = {}
        self.reverse_log = {}
        for err in self.errors:
            self.reverse_log[err.errno] = set()


    def autolog(self, obj, report=False):
        """Log all errors relevant to the object and return an error count.

        Detect and log all errors applicable to `obj` and return the number
        of errors logged. If `report` is True, also print to stderr a
        description of each error.

        Parameters
        ----------
        obj : hashable
            The object to check for errors.
        report : bool, optional
            True if a description of each error found in `obj` should be
            printed to stderr, and False if not (default False).

        Returns
        -------
        int
            The number of errors logged.

        Notes
        -----
        This is intended to be implemented by subclasses where the nature
        of the objects and errors can be more determinate.

        """
        raise NotImplementedError()

    def log_error(self, obj, err):
        """Add the error to the object's log entry.

        Parameters
        ----------
        obj : hashable
            The object to map `err` to.
        err : Error instance
            The error to be mapped to `obj`.

        """
        obj_key = hash(obj)

        try:
            self.log[obj_key] |= err.errno
        except KeyError:
            self.log[obj_key] = err.errno

        self.reverse_log[err.errno].add(obj_key)

    def unlog_error(self, obj, err):
        """Remove the error from the object's log entry.

        Parameters
        ----------
        obj : hashable
            The object whose log entry is to be modified.
        err : Error instance
            The error to remove from the log entry for `obj`.

        """
        self.clear_error(err, obj=obj)


    def log_entry(self, obj):
        """Return the log entry for the object.

        Parameters
        ----------
        obj : hashable
            The object whose log entry is to be returned.

        Returns
        -------
        int
            The value containing the flags that summarize what errors apply
            to `obj` or 0 if `obj` is not in the log.

        """
        try:
            obj_key = hash(obj)
            flags = self.log[obj_key]
            return flags
        except KeyError:
            return 0

    def in_mask(self, obj, mask):
        """Return whether the object has errors in the given error mask.

        Parameters
        ----------
        obj : hashable
            The object whose log entry is to be compared with `mask`.
        mask : int
            The mask to compare with the flags in the log entry of `obj`.

        Returns
        -------
        bool
            True if the log entry for `obj` contains errors given in
            `mask`, and False if not.

        """
        return self.log_entry(obj) & mask


    def add_error(self, err):
        """Add an error to the instance's collection of known errors.

        Parameters
        ----------
        err : Error instance
            The error to add to the instance's `errors` set.

        """
        self.errors.add(err)
        self.reverse_log[err.errno] = set()

    def remove_error(self, err):
        """Remove an error from the instance's collection of known errors.

        Parameters
        ----------
        err : Error instance
            The error to remove from the instance's `errors` set

        Notes
        -----
        This method does not delete references to the error: use
        `clear_error` for that.

        """
        self.errors.remove(err)

    def clear_error(self, err, obj=None):
        """Remove references to an error in the log.

        Remove all references to an error or, if `obj` is given, all
        references within the log entry for `obj`.

        Parameters
        ----------
        err : Error instance
            The error to clear from all log entries or the log entry of
            `obj` (if given).
        obj : hashable, optional
            The object whose log entry is to be cleared of references to
            `err` (default None).

        """
        targets = self.reverse_log[err.errno] if obj is None else [hash(obj)]

        for obj_key in targets:
            self.log[obj_key] &= ~err.errno
            self.reverse_log[err.errno].remove(obj_key)


    def error_count(self, obj=None):
        """Return the number of errors logged.

        Return the number of errors logged globally or, if `obj` is given,
        locally for that object.

        Parameters
        ----------
        obj : hashable, optional
            The object whose errors are to be counted (default None).

        Returns
        -------
        int
            An error count for all objects if `obj` is not given, or an
            error count for `obj` if given.

        """
        if obj is None:
            # The overall error count
            return sum(len(hash_set) for hash_set in self.reverse_log.values())

        count = 0
        flags = self.log_entry(obj)
        while flags:
            flags = flags & (flags - 1)
            count += 1
        return count


    def report_errors(self, obj, prelude=None):
        """Print to stderr all errors applicable to the object.

        Print to stderr the `strerror` of each error applicable to `obj`
        preceded by `prelude` (if not given, the hash of `obj`), a colon,
        and a space.

        Parameters
        ----------
        obj : hashable
            The object whose errors are to be reported.
        prelude : str, optional
            The text to print before each error report (default the hash of
            `obj`).

        """
        if prelude is None:
            prelude = str(hash(obj))

        flags = self.log_entry(obj)
        if not flags:
            error.error('(no errors)', prelude=prelude)
            return

        for err in self.errors:
            if err.errno & flags:
                error.error(err.strerror, prelude=prelude)

    def print_summary(self):
        """Print to stdout how many of each error were logged.

        """
        print('Error Summary:')

        if not self.error_count():
            print('(no errors)')
            return

        for err in self.errors:
            count = len(self.reverse_log[err.errno])
            if count > 0:
                print('{} case{} of {}'.format(count, 's' if count != 1 else '', err.strerror))
