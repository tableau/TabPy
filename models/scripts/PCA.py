from tabpy_tools.client import Client
import pandas as pd
from numpy import array
from sklearn.decomposition import PCA as sklearnPCA
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
import sys


def PCA(component, _arg1, _arg2, *_argN):
    '''
    Principal Component Analysis is a technique that extracts the key
    distinct components from a high dimensional space whie attempting
    to capture as much of the variance as possible. For more information
    on the function and how to use it please refer to tabpy-tools.md
    '''
    cols = [_arg1, _arg2] + list(_argN)
    encodedCols = []
    labelEncoder = LabelEncoder()
    oneHotEncoder = OneHotEncoder(categories='auto', sparse=False)

    for col in cols:
        if (type(col[0]) is int or type(col[0]) is float):
            encodedCols.append(col)
        elif (type(col[0]) is bool):
            intCol = array(col)
            encodedCols.append(intCol.astype(int))
        else:
            if (len(set(col)) > 25):
                print('ERROR: Non-numeric arguments cannot have more than '
                      '25 unique values')
                assert (False)
            integerEncoded = labelEncoder.fit_transform(array(col))
            integerEncoded = integerEncoded.reshape(len(col), 1)
            oneHotEncoded = oneHotEncoder.fit_transform(integerEncoded)
            transformedMatrix = oneHotEncoded.transpose()
            encodedCols += list(transformedMatrix)

    dataDict = {}
    for i in range(len(encodedCols)):
        dataDict['col' + str(1 + i)] = list(encodedCols[i])

    if (component <= 0 or component > len(dataDict)):
        print('ERROR: Component specified must be >= 0 and '
              '<= number of arguments')
        assert (False)

    df = pd.DataFrame(data=dataDict, dtype=float)
    scale = StandardScaler()
    scaledData = scale.fit_transform(df)

    pca = sklearnPCA()
    pcaComponents = pca.fit_transform(scaledData)

    return pcaComponents[:, component - 1].tolist()


if __name__ == '__main__':
    port = sys.argv[1]
    # to do: once auth is enabled in tabpy-tools this will need to be updated
    connection = Client('http://localhost:' + port + '/')
    connection.deploy('PCA', PCA,
                      'Returns the specified principal component.',
                      override=True)
    print("Successfully deployed PCA")
