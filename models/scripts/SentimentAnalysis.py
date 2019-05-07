from tabpy_tools.client import Client
import pandas as pd
from textblob import TextBlob
from nltk.sentiment import SentimentIntensityAnalyzer
import sys
import configparser
import getpass
from pathlib import Path


def SentimentAnalysis(_arg1, library='nltk'):
    '''
    Sentiment Analysis is a procedure that assigns a score from -1 to 1
    for a piece of text with -1 being negative and 1 being positive. For
    more information on the function and how to use it please refer to
    tabpy-tools.md
    '''
    assert (type(_arg1[0]) is str)

    library = library.lower()
    supportedLibraries = {'nltk', 'textblob'}

    assert (library in supportedLibraries)
    scores = []
    if library == 'nltk':
        sid = SentimentIntensityAnalyzer()
        for text in _arg1:
            sentimentResults = sid.polarity_scores(text)
            score = sentimentResults['compound']
            scores.append(score)
    elif libary == 'textblob':
        for text in _arg1:
            currScore = TextBlob(text)
            scores.append(currScore.sentiment.polarity)
    return scores


if __name__ == '__main__':
    #running from setup.py
    if (len(sys.argv) > 1):
        config_file_path = sys.argv[1]
    else: 
        config_file_path = str(Path(__file__).resolve().parent.parent.parent
                               / 'tabpy-server' / 'tabpy_server' / 'common'
                               / 'default.conf')
    config = configparser.ConfigParser()
    config.read(config_file_path)
    tabpy_config = config['TabPy']
    port = tabpy_config['TABPY_PORT']
    auth_on = 'TABPY_PWD_FILE' in tabpy_config
    ssl_on = 'TABPY_TRANSFER_PROTOCOL' in tabpy_config and 'TABPY_CERTIFICATE_FILE' in tabpy_config and 'TABPY_KEY_FILE' in tabpy_config
    prefix = "https" if ssl_on else "http"

    connection = Client(f'{prefix}://localhost:{port}/')

    if(auth_on):
        #credentials are passed in from setup.py
        if(len(sys.argv) == 4):
            user, passwd = sys.argv[2], sys.argv[3]
        #running Sentiment Analysis independently 
        else:
            user = input("Username: ")
            passwd = getpass.getpass("Password: ")
        connection.set_credentials(user, passwd)

    connection.deploy('Sentiment Analysis', SentimentAnalysis,
                      'Returns a sentiment score between -1 and '
                      '1 for a given string.', override=True)
    print("Successfully deployed SentimentAnalysis")
