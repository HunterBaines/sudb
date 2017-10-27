# Author: Hunter Baines <0x68@protonmail.com>
# Copyright: (C) 2017 Hunter Baines
# License: GNU GPL version 3

"""The module containing the CommandMapper class.

"""
import re
import inspect
import rlcompleter


class CommandMapper(object):
    """A map of function names to functions and partial names to full ones.

    A tool that, given an object such as a class or module, discovers
    methods or functions within it that contain some specified text and
    then maps the names of those methods or functions (minus the specified
    text and with underscores replaced with, by default, spaces) to the
    methods or functions themselves. Methods are also provided for
    completing a function name given some of its initial characters.

    Parameters
    ----------
    obj : object
        The object (e.g., class or module) whose methods or functions are
        to be mapped.
    pattern : str, optional
        A regex string specifying the text that must be contained in the
        names of the methods or functions for it to be mapped and that
        will ultimately be removed from those names in the final mapping of
        name to method/function (default '', which matches all
        methods/functions and removes nothing from their names).
    sep : str
        The text to replace underscores in method names with (default ' ').

    Attributes
    ----------
    CommandCompleter : class
        A Completer instance that only matches the namespace it is
        initialized with (instead of also matching Python built-ins).
    commands : dict of str to method
        A mapping of cleaned-up method names (e.g., 'help') to the method
        itself (e.g., '_cmd_help').
    completer : CommandCompleter instance
        The engine for getting a full command name (e.g., 'help') from a
        partial one (e.g., 'h').

    """
    class CommandCompleter(rlcompleter.Completer):
        """Completer that ignores builtins and uses ' ' as callable postfix

        """
        def global_matches(self, text):
            # Patch `global_matches` in Completer to not match built-ins
            matches = []
            seen = set()
            text_n = len(text)
            for word, val in self.namespace.items():
                if word[:text_n] == text and word not in seen:
                    seen.add(word)
                    matches.append(self._callable_postfix(val, word))
            return matches

        def _callable_postfix(self, val, word):
            # Patch `_callable_postfix` to find commands that could take
            # arguments or have subcommands and append ' ', not '('
            word_n = len(word)
            for other_word in self.namespace:
                if not other_word.startswith(word):
                    continue
                try:
                    next_char = other_word[word_n]
                    if next_char != ' ':
                        # A completion aside from space is possible
                        return word
                except IndexError:
                    # Ignore when `other_word == word`
                    pass
            # Either `word` never prefixes any other command or in all
            # commands it prefixes a space always follows that prefix
            return word + ' '


    def __init__(self, obj, pattern=None, sep=None):
        regex_engine = re.compile('' if pattern is None else pattern)

        self.commands = self._get_commands(obj, regex_engine, sep=sep)
        self.completer = self._get_completer(self.commands)


    @staticmethod
    def _get_commands(obj, regex_engine, sep=None):
        def is_command(cmd):
            """Return True if is a callable whose name matching regex.

            """
            if not inspect.isfunction(cmd) and not inspect.ismethod(cmd):
                return False
            if not regex_engine.findall(cmd.__name__):
                return False
            return True

        sep = ' ' if sep is None else sep

        command_dict = {}
        for command_name, command in inspect.getmembers(obj, predicate=is_command):
            command_name = regex_engine.sub('', command_name)
            command_name = command_name.replace('_', sep)
            command_dict[command_name] = command

        return command_dict

    @staticmethod
    def _get_completer(commands):
        command_namespace = dict(zip(commands.keys(), commands.keys()))
        command_completer = CommandMapper.CommandCompleter(command_namespace)
        return command_completer


    def completions(self, command_name):
        """Return possible command completions for the given text.

        Parameters
        ----------
        command_name : str
            The text to attempt to complete (e.g., 'p').

        Returns
        -------
        list of str
            A list of possible command completions for the given text (e.g,
            ['print', 'put']).

        """
        if not command_name:
            return self.commands.keys()

        possible_commands = ['']

        names = command_name.split()
        # So `names.pop()` will return leftmost name
        names.reverse()

        while names:
            name = names.pop()
            new_possible_commands = []
            while possible_commands:
                prev_name = possible_commands.pop()
                full_name = '{} {}'.format(prev_name, name).strip()
                for next_name in self.completer.global_matches(full_name):
                    # Completions returned should not have a trailing
                    # space, and `full_name` expects no such space from the
                    # entries that make it into `possible_commands`
                    new_possible_commands.append(next_name.strip())
            possible_commands = new_possible_commands[:]

        return possible_commands
