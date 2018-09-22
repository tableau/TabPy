import logging
import logging.handlers
import os
import tempfile


# Create application wide logging
logger = logging.getLogger(__name__)
logger.setLevel("INFO")
temp_dir = tempfile.gettempdir()
fh = logging.handlers.RotatingFileHandler(
    filename=os.path.join(temp_dir, "tabpy_log.log"),
    maxBytes=10000000, backupCount=5)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
