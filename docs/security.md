# TabPy Security Considerations

The following security issues should be kept in mind as you use TabPy with Tableau:

- REST server and Python execution context are the same meaning they share
  Python session, e.g. HTTP requests are served in the same space where
  user scripts are evaluated.
- Python scripts can contain code which can harm security on the server where
  the TabPy is running. For example:
  - Access file system (read/write)
  - Install new Python packages which can contain binary code
  - Execute operating system commands
  - Open network connections to other servers and download files
