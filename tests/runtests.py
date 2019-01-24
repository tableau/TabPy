import os
import sys
import unittest


if __name__ == '__main__':
    dirs = {'tabpy-tools', 'tabpy-server'}

    for dir_ in dirs:
        sys.path.insert(0, os.path.join(
            os.path.abspath(os.path.dirname(__file__)), dir_))

    # Get all of the tests we need from the two project
    suite_list = []
    for dir_ in dirs:
        suite_list.append(unittest.TestLoader().discover(dir_))

    suite = unittest.TestSuite(suite_list)

    runner = unittest.TextTestRunner()
    runner.run(suite)
