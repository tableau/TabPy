from tabpy_tools.client import Client
import pandas as pd
from numpy import array
from sklearn.decomposition import PCA as sklearnPCA
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
import sys
from utils import setup_utils

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
        if isinstance(col[0], (int, float)):
            encodedCols.append(col)
        elif type(col[0]) is bool:
            intCol = array(col)
            encodedCols.append(intCol.astype(int))
        else:
            if len(set(col)) > 25:
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
        dataDict[f'col{1 + i}'] = list(encodedCols[i])

    if component <= 0 or component > len(dataDict):
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
    #running from setup.py
    if len(sys.argv) > 1:
        config_file_path = sys.argv[1]
    else: 
        config_file_path = setup_utils.get_default_config_file_path()
    port, auth_on, prefix = setup_utils.parse_config(config_file_path)

    connection = Client(f'{prefix}://localhost:{port}/')

    if auth_on:
        #credentials are passed in from setup.py
        if len(sys.argv) == 4:
            user, passwd = sys.argv[2], sys.argv[3]
        #running PCA independently 
        else:
            user, passwd = setup_utils.get_creds()
        connection.set_credentials(user, passwd)

    connection.deploy('PCA', PCA,
                      'Returns the specified principal component.',
                      override=True)
    print("Successfully deployed PCA")
