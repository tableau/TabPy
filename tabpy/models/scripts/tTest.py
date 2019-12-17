from scipy import stats
from tabpy.models.utils import setup_utils


def ttest(_arg1, _arg2):
    """
    T-Test is a statistical hypothesis test that is used to compare
    two sample means or a sample’s mean against a known population mean.
    For more information on the function and how to use it please refer
    to tabpy-tools.md
    """
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


if __name__ == "__main__":
    setup_utils.deploy_model("ttest", ttest, "Returns the p-value form a t-test")
