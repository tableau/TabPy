from tabpy_tools.client import Client
import pandas as pd
from textblob import TextBlob
from nltk.sentiment import SentimentIntensityAnalyzer
import sys


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
    port = sys.argv[1]
    # to do: once auth is enabled in tabpy-tools this will need to be updated
    connection = Client('http://localhost:' + port + '/')
    connection.deploy('Sentiment Analysis', SentimentAnalysis,
                      'Returns a sentiment score between -1 and '
                      '1 for a given string.', override=True)
    print("Successfully deployed SentimentAnalysis")
