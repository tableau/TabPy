# TabPy Frequently Asked Questions

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [Startup Issues](#startup-issues)
  * [AttributeError: module 'tornado.web' has no attribute 'asynchronous'](#attributeerror-module-tornadoweb-has-no-attribute-asynchronous)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## Startup Issues

### AttributeError: module 'tornado.web' has no attribute 'asynchronous'

TabPy uses Tornado 5.1.1. To it to your Python environment run
`pip install tornado==5.1.1` and then try to start TabPy again.
