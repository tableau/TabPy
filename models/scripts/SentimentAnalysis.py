from tabpy_tools.client import Client
from textblob import TextBlob
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'models'))
from utils import setup_utils


nltk.download('vader_lexicon')
nltk.download('punkt')


def SentimentAnalysis(_arg1, library='nltk'):
    '''
    Sentiment Analysis is a procedure that assigns a score from -1 to 1
    for a piece of text with -1 being negative and 1 being positive. For
    more information on the function and how to use it please refer to
    tabpy-tools.md
    '''
    if not (isinstance(_arg1[0], str)):
        raise TypeError

    supportedLibraries = {'nltk', 'textblob'}

    library = library.lower()
    if library not in supportedLibraries:
        raise ValueError

    scores = []
    if library == 'nltk':
        sid = SentimentIntensityAnalyzer()
        for text in _arg1:
            sentimentResults = sid.polarity_scores(text)
            score = sentimentResults['compound']
            scores.append(score)
    elif library == 'textblob':
        for text in _arg1:
            currScore = TextBlob(text)
            scores.append(currScore.sentiment.polarity)
    return scores


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
        # running Sentiment Analysis independently
        else:
            user, passwd = setup_utils.get_creds()
        connection.set_credentials(user, passwd)

    connection.deploy('Sentiment Analysis', SentimentAnalysis,
                      'Returns a sentiment score between -1 and '
                      '1 for a given string.', override=True)
    print("Successfully deployed SentimentAnalysis")
