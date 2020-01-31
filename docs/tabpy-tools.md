# TabPy Tools

TabPy tools is the Python package of tools for managing the published Python functions
on TabPy server.

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [Connecting to TabPy](#connecting-to-tabpy)
- [Authentication](#authentication)
- [Deploying a Function](#deploying-a-function)
- [Predeployed Functions](#predeployed-functions)
  * [Principal Component Analysis (PCA)](#principal-component-analysis-pca)
  * [Sentiment Analysis](#sentiment-analysis)
  * [T-Test](#t-test)
  * [ANOVA](#anova)
- [Providing Schema Metadata](#providing-schema-metadata)
- [Querying an Endpoint](#querying-an-endpoint)
- [Evaluating Arbitrary Python Scripts](#evaluating-arbitrary-python-scripts)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## Connecting to TabPy

The tools library uses the notion of connecting to a service to avoid having
to specify the service location for all subsequent operations:

```python

from tabpy.tabpy_tools.client import Client

client = Client('http://localhost:9004/')

```

The URL and port are where the Tableau-Python-Server process has been started -
more info can be found in the
[server section](server-startup.md#Command-Line-Arguments) of the documentation.

## Authentication

When TabPy is configured with the authentication feature on, client code
has to specify the credentials to use during model deployment with the
`set_credentials` call for a client:

```python
client.set_credentials('username', 'P@ssw0rd')
```

Credentials only need to be set once for all further client operations.

In cases where credentials are not provided but are required, the deployment will
fail with an "Unauthorized" code (401).

For instructions on how to configure and enable the authentication feature for
TabPy, see [TabPy Server Configuration Instructions](server-config.md).

## Deploying a Function

A persisted endpoint is backed by a Python method. For example:

```python
def add(x,y):
    import numpy as np
    return np.add(x, y).tolist()

client.deploy('add', add, 'Adds two numbers x and y')
```

The next example is more complex, using scikit-learn's clustering API:

```python

def clustering(x, y):
    import numpy as np
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    X = np.column_stack([x, y])
    X = StandardScaler().fit_transform(X)
    db = DBSCAN(eps=1, min_samples=3).fit(X)
    return db.labels_.tolist()


client.deploy('clustering',
              clustering,
              'Returns cluster Ids for each data point specified by the '
              'pairs in x and y')

```

In this example the function `clustering` expects a set of two-dimensional
data points, represented by the list of all x-coordinates and the list of all
y-coordinates. It will return a set of numerical labels corresponding to the
clusters to which each datapoint is assigned. We deploy this function as an
endpoint named `clustering`.
It is now reachable as a [REST API](server-rest.md#httppost-queryendpoint), as
well as through the TabPy tools - for details see the next section.

You can re-deploy a function (for example, after you modified its code) by setting
the `override` parameter to `True`:

```python
client.deploy('add', add, 'Adds two numbers x and y', override=True)
```

Each re-deployment of an endpoint will increment its version number, which is also
returned as part of the query result.

When deploying endpoints which rely on supervised learning models, you may want to
load a saved model instead of training on-the-fly for performance reasons.

Below is an excerpt from the training stage of a hypothetical model that predicts
whether or not a loan will default:

```python

from sklearn.ensemble import GradientBoostingClassifier

predictors = [x for x in train.columns if x not in [target, RowID]]
gbm = GradientBoostingClassifier(learning_rate=0.01, n_estimators=600,max_depth=9,
min_samples_split=1200, min_samples_leaf=60, subsample=0.85, random_state=10)
modelfit(gbm, train, test, predictors)

```

When the trained model (named `gbm` in this case) is used in a function being
deployed (as in `gbm.predict(...)` below), Tableau will automatically save its
definition using `cloudpickle` along with the definition of the function. The model
will also be kept in memory on the server in order to achieve faster response times.
If you persist your model manually to disk and read as part of your scoring function
code however, you will notice that the response times are noticeably longer - as
every time a client hits an endpoint, the code (including model loading) will get
executed. In order to get the best performance, we recommended following the
methodology outlined in this example.

```python
def LoanDefaultClassifier(Loan_Amount, Loan_Tenure, Monthly_Income, Age):
    import pandas as pd
    data=pd.concat([Loan_Amount,Loan_Tenure,Monthly_Income,Age],axis=1)
    return gbm.predict(data)

client.deploy('WillItDefault',
              LoanDefaultClassifier,
              'Returns whether a loan application is likely to default.')
```

You can find a detailed working example with a downloadable sample Tableau workbook
and an accompanying Jupyter workbook that walks through model fitting, evaluation
and publishing steps on
[our blog](https://www.tableau.com/about/blog/2017/1/building-advanced-analytics-applications-tabpy-64916).

The endpoints that are no longer needed can be removed the following way:

```python

client.remove('WillItDefault')

```

## Predeployed Functions

### Deploying Models Shipped With TabPy

To deploy models shipped with TabPy follow the
[TabPy Installation Instructions](server-install.md) and then
[TabPy Server Configuration Instructions](server-config.md).
Once your server is running execute the following command:

```sh
tabpy-deploy-models
```

If your server is running using a custom config specify the config
in the command line:

```sh
tabpy-deploy-models custom.conf
```

The command will deploy all of the prebuilt models.
For every successfully deployed model a message will be printed to the console:

```sh
"Successfully deployed PCA"
```

Use code in [`tabpy/models/scripts`](../tabpy/models/scripts)
as an example of how to create a model and
[`tabpy/models/deploy_models.py`](../tabpy/models/deploy_models.py)
as an example for how to deploy a model. Before executing delpoyment script
install all the required dependencies with `pip`.

You can deploy models individually by navigating to
[`tabpy/models/scripts`](../tabpy/models/scripts) and running
each file in isolation like so:

```sh

python PCA.py

```

Similarly to the setup script, if your server is running using a custom config,
you can specify the config's file path through the command line.

### Principal Component Analysis (PCA)

[Principal component analysis](https://en.wikipedia.org/wiki/Principal_component_analysis)
is a statistical technique which extracts new, linearly uncorrelated,
variables out of a dataset which capture the maximum variance in the
data. In this way, `PCA` can be used to reduce the number of variables
in a high dimensional dataset, a process that is called dimensionality
reduction. The first principal component captures the largest amount of
variance, while the second captures the largest portion of the remaining
variance while remaining orthogonal to the first and so on. This allows the
reduction of the number of dimensions while maintaining as much of the
information from the original data as possible. `PCA` is useful in
exploratory data analysis because complex linear relationships can be
visualized in a 2D scatter plot of the first few principal components.

TabPy’s implementation of `PCA` uses the scikit-learn
[decomposition.PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)
algorithm, which is further documented [here](https://scikit-learn.org/stable/modules/decomposition.html#pca).
In the Tableau script, after the function name `PCA`, you must specify a
principal component to return. This integer input should be > 0 and <= the
number of variables you pass in to the function. When passing categorical
variables we perform the `scikit-learn` [One Hot Encoding](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html)
to transform your non-numeric variables into a one-hot numeric array of 0s and
1s. In order for `One Hot Encoding` to be performant we have limited the number
of unique values your categorical column may contain to 25 and do not permit
any nulls or empty strings in the column. In Tableau's implementation of `PCA`
is performed, all variables are normalized to have a mean of 0 and unit
variance using the `scikit-learn` [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).

A Tableau calculated field to perform PCA will look like:

```python

tabpy.query(‘PCA’, 1, _arg1, _arg2, _arg3)[‘response’]

```

### Sentiment Analysis

[Sentiment analysis](https://en.wikipedia.org/wiki/Sentiment_analysis) is
a technique which uses natural language processing to extract the emotional
positivity or negativity – the sentiment – behind a piece of text and converts
that into a numeric value. Our implementation of `sentiment analysis` returns a
polarity score between -1 and 1 which rates the positivity of the string with
1 being very positive and -1 being very negative. Calling the `Sentiment
Analysis` function from TabPy in Tableau will look like the following,
where \_arg1 is a Tableau dimension containing text

```python

tabpy.query('Sentiment Analysis', _arg1)[‘response’]

```

Python provides multiple packages that compute `sentiment analysis` – our implementation
defaults to use [NLTK’s sentiment package](https://www.nltk.org/api/nltk.sentiment.html).
If you would like to use [TextBlob’s sentiment analysis](https://textblob.readthedocs.io/en/dev/quickstart.html)
algorithm you can do so by specifying the optional argument “library=textblob”
when calling the `Sentiment Analysis` function through a calculated field in
Tableau

```python

tabpy.query('Sentiment Analysis', _arg1, library='textblob')[‘response’]

```

### T-Test

A [t-test](https://en.wikipedia.org/wiki/Student%27s_t-test) is a statistical
hypothesis test that is used to compare two sample means or a sample’s mean against
a known population mean. The ttest should be used when the means of the samples
follows a normal distribution but the variance may not be known.

TabPy’s pre-deployed t-test implementation can be called using the following syntax,

```python

tabpy.query(‘ttest’, _arg1, _arg2)[‘response’]

```

and is capable of performing two types of t-tests:

<!-- markdownlint-disable MD029 -->
1\. [A t-test for the means of two independent samples with equal variance](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html)
This is a two-sided t test with the null hypothesis being that the mean of
sample1 is equal to the mean of sample2.
_arg1 (list of numeric values): a list of independent observations
_arg2 (list of numeric values): a list of independent observations equal to
the length of _arg1

Alternatively, your data may not be split into separate measures. If that is
the case you can pass the following fields to ttest,

_arg1 (list of numeric values): a list of independent observations
_arg2 (list of categorical variables with cardinality two): a binary factor
that maps each observation in _arg1 to either sample1 or sample2 (this list
should be equal to the length of _arg1)

2\. [A t-test for the mean of one group](https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.stats.ttest_1samp.html)
_arg1 (list of numeric values): a list of independent observations
_arg2 (a numeric value): the known population mean
A two-sided t test with the null hypothesis being that the mean of a sample of
independent observations is equal to the given population mean.

The function returns a two-tailed [p-value](https://en.wikipedia.org/wiki/P-value)
(between 0 and 1). Depending on your [significance level](https://en.wikipedia.org/wiki/Statistical_significance)
you may reject or fail to reject the null hypothesis.
<!-- markdownlint-enable MD029 -->

### ANOVA

[Analysis of variance](https://en.wikipedia.org/wiki/Analysis_of_variance)
helps inform if two or more group means within a sample differ. By measuring
the variation between and among groups and computing the resulting F-statistic
we are able to obtain a p-value. While a statistically significant p-value
will inform you that at least 2 of your groups’ means are different from each
other, it will not tell you which of the two groups differ.

You can call ANOVA from tableau in the following way,

```python

tabpy.query(‘anova’, _arg1, _arg2, _arg3)[‘response’]
```

## Providing Schema Metadata

As soon as you share your deployed functions, you also need to share metadata
about the function. The consumer of an endpoint needs to know the details of how
to use the endpoint, such as:

- The general purpose of the endpoint
- Input parameter names, data types, and their meaning
- Return data type and description

This data goes beyond the single string that we used above when deploying the
function `add`. You can use an optional parameter to `deploy` to provide such
a structured description, which can then be retrieved by other users connected
to the same server. The schema is interpreted as a [Json Schema](<http://json-schema.org/documentation.html>)
object, which you can either manually create or generate using a utility
method provided in this tools package:

```python

from tabpy_tools.schema import generate_schema

schema = generate_schema(
  input={'x': 3, 'y': 2},
  output=5,
  input_description={'x': 'first value',
                     'y': 'second value'},
  output_description='the sum of x and y')

  client.deploy('add', add, 'Adds two numbers x and y', schema=schema)

```

To describe more complex input, like arrays, you would use the following syntax:

```python

from tabpy_tools.schema import generate_schema

schema = generate_schema(
  input={'x': [6.35, 6.40, 6.65, 8.60],
         'y': [1.95, 1.95, 2.05, 3.05]},
  output=[0, 0, 0, 1],
  input_description={'x': 'list of x values',
                     'y': 'list of y values'},
  output_description='cluster Ids for each point x, y')

  client.deploy('clustering',
      clustering,
      'Returns cluster Ids for each data point specified by the pairs in x and y',
      schema=schema)

```

A schema described as such can be retrieved through the [REST Endpoints API](server-rest.md#httpget-endpoints)
or through the `get_endpoints` client API as follows:

```python

client.get_endpoints()['add']['schema']

```

## Querying an Endpoint

Once a Python function has been deployed to the server process, you can use the
client's `query` method to query it (assuming that you’re already connected to the
service):

```python

x = [6.35, 6.40, 6.65, 8.60, 8.90, 9.00, 9.10]
y = [1.95, 1.95, 2.05, 3.05, 3.05, 3.10, 3.15]

client.query('clustering', x, y)

```

Response:

```json
{
  'model': 'clustering',
  'response': [0, 0, 0, 1, 1, 1, 1],
  'uuid': '1ca01e46-733c-4a77-b3da-3ded84dff4cd',
  'version': 2
}

```

## Evaluating Arbitrary Python Scripts

The other core functionality aside from deploying and querying methods as endpoints
is the ad-hoc execution of Python code, called `evaluate`. Evaluate does not
have a Python API in `tabpy-tools`, only a raw [REST interface](server-rest.md#httppost-evaluate)
that other client bindings can easily implement. Tableau connects to TabPy
using REST `Evaluate`.

`evaluate` allows calling a deployed endpoint from within the Python code block.
The convention for this is to use a provided function call `tabpy.query` in the
code, which behaves like the `query` method in `tabpy-tools`. See the
[REST API documentation](server-rest.md) for an example.
