from tabpy_tools.client import Client
import pandas as pd
from textblob import TextBlob
from nltk.sentiment import SentimentIntensityAnalyzer
import sys


def SentimentAnalysis(_arg1, library='nltk'):
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
    connection = Client('http://localhost:' + port + '/')
    connection.deploy('Sentiment Analysis',
                      SentimentAnalysis,
                      'Returns a sentiment score between -1 and 1 for a given string.', override=True)
    print("Successfully deployed SentimentAnalysis")
