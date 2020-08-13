import coverage
import http.client
import os
import platform
import shutil
import signal
import subprocess
import tabpy
import tempfile
import time
import unittest


class IntegTestBase(unittest.TestCase):
    """
    Base class for integration tests.
    """

    def __init__(self, methodName="runTest"):
        super(IntegTestBase, self).__init__(methodName)
        self.process = None
        self.delete_temp_folder = True

    def set_delete_temp_folder(self, delete_temp_folder: bool):
        """
        Specify if temporary folder for state, config and log
        files should be deleted when test is done.
        By default the folder is deleted.

        Parameters
        ----------
        delete_test_folder: bool
            If True temp folder will be deleted.
        """
        self.delete_temp_folder = delete_temp_folder

    def _get_state_file_path(self) -> str:
        """
        Generates state.ini and returns absolute path to it.
        Overwrite this function for tests to run against not default state
        file.

        Returns
        -------
        str
            Absolute path to state file folder.
        """
        state_file = open(os.path.join(self.tmp_dir, "state.ini"), "w+")
        state_file.write(
            "[Service Info]\n"
            "Name = TabPy Serve\n"
            "Description = \n"
            "Creation Time = 0\n"
            "Access-Control-Allow-Origin = \n"
            "Access-Control-Allow-Headers = \n"
            "Access-Control-Allow-Methods = \n"
            "\n"
            "[Query Objects Service Versions]\n"
            "\n"
            "[Query Objects Docstrings]\n"
            "\n"
            "[Meta]\n"
            "Revision Number = 1\n"
        )
        state_file.close()

        return self.tmp_dir

    def _get_port(self) -> str:
        """
        Returns port TabPy should run on. Default implementation
        returns '9004'.

        Returns
        -------
        str
            Port number.
        """
        return "9004"

    def _get_pwd_file(self) -> str:
        """
        Returns absolute or relative path to password file.
        Overwrite to create and/or specify your own file.
        Default implementation returns None which means
        TABPY_PWD_FILE setting won't be added to config.

        Returns
        -------
        str
            Absolute or relative path to password file.
            If None TABPY_PWD_FILE setting won't be added to
            config.
        """
        return None

    def _get_transfer_protocol(self) -> str:
        """
        Returns transfer protocol for configuration file.
        Default implementation returns None which means
        TABPY_TRANSFER_PROTOCOL setting won't be added to config.

        Returns
        -------
        str
            Transfer protocol (e.g 'http' or 'https').
            If None TABPY_TRANSFER_PROTOCOL setting won't be
            added to config.
        """
        return None

    def _get_certificate_file_name(self) -> str:
        """
        Returns absolute or relative certificate file name
        for configuration file.
        Default implementation returns None which means
        TABPY_CERTIFICATE_FILE setting won't be added to config.

        Returns
        -------
        str
            Absolute or relative certificate file name.
            If None TABPY_CERTIFICATE_FILE setting won't be
            added to config.
        """
        return None

    def _get_key_file_name(self) -> str:
        """
        Returns absolute or relative private key file name
        for configuration file.
        Default implementation returns None which means
        TABPY_KEY_FILE setting won't be added to config.

        Returns
        -------
        str
            Absolute or relative private key file name.
            If None TABPY_KEY_FILE setting won't be
            added to config.
        """
        return None

    def _get_evaluate_timeout(self) -> str:
        """
        Returns the configured timeout for the /evaluate method.
        Default implementation returns None, which means that
        the timeout will default to 30.

        Returns
        -------
        str
            Timeout for calling /evaluate.
            If None, defaults TABPY_EVALUATE_TIMEOUT setting
            will default to '30'.
        """
        return None

    def _get_config_file_name(self) -> str:
        """
        Generates config file. Overwrite this function for tests to
        run against not default state file.

        Returns
        -------
        str
            Absolute path to config file.
        """
        config_file = open(os.path.join(self.tmp_dir, "test.conf"), "w+")
        config_file.write(
            "[TabPy]\n"
            f"TABPY_QUERY_OBJECT_PATH = {self.tmp_dir}/query_objects\n"
            f"TABPY_PORT = {self._get_port()}\n"
            f"TABPY_STATE_PATH = {self.tmp_dir}\n"
        )

        pwd_file = self._get_pwd_file()
        if pwd_file is not None:
            pwd_file = os.path.abspath(pwd_file)
            config_file.write(f"TABPY_PWD_FILE = {pwd_file}\n")

        transfer_protocol = self._get_transfer_protocol()
        if transfer_protocol is not None:
            config_file.write(f"TABPY_TRANSFER_PROTOCOL = {transfer_protocol}\n")

        cert_file_name = self._get_certificate_file_name()
        if cert_file_name is not None:
            cert_file_name = os.path.abspath(cert_file_name)
            config_file.write(f"TABPY_CERTIFICATE_FILE = {cert_file_name}\n")

        key_file_name = self._get_key_file_name()
        if key_file_name is not None:
            key_file_name = os.path.abspath(key_file_name)
            config_file.write(f"TABPY_KEY_FILE = {key_file_name}\n")

        evaluate_timeout = self._get_evaluate_timeout()
        if evaluate_timeout is not None:
            config_file.write(f"TABPY_EVALUATE_TIMEOUT = {evaluate_timeout}\n")

        config_file.close()

        self.delete_config_file = True
        return config_file.name

    def setUp(self):
        super(IntegTestBase, self).setUp()
        prefix = "TabPy_IntegTest_"
        self.tmp_dir = tempfile.mkdtemp(prefix=prefix)

        # create temporary state.ini
        orig_state_file_name = os.path.abspath(
            self._get_state_file_path() + "/state.ini"
        )
        self.state_file_name = os.path.abspath(self.tmp_dir + "/state.ini")
        if orig_state_file_name != self.state_file_name:
            shutil.copyfile(orig_state_file_name, self.state_file_name)

        # create config file
        orig_config_file_name = os.path.abspath(self._get_config_file_name())
        self.config_file_name = os.path.abspath(
            self.tmp_dir + "/" + os.path.basename(orig_config_file_name)
        )
        if orig_config_file_name != self.config_file_name:
            shutil.copyfile(orig_config_file_name, self.config_file_name)

        # Platform specific - for integration tests we want to engage
        # startup script
        with open(self.tmp_dir + "/output.txt", "w") as outfile:
            cmd = ["tabpy", "--config=" + self.config_file_name]
            preexec_fn = None
            if platform.system() == "Windows":
                self.py = "python"
            else:
                self.py = "python3"
                preexec_fn = os.setsid

            coverage.process_startup()
            self.process = subprocess.Popen(
                cmd, preexec_fn=preexec_fn, stdout=outfile, stderr=outfile
            )

            # give the app some time to start up...
            time.sleep(5)

    def tearDown(self):
        # stop TabPy
        if self.process is not None:
            if platform.system() == "Windows":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(self.process.pid)])
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.kill()

            # after shutting down TabPy and before we start it again
            # for next test give it some time to terminate.
            time.sleep(5)

        # remove temporary files
        if self.delete_temp_folder:
            os.remove(self.state_file_name)
            os.remove(self.config_file_name)
            shutil.rmtree(self.tmp_dir)

        super(IntegTestBase, self).tearDown()

    def _get_connection(self) -> http.client.HTTPConnection:
        protocol = self._get_transfer_protocol()
        url = "localhost:" + self._get_port()

        if protocol is not None and protocol.lower() == "https":
            connection = http.client.HTTPSConnection(url)
        else:
            connection = http.client.HTTPConnection(url)

        return connection

    def _get_username(self) -> str:
        return "user1"

    def _get_password(self) -> str:
        return "P@ssw0rd"

    def deploy_models(self, username: str, password: str):
        repo_dir = os.path.abspath(os.path.dirname(tabpy.__file__))
        path = os.path.join(repo_dir, "models", "deploy_models.py")
        with open(self.tmp_dir + "/deploy_models_output.txt", "w") as outfile:
            outfile.write(
                f"--<< Running {self.py} {path} "
                f"{self._get_config_file_name()} >>--\n"
            )
            input_string = f"{username}\n{password}\n"
            outfile.write(f"--<< Input = {input_string} >>--")
            coverage.process_startup()
            subprocess.run(
                [self.py, path, self._get_config_file_name()],
                input=input_string.encode("utf-8"),
                stdout=outfile,
                stderr=outfile,
            )

    def _get_process(self):
        return self.process
