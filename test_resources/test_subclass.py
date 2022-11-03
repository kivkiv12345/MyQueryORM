"""
This module borrows code from:
    https://stackoverflow.com/questions/4319825/python-unittest-opposite-of-assertraises/49062929#49062929,
Allows us to check that a given piece of code doesn't raise an exception.
"""

if __name__ == '__main__':
    raise SystemExit("In my humble opinion, attempting to run the subclasses for use in our unit tests, is quite"
                     "the nonsensical idea.")

import unittest
import traceback
from unittest.case import _AssertRaisesContext


class _AssertNotRaisesContext(_AssertRaisesContext):
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            self.exception = exc_value.with_traceback(None)

            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)

            if self.obj_name:
                self._raiseFailure("{} raised by {}".format(exc_name,
                    self.obj_name))
            else:
                self._raiseFailure("{} raised".format(exc_name))

        else:
            traceback.clear_frames(tb)

        return True


class MoreTestCases(unittest.TestCase):
    def assertNotRaises(self, expected_exception, *args, **kwargs):
        context = _AssertNotRaisesContext(expected_exception, self)
        try:
            return context.handle('assertNotRaises', args, kwargs)
        finally:
            context = None
