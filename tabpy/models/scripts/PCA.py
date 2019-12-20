import pandas as pd
from numpy import array
from sklearn.decomposition import PCA as sklearnPCA
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
from tabpy.models.utils import setup_utils


def PCA(component, _arg1, _arg2, *_argN):
    """
    Principal Component Analysis is a technique that extracts the key
    distinct components from a high dimensional space whie attempting
    to capture as much of the variance as possible. For more information
    on the function and how to use it please refer to tabpy-tools.md
    """
    cols = [_arg1, _arg2] + list(_argN)
    encodedCols = []
    labelEncoder = LabelEncoder()
    oneHotEncoder = OneHotEncoder(categories="auto", sparse=False)

    for col in cols:
        if isinstance(col[0], (int, float)):
            encodedCols.append(col)
        elif type(col[0]) is bool:
            intCol = array(col)
            encodedCols.append(intCol.astype(int))
        else:
            if len(set(col)) > 25:
                print(
                    "ERROR: Non-numeric arguments cannot have more than "
                    "25 unique values"
                )
                raise ValueError
            integerEncoded = labelEncoder.fit_transform(array(col))
            integerEncoded = integerEncoded.reshape(len(col), 1)
            oneHotEncoded = oneHotEncoder.fit_transform(integerEncoded)
            transformedMatrix = oneHotEncoded.transpose()
            encodedCols += list(transformedMatrix)

    dataDict = {}
    for i in range(len(encodedCols)):
        dataDict[f"col{1 + i}"] = list(encodedCols[i])

    if component <= 0 or component > len(dataDict):
        print("ERROR: Component specified must be >= 0 and " "<= number of arguments")
        raise ValueError

    df = pd.DataFrame(data=dataDict, dtype=float)
    scale = StandardScaler()
    scaledData = scale.fit_transform(df)

    pca = sklearnPCA()
    pcaComponents = pca.fit_transform(scaledData)

    return pcaComponents[:, component - 1].tolist()


if __name__ == "__main__":
    setup_utils.deploy_model("PCA", PCA, "Returns the specified principal component")
