# TabPy Security Considerations

If security is a significant concern within your organization,
you may want to consider the following as you use TabPy:

- The REST server and Python execution share the same Python session,
  meaning that HTTP requests and user scripts are evaluated in the
  same addressable memory and processor threads.
- The tabpy.tabpy_tools client does not perform client-side validation of the
  SSL certificate on TabPy Server.
- Python scripts can contain code which can harm security on the server
  where the TabPy is running. For example, Python scripts can:
  - Access the file system (read/write).
  - Install new Python packages which can contain binary code.
  - Execute operating system commands.
  - Open network connections to other servers and download files.
- Execution of ad-hoc Python scripts can be disabled by turning off the
  /evaluate endpoint. To disable /evaluate endpoint, set "TABPY_EVALUATE_ENABLE"
  to false in config file.
- Always use the most up-to-date version of Python.
  TabPy relies on Tornado and if older verions of Python are used with Tornado
  then malicious users can potentially poison Python server web caches
  with parameter cloaking.
