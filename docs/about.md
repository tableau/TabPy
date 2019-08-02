# About TabPy

TabPy framework allows Tableau to remotely execute Python code. It has two components:

1. A process built on Tornado, which allows for the remote execution of Python
   code through a set of [REST APIs](server-rest.md). The code can either be immediately
   executed or persisted in the server process and exposed as a REST endpoint,
   to be called later.

2. A [tools library](tabpy-tools.md),
   based on Python functions which enables the deployment of such endpoints.

Tableau can connect to the TabPy server to execute Python code on the fly and
display results in Tableau visualizations. Users can control data and parameters
being sent to TabPy by interacting with their Tableau worksheets, dashboard or stories.

For how to configure Tableau to connect to TabPy server follow steps in
[Tableau Configuration Document](TableauConfiguration.md).
