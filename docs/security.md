# TabPy Security Considerations

The following security issues should be kept in mind as you use TabPy with Tableau:

- TabPy currently does not use authentication.
- Python scripts can contain code which can harm security on the server where the TabPy is running. For example:
  - Access file system (read/write)
  - Install new Python packages which can contain binary code
  - Execute operating system commands
  - Open network connections to other servers and download files
