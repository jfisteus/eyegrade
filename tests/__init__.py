import unittest
import os.path


def _load_tests(loader, standard_tests, pattern):
    this_dir = os.path.dirname(__file__)
    package_tests = loader.discover(start_dir=this_dir, pattern=pattern)
    standard_tests.addTests(package_tests)
    return standard_tests


def get_tests():
    return _load_tests(unittest.TestLoader(), unittest.TestSuite(), "test*.py")
