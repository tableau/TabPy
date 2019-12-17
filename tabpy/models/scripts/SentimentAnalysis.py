from textblob import TextBlob
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from tabpy.models.utils import setup_utils


import ssl

_ctx = ssl._create_unverified_context
ssl._create_default_https_context = _ctx


nltk.download("vader_lexicon")
nltk.download("punkt")


def SentimentAnalysis(_arg1, library="nltk"):
    """
    Sentiment Analysis is a procedure that assigns a score from -1 to 1
    for a piece of text with -1 being negative and 1 being positive. For
    more information on the function and how to use it please refer to
    tabpy-tools.md
    """
    if not (isinstance(_arg1[0], str)):
        raise TypeError

    supportedLibraries = {"nltk", "textblob"}

    library = library.lower()
    if library not in supportedLibraries:
        raise ValueError

    scores = []
    if library == "nltk":
        sid = SentimentIntensityAnalyzer()
        for text in _arg1:
            sentimentResults = sid.polarity_scores(text)
            score = sentimentResults["compound"]
            scores.append(score)
    elif library == "textblob":
        for text in _arg1:
            currScore = TextBlob(text)
            scores.append(currScore.sentiment.polarity)
    return scores


if __name__ == "__main__":
    setup_utils.deploy_model(
        "Sentiment Analysis",
        SentimentAnalysis,
        "Returns a sentiment score between -1 and 1 for " "a given string",
    )
