from tabpy_tools.client import Client
from scipy import stats
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'models'))
from utils import setup_utils


def ttest(_arg1, _arg2):
    # one sample test with mean
    if len(_arg2) == 1:
        test_stat, p_value = stats.ttest_1samp(_arg1, _arg2)
        return p_value
    # two sample t-test where _arg1 is numeric and _arg2 is a binary factor
    elif len(set(_arg2)) == 2:
        # each sample in _arg1 needs to have a corresponding classification
        # in _arg2
        if not (len(_arg1) == len(_arg2)):
            raise ValueError
        class1, class2 = set(_arg2)
        sample1 = []
        sample2 = []
        for i in range(len(_arg1)):
            if _arg2[i] == class1:
                sample1.append(_arg1[i])
            else:
                sample2.append(_arg1[i])
        test_stat, p_value = stats.ttest_ind(sample1, sample2, equal_var=False)
        return p_value
    # arg1 is a sample and arg2 is a sample
    else:
        test_stat, p_value = stats.ttest_ind(_arg1, _arg2, equal_var=False)
        return p_value


if __name__ == '__main__':
    # running from setup.py
    if len(sys.argv) > 1:
        config_file_path = sys.argv[1]
    else:
        config_file_path = setup_utils.get_default_config_file_path()
    port, auth_on, prefix = setup_utils.parse_config(config_file_path)

    connection = Client(f'{prefix}://localhost:{port}/')

    if auth_on:
        # credentials are passed in from setup.py
        if len(sys.argv) == 4:
            user, passwd = sys.argv[2], sys.argv[3]
        # running ttest independently
        else:
            user, passwd = setup_utils.get_creds()
        connection.set_credentials(user, passwd)

    connection.deploy('ttest', ttest,
                      'Returns the p-value from a t-test.',
                      override=True)
    print("Successfully deployed ttest")
