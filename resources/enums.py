""" This file consists of different enumerations used by this program. """

if __name__ == '__main__':
    # Gently remind the user to not run enums.py themselves
    raise SystemExit("Hiya (ʘ‿ʘ)╯, it appears you're trying to run enums.py instead of app.py. This, sadly, will not work :(")

from enum import Enum


class KeyModes(Enum):
    """ Enum to hold keystroke modifiers. """
    SHIFT   = 1
    CONTROL = 2
    ALT     = 3


class ViewModes(Enum):
    """ Enum to hold different types of tables to show in the table button list. """
    TABLE   = 'BASE TABLE'
    VIEW    = 'VIEW'


class FieldTypes(Enum):
    """ Enum to hold the different types of fields a ModelField may be of. """
    FOREIGN_KEY = 'MUL'
    PRIMARY_KEY = 'PRI'


class SysArgs(Enum):
    """ Holds the different arguments that may be passed when running app.py """
    UNIT_TEST = 'unittests'


class DatabaseLocations(Enum):
    """ Describes possible locations of the program database. """
    LOCAL   = 1
    DOCKER  = 2
