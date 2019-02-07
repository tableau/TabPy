# TabPy Tools

TabPy tools is the Python package of tools for managing the published Python functions
on TabPy server.

<!-- toc -->

- [Connecting to TabPy](#connecting-to-tabpy)
- [Deploying a Function](#deploying-a-function)
- [Providing Schema Metadata](#providing-schema-metadata)
- [Querying an Endpoint](#querying-an-endpoint)
- [Evaluating Arbitrary Python Scripts](#evaluating-arbitrary-python-scripts)

<!-- tocstop -->

## Connecting to TabPy

The tools library uses the notion of connecting to a service to avoid having
to specify the service location for all subsequent operations:

```python

from tabpy_tools.client import Client

client = Client('http://localhost:9004/')

```

The URL and port are where the Tableau-Python-Server process has been started -
more info can be found in the [server section](server.md) of the documentation.

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
                'Returns cluster Ids for each data point specified by the pairs in x and y')

```

In this example the function `clustering` expects a set of two-dimensional data
points, represented by the list of all x-coordinates and the list of all y-coordinates.
It will return a set of numerical labels corresponding to the clusters each datapoint
is assigned to. We deploy this function as an endpoint named `clustering`. It is now
reachable as a [REST API](server.md#httppost-queryendpoint), as well as through the
TabPy tools - for details see the next section.

You can re-deploy a function (for example, after you modified its code) by setting
the `override` parameter to `True`:

```python

client.deploy('add', add, 'Adds two numbers x and y', override=True)

```

Each re-deployment of an endpoint will increment its version number, which is also
returned as part of the query result.

When deploying endpoints that rely on supervised learning models, you may want to
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
will also be kept in memory on the server to achieve fast response times. If you
persist your model manually to disk and read as part of your scoring function code
however, you will notice that response times are noticeably longer as every time a
client hits an endpoint, the code (including model loading) will get executed. In
order to get the best performance, we recommended following the methodology outlined
in this example.

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
and publishing steps on [our blog](https://www.tableau.com/about/blog/2017/1/building-advanced-analytics-applications-tabpy-64916).

The endpoints that are no longer needed can be removed the following way:

```python

client.remove('WillItDefault')

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

A schema described as such can be retrieved through the [REST Endpoints API](server.md#httpget-endpoints)
or through the `get_endpoints` client API as follows:

```python

client.get_endpoints()['add']['schema']

```

## Querying an Endpoint

Once a Python function has been deployed to the server process, you can use the
client's `query` method to query it (assumes you’re already connected to the
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

The other core functionality besides deploying and querying methods as endpoints
is the ad-hoc execution of Python code, called `evaluate`. Evaluate does not
have a Python API in `tabpy-tools`, only a raw [REST interface](server.md#httppost-evaluate)
that other client bindings can easily implement. Tableau connects to TabPy
using REST `Evaluate`.

`Evaluate` allows calling a deployed endpoint from within the Python code block.
The convention for this is to use a provided function call `tabpy.query` in the
code, which behaves like the `query` method in `tabpy-tools`. See the
[REST API documentation](server.md#rest-interfaces) for an example.
