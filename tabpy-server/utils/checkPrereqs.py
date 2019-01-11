message = 'Searching for Python module {}...\t{}'


def check_for_module(module_name):
    try:
        ret = __import__(module_name)
        print(message.format(module_name, 'success'))
        return ret
    except ImportError:
        print(message.format(module_name, 'failed'))
        exit(1)


sys = check_for_module('sys')
if sys is not None:
    msg = 'System must be running Python 3...\t{}'
    version = sys.version_info[0]
    if version < 3:
        print(msg.format('failed, found Python {}'.format(version)))
        exit(1)
    else:
        print(msg.format('success'))

subprocess = check_for_module('subprocess')
setuptools = check_for_module('setuptools')
os = check_for_module('os')

sys.exit(0)