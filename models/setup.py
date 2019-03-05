import pip
import os
import sys
import platform

# pip 10.0 introduced a breaking change that moves the location of main
try:
    from pip import main
except:
    from pip._internal import main

def install_dependencies(packages):
    pip_arg = ['install'] + packages + ['--no-cache-dir']
    if hasattr(pip, 'main'):
        pip.main(pip_arg)
    else:
        pip._internal.main(pip_arg)


if __name__ == '__main__':
    install_dependencies(['sklearn', 'pandas', 'numpy', 'textblob', 'nltk'])
    
    # Determine if we run python or python3
    if platform.system() == 'Windows':
        py = 'python '
    else:
        py = 'python3 '

    # When no port is specified we will assume the default of 9004
    if len(sys.argv) == 1:
        port = 9004
    else:
        port = sys.argv[1]
    
    # Deploy each model in the scripts directory
    directory = os.path.join(os.getcwd(), 'scripts/')
    for filename in os.listdir(directory):
        path = py + directory + filename + ' ' + str(port)
        os.system(path)
