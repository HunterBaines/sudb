# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""The module containing the CommandMapper class.

"""
import re
import inspect


class CommandMapper(object):
    """A map of function names to functions and partial names to full ones.

    A tool that, given an object such as a class or module, discovers
    methods or functions within it that contain some specified text and
    then maps the names of those methods or functions (minus the specified
    text and with underscores replaced, by default, with spaces) to the
    methods or functions themselves. Methods are also provided for
    completing a function name given some of its initial characters.

    Parameters
    ----------
    obj : object, optional
        The object (e.g., class or module) whose methods or functions are
        to be mapped (default None); if None, the user is expected to
        define `self.commands` manually before using the instance.
    pattern : str, optional
        A regex string specifying the text that must be contained in the
        names of the methods or functions for it to be mapped and that
        will ultimately be removed from those names in the final mapping of
        name to method/function (default '', which matches all
        methods/functions and removes nothing from their names).
    sep : str, optional
        The value to assign to the attribute `sep` (default ' '); see
        below.
    use_trailing_sep : bool, optional
        The value to assign to the attribute `use_trailing_sep` (default
        False); see below.

    Attributes
    ----------
    commands : dict of str to callable
        A mapping of cleaned-up method/function names (e.g., 'help') to the
        callables (e.g., `<function _cmd_help at 0x7375646f6b75>`)
        themselves.
    sep : str
        The text to replace underscores with in the cleaned-up
        method/function names used in `self.commands` and for completions.
    use_trailing_sep : bool
        True if completions should take into account a trailing `sep` and
        return completions with a trailing `sep` when possible; this can be
        useful, for example, when setting up the class to be used with tab
        completion.

    """
    def __init__(self, obj=None, pattern=None, sep=None, use_trailing_sep=False):
        self.use_trailing_sep = use_trailing_sep
        self.sep = ' ' if sep is None else sep
        pattern = '' if pattern is None else pattern
        self.commands = self._get_commands(obj, pattern, self.sep)
        # A cache of completions
        self._matches = []

    @staticmethod
    def _get_commands(obj, pattern, sep):
        # Return a dict of cleaned-up method/function names to the
        # methods/functions itself
        if obj is None:
            return None

        regex_engine = re.compile(pattern)

        def is_command(cmd):
            """Return True if is a callable whose name matches regex.

            """
            if not inspect.isfunction(cmd) and not inspect.ismethod(cmd):
                return False
            if not regex_engine.findall(cmd.__name__):
                return False
            return True

        command_dict = {}
        for command_name, command in inspect.getmembers(obj, predicate=is_command):
            command_name = regex_engine.sub('', command_name)
            command_name = command_name.replace('_', sep)
            command_dict[command_name] = command

        return command_dict


    def complete(self, command_name, state):
        """Return the next possible completion for given text.

        Parameters
        ----------
        command_name : str
            The text to attempt to complete.
        state : int
            The index of the completion to return (starting from 0).

        Returns
        -------
        str
            The `state`th completion of `command_name` or None if no
            completions are left.

        Notes
        -----
        This is based on the `complete` method in `rlcompleter.Completer`
        and has the appropriate parameters for use with
        `readline.set_completer`.

        """
        if state == 0:
            self._matches = self.completions(command_name)
        try:
            return self._matches[state]
        except IndexError:
            return None

    def completions(self, command_name):
        """Return all possible command completions for the given text.

        Parameters
        ----------
        command_name : str
            The text to attempt to complete (e.g., 'p').

        Returns
        -------
        list of str
            A list of possible command completions for the given text (e.g,
            ['print', 'put']) sorted alphabetically.

        """
        if not command_name:
            return self.commands.keys()

        possible_commands = []

        # Comprehension to remove empty strings due to repeated `self.sep`
        words = [w for w in command_name.split(self.sep) if w]
        if self.use_trailing_sep and command_name.endswith(self.sep):
            # Require at least one word beyond those in `command_name`
            words.append('')

        for other_command_name in self.commands:
            other_words = other_command_name.split()
            for i, word in enumerate(words):
                try:
                    other_word = other_words[i]
                except IndexError:
                    break
                if not other_word.startswith(word):
                    break
            else:
                # Every word in `other_command_name` has the
                # coresponding word in `command_name` as a prefix
                match_name = other_command_name
                if self.use_trailing_sep:
                    match_name = self._sep_postfixed_name(match_name)
                possible_commands.append(match_name)

        return sorted(possible_commands)

    def _sep_postfixed_name(self, command_name):
        # Return `command_name` with `self.sep` added to its end if
        # `command_name` never prefixes any other command or if in all
        # commands it prefixes `self.sep` follows that prefix; otherwise
        # just return `command_name`
        name_n = len(command_name)
        for other_command_name in self.commands:
            if not other_command_name.startswith(command_name):
                continue
            try:
                next_char = other_command_name[name_n]
                if next_char != self.sep:
                    # A next-char completion aside from `self.sep` is
                    # possible
                    return command_name
            except IndexError:
                # Ignore when `other_command_name == command_name`
                pass
        return command_name + self.sep
