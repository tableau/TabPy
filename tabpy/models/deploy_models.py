import os
from pathlib import Path
import platform
import subprocess
import sys
from tabpy.models.utils import setup_utils


def main():
    # Determine if we run python or python3
    py = "python" if platform.system() == "Windows" else "python3"

    file_path = sys.argv[1] if len(sys.argv) > 1 else setup_utils.get_default_config_file_path()
    print(f"Using config file at {file_path}")

    port, auth_on, prefix = setup_utils.parse_config(file_path)
    auth_args = setup_utils.get_creds() if auth_on else []

    directory = str(Path(__file__).resolve().parent / "scripts")
    # Deploy each model in the scripts directory
    for filename in os.listdir(directory):
        subprocess.run([py, f"{directory}/{filename}", file_path] + auth_args)


if __name__ == "__main__":
    main()
