import os
import sys
import unittest


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(__file__).join('tabpy-client'))
    sys.path.insert(0, os.path.dirname(__file__).join('tabpy-server'))
    runner = unittest.TextTestRunner()

    # Get all of the tests we need from the two project
    suite_list = []
    for dir in ('tabpy-client', 'tabpy-server'):
        suite_list.append(unittest.TestLoader().discover(dir))

    suite = unittest.TestSuite(suite_list)
    runner.run(suite)
