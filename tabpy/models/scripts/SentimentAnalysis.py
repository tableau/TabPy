import sys
from textblob import TextBlob
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from tabpy.models.utils import setup_utils


import ssl

_ctx = ssl._create_unverified_context
ssl._create_default_https_context = _ctx


def setup():
    file_path = sys.argv[1] if len(sys.argv) > 1 else setup_utils.get_default_config_file_path()
    config = setup_utils.get_config(file_path)
    download_dir = None
    if "nltk" in config:
        nltk_config = config["nltk"]
        download_dir = nltk_config.get("NLTK_DOWNLOAD_PATH")
        if "NLTK_PROXY" in nltk_config:
            nltk.set_proxy(nltk_config["NLTK_PROXY"])

    nltk.download("vader_lexicon", download_dir=download_dir)
    nltk.download("punkt", download_dir=download_dir)


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
    setup()
    setup_utils.deploy_model(
        "Sentiment Analysis",
        SentimentAnalysis,
        "Returns a sentiment score between -1 and 1 for " "a given string",
    )
