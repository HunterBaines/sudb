# License: GNU GPL version 3

import re
import inspect
import readline
import rlcompleter

class CommandMapper(object):

    class LocalCompleter(rlcompleter.Completer):
        def global_matches(self, text):
            matches = []
            seen = set()
            n = len(text)
            for word, val in self.namespace.items():
                if word[:n] == text and word not in seen:
                    seen.add(word)
                    matches.append(self._callable_postfix(val, word))
            return matches


    def __init__(self, obj, pattern=None, sep=None):
        regex_engine = re.compile('' if pattern is None else pattern)

        self.commands = self._install_commands(obj, regex_engine, sep=sep)
        self.completer = self._install_completer()


    def _install_commands(self, obj, regex_engine, sep=None):
        def is_command(cmd):
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

    def _install_completer(self):
        command_namespace = dict(zip(self.commands.keys(), self.commands.keys()))
        command_completer = self.LocalCompleter(command_namespace)

        #TODO: Does this belong here? Should the caller set up tab completion for itself?
        readline.set_completer(command_completer.complete)
        readline.parse_and_bind('tab: complete')

        return command_completer


    def completions(self, command_name):
        if not command_name:
            return self.commands.keys()

        possible_commands = ['']

        names = command_name.split()
        names.reverse()

        while names:
            name = names.pop()
            new_possible_commands = []
            while possible_commands:
                full_name = '{} {}'.format(possible_commands.pop(), name).strip()
                next_state = 0
                while True:
                    next_name = self.completer.complete(full_name, next_state)
                    if next_name is None:
                        break
                    new_possible_commands.append(next_name)
                    next_state += 1
            possible_commands = new_possible_commands[:]

        return possible_commands
